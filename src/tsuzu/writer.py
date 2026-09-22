"""Single-writer, directory-atomic Canonical Source persistence (A2)."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from .source import (
    SourceValidationError,
    create_source as build_source,
    parse_source,
    serialize_source,
    update_source_metadata as patch_source,
    validate_payload,
    validate_source,
)
from .vault import ActiveVaultLocator, StaleGenerationError, VaultHandle


@dataclass(frozen=True)
class WriteResult:
    status: str
    source_id: str
    revision: int | None = None
    path: Path | None = None
    reason: str = ""


@dataclass(frozen=True)
class InspectResult:
    status: str
    source_id: str
    revision: int | None = None
    path: Path | None = None
    reason: str = ""


@dataclass(frozen=True)
class RecoveryReport:
    removed: int = 0
    quarantined: int = 0


class WriterError(RuntimeError):
    def __init__(self, status: str, reason: str = ""):
        super().__init__(reason or status)
        self.status = status
        self.reason = reason


class AtomicSourceWriter:
    def __init__(
        self,
        locator: ActiveVaultLocator,
        *,
        failure_injector: Callable[[str], None] | None = None,
    ):
        self.locator = locator
        self.failure_injector = failure_injector

    def create_source(
        self,
        payload: bytes | str,
        *,
        kind: str,
        capture_method: str,
        object_id: str | None = None,
        created_at: str | None = None,
        original_name: str | None = None,
        origin_locator: dict[str, object] | None = None,
        sensitivity: str = "PERSONAL",
        provenance: dict[str, object] | None = None,
        import_metadata: dict[str, object] | None = None,
    ) -> WriteResult:
        source_id = object_id or ""
        try:
            manifest = build_source(
                payload,
                kind=kind,
                capture_method=capture_method,
                object_id=object_id,
                original_name=original_name,
                origin_locator=origin_locator,
                sensitivity=sensitivity,
                captured_at=created_at,
                provenance=provenance,
                import_metadata=import_metadata,
            )
        except SourceValidationError as exc:
            return WriteResult("VALIDATION_FAILED", source_id, reason=str(exc))
        source_id = manifest["object_id"]
        if manifest["sensitivity"]["level"] == "RESTRICTED":
            return WriteResult("VALIDATION_FAILED", source_id, reason="RESTRICTED Source requires A3 guard")

        try:
            with self._locked() as handle:
                canonical = self._canonical_root(handle)
                system = self._system_root(handle)
                self._ensure_layout(canonical, system)
                final = canonical / "sources" / source_id
                if final.exists() or final.is_symlink():
                    existing = self._inspect_path(final, source_id)
                    if existing.status == "VALID" and self._same_create_intent(existing.path, manifest):
                        return WriteResult("ALREADY_COMMITTED", source_id, existing.revision, final)
                    return WriteResult("OBJECT_ID_COLLISION", source_id, reason="existing Source differs")

                tx_root = system / "staging" / str(uuid.uuid4())
                create_dir = tx_root / "create"
                payload_path = create_dir / "payload" / "original"
                payload_path.parent.mkdir(parents=True, exist_ok=False, mode=0o700)
                self._write_bytes(payload_path, _as_bytes(payload))
                self._failure("payload_synced")
                validate_source(manifest)
                if not validate_payload(manifest, _as_bytes(payload)):
                    raise WriterError("VALIDATION_FAILED", "payload integrity mismatch")
                self._write_text(create_dir / "source.md", serialize_source(manifest))
                self._failure("manifest_synced")
                validate_source(parse_source((create_dir / "source.md").read_text()))
                self._failure("validated")
                self.locator.assert_current(handle)
                self._failure("before_publish")
                final.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                os.rename(create_dir, final)
                self._failure("after_publish")
                self._fsync_directory(final.parent)
                checked = self._inspect_path(final, source_id)
                if checked.status != "VALID":
                    return WriteResult("COMMIT_UNCERTAIN", source_id, reason="post-publish validation failed")
                shutil.rmtree(tx_root, ignore_errors=True)
                return WriteResult("COMMITTED_LOCAL", source_id, 1, final)
        except WriterError as exc:
            self._cleanup_tx(tx_root if "tx_root" in locals() else None)
            return WriteResult(exc.status, source_id, reason=exc.reason)
        except (OSError, SourceValidationError, StaleGenerationError) as exc:
            self._cleanup_tx(tx_root if "tx_root" in locals() else None)
            status = "STALE_GENERATION" if isinstance(exc, StaleGenerationError) else "COMMIT_UNCERTAIN" if "final" in locals() and final.exists() else "IO_FAILED"
            return WriteResult(status, source_id, reason=str(exc))

    def update_source_metadata(
        self, source_id: str, *, expected_revision: int, patch: dict[str, object]
    ) -> WriteResult:
        try:
            _validate_source_id(source_id)
        except SourceValidationError as exc:
            raise WriterError("VALIDATION_FAILED", str(exc)) from exc
        try:
            with self._locked() as handle:
                canonical = self._canonical_root(handle)
                system = self._system_root(handle)
                final = canonical / "sources" / source_id
                current = self._inspect_path(final, source_id)
                if current.status != "VALID":
                    return WriteResult("CANONICAL_CORRUPT", source_id, reason=current.reason)
                if current.revision != expected_revision:
                    return WriteResult("REVISION_CONFLICT", source_id, current.revision)
                manifest = parse_source((final / "source.md").read_text())
                try:
                    updated = patch_source(manifest, expected_revision=expected_revision, **patch)
                except SourceValidationError as exc:
                    raise WriterError("VALIDATION_FAILED", str(exc)) from exc
                if updated["sensitivity"]["level"] == "RESTRICTED":
                    return WriteResult("VALIDATION_FAILED", source_id, reason="RESTRICTED Source requires A3 guard")
                tx_root = system / "staging" / str(uuid.uuid4())
                update_dir = tx_root / "update"
                update_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
                staged_manifest = update_dir / "source.md"
                self._write_text(staged_manifest, serialize_source(updated))
                self._failure("manifest_synced")
                validate_source(parse_source(staged_manifest.read_text()))
                if not validate_payload(updated, (final / "payload/original").read_bytes()):
                    return WriteResult("CANONICAL_CORRUPT", source_id, current.revision, reason="payload integrity mismatch")
                latest = self._inspect_path(final, source_id)
                if latest.status != "VALID" or latest.revision != expected_revision:
                    return WriteResult("CANONICAL_CHANGED_EXTERNALLY", source_id, latest.revision)
                self.locator.assert_current(handle)
                self._failure("before_replace")
                replaced = False
                os.replace(staged_manifest, final / "source.md")
                replaced = True
                self._failure("after_replace")
                self._fsync_directory(final)
                checked = self._inspect_path(final, source_id)
                if checked.status != "VALID":
                    return WriteResult("COMMIT_UNCERTAIN", source_id, reason="post-replace validation failed")
                shutil.rmtree(tx_root, ignore_errors=True)
                return WriteResult("COMMITTED_LOCAL", source_id, updated["revision"], final)
        except WriterError:
            raise
        except StaleGenerationError as exc:
            return WriteResult("STALE_GENERATION", source_id, reason=str(exc))
        except OSError as exc:
            return WriteResult("COMMIT_UNCERTAIN" if "replaced" in locals() and replaced else "IO_FAILED", source_id, reason=str(exc))

    def inspect_source(self, source_id: str) -> InspectResult:
        try:
            _validate_source_id(source_id)
            handle = self.locator.resolve_active_vault()
            return self._inspect_path(self._canonical_root(handle) / "sources" / source_id, source_id)
        except (SourceValidationError, OSError) as exc:
            return InspectResult("CORRUPT", source_id, reason=str(exc))

    def recover_staging(self) -> RecoveryReport:
        with self._locked() as handle:
            system = self._system_root(handle)
            staging_root = system / "staging"
            quarantine = system / "quarantine"
            removed = quarantined = 0
            if not staging_root.exists():
                return RecoveryReport()
            for tx_root in list(staging_root.iterdir()):
                if tx_root.is_symlink():
                    tx_root.unlink()
                    removed += 1
                    continue
                create_dir = tx_root / "create"
                source_id = self._staged_source_id(create_dir)
                final = self._canonical_root(handle) / "sources" / source_id if source_id else None
                if final and final.exists():
                    staged = self._inspect_path(create_dir, source_id)
                    existing = self._inspect_path(final, source_id)
                    if staged.status == existing.status == "VALID" and self._same_create_intent(staged.path, parse_source((final / "source.md").read_text())):
                        shutil.rmtree(tx_root, ignore_errors=True)
                        removed += 1
                        continue
                    quarantine.mkdir(parents=True, exist_ok=True, mode=0o700)
                    os.rename(tx_root, quarantine / tx_root.name)
                    quarantined += 1
                else:
                    shutil.rmtree(tx_root, ignore_errors=True)
                    removed += 1
            return RecoveryReport(removed, quarantined)

    @contextlib.contextmanager
    def _locked(self) -> Iterator[VaultHandle]:
        with shared_writer_lock(self.locator) as handle:
            yield handle

    def _canonical_root(self, handle: VaultHandle | None = None) -> Path:
        handle = handle or self.locator.resolve_active_vault()
        return handle.root_ref / "canonical"

    def _system_root(self, handle: VaultHandle | None = None) -> Path:
        handle = handle or self.locator.resolve_active_vault()
        return handle.root_ref / "system"

    @staticmethod
    def _ensure_layout(canonical: Path, system: Path) -> None:
        for path in (canonical, canonical / "sources", system, system / "staging", system / "quarantine"):
            if path.is_symlink():
                raise WriterError("FILESYSTEM_UNSUPPORTED", "Vault layout contains symlink")
            path.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _inspect_path(self, path: Path, source_id: str) -> InspectResult:
        if path.is_symlink():
            return InspectResult("CORRUPT", source_id, path=path, reason="Source directory is symlink")
        if not path.exists():
            return InspectResult("MISSING", source_id, path=path, reason="Source directory missing")
        manifest_path = path / "source.md"
        payload_path = path / "payload" / "original"
        if manifest_path.is_symlink() or payload_path.is_symlink():
            return InspectResult("CORRUPT", source_id, path=path, reason="Source file is symlink")
        if not manifest_path.exists() or not payload_path.exists():
            return InspectResult("CORRUPT", source_id, path=path, reason="Source payload or manifest missing")
        try:
            manifest = parse_source(manifest_path.read_text())
            validate_source(manifest, expected_object_id=source_id)
            if not validate_payload(manifest, payload_path.read_bytes()):
                return InspectResult("CORRUPT", source_id, manifest["revision"], path, "payload integrity mismatch")
            return InspectResult("VALID", source_id, manifest["revision"], path)
        except (OSError, SourceValidationError, json.JSONDecodeError) as exc:
            return InspectResult("CORRUPT", source_id, path=path, reason=str(exc))

    def _same_create_intent(self, path: Path | None, manifest: dict[str, object]) -> bool:
        if path is None:
            return False
        try:
            existing = parse_source((path / "source.md").read_text())
        except (OSError, SourceValidationError):
            return False
        keys = ("object_id", "object_type", "schema_version", "created_at", "scope", "provenance", "trust", "sensitivity", "source")
        return all(existing[key] == manifest[key] for key in keys)

    def _failure(self, stage: str) -> None:
        if self.failure_injector:
            self.failure_injector(stage)

    @staticmethod
    def _write_bytes(path: Path, payload: bytes) -> None:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    @staticmethod
    def _cleanup_tx(tx_root: Path | None) -> None:
        if tx_root is None:
            return
        shutil.rmtree(tx_root, ignore_errors=True)

    @staticmethod
    def _staged_source_id(create_dir: Path) -> str | None:
        try:
            manifest = parse_source((create_dir / "source.md").read_text())
            return manifest["object_id"]
        except (OSError, SourceValidationError):
            return None


def _validate_source_id(source_id: str) -> None:
    try:
        value = uuid.UUID(source_id)
    except (ValueError, AttributeError) as exc:
        raise SourceValidationError("source_id must be UUIDv4") from exc
    if value.version != 4 or str(value) != source_id:
        raise SourceValidationError("source_id must be UUIDv4")


def _as_bytes(payload: bytes | str) -> bytes:
    return payload.encode("utf-8") if isinstance(payload, str) else payload


@contextlib.contextmanager
def shared_writer_lock(locator: ActiveVaultLocator) -> Iterator[VaultHandle]:
    """The one mutable-writer lock shared by A2 and C1."""
    handle = locator.resolve_active_vault()
    system = handle.root_ref / "system"
    if system.is_symlink():
        raise WriterError("FILESYSTEM_UNSUPPORTED", "Vault system directory is symlink")
    system.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = system / "write.lock"
    if lock_path.is_symlink():
        raise WriterError("FILESYSTEM_UNSUPPORTED", "writer lock is symlink")
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WriterError("WRITER_BUSY", "writer lock is busy") from exc
        try:
            yield handle
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
