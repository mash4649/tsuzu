"""Monotonic Canonical deletion facts and fail-closed resolution (A6/C3)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from .source import SourceValidationError, parse_source, validate_payload, validate_source
from .vault import ActiveVaultLocator
from .writer import AtomicSourceWriter, WriterError, shared_writer_lock

if TYPE_CHECKING:
    from .index import IndexManager


NOT_DELETED = "NOT_DELETED"
DELETED = "DELETED"
UNKNOWN_FAIL_CLOSED = "UNKNOWN_FAIL_CLOSED"


@dataclass(frozen=True)
class DeletionResolution:
    state: str
    reason: str = ""
    path: Path | None = None


@dataclass(frozen=True)
class DeletionRequest:
    object_type: str
    object_id: str
    expected_revision: int | None
    request_id: str
    idempotency_key: str
    requested_at: str
    actor: str = "USER"
    method: str = "LOCAL_DELETE"
    reason_code: str = "USER_REQUEST"

    @classmethod
    def source(
        cls,
        source_id: str,
        *,
        expected_revision: int,
        request_id: str | None = None,
        idempotency_key: str | None = None,
        requested_at: str | None = None,
    ) -> "DeletionRequest":
        return cls(
            "SOURCE",
            source_id,
            expected_revision,
            request_id or str(uuid.uuid4()),
            idempotency_key or str(uuid.uuid4()),
            requested_at or _now(),
        )


@dataclass(frozen=True)
class DeletionResult:
    status: str
    object_type: str
    object_id: str
    revision: int | None = None
    path: Path | None = None
    reason: str = ""


class DeletionResolver:
    """Resolve ledger-first deletion state and execute Source deletion."""

    def __init__(self, locator: ActiveVaultLocator, writer: AtomicSourceWriter | None = None):
        self.locator = locator
        self.writer = writer or AtomicSourceWriter(locator)

    def resolve_source(self, source_id: str) -> DeletionResolution:
        return self.resolve("SOURCE", source_id)

    def resolve(self, object_type: str, object_id: str) -> DeletionResolution:
        try:
            _validate_target(object_type, object_id)
            handle = self.locator.resolve_active_vault()
            ledger_root = handle.root_ref / "system" / "deletion-ledger"
            if ledger_root.is_symlink() or (ledger_root.exists() and not ledger_root.is_dir()):
                return DeletionResolution(UNKNOWN_FAIL_CLOSED, "DELETION_LEDGER_UNAVAILABLE")
            type_root = ledger_root / object_type
            if type_root.is_symlink() or (type_root.exists() and not type_root.is_dir()):
                return DeletionResolution(UNKNOWN_FAIL_CLOSED, "DELETION_LEDGER_UNAVAILABLE")
            record_path = type_root / f"{object_id}.md"
            if record_path.is_symlink():
                return DeletionResolution(UNKNOWN_FAIL_CLOSED, "DELETION_LEDGER_CORRUPT", record_path)
            if record_path.exists():
                try:
                    record = _read_record(record_path)
                    _validate_record(record, object_type, object_id)
                except (OSError, SourceValidationError, KeyError, TypeError, ValueError):
                    return DeletionResolution(UNKNOWN_FAIL_CLOSED, "DELETION_LEDGER_CORRUPT", record_path)
                return DeletionResolution(DELETED, "DELETION_LEDGER", record_path)
            return self._resolve_manifest(object_type, object_id, handle.root_ref)
        except (OSError, SourceValidationError, KeyError, TypeError, ValueError):
            return DeletionResolution(UNKNOWN_FAIL_CLOSED, "DELETION_LEDGER_UNAVAILABLE")

    def delete_source(self, request: DeletionRequest, *, index: "IndexManager | None" = None) -> DeletionResult:
        if request.object_type != "SOURCE":
            return DeletionResult("VALIDATION_FAILED", request.object_type, request.object_id, reason="SOURCE request required")
        try:
            _validate_request(request)
        except SourceValidationError as exc:
            return DeletionResult("VALIDATION_FAILED", request.object_type, request.object_id, reason=str(exc))
        source_id = request.object_id
        try:
            with shared_writer_lock(self.locator) as handle:
                root = handle.root_ref
                source_path = root / "canonical" / "sources" / source_id
                current = _read_source(source_path, source_id)
                if current["deletion"]["state"] == "TOMBSTONED":
                    return DeletionResult("ALREADY_DELETED", "SOURCE", source_id, current["revision"], source_path)
                if current["revision"] != request.expected_revision:
                    return DeletionResult("REVISION_CONFLICT", "SOURCE", source_id, current["revision"], source_path)
                ledger_path = _ledger_path(root, "SOURCE", source_id)
                if ledger_path.exists():
                    try:
                        _validate_record(_read_record(ledger_path), "SOURCE", source_id)
                    except (OSError, SourceValidationError, KeyError, TypeError, ValueError) as exc:
                        return DeletionResult("DELETION_LEDGER_CONFLICT", "SOURCE", source_id, current["revision"], ledger_path, str(exc))
                    return DeletionResult("ALREADY_DELETED", "SOURCE", source_id, current["revision"], ledger_path)
                record = _source_record(current, request)
                _atomic_record_write(root, ledger_path, record)
                _validate_record(_read_record(ledger_path), "SOURCE", source_id)
        except WriterError as exc:
            return DeletionResult(exc.status, "SOURCE", source_id, reason=exc.reason)
        except (OSError, SourceValidationError) as exc:
            return DeletionResult("IO_FAILED", "SOURCE", source_id, reason=str(exc))

        try:
            tombstoned_at = record["deleted_at"]
            updated = self.writer.update_source_metadata(
                source_id,
                expected_revision=request.expected_revision,
                patch={"deletion": {"state": "TOMBSTONED", "tombstoned_at": tombstoned_at}},
            )
        except WriterError as exc:
            return DeletionResult("DELETED_PENDING_RECONCILE", "SOURCE", source_id, request.expected_revision, reason=exc.reason)
        if updated.status not in {"COMMITTED_LOCAL", "ALREADY_COMMITTED"}:
            return DeletionResult("DELETED_PENDING_RECONCILE", "SOURCE", source_id, updated.revision, updated.path, updated.status)
        if index is not None:
            try:
                index.upsert_source(source_id)
            except Exception as exc:  # deletion truth must not roll back on derived failure
                return DeletionResult("DELETED_INDEX_PENDING", "SOURCE", source_id, updated.revision, updated.path, str(exc))
        return DeletionResult("DELETED", "SOURCE", source_id, updated.revision, updated.path)

    def reconcile_source(self, source_id: str) -> DeletionResult:
        state = self.resolve_source(source_id)
        if state.state != DELETED:
            return DeletionResult(state.state, "SOURCE", source_id, reason=state.reason)
        try:
            handle = self.locator.resolve_active_vault()
            source_path = handle.root_ref / "canonical" / "sources" / source_id
            manifest = _read_source(source_path, source_id)
            if manifest["deletion"]["state"] == "TOMBSTONED":
                return DeletionResult("ALREADY_DELETED", "SOURCE", source_id, manifest["revision"], source_path)
            result = self.writer.update_source_metadata(
                source_id,
                expected_revision=manifest["revision"],
                patch={"deletion": {"state": "TOMBSTONED", "tombstoned_at": _record_deleted_at(self.locator, source_id)}},
            )
            return DeletionResult(result.status, "SOURCE", source_id, result.revision, result.path, result.reason)
        except (OSError, SourceValidationError, WriterError) as exc:
            return DeletionResult("DELETED_PENDING_RECONCILE", "SOURCE", source_id, reason=str(exc))

    def purge_source_payload(self, source_id: str) -> DeletionResult:
        """Best-effort active-store purge after the ledger is durable."""
        state = self.resolve_source(source_id)
        if state.state != DELETED:
            return DeletionResult(state.state, "SOURCE", source_id, reason=state.reason)
        try:
            root = self.locator.resolve_active_vault().root_ref
            payload = root / "canonical" / "sources" / source_id / "payload" / "original"
            if payload.is_symlink():
                return DeletionResult("PURGE_FAILED", "SOURCE", source_id, reason="payload is symlink")
            if payload.exists():
                payload.unlink()
                _fsync_dir(payload.parent)
            return DeletionResult("PURGED", "SOURCE", source_id)
        except OSError as exc:
            return DeletionResult("PURGE_FAILED", "SOURCE", source_id, reason=str(exc))

    def _resolve_manifest(self, object_type: str, object_id: str, root: Path) -> DeletionResolution:
        if object_type == "SOURCE":
            path = root / "canonical" / "sources" / object_id
            try:
                manifest = _read_source(path, object_id)
            except (OSError, SourceValidationError):
                return DeletionResolution(UNKNOWN_FAIL_CLOSED, "SOURCE_UNAVAILABLE", path)
        else:
            path = root / "canonical" / "objects" / object_type / object_id
            if path.is_symlink() or not path.exists():
                return DeletionResolution(UNKNOWN_FAIL_CLOSED, "OBJECT_UNAVAILABLE", path)
            try:
                manifest = _read_manifest(path / "object.md")
            except (OSError, SourceValidationError):
                return DeletionResolution(UNKNOWN_FAIL_CLOSED, "OBJECT_CORRUPT", path)
        deletion = manifest.get("deletion")
        if not isinstance(deletion, dict) or deletion.get("state") not in {"LIVE", "TOMBSTONED"}:
            return DeletionResolution(UNKNOWN_FAIL_CLOSED, "OBJECT_DELETION_UNKNOWN", path)
        return DeletionResolution(DELETED if deletion["state"] == "TOMBSTONED" else NOT_DELETED, "MANIFEST", path)


def _source_record(manifest: dict[str, object], request: DeletionRequest) -> dict[str, object]:
    source = manifest["source"]
    return {
        "record_type": "DELETION_RECORD",
        "ledger_schema_version": "1.0.0",
        "record_id": str(uuid.uuid4()),
        "target": {"object_type": "SOURCE", "object_id": request.object_id},
        "deleted_at": request.requested_at,
        "deleted_by": {"actor": request.actor, "method": request.method},
        "source_snapshot": {
            "revision_at_delete": manifest["revision"],
            "payload_sha256": source["payload_sha256"],
            "schema_version": manifest["schema_version"],
        },
        "request": {
            "request_id": request.request_id,
            "idempotency_key_hash": hashlib.sha256(request.idempotency_key.encode()).hexdigest(),
        },
        "reason_code": request.reason_code,
    }


def _ledger_path(root: Path, object_type: str, object_id: str) -> Path:
    ledger_root = root / "system" / "deletion-ledger"
    for path in (root / "system", ledger_root, ledger_root / object_type):
        if path.is_symlink():
            raise WriterError("FILESYSTEM_UNSUPPORTED", "deletion ledger path contains symlink")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return ledger_root / object_type / f"{object_id}.md"


def _atomic_record_write(root: Path, destination: Path, record: dict[str, object]) -> None:
    if destination.exists() or destination.is_symlink():
        raise SourceValidationError("deletion ledger already exists")
    staging = root / "system" / "staging" / f"deletion-{uuid.uuid4()}"
    staging.mkdir(parents=True, exist_ok=False, mode=0o700)
    try:
        staged = staging / "record.md"
        _write_text(staged, _serialize_record(record))
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.replace(staged, destination)
        _fsync_dir(destination.parent)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _read_record(path: Path) -> dict[str, object]:
    document = path.read_text(encoding="utf-8")
    if not document.startswith("---\n") or "\n---\n" not in document:
        raise SourceValidationError("invalid deletion record")
    end = document.find("\n---\n", 4)
    if document[end + 5 :].strip():
        raise SourceValidationError("deletion record body is not allowed")
    value = json.loads(document[4:end])
    if not isinstance(value, dict):
        raise SourceValidationError("deletion record must be an object")
    return value


def _validate_record(record: dict[str, object], object_type: str, object_id: str) -> None:
    required = {"record_type", "ledger_schema_version", "record_id", "target", "deleted_at", "deleted_by", "request", "reason_code"}
    if not required <= set(record) or record["record_type"] != "DELETION_RECORD" or record["ledger_schema_version"] not in {"1.0.0", "2.0.0"}:
        raise SourceValidationError("invalid deletion record envelope")
    if record["target"] != {"object_type": object_type, "object_id": object_id}:
        raise SourceValidationError("deletion target mismatch")
    _validate_uuid(record["record_id"])
    _timestamp(record["deleted_at"])
    deleted_by = record["deleted_by"]
    if not isinstance(deleted_by, dict) or deleted_by.get("actor") not in {"USER", "SYSTEM_ALLOWED"} or not isinstance(deleted_by.get("method"), str) or not deleted_by["method"]:
        raise SourceValidationError("invalid deletion actor")
    request = record["request"]
    if not isinstance(request, dict) or set(request) != {"request_id", "idempotency_key_hash"}:
        raise SourceValidationError("invalid deletion request")
    _validate_uuid(request["request_id"])
    if not isinstance(request["idempotency_key_hash"], str) or len(request["idempotency_key_hash"]) != 64:
        raise SourceValidationError("invalid deletion idempotency hash")
    if object_type == "SOURCE":
        snapshot = record.get("source_snapshot") or record.get("snapshot")
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("revision_at_delete"), int) or not isinstance(snapshot.get("payload_sha256"), str) or len(snapshot["payload_sha256"]) != 64:
            raise SourceValidationError("invalid Source deletion snapshot")


def _read_source(path: Path, source_id: str) -> dict[str, object]:
    if path.is_symlink() or (path / "source.md").is_symlink() or (path / "payload" / "original").is_symlink():
        raise SourceValidationError("Source path contains symlink")
    manifest = parse_source((path / "source.md").read_text())
    validate_source(manifest, expected_object_id=source_id)
    if not validate_payload(manifest, (path / "payload" / "original").read_bytes()):
        raise SourceValidationError("Source payload integrity mismatch")
    return manifest


def _read_manifest(path: Path) -> dict[str, object]:
    document = path.read_text(encoding="utf-8")
    if not document.startswith("---\n") or "\n---\n" not in document:
        raise SourceValidationError("invalid object manifest")
    value = json.loads(document[4 : document.find("\n---\n", 4)])
    if not isinstance(value, dict):
        raise SourceValidationError("invalid object manifest")
    return value


def _validate_request(request: DeletionRequest) -> None:
    _validate_target(request.object_type, request.object_id)
    if request.expected_revision is None or isinstance(request.expected_revision, bool) or not isinstance(request.expected_revision, int) or request.expected_revision < 1:
        raise SourceValidationError("expected_revision is required")
    _validate_uuid(request.request_id)
    if not isinstance(request.idempotency_key, str) or not request.idempotency_key:
        raise SourceValidationError("idempotency_key is required")
    _timestamp(request.requested_at)
    if request.actor not in {"USER", "SYSTEM_ALLOWED"} or not request.method:
        raise SourceValidationError("invalid deletion actor")


def _validate_target(object_type: str, object_id: str) -> None:
    if not isinstance(object_type, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", object_type):
        raise SourceValidationError("invalid object type")
    _validate_uuid(object_id)


def _validate_uuid(value: object) -> None:
    try:
        parsed = uuid.UUID(str(value))
    except (ValueError, AttributeError) as exc:
        raise SourceValidationError("UUIDv4 is required") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise SourceValidationError("UUIDv4 is required")


def _serialize_record(record: dict[str, object]) -> str:
    return "---\n" + json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n---\n"


def _write_text(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _timestamp(value: object) -> None:
    if not isinstance(value, str):
        raise SourceValidationError("timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceValidationError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise SourceValidationError("timestamp timezone is required")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _record_deleted_at(locator: ActiveVaultLocator, source_id: str) -> str:
    state = locator.resolve_active_vault().root_ref / "system" / "deletion-ledger" / "SOURCE" / f"{source_id}.md"
    return _read_record(state)["deleted_at"]
