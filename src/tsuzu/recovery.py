"""R5 immutable backup and temporary-vault restore for current Canonical types."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .canonical import _parse_manifest
from .deletion import _read_record, _validate_record
from .index import IndexManager
from .source import SourceValidationError, parse_source, validate_payload, validate_source
from .vault import ActiveVaultLocator, LocatorError, VaultHandle
from .writer import WriterError, maintenance_lock


PROTECTED = "PROTECTED"
REBUILDABLE = "REBUILDABLE"
RUNTIME = "RUNTIME"
EXTERNAL_SECRET = "EXTERNAL_SECRET"
PROTECTION_REGISTRY_VERSION = "r5-1.0"
_PROTECTED_TYPES = frozenset({"SOURCE", "SOURCE_VERSION"})
_SCHEMA_VERSIONS = {"SOURCE": "1.0.0", "SOURCE_VERSION": "1.0.0"}


@dataclass(frozen=True)
class BackupResult:
    status: str
    backup_id: str = ""
    path: Path | None = None
    reason: str = ""


@dataclass(frozen=True)
class RestoreResult:
    status: str
    backup_id: str
    previous_vault_id: str = ""
    candidate_vault_id: str = ""
    reason: str = ""


class RecoveryCoordinator:
    """Keep backups immutable and never mutate the active Vault in place."""

    def __init__(
        self,
        locator: ActiveVaultLocator,
        backup_root: str | os.PathLike[str],
        *,
        index_root: str | os.PathLike[str] | None = None,
        failure_injector: Callable[[str], None] | None = None,
    ):
        self.locator = locator
        self.backup_root = Path(backup_root)
        self.index_root = Path(index_root) if index_root is not None else None
        self.failure_injector = failure_injector

    def create_backup(self, *, backup_id: str | None = None) -> BackupResult:
        backup_id = backup_id or str(uuid.uuid4())
        if not _is_uuid4(backup_id):
            return BackupResult("VALIDATION_FAILED", reason="backup_id must be UUIDv4")
        try:
            with maintenance_lock(self.locator):
                active = self.locator.resolve_active_vault()
                self._preflight_destination(active.root_ref)
                self._ensure_ledger_root(active.root_ref)
                snapshot = self.backup_root / backup_id
                if snapshot.exists() or snapshot.is_symlink():
                    return BackupResult("BACKUP_ID_CONFLICT", backup_id, snapshot)
                staging = self.backup_root / f".{backup_id}.staging"
                if staging.exists() or staging.is_symlink():
                    return BackupResult("BACKUP_ID_CONFLICT", backup_id, staging)
                files, privacy = self._enumerate_protected(active.root_ref)
                staging.mkdir(mode=0o700)
                try:
                    protected = staging / "protected"
                    for source, relative, object_type in files:
                        destination = protected / relative
                        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                        shutil.copyfile(source, destination)
                        if _sha256(destination) != _sha256(source):
                            raise RecoveryError("BACKUP_COPY_HASH_MISMATCH")
                    manifest = self._manifest(backup_id, active, protected, files, privacy)
                    _write_new(staging / "backup.md", _document(manifest))
                    self._failure("before_commit")
                    os.rename(staging, snapshot)
                    _fsync_dir(self.backup_root)
                    self._failure("before_committed_marker")
                    _write_new(snapshot / "COMMITTED", "R5 committed snapshot\n")
                    _fsync_dir(snapshot)
                    self._validate_snapshot(snapshot, backup_id)
                    self._receipt(active.root_ref, "BACKUP_COMMITTED", backup_id)
                    return BackupResult("COMMITTED", backup_id, snapshot)
                except Exception:
                    shutil.rmtree(staging, ignore_errors=True)
                    raise
        except (OSError, LocatorError, WriterError, RecoveryError, SourceValidationError) as exc:
            return BackupResult(_status(exc, "BACKUP_FAILED"), backup_id, reason=str(exc))
        except Exception as exc:
            return BackupResult("BACKUP_FAILED", backup_id, reason=str(exc))

    def restore(self, backup_id: str, candidate_root: str | os.PathLike[str]) -> RestoreResult:
        if not _is_uuid4(backup_id):
            return RestoreResult("VALIDATION_FAILED", backup_id, reason="backup_id must be UUIDv4")
        snapshot = self.backup_root / backup_id
        try:
            self._validate_snapshot(snapshot, backup_id)
            active = self.locator.resolve_active_vault()
            self._validate_ledger(active.root_ref, required=True)
            pre_restore = self.create_backup()
            if pre_restore.status != "COMMITTED":
                return RestoreResult("PRE_RESTORE_BACKUP_FAILED", backup_id, reason=pre_restore.reason)
            with maintenance_lock(self.locator):
                previous = self.locator.resolve_active_vault()
                if (previous.vault_id, previous.generation) != (active.vault_id, active.generation):
                    return RestoreResult("STALE_GENERATION", backup_id)
                candidate_path = Path(candidate_root)
                if candidate_path.exists() or candidate_path.is_symlink():
                    return RestoreResult("CANDIDATE_EXISTS", backup_id)
                candidate_path.mkdir(parents=True, mode=0o700)
                try:
                    protected = snapshot / "protected"
                    shutil.copytree(protected / "canonical", candidate_path / "canonical", symlinks=True)
                    ledger = protected / "system" / "deletion-ledger"
                    if ledger.exists():
                        shutil.copytree(ledger, candidate_path / "system" / "deletion-ledger", symlinks=True)
                    self._merge_current_ledger(previous.root_ref, candidate_path)
                    self._validate_vault(candidate_path)
                    self._migrate_n_minus_one(candidate_path)
                    self._validate_vault(candidate_path)
                    self._failure("before_cutover")
                    candidate = self.locator.prepare_candidate(candidate_path)
                    switched = self.locator.switch_active_vault(previous.generation, candidate, f"restore-{backup_id}")
                    try:
                        self._rebuild_index()
                        self._failure("after_cutover")
                        if self.locator.inspect_locator().status != "HEALTHY":
                            raise RecoveryError("CUTOVER_HEALTH_FAILED")
                    except Exception:
                        self.locator.rollback_active_vault(switched.generation, previous, f"restore-rollback-{backup_id}")
                        raise
                    self._receipt(candidate_path, "RESTORE_COMMITTED", backup_id)
                    return RestoreResult("RESTORED", backup_id, previous.vault_id, candidate.vault_id)
                except Exception:
                    # A pre-cutover candidate has no authority and is retained for diagnosis.
                    raise
        except RecoveryError as exc:
            return RestoreResult(_status(exc, "RESTORE_FAILED"), backup_id, reason=str(exc))
        except (OSError, LocatorError, WriterError, SourceValidationError) as exc:
            return RestoreResult("RESTORE_FAILED", backup_id, reason=str(exc))
        except Exception as exc:
            return RestoreResult("RESTORE_FAILED", backup_id, reason=str(exc))

    def _preflight_destination(self, active_root: Path) -> None:
        self.backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.backup_root.is_symlink() or not self.backup_root.is_dir():
            raise RecoveryError("BACKUP_DESTINATION_INVALID")
        destination = self.backup_root.resolve()
        active = active_root.resolve()
        if destination == active or active in destination.parents:
            raise RecoveryError("BACKUP_DESTINATION_RECURSIVE")
        probe = destination / f".r5-probe-{uuid.uuid4().hex}"
        _write_new(probe, "probe")
        probe.unlink()

    @staticmethod
    def _ensure_ledger_root(root: Path) -> None:
        ledger = root / "system" / "deletion-ledger"
        if ledger.is_symlink():
            raise RecoveryError("DELETION_LEDGER_UNAVAILABLE")
        ledger.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _enumerate_protected(self, root: Path):
        canonical = root / "canonical"
        if canonical.is_symlink() or not canonical.exists():
            raise RecoveryError("CANONICAL_INTEGRITY_FAILURE")
        files: list[tuple[Path, Path, str]] = []
        privacy = {"PUBLIC": False, "PERSONAL": False, "SENSITIVE": False}
        source_root = canonical / "sources"
        if source_root.exists():
            if source_root.is_symlink():
                raise RecoveryError("CANONICAL_INTEGRITY_FAILURE")
            for item in sorted(source_root.iterdir()):
                self._validate_source(item)
                manifest = parse_source((item / "source.md").read_text())
                privacy[manifest["sensitivity"]["level"]] = True
                files.extend(_files_under(item, Path("canonical/sources") / item.name, "SOURCE"))
        objects = canonical / "objects"
        if objects.exists():
            if objects.is_symlink():
                raise RecoveryError("CANONICAL_INTEGRITY_FAILURE")
            for type_root in sorted(objects.iterdir()):
                if type_root.name not in _PROTECTED_TYPES or type_root.name == "SOURCE" or not type_root.is_dir() or type_root.is_symlink():
                    raise RecoveryError("BACKUP_CLASS_UNKNOWN")
                for item in sorted(type_root.iterdir()):
                    self._validate_object(item, type_root.name)
                    manifest = _parse_manifest((item / "object.md").read_text())
                    privacy[manifest["sensitivity"]["level"]] = True
                    files.extend(_files_under(item, Path("canonical/objects") / type_root.name / item.name, type_root.name))
        ledger = root / "system" / "deletion-ledger"
        self._validate_ledger(root, required=True)
        files.extend(_files_under(ledger, Path("system/deletion-ledger"), "DELETION_LEDGER"))
        return files, privacy

    def _manifest(self, backup_id: str, active: VaultHandle, protected: Path, files, privacy: dict[str, bool]) -> dict[str, object]:
        entries = [{"relative_path": str(relative), "protection_class": PROTECTED, "object_type": object_type, "byte_length": path.stat().st_size, "sha256": _sha256(protected / relative)} for path, relative, object_type in files]
        encoded_entries = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
        ledger_entries = [entry for entry in entries if entry["object_type"] == "DELETION_LEDGER"]
        schema = [{"object_type": object_type, "schema_versions": [version], "count": sum(1 for _, _, kind in files if kind == object_type and _.name == "object.md")} for object_type, version in _SCHEMA_VERSIONS.items()]
        now = _now()
        return {"backup_id": backup_id, "backup_contract_version": "1.0.0", "created_at": now, "completed_at": now, "source": {"vault_instance_id": active.vault_id, "vault_locator_hash": active.capability_report_hash}, "protection_registry_version": PROTECTION_REGISTRY_VERSION, "schema_inventory": schema, "content_manifest": {"algorithm": "SHA-256", "entry_count": len(entries), "manifest_hash": hashlib.sha256(encoded_entries).hexdigest(), "entries": entries}, "privacy_summary": {"contains_public": privacy["PUBLIC"], "contains_personal": privacy["PERSONAL"], "contains_sensitive": privacy["SENSITIVE"], "contains_restricted_knowledge": False}, "deletion_ledger": {"record_count": len(ledger_entries), "ledger_manifest_hash": hashlib.sha256(json.dumps(ledger_entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}, "app_contract": {"canonical_contract_version": "1.0.0", "created_by_app_version": "p0"}}

    def _validate_snapshot(self, snapshot: Path, backup_id: str) -> None:
        if snapshot.is_symlink() or not snapshot.is_dir() or not (snapshot / "COMMITTED").is_file():
            raise RecoveryError("INCOMPLETE_BACKUP")
        manifest_path = snapshot / "backup.md"
        if manifest_path.is_symlink():
            raise RecoveryError("BACKUP_MANIFEST_INVALID")
        manifest = _parse_document(manifest_path.read_text())
        if manifest.get("backup_id") != backup_id or manifest.get("backup_contract_version") != "1.0.0":
            raise RecoveryError("BACKUP_MANIFEST_INVALID")
        entries = manifest.get("content_manifest", {}).get("entries")
        if not isinstance(entries, list):
            raise RecoveryError("BACKUP_MANIFEST_INVALID")
        digest = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if manifest["content_manifest"].get("manifest_hash") != digest:
            raise RecoveryError("BACKUP_MANIFEST_INVALID")
        for entry in entries:
            relative = _safe_relative(entry.get("relative_path"))
            path = snapshot / "protected" / relative
            if path.is_symlink() or not path.is_file() or path.stat().st_size != entry.get("byte_length") or _sha256(path) != entry.get("sha256"):
                raise RecoveryError("BACKUP_INTEGRITY_FAILED")

    def _validate_vault(self, root: Path) -> None:
        self._enumerate_protected(root)

    @staticmethod
    def _validate_source(path: Path) -> None:
        if path.is_symlink() or not path.is_dir():
            raise RecoveryError("RESTORE_CANONICAL_INTEGRITY_FAILED")
        manifest_path, payload = path / "source.md", path / "payload" / "original"
        if any(item.is_symlink() or not item.is_file() for item in (manifest_path, payload)):
            raise RecoveryError("RESTORE_CANONICAL_INTEGRITY_FAILED")
        manifest = parse_source(manifest_path.read_text())
        validate_source(manifest, expected_object_id=path.name)
        if not validate_payload(manifest, payload.read_bytes()):
            raise RecoveryError("RESTORE_CANONICAL_INTEGRITY_FAILED")

    @staticmethod
    def _validate_object(path: Path, object_type: str) -> None:
        if path.is_symlink() or not path.is_dir() or (path / "object.md").is_symlink():
            raise RecoveryError("RESTORE_CANONICAL_INTEGRITY_FAILED")
        manifest = _parse_manifest((path / "object.md").read_text())
        if manifest.get("object_type") != object_type or manifest.get("object_id") != path.name or manifest.get("schema_version") not in {"1.0.0", "0.9.0"}:
            raise RecoveryError("SCHEMA_UNKNOWN_FAIL_CLOSED")
        payload = path / "payload" / "original"
        details = manifest.get("payload")
        if not isinstance(details, dict) or payload.is_symlink() or not payload.is_file() or _sha256(payload) != details.get("sha256") or payload.stat().st_size != details.get("bytes"):
            raise RecoveryError("RESTORE_CANONICAL_INTEGRITY_FAILED")

    def _validate_ledger(self, root: Path, *, required: bool) -> None:
        ledger = root / "system" / "deletion-ledger"
        if not ledger.exists() and required:
            raise RecoveryError("DELETION_LEDGER_UNAVAILABLE")
        if not ledger.exists():
            return
        if ledger.is_symlink() or not ledger.is_dir():
            raise RecoveryError("DELETION_LEDGER_UNAVAILABLE")
        for path in ledger.rglob("*.md"):
            relative = path.relative_to(ledger)
            if len(relative.parts) != 2 or path.is_symlink():
                raise RecoveryError("DELETION_LEDGER_UNAVAILABLE")
            try:
                _validate_record(_read_record(path), relative.parts[0], path.stem)
            except (OSError, SourceValidationError, KeyError, TypeError, ValueError) as exc:
                raise RecoveryError("DELETION_LEDGER_UNAVAILABLE") from exc

    def _merge_current_ledger(self, current_root: Path, candidate_root: Path) -> None:
        current = current_root / "system" / "deletion-ledger"
        target = candidate_root / "system" / "deletion-ledger"
        self._validate_ledger(current_root, required=True)
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._validate_ledger(candidate_root, required=True)
        for current_record in current.rglob("*.md"):
            relative = current_record.relative_to(current)
            destination = target / relative
            if destination.exists():
                if current_record.read_bytes() != destination.read_bytes():
                    raise RecoveryError("DELETION_LEDGER_CONFLICT")
                continue
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copyfile(current_record, destination)
        self._validate_ledger(candidate_root, required=True)

    def _migrate_n_minus_one(self, root: Path) -> None:
        for path in (root / "canonical" / "objects").glob("*/*/object.md"):
            manifest = _parse_manifest(path.read_text())
            if manifest.get("schema_version") == "0.9.0":
                self._failure("during_migration")
                manifest["schema_version"] = "1.0.0"
                _replace_file(path, _document(manifest))

    def _rebuild_index(self) -> None:
        if self.index_root is None:
            return
        manager = IndexManager(self.index_root, self.locator)
        manager.open()
        try:
            manager.discard_and_rebuild()
            if manager.health().status != "HEALTHY":
                raise RecoveryError("INDEX_REBUILD_FAILED")
        finally:
            manager.close()

    def _receipt(self, root: Path, status: str, backup_id: str) -> None:
        path = root / "system" / "recovery-receipts.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        record = {"status": status, "backup_id": backup_id, "at": _now()}
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _failure(self, stage: str) -> None:
        if self.failure_injector:
            self.failure_injector(stage)


class RecoveryError(RuntimeError):
    pass


def _files_under(root: Path, relative_root: Path, object_type: str):
    if root.is_symlink() or not root.is_dir():
        raise RecoveryError("CANONICAL_INTEGRITY_FAILURE")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RecoveryError("CANONICAL_INTEGRITY_FAILURE")
        if path.is_file():
            files.append((path, relative_root / path.relative_to(root), object_type))
    return files


def _safe_relative(value: object) -> Path:
    if not isinstance(value, str):
        raise RecoveryError("BACKUP_MANIFEST_INVALID")
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise RecoveryError("BACKUP_MANIFEST_INVALID")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_new(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())


def _replace_file(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    _write_new(temporary, text)
    os.replace(temporary, path)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _document(value: dict[str, object]) -> str:
    return "---\n" + json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n---\n"


def _parse_document(value: str) -> dict[str, object]:
    if not value.startswith("---\n") or "\n---\n" not in value:
        raise RecoveryError("BACKUP_MANIFEST_INVALID")
    parsed = json.loads(value[4 : value.find("\n---\n", 4)])
    if not isinstance(parsed, dict):
        raise RecoveryError("BACKUP_MANIFEST_INVALID")
    return parsed


def _is_uuid4(value: str) -> bool:
    try:
        return str(uuid.UUID(value)) == value and uuid.UUID(value).version == 4
    except (ValueError, AttributeError):
        return False


def _status(exc: Exception, fallback: str) -> str:
    text = str(exc)
    return text if text.isupper() and " " not in text else fallback


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
