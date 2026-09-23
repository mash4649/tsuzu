"""Import Tauri capture drafts through the existing A3/A4 Core path."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from .capture import CaptureRequest, CaptureService, CaptureStatus
from .index import IndexManager
from .source import SourceValidationError, parse_source, validate_payload
from .vault import ActiveVaultLocator
from .worker import SingleWriterWorker, WorkerStatus
from .writer import AtomicSourceWriter


_LAYOUT = '{"format":"tsuzu-capture-draft-v1"}'


class DesktopIngressStatus:
    QUEUED = "QUEUED"
    ALREADY_QUEUED = "ALREADY_QUEUED"
    COMMITTED = "COMMITTED"
    ALREADY_COMMITTED = "ALREADY_COMMITTED"
    REJECTED_RESTRICTED = "REJECTED_RESTRICTED"
    REJECTED_INVALID_DRAFT = "REJECTED_INVALID_DRAFT"
    PAUSED = "PAUSED"
    IDLE = "IDLE"


@dataclass(frozen=True)
class DesktopIngressResult:
    status: str
    draft_id: str | None = None
    job_id: str | None = None
    source_id: str | None = None
    reason: str = ""


class DesktopDraftIngress:
    """Treat app-local Tauri files as untrusted ingress, never Canonical state."""

    def __init__(self, app_local_root: str | os.PathLike[str], queue_root: str | os.PathLike[str], locator: ActiveVaultLocator, index: IndexManager):
        self.draft_root = Path(app_local_root) / "capture-drafts"
        self.queue_root = Path(queue_root)
        self.locator = locator
        self.index = index

    def submit(self, draft_id: str) -> DesktopIngressResult:
        try:
            manifest, payload, source_root = self._read_draft(draft_id)
            receipt = self._draft_receipt(source_root, draft_id, manifest["source"]["payload_sha256"])
            if receipt is not None:
                source_id = receipt["source_id"]
                if AtomicSourceWriter(self.locator).inspect_source(source_id).status == "VALID":
                    return DesktopIngressResult(DesktopIngressStatus.ALREADY_COMMITTED, draft_id, source_id=source_id)
            request = CaptureRequest(
                request_id=_uuid4(f"tsuzu-desktop-request/v1/{draft_id}"),
                idempotency_key=f"tsuzu-desktop-draft/v1/{draft_id}",
                kind="TEXT",
                content=payload,
                requested_at=manifest["source"]["captured_at"],
                capture_method="LOCAL_TEXT",
            )
            captured = CaptureService(self.queue_root).capture(request)
        except (OSError, ValueError, KeyError, SourceValidationError, json.JSONDecodeError) as exc:
            return DesktopIngressResult(DesktopIngressStatus.REJECTED_INVALID_DRAFT, draft_id, reason=str(exc))
        if captured.status == CaptureStatus.ACCEPTED:
            return DesktopIngressResult(DesktopIngressStatus.QUEUED, draft_id, captured.job_id, captured.source_id)
        if captured.status == CaptureStatus.ALREADY_ACCEPTED:
            return DesktopIngressResult(DesktopIngressStatus.ALREADY_QUEUED, draft_id, captured.job_id, captured.source_id)
        if captured.status == CaptureStatus.REJECTED_RESTRICTED:
            return DesktopIngressResult(DesktopIngressStatus.REJECTED_RESTRICTED, draft_id, reason=captured.reason)
        return DesktopIngressResult(DesktopIngressStatus.PAUSED, draft_id, captured.job_id, captured.source_id, captured.reason)

    def materialize(self) -> DesktopIngressResult:
        worker = SingleWriterWorker(self.queue_root, self.locator)
        while True:
            result = worker.run_once()
            if result.status == WorkerStatus.IDLE:
                break
            if result.status not in {WorkerStatus.COMMITTED, WorkerStatus.ALREADY_COMMITTED, WorkerStatus.BLOCKED_RESTRICTED}:
                return DesktopIngressResult(DesktopIngressStatus.PAUSED, job_id=result.job_id, source_id=result.source_id, reason=result.reason)
        reconciled = self.reconcile()
        return reconciled[0] if reconciled else DesktopIngressResult(DesktopIngressStatus.IDLE)

    def process_all(self) -> tuple[DesktopIngressResult, ...]:
        submitted = tuple(self.submit(draft_id) for draft_id in self._draft_ids())
        materialized = self.materialize()
        return submitted + (() if materialized.status == DesktopIngressStatus.IDLE else (materialized,))

    def reconcile(self) -> tuple[DesktopIngressResult, ...]:
        results = []
        writer = AtomicSourceWriter(self.locator)
        for draft_id in self._draft_ids():
            try:
                manifest, _, source_root = self._read_draft(draft_id)
                existing = self._draft_receipt(source_root, draft_id, manifest["source"]["payload_sha256"])
                if existing is not None:
                    continue
                receipt = self._core_receipt(draft_id)
                if receipt is None or receipt.get("terminal_state") != "COMMITTED":
                    continue
                source_id = receipt.get("source_id")
                if not isinstance(source_id, str) or writer.inspect_source(source_id).status != "VALID":
                    continue
                self.index.upsert_source(source_id)
                self._write_receipt(source_root, draft_id, receipt, manifest["source"]["payload_sha256"])
                results.append(DesktopIngressResult(DesktopIngressStatus.COMMITTED, draft_id, receipt["job_id"], source_id))
            except (OSError, ValueError, KeyError, SourceValidationError, json.JSONDecodeError):
                continue
        return tuple(results)

    def _draft_ids(self) -> tuple[str, ...]:
        try:
            self._check_layout()
            sources = self.draft_root / "sources"
            if sources.is_symlink() or not sources.is_dir():
                return ()
            return tuple(path.name for path in sorted(sources.iterdir()) if path.is_dir() and not path.is_symlink() and _is_uuid4(path.name))
        except OSError:
            return ()

    def _read_draft(self, draft_id: str):
        if not _is_uuid4(draft_id):
            raise ValueError("invalid draft identity")
        self._check_layout()
        source_root = self.draft_root / "sources" / draft_id
        manifest_path = source_root / "source.md"
        payload_path = source_root / "payload" / "original"
        if source_root.is_symlink() or manifest_path.is_symlink() or payload_path.is_symlink():
            raise ValueError("draft path is symlink")
        manifest = parse_source(manifest_path.read_text())
        if manifest["object_id"] != draft_id or not _is_tauri_text_draft(manifest):
            raise ValueError("unsupported Tauri draft")
        payload = payload_path.read_bytes()
        if not validate_payload(manifest, payload):
            raise ValueError("draft payload integrity mismatch")
        return manifest, payload, source_root

    def _check_layout(self) -> None:
        marker = self.draft_root / "layout.json"
        if self.draft_root.is_symlink() or marker.is_symlink() or marker.read_text() != _LAYOUT:
            raise ValueError("untrusted capture-draft layout")

    def _core_receipt(self, draft_id: str) -> dict[str, object] | None:
        key_hash = hashlib.sha256(f"tsuzu-desktop-draft/v1/{draft_id}".encode()).hexdigest()
        path = self.queue_root / "receipts" / f"{key_hash}.json"
        if path.is_symlink() or not path.exists():
            return None
        receipt = json.loads(path.read_text())
        return receipt if receipt.get("idempotency_key_hash") == key_hash else None

    @staticmethod
    def _draft_receipt(source_root: Path, draft_id: str, payload_sha256: str) -> dict[str, object] | None:
        path = source_root / "core-receipt.json"
        if path.is_symlink() or not path.exists():
            return None
        receipt = json.loads(path.read_text())
        if (
            receipt.get("receipt_schema_version") != "1.0.0"
            or receipt.get("draft_id") != draft_id
            or receipt.get("payload_sha256") != payload_sha256
            or not isinstance(receipt.get("source_id"), str)
        ):
            raise ValueError("invalid Core receipt")
        return receipt

    @staticmethod
    def _write_receipt(source_root: Path, draft_id: str, core: dict[str, object], payload_sha256: str) -> None:
        record = {
            "receipt_schema_version": "1.0.0",
            "draft_id": draft_id,
            "job_id": core["job_id"],
            "source_id": core["source_id"],
            "canonical_revision": core["canonical_revision"],
            "payload_sha256": payload_sha256,
        }
        path = source_root / "core-receipt.json"
        fd, staged_name = tempfile.mkstemp(prefix=".core-receipt.", suffix=".tmp", dir=source_root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(record, stream, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(staged_name, path)
        finally:
            if os.path.exists(staged_name):
                os.unlink(staged_name)


def _is_uuid4(value: object) -> bool:
    try:
        parsed = uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return False
    return parsed.version == 4 and str(parsed) == value


def _uuid4(value: str) -> str:
    raw = bytearray(hashlib.sha256(value.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))


def _is_tauri_text_draft(manifest: dict[str, object]) -> bool:
    return (
        manifest["revision"] == 1
        and manifest["created_at"] == manifest["updated_at"] == manifest["source"]["captured_at"]
        and manifest["scope"] == {"scope_type": "GLOBAL", "scope_id": None}
        and manifest["provenance"] == {"origin": "USER_EXPLICIT", "source_refs": [], "actor": "USER", "explicitness": "EXPLICIT"}
        and manifest["trust"] == {"level": "ASSERTED", "confidence": 1}
        and manifest["sensitivity"] == {"level": "PERSONAL"}
        and manifest["temporal"] == {"valid_from": None, "valid_until": None}
        and manifest["deletion"] == {"state": "LIVE", "tombstoned_at": None}
        and manifest["source"]["kind"] == "TEXT"
        and manifest["source"]["capture_method"] == "LOCAL_TEXT"
        and manifest["source"]["origin_locator"] == {"type": "NONE", "value": None}
        and manifest["source"]["original_name"] is None
    )
