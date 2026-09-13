"""Generic Canonical persistence core (C1), reusing A2's writer lock."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .source import SourceValidationError
from .vault import ActiveVaultLocator, StaleGenerationError
from .writer import WriterError, shared_writer_lock


@dataclass(frozen=True)
class ObjectRegistration:
    object_type: str
    storage_class: str
    mutability: str
    body_mode: str
    schema_owner: str
    mutable_fields: frozenset[str] = field(default_factory=frozenset)
    specialized: bool = False
    schema_versions: tuple[str, ...] = ("1.0.0",)


class ObjectRegistry:
    def __init__(self):
        self._items: dict[str, ObjectRegistration] = {
            "SOURCE": ObjectRegistration("SOURCE", "CANONICAL", "REVISIONED", "PAYLOAD", "A1/A2", specialized=True)
        }

    def register(self, registration: ObjectRegistration) -> None:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", registration.object_type):
            raise SourceValidationError("invalid object_type")
        if registration.object_type in self._items:
            raise SourceValidationError("object_type already registered")
        if registration.storage_class not in {"CANONICAL", "DERIVED", "RUNTIME_ONLY"}:
            raise SourceValidationError("invalid storage class")
        if registration.mutability not in {"IMMUTABLE", "REVISIONED"} or registration.body_mode not in {"NONE", "INLINE", "PAYLOAD"}:
            raise SourceValidationError("invalid object registration")
        if registration.storage_class == "RUNTIME_ONLY":
            raise SourceValidationError("runtime-only objects are not persistent")
        self._items[registration.object_type] = registration

    def get(self, object_type: str) -> ObjectRegistration | None:
        return self._items.get(object_type)


@dataclass(frozen=True)
class CreateCanonicalIntent:
    object_type: str
    object_id: str
    schema_version: str
    created_at: str
    idempotency_key: str
    manifest_fields: dict[str, object]
    payload: bytes | None = None


@dataclass(frozen=True)
class UpdateCanonicalIntent:
    object_type: str
    object_id: str
    expected_revision: int
    idempotency_key: str
    patch: dict[str, object]


@dataclass(frozen=True)
class CommitResult:
    status: str
    object_type: str
    object_id: str
    revision: int | None = None
    path: Path | None = None
    reason: str = ""


@dataclass(frozen=True)
class IntegrityResult:
    status: str
    object_type: str
    object_id: str
    revision: int | None = None
    path: Path | None = None
    reason: str = ""


class CanonicalStore:
    def __init__(self, locator: ActiveVaultLocator, registry: ObjectRegistry | None = None):
        self.locator = locator
        self.registry = registry or ObjectRegistry()

    def create_canonical(self, intent: CreateCanonicalIntent) -> CommitResult:
        registration = self.registry.get(intent.object_type)
        if registration is None:
            return CommitResult("UNKNOWN_OBJECT_TYPE", intent.object_type, intent.object_id)
        if registration.specialized:
            return CommitResult("SPECIALIZED_WRITER_REQUIRED", intent.object_type, intent.object_id)
        try:
            manifest = self._build_manifest(intent, registration)
            _validate_manifest(manifest, registration, intent.payload)
        except SourceValidationError as exc:
            return CommitResult("VALIDATION_FAILED", intent.object_type, intent.object_id, reason=str(exc))
        if manifest["sensitivity"]["level"] == "RESTRICTED":
            return CommitResult("VALIDATION_FAILED", intent.object_type, intent.object_id, reason="RESTRICTED object requires owner guard")
        fingerprint = _fingerprint(manifest)
        try:
            key_hash = _key_hash(intent.idempotency_key)
        except SourceValidationError as exc:
            return CommitResult("VALIDATION_FAILED", intent.object_type, intent.object_id, reason=str(exc))
        tx_root: Path | None = None
        published = False
        try:
            with shared_writer_lock(self.locator) as handle:
                root = handle.root_ref
                canonical, system = _ensure_layout(root)
                receipt = _receipt_path(system)
                prior = _find_receipt(receipt, intent.object_type, intent.object_id, "create", key_hash)
                if prior:
                    if prior.get("fingerprint") != fingerprint:
                        return CommitResult("IDEMPOTENCY_CONFLICT", intent.object_type, intent.object_id, reason="idempotency key fingerprint differs")
                    return _receipt_result(prior, intent.object_type, intent.object_id, canonical)
                final = _object_path(canonical, intent.object_type, intent.object_id)
                if final.exists() or final.is_symlink():
                    existing = self.inspect_canonical(intent.object_type, intent.object_id)
                    if existing.status == "VALID" and _manifest_at(final) == manifest:
                        return CommitResult("ALREADY_COMMITTED", intent.object_type, intent.object_id, existing.revision, final)
                    return CommitResult("IDEMPOTENCY_CONFLICT", intent.object_type, intent.object_id, reason="existing object differs")
                tx_root = system / "staging" / str(uuid.uuid4())
                staged = tx_root / "object"
                staged.mkdir(parents=True, exist_ok=False, mode=0o700)
                if intent.payload is not None:
                    payload_path = staged / "payload" / "original"
                    payload_path.parent.mkdir(mode=0o700)
                    _write_bytes(payload_path, intent.payload)
                _write_text(staged / "object.md", _serialize_manifest(manifest))
                _validate_manifest(_parse_manifest((staged / "object.md").read_text()), registration, intent.payload)
                self.locator.assert_current(handle)
                final.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                os.rename(staged, final)
                published = True
                _fsync_directory(final.parent)
                checked = self.inspect_canonical(intent.object_type, intent.object_id)
                if checked.status != "VALID":
                    return CommitResult("COMMIT_UNCERTAIN", intent.object_type, intent.object_id, reason="post-publish validation failed")
                _append_receipt(receipt, intent.object_type, intent.object_id, "create", key_hash, fingerprint, 1, manifest["payload"]["sha256"] if "payload" in manifest else None)
                shutil.rmtree(tx_root, ignore_errors=True)
                return CommitResult("COMMITTED_LOCAL", intent.object_type, intent.object_id, 1, final)
        except WriterError as exc:
            return CommitResult(exc.status, intent.object_type, intent.object_id, reason=exc.reason)
        except StaleGenerationError as exc:
            return CommitResult("STALE_GENERATION", intent.object_type, intent.object_id, reason=str(exc))
        except OSError as exc:
            return CommitResult("COMMIT_UNCERTAIN" if published else "IO_FAILED", intent.object_type, intent.object_id, reason=str(exc))
        finally:
            if tx_root is not None and tx_root.exists():
                shutil.rmtree(tx_root, ignore_errors=True)

    def update_canonical(self, intent: UpdateCanonicalIntent) -> CommitResult:
        registration = self.registry.get(intent.object_type)
        if registration is None:
            return CommitResult("UNKNOWN_OBJECT_TYPE", intent.object_type, intent.object_id)
        if registration.specialized or registration.mutability != "REVISIONED":
            return CommitResult("VALIDATION_FAILED", intent.object_type, intent.object_id, reason="object is not revisioned here")
        if isinstance(intent.expected_revision, bool) or not isinstance(intent.expected_revision, int) or set(intent.patch) - registration.mutable_fields:
            return CommitResult("VALIDATION_FAILED", intent.object_type, intent.object_id, reason="patch is not allowed")
        try:
            _validate_id(intent.object_id)
        except SourceValidationError as exc:
            return CommitResult("VALIDATION_FAILED", intent.object_type, intent.object_id, reason=str(exc))
        key_hash = _key_hash(intent.idempotency_key)
        fingerprint = _fingerprint({"expected_revision": intent.expected_revision, "patch": intent.patch})
        try:
            with shared_writer_lock(self.locator) as handle:
                canonical, system = _ensure_layout(handle.root_ref)
                receipt = _receipt_path(system)
                prior = _find_receipt(receipt, intent.object_type, intent.object_id, "update", key_hash)
                if prior:
                    if prior.get("fingerprint") != fingerprint:
                        return CommitResult("IDEMPOTENCY_CONFLICT", intent.object_type, intent.object_id, reason="idempotency key fingerprint differs")
                    return _receipt_result(prior, intent.object_type, intent.object_id, canonical)
                final = _object_path(canonical, intent.object_type, intent.object_id)
                current = self.inspect_canonical(intent.object_type, intent.object_id)
                if current.status != "VALID":
                    return CommitResult("CANONICAL_CORRUPT", intent.object_type, intent.object_id, reason=current.reason)
                from .deletion import NOT_DELETED, DeletionResolver

                deletion = DeletionResolver(self.locator).resolve(intent.object_type, intent.object_id)
                if deletion.state != NOT_DELETED and deletion.reason != "MANIFEST":
                    return CommitResult("DELETED" if deletion.state == "DELETED" else "DELETION_UNKNOWN", intent.object_type, intent.object_id, current.revision, reason=deletion.reason)
                if current.revision != intent.expected_revision:
                    return CommitResult("REVISION_CONFLICT", intent.object_type, intent.object_id, current.revision)
                manifest = _manifest_at(final)
                if manifest["deletion"]["state"] == "TOMBSTONED" and intent.patch.get("deletion", {}).get("state") == "LIVE":
                    return CommitResult("VALIDATION_FAILED", intent.object_type, intent.object_id, current.revision, reason="deleted object cannot be resurrected")
                updated = copy.deepcopy(manifest)
                updated.update(copy.deepcopy(intent.patch))
                if updated["sensitivity"]["level"] == "RESTRICTED":
                    return CommitResult("VALIDATION_FAILED", intent.object_type, intent.object_id, current.revision, reason="RESTRICTED object requires owner guard")
                updated["revision"] += 1
                updated["updated_at"] = _now()
                _validate_manifest(updated, registration, _payload_at(final, registration))
                tx_root = system / "staging" / str(uuid.uuid4())
                staged = tx_root / "object.md"
                staged.parent.mkdir(parents=True, exist_ok=False, mode=0o700)
                _write_text(staged, _serialize_manifest(updated))
                self.locator.assert_current(handle)
                os.replace(staged, final / "object.md")
                _fsync_directory(final)
                checked = self.inspect_canonical(intent.object_type, intent.object_id)
                if checked.status != "VALID":
                    return CommitResult("COMMIT_UNCERTAIN", intent.object_type, intent.object_id, reason="post-replace validation failed")
                _append_receipt(receipt, intent.object_type, intent.object_id, "update", key_hash, fingerprint, updated["revision"])
                return CommitResult("COMMITTED_LOCAL", intent.object_type, intent.object_id, updated["revision"], final)
        except WriterError as exc:
            return CommitResult(exc.status, intent.object_type, intent.object_id, reason=exc.reason)
        except StaleGenerationError as exc:
            return CommitResult("STALE_GENERATION", intent.object_type, intent.object_id, reason=str(exc))
        except (OSError, SourceValidationError) as exc:
            return CommitResult("IO_FAILED", intent.object_type, intent.object_id, reason=str(exc))

    def append_canonical_event(self, intent: CreateCanonicalIntent) -> CommitResult:
        registration = self.registry.get(intent.object_type)
        if registration is None or registration.mutability != "IMMUTABLE":
            return CommitResult("VALIDATION_FAILED", intent.object_type, intent.object_id, reason="event registration required")
        return self.create_canonical(intent)

    def inspect_canonical(self, object_type: str, object_id: str) -> IntegrityResult:
        registration = self.registry.get(object_type)
        if registration is None:
            return IntegrityResult("UNKNOWN_OBJECT_TYPE", object_type, object_id)
        if registration.specialized:
            return IntegrityResult("SPECIALIZED_WRITER_REQUIRED", object_type, object_id)
        try:
            _validate_id(object_id)
            handle = self.locator.resolve_active_vault()
            path = _object_path(handle.root_ref / "canonical", object_type, object_id, create=False)
            if path.is_symlink() or not path.exists():
                return IntegrityResult("MISSING", object_type, object_id, path=path)
            manifest = _parse_manifest((path / "object.md").read_text())
            _validate_manifest(manifest, registration, _payload_at(path, registration))
            return IntegrityResult("VALID", object_type, object_id, manifest["revision"], path)
        except (OSError, SourceValidationError, KeyError, WriterError) as exc:
            return IntegrityResult("CORRUPT", object_type, object_id, reason=str(exc))

    def _build_manifest(self, intent: CreateCanonicalIntent, registration: ObjectRegistration) -> dict[str, object]:
        _validate_id(intent.object_id)
        if intent.schema_version not in registration.schema_versions:
            raise SourceValidationError("unsupported schema version")
        if set(intent.manifest_fields) & {"object_id", "object_type", "schema_version", "created_at", "updated_at", "revision"}:
            raise SourceValidationError("identity fields are writer-owned")
        manifest = copy.deepcopy(intent.manifest_fields)
        if "payload" in manifest:
            raise SourceValidationError("payload integrity is writer-owned")
        if registration.body_mode == "PAYLOAD":
            if not isinstance(intent.payload, bytes):
                raise SourceValidationError("payload bytes are required")
            manifest["payload"] = {
                "path": "payload/original",
                "sha256": hashlib.sha256(intent.payload).hexdigest(),
                "bytes": len(intent.payload),
            }
        manifest.update({
            "object_id": intent.object_id,
            "object_type": intent.object_type,
            "schema_version": intent.schema_version,
            "created_at": intent.created_at,
            "updated_at": intent.created_at,
            "revision": 1,
        })
        return manifest


def _ensure_layout(root: Path) -> tuple[Path, Path]:
    canonical, system = root / "canonical", root / "system"
    for path in (canonical, canonical / "objects", system, system / "staging"):
        if path.is_symlink():
            raise WriterError("FILESYSTEM_UNSUPPORTED", "generic layout contains symlink")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return canonical, system


def _object_path(canonical: Path, object_type: str, object_id: str, *, create: bool = True) -> Path:
    objects = canonical / "objects"
    type_root = objects / object_type
    if objects.is_symlink() or type_root.is_symlink():
        raise WriterError("FILESYSTEM_UNSUPPORTED", "generic object path contains symlink")
    if create:
        type_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return type_root / object_id


def _receipt_path(system: Path) -> Path:
    path = system / "c1-receipts.jsonl"
    if path.is_symlink():
        raise WriterError("FILESYSTEM_UNSUPPORTED", "receipt path is symlink")
    return path


def _validate_manifest(manifest: object, registration: ObjectRegistration, payload: bytes | None) -> None:
    if not isinstance(manifest, dict):
        raise SourceValidationError("manifest must be an object")
    required = {"object_id", "object_type", "schema_version", "created_at", "updated_at", "revision", "scope", "provenance", "trust", "sensitivity", "temporal", "deletion"}
    if not required <= set(manifest):
        raise SourceValidationError("Canonical envelope is incomplete")
    _validate_id(manifest["object_id"])
    if manifest["object_type"] != registration.object_type or manifest["schema_version"] not in registration.schema_versions:
        raise SourceValidationError("manifest registration mismatch")
    for key in ("created_at", "updated_at"):
        _timestamp(manifest[key])
    if isinstance(manifest["revision"], bool) or not isinstance(manifest["revision"], int) or manifest["revision"] < 1:
        raise SourceValidationError("invalid revision")
    _validate_envelope(manifest)
    if registration.body_mode == "PAYLOAD":
        details = manifest.get("payload")
        if not isinstance(details, dict) or set(details) != {"path", "sha256", "bytes"} or details["path"] != "payload/original":
            raise SourceValidationError("payload metadata is required")
        if payload is None or not isinstance(payload, bytes) or details["bytes"] != len(payload) or details["sha256"] != hashlib.sha256(payload).hexdigest():
            raise SourceValidationError("payload integrity mismatch")
    elif "payload" in manifest:
        raise SourceValidationError("payload is not allowed for this registration")


def _validate_envelope(manifest: dict[str, object]) -> None:
    expected = {
        "scope": {"scope_type", "scope_id"},
        "provenance": {"origin", "source_refs", "actor", "explicitness"},
        "trust": {"level", "confidence"},
        "sensitivity": {"level"},
        "temporal": {"valid_from", "valid_until"},
        "deletion": {"state", "tombstoned_at"},
    }
    for key, fields in expected.items():
        value = manifest[key]
        if not isinstance(value, dict) or set(value) != fields:
            raise SourceValidationError("invalid Canonical envelope")
    if manifest["scope"]["scope_type"] != "GLOBAL" or manifest["scope"]["scope_id"] is not None:
        raise SourceValidationError("invalid scope")
    if manifest["provenance"]["origin"] not in {"USER_EXPLICIT", "IMPORTED", "EXTERNAL_SOURCE", "SYSTEM_OBSERVED"}:
        raise SourceValidationError("invalid provenance")
    if not isinstance(manifest["provenance"]["source_refs"], list) or not isinstance(manifest["provenance"]["actor"], str) or not manifest["provenance"]["actor"] or manifest["provenance"]["explicitness"] not in {"EXPLICIT", "IMPORTED", "OBSERVED"}:
        raise SourceValidationError("invalid provenance")
    if manifest["trust"]["level"] not in {"UNTRUSTED", "INFERRED", "ASSERTED", "OBSERVED"} or isinstance(manifest["trust"]["confidence"], bool) or not isinstance(manifest["trust"]["confidence"], (int, float)) or not 0 <= manifest["trust"]["confidence"] <= 1:
        raise SourceValidationError("invalid trust")
    if manifest["sensitivity"]["level"] not in {"PUBLIC", "PERSONAL", "SENSITIVE", "RESTRICTED"}:
        raise SourceValidationError("invalid sensitivity")
    for value in manifest["temporal"].values():
        if value is not None:
            _timestamp(value)
    if manifest["deletion"]["state"] not in {"LIVE", "TOMBSTONED"}:
        raise SourceValidationError("invalid deletion")
    if manifest["deletion"]["tombstoned_at"] is not None:
        _timestamp(manifest["deletion"]["tombstoned_at"])


def _serialize_manifest(manifest: dict[str, object]) -> str:
    return "---\n" + json.dumps(manifest, ensure_ascii=False, indent=2) + "\n---\n"


def _parse_manifest(document: str) -> dict[str, object]:
    if not document.startswith("---\n") or "\n---\n" not in document:
        raise SourceValidationError("invalid manifest frontmatter")
    end = document.find("\n---\n", 4)
    if document[end + 5 :].strip():
        raise SourceValidationError("manifest body is not allowed")
    try:
        value = json.loads(document[4:end])
    except json.JSONDecodeError as exc:
        raise SourceValidationError("invalid manifest JSON") from exc
    if not isinstance(value, dict):
        raise SourceValidationError("manifest must be an object")
    return value


def _manifest_at(path: Path) -> dict[str, object]:
    return _parse_manifest((path / "object.md").read_text())


def _payload_at(path: Path, registration: ObjectRegistration) -> bytes | None:
    if registration.body_mode != "PAYLOAD":
        return None
    payload = path / "payload" / "original"
    if payload.is_symlink() or not payload.exists():
        raise SourceValidationError("payload missing")
    return payload.read_bytes()


def _write_bytes(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _write_text(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _validate_id(value: object) -> None:
    try:
        parsed = uuid.UUID(str(value))
    except (ValueError, AttributeError) as exc:
        raise SourceValidationError("object_id must be UUIDv4") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise SourceValidationError("object_id must be UUIDv4")


def _timestamp(value: object) -> None:
    if not isinstance(value, str):
        raise SourceValidationError("timestamp must be text")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceValidationError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise SourceValidationError("timestamp must include timezone")


def _now() -> str:
    from datetime import timezone

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _key_hash(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise SourceValidationError("idempotency key is required")
    return hashlib.sha256(value.encode()).hexdigest()


def _fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _append_receipt(path: Path, object_type: str, object_id: str, operation: str, key_hash: str, fingerprint: str, revision: int, payload_hash: str | None = None) -> None:
    record = {"object_type": object_type, "object_id": object_id, "operation": operation, "idempotency_key_hash": key_hash, "fingerprint": fingerprint, "revision": revision}
    if payload_hash:
        record["payload_sha256"] = payload_hash
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _find_receipt(path: Path, object_type: str, object_id: str, operation: str, key_hash: str) -> dict[str, object] | None:
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (record.get("object_type"), record.get("object_id"), record.get("operation"), record.get("idempotency_key_hash")) == (object_type, object_id, operation, key_hash):
            return record
    return None


def _receipt_result(record: dict[str, object], object_type: str, object_id: str, canonical: Path) -> CommitResult:
    path = _object_path(canonical, object_type, object_id, create=False)
    if not path.exists() or path.is_symlink():
        return CommitResult("CANONICAL_CORRUPT", object_type, object_id, record.get("revision"), path, "receipt exists but Canonical object is missing")
    return CommitResult("ALREADY_COMMITTED", object_type, object_id, record.get("revision"), path)
