"""Generation-safe local Active Vault Locator (C0)."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


SCHEMA_VERSION = "1.0.0"
_CAPABILITY_KEYS = (
    "local_read",
    "local_write",
    "same_volume_staging",
    "atomic_rename",
    "no_clobber_publish",
    "coordinated_access",
)


class LocatorError(RuntimeError):
    """The local locator is missing, invalid, or cannot safely be changed."""


class StaleGenerationError(LocatorError):
    """An operation attempted to use a locator generation that is no longer current."""


@dataclass(frozen=True)
class CapabilityReport:
    local_read: bool
    local_write: bool
    same_volume_staging: bool
    atomic_rename: bool
    no_clobber_publish: bool
    coordinated_access: str
    reason: str = ""

    @property
    def supported(self) -> bool:
        return (
            self.local_read
            and self.local_write
            and self.same_volume_staging
            and self.atomic_rename
            and self.no_clobber_publish
            and self.coordinated_access != "UNSUPPORTED"
        )

    def as_record(self) -> dict[str, object]:
        return {key: getattr(self, key) for key in _CAPABILITY_KEYS}


@dataclass(frozen=True)
class VaultHandle:
    vault_id: str
    root_ref: Path
    generation: int
    capability_report_hash: str
    resolved_at: str


@dataclass(frozen=True)
class SwitchResult:
    vault_id: str
    generation: int


@dataclass(frozen=True)
class LocatorHealth:
    status: str
    generation: int | None = None
    vault_id: str | None = None
    capabilities_supported: bool = False
    reason: str = ""


class ActiveVaultLocator:
    """Own the one local authority that selects the active Vault."""

    def __init__(self, state_dir: str | os.PathLike[str] | None = None):
        default = Path.home() / "Library" / "Application Support" / "TSUZU" / "control"
        self.state_dir = Path(state_dir or os.environ.get("TSUZU_STATE_DIR", default)).expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.locator_path = self.state_dir / "active-vault.json"
        self.lock_path = self.state_dir / "active-vault.lock"
        self.receipt_path = self.state_dir / "locator-receipts.jsonl"

    def preflight_vault(self, root_ref: str | os.PathLike[str]) -> CapabilityReport:
        requested = Path(root_ref).expanduser()
        try:
            if not requested.is_absolute():
                return self._unsupported("root must be an absolute path")
            if requested.is_symlink():
                return self._unsupported("symlink root is not allowed")
            root = requested.resolve(strict=True)
            if not root.is_dir():
                return self._unsupported("root must be a real directory")
            if root == self.state_dir or self.state_dir.resolve().is_relative_to(root):
                return self._unsupported("locator state must remain outside Vault root")

            local_read = os.access(root, os.R_OK)
            local_write = os.access(root, os.W_OK)
            same_volume = root.stat().st_dev == self.state_dir.stat().st_dev
            atomic_rename, no_clobber, fsync_ok = self._probe_filesystem(root)
            if not fsync_ok:
                atomic_rename = False
            return CapabilityReport(
                local_read=local_read,
                local_write=local_write,
                same_volume_staging=same_volume,
                atomic_rename=atomic_rename,
                no_clobber_publish=no_clobber,
                coordinated_access="NOT_REQUIRED",
                reason="" if all((local_read, local_write, same_volume, atomic_rename, no_clobber, fsync_ok)) else "filesystem capability check failed",
            )
        except (OSError, RuntimeError) as exc:
            return self._unsupported(str(exc))

    def initialize(
        self,
        root_ref: str | os.PathLike[str],
        *,
        vault_id: str | None = None,
        operation_id: str | None = None,
    ) -> VaultHandle:
        if self.locator_path.exists():
            raise LocatorError("active locator already exists")
        report = self.preflight_vault(root_ref)
        if not report.supported:
            raise LocatorError(f"unsupported Vault filesystem: {report.reason}")
        root = Path(root_ref).expanduser().resolve(strict=True)
        record = self._record(
            root,
            vault_id or str(uuid.uuid4()),
            generation=1,
            report=report,
            operation_id=operation_id or str(uuid.uuid4()),
        )
        with self._locked():
            if self.locator_path.exists():
                raise LocatorError("active locator already exists")
            self._atomic_write(record)
            self._append_receipt(record, None)
        return self._handle(record)

    def prepare_candidate(
        self, root_ref: str | os.PathLike[str], *, vault_id: str | None = None
    ) -> VaultHandle:
        report = self.preflight_vault(root_ref)
        if not report.supported:
            raise LocatorError(f"unsupported Vault filesystem: {report.reason}")
        root = Path(root_ref).expanduser().resolve(strict=True)
        candidate_id = vault_id or str(uuid.uuid4())
        self._validate_uuid(candidate_id)
        return VaultHandle(
            vault_id=candidate_id,
            root_ref=root,
            generation=0,
            capability_report_hash=self._report_hash(report),
            resolved_at=_now(),
        )

    def resolve_active_vault(self) -> VaultHandle:
        with self._locked():
            record = self._read_record()
        root = Path(record["active"]["root_ref"])
        self._verify_root_binding(record, root)
        report = self.preflight_vault(root)
        if not report.supported:
            raise LocatorError(f"active Vault is unavailable: {report.reason}")
        if self._report_hash(report) != record["active"]["capability_report_hash"]:
            raise LocatorError("active Vault capabilities changed")
        return self._handle(record)

    def compare_generation(self, handle: VaultHandle) -> str:
        with self._locked():
            record = self._read_record()
        active = record["active"]
        return "CURRENT" if (active["vault_id"], active["generation"]) == (handle.vault_id, handle.generation) else "STALE"

    def assert_current(self, handle: VaultHandle) -> None:
        if self.compare_generation(handle) != "CURRENT":
            raise StaleGenerationError("Vault handle generation is stale")

    def switch_active_vault(
        self, expected_generation: int, candidate_handle: VaultHandle, operation_id: str
    ) -> SwitchResult:
        with self._locked():
            current = self._read_record()
            active = current["active"]
            if active["generation"] != expected_generation:
                raise StaleGenerationError("locator generation changed before cutover")
            if active["vault_id"] == candidate_handle.vault_id:
                raise LocatorError("candidate Vault must differ from active Vault")
            report = self.preflight_vault(candidate_handle.root_ref)
            if not report.supported:
                raise LocatorError(f"unsupported candidate filesystem: {report.reason}")
            record = self._record(
                candidate_handle.root_ref,
                candidate_handle.vault_id,
                generation=expected_generation + 1,
                report=report,
                operation_id=operation_id,
            )
            self._atomic_write(record)
            read_back = self._read_record()
            if read_back["active"]["generation"] != expected_generation + 1:
                raise LocatorError("locator cutover read-back failed")
            self._append_receipt(record, current)
            return SwitchResult(candidate_handle.vault_id, expected_generation + 1)

    def rollback_active_vault(
        self, expected_generation: int, previous_handle: VaultHandle, operation_id: str
    ) -> SwitchResult:
        return self.switch_active_vault(expected_generation, previous_handle, operation_id)

    def inspect_locator(self) -> LocatorHealth:
        if not self.locator_path.exists():
            return LocatorHealth("MISSING", reason="locator is absent")
        try:
            with self._locked():
                record = self._read_record()
            active = record["active"]
            capabilities = record["capabilities"]
            root = Path(active["root_ref"])
            if not root.exists():
                return LocatorHealth(
                    "DEGRADED",
                    generation=active["generation"],
                    vault_id=active["vault_id"],
                    reason="active Vault root is unavailable",
                )
            self._verify_root_binding(record, root)
            report = self.preflight_vault(active["root_ref"])
            if not report.supported:
                return LocatorHealth(
                    "DEGRADED",
                    generation=active["generation"],
                    vault_id=active["vault_id"],
                    reason="active Vault capability check failed",
                )
            return LocatorHealth(
                "HEALTHY",
                generation=active["generation"],
                vault_id=active["vault_id"],
                capabilities_supported=all(
                    capabilities[key] for key in _CAPABILITY_KEYS[:-1]
                ) and capabilities["coordinated_access"] != "UNSUPPORTED",
            )
        except LocatorError as exc:
            return LocatorHealth("CORRUPT", reason=str(exc))

    @contextlib.contextmanager
    def _locked(self) -> Iterator[None]:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _read_record(self) -> dict[str, object]:
        try:
            record = json.loads(self.locator_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise LocatorError("locator cannot be read") from exc
        self._validate_record(record)
        return record

    def _atomic_write(self, record: dict[str, object]) -> None:
        payload = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        fd, name = tempfile.mkstemp(prefix="active-vault.", suffix=".tmp", dir=self.state_dir)
        try:
            with os.fdopen(fd, "wb") as staged:
                staged.write(payload)
                staged.flush()
                os.fsync(staged.fileno())
            os.replace(name, self.locator_path)
            self._fsync_directory(self.state_dir)
        except OSError as exc:
            try:
                os.unlink(name)
            except OSError:
                pass
            raise LocatorError("atomic locator replace failed") from exc

    def _append_receipt(self, record: dict[str, object], previous: dict[str, object] | None) -> None:
        active = record["active"]
        receipt = {
            "event": "locator_change",
            "operation_id": record["updated_by_operation_id"],
            "generation": active["generation"],
            "vault_id": active["vault_id"],
            "previous_generation": previous["active"]["generation"] if previous else None,
            "previous_vault_id": previous["active"]["vault_id"] if previous else None,
            "at": record["updated_at"],
        }
        with self.receipt_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _record(self, root: Path, vault_id: str, generation: int, report: CapabilityReport, operation_id: str) -> dict[str, object]:
        self._validate_uuid(vault_id)
        return {
            "locator_schema_version": SCHEMA_VERSION,
            "locator_revision": generation,
            "active": {
                "vault_id": vault_id,
                "root_ref": str(root),
                "root_fingerprint": self._root_fingerprint(root),
                "volume_identity": str(root.stat().st_dev),
                "generation": generation,
                "capability_report_hash": self._report_hash(report),
            },
            "capabilities": report.as_record(),
            "updated_at": _now(),
            "updated_by_operation_id": operation_id,
        }

    def _handle(self, record: dict[str, object]) -> VaultHandle:
        active = record["active"]
        return VaultHandle(
            vault_id=active["vault_id"],
            root_ref=Path(active["root_ref"]),
            generation=active["generation"],
            capability_report_hash=active["capability_report_hash"],
            resolved_at=record["updated_at"],
        )

    @staticmethod
    def _verify_root_binding(record: dict[str, object], root: Path) -> None:
        active = record["active"]
        try:
            resolved = root.resolve(strict=True)
            volume_identity = str(resolved.stat().st_dev)
        except OSError as exc:
            raise LocatorError("active Vault root is unavailable") from exc
        if ActiveVaultLocator._root_fingerprint(resolved) != active["root_fingerprint"]:
            raise LocatorError("active Vault root fingerprint mismatch")
        if volume_identity != active["volume_identity"]:
            raise LocatorError("active Vault volume identity mismatch")

    @staticmethod
    def _unsupported(reason: str) -> CapabilityReport:
        return CapabilityReport(False, False, False, False, False, "UNSUPPORTED", reason)

    @staticmethod
    def _root_fingerprint(root: Path) -> str:
        return hashlib.sha256(str(root).encode()).hexdigest()

    @staticmethod
    def _report_hash(report: CapabilityReport) -> str:
        payload = json.dumps(report.as_record(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def _validate_uuid(value: object) -> None:
        try:
            uuid.UUID(str(value))
        except (ValueError, AttributeError) as exc:
            raise LocatorError("invalid vault_id") from exc

    @staticmethod
    def _validate_record(record: object) -> None:
        if not isinstance(record, dict) or record.get("locator_schema_version") != SCHEMA_VERSION:
            raise LocatorError("unsupported locator schema")
        if set(record) != {"locator_schema_version", "locator_revision", "active", "capabilities", "updated_at", "updated_by_operation_id"}:
            raise LocatorError("locator fields are ambiguous")
        active = record.get("active")
        capabilities = record.get("capabilities")
        if not isinstance(active, dict) or set(active) != {"vault_id", "root_ref", "root_fingerprint", "volume_identity", "generation", "capability_report_hash"}:
            raise LocatorError("invalid active locator record")
        if not isinstance(capabilities, dict) or set(capabilities) != set(_CAPABILITY_KEYS):
            raise LocatorError("invalid capability record")
        ActiveVaultLocator._validate_uuid(active.get("vault_id"))
        if not isinstance(active.get("root_ref"), str) or not Path(active["root_ref"]).is_absolute():
            raise LocatorError("invalid root reference")
        if isinstance(active.get("generation"), bool) or not isinstance(active.get("generation"), int) or active["generation"] < 1:
            raise LocatorError("invalid locator generation")
        if record["locator_revision"] != active["generation"]:
            raise LocatorError("locator revision mismatch")
        if capabilities["coordinated_access"] not in {"SUPPORTED", "NOT_REQUIRED", "UNSUPPORTED"}:
            raise LocatorError("invalid coordination capability")
        if any(not isinstance(capabilities[key], bool) for key in _CAPABILITY_KEYS[:-1]):
            raise LocatorError("invalid boolean capability")
        if not isinstance(active["root_fingerprint"], str) or len(active["root_fingerprint"]) != 64:
            raise LocatorError("invalid root fingerprint")
        if not isinstance(active["volume_identity"], str) or not active["volume_identity"]:
            raise LocatorError("invalid volume identity")
        if not isinstance(active["capability_report_hash"], str) or len(active["capability_report_hash"]) != 64:
            raise LocatorError("invalid capability hash")
        if not isinstance(record["updated_at"], str) or not isinstance(record["updated_by_operation_id"], str):
            raise LocatorError("invalid locator metadata")
        report = CapabilityReport(
            *(capabilities[key] for key in _CAPABILITY_KEYS[:-1]),
            capabilities["coordinated_access"],
        )
        expected_hash = ActiveVaultLocator._report_hash(report)
        if active["capability_report_hash"] != expected_hash:
            raise LocatorError("capability hash mismatch")

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    @staticmethod
    def _probe_filesystem(root: Path) -> tuple[bool, bool, bool]:
        temp_name = ""
        probe = root / f".tsuzu-probe-{uuid.uuid4().hex}"
        try:
            fd, temp_name = tempfile.mkstemp(prefix=".tsuzu-stage-", dir=root)
            with os.fdopen(fd, "wb") as stream:
                stream.write(b"probe")
                stream.flush()
                os.fsync(stream.fileno())
            no_clobber = False
            try:
                os.link(temp_name, probe)
                no_clobber = True
            finally:
                if probe.exists():
                    probe.unlink()
            replacement = root / f".tsuzu-replace-{uuid.uuid4().hex}"
            os.replace(temp_name, replacement)
            temp_name = ""
            replacement.unlink()
            ActiveVaultLocator._fsync_directory(root)
            return True, no_clobber, True
        except OSError:
            return False, False, False
        finally:
            if temp_name:
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
