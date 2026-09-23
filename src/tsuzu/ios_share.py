"""Create-only mobile outbox and authenticated Mac ingestion bridge (R4)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .capture import CaptureRequest, CaptureService, CaptureStatus, SecretScanner, _fsync_directory, _validate_timestamp, _validate_uuid
from .vault import ActiveVaultLocator
from .worker import SingleWriterWorker, WorkerStatus


class TransportStatus:
    LOCAL_PENDING = "LOCAL_PENDING"
    REJECTED_RESTRICTED = "REJECTED_RESTRICTED"
    IO_FAILED = "IO_FAILED"
    TRANSPORT_AUTHENTICITY_FAILED = "TRANSPORT_AUTHENTICITY_FAILED"
    MAC_COMMITTED = "MAC_COMMITTED"
    MAC_ACCEPTED = "MAC_ACCEPTED"


_MAX_ENVELOPE_AGE = timedelta(days=30)
_MAX_CLOCK_SKEW = timedelta(minutes=5)
_SIGNATURE_ALGORITHM = "Ed25519"


@dataclass(frozen=True)
class MobileShareRequest:
    mobile_capture_id: str
    idempotency_key: str
    kind: str
    content: bytes | str | os.PathLike[str]
    created_at: str
    device_key_id: str
    signature_algorithm: str
    original_name: str | None = None
    media_type: str | None = None


@dataclass(frozen=True)
class TransportResult:
    status: str
    envelope_dir: Path | None = None
    source_id: str | None = None
    reason: str = ""


class MobileOutbox:
    """Mobile-owned namespace only; it never receives a Vault locator."""

    def __init__(self, root: str | os.PathLike[str], *, signer: Callable[[bytes], str], scanner: SecretScanner | None = None, max_file_bytes: int = 100 * 1024 * 1024):
        self.root = Path(root)
        self.signer = signer
        self.scanner = scanner or SecretScanner()
        self.max_file_bytes = max_file_bytes

    def accept(self, request: MobileShareRequest) -> TransportResult:
        try:
            _validate_uuid(request.mobile_capture_id)
            _validate_uuid(request.idempotency_key)
            _validate_timestamp(request.created_at)
            kind = request.kind.upper()
            if kind not in {"TEXT", "URL", "FILE"} or not request.device_key_id or request.signature_algorithm != _SIGNATURE_ALGORITHM:
                raise ValueError("invalid mobile envelope")
            final = self.root / "pending" / request.mobile_capture_id
            if final.exists() and not final.is_symlink():
                return TransportResult(TransportStatus.LOCAL_PENDING, final)
            staging = self.root / "staging" / request.mobile_capture_id
            self._layout()
            if staging.exists() or staging.is_symlink():
                raise OSError("mobile staging collision")
            payload = staging / "payload" / "original"
            payload.parent.mkdir(parents=True, mode=0o700)
            digest, size = self._copy_payload(request, payload, kind)
            with payload.open("rb") as stream:
                scan = self.scanner.scan_stream(stream)
            if scan.outcome != "CLEAR":
                shutil.rmtree(staging, ignore_errors=True)
                return TransportResult(TransportStatus.REJECTED_RESTRICTED)
            if scan.payload_sha256 != digest or scan.bytes_scanned != size:
                raise OSError("mobile payload changed during scan")
            envelope = {
                "envelope_schema_version": "1.0.0", "mobile_capture_id": request.mobile_capture_id, "idempotency_key": request.idempotency_key,
                "created_at": request.created_at,
                "input": {"kind": kind, "original_name": request.original_name, "media_type": request.media_type or _media_type(kind)},
                "payload": {"relative_path": "payload/original", "sha256": digest, "bytes": size},
                "source_plan": {"capture_method": f"IOS_SHARE_{kind}", "requested_scope": "GLOBAL", "sensitivity_hint": "PERSONAL"},
                "authenticity": {"device_key_id": request.device_key_id, "signature_algorithm": request.signature_algorithm},
                "transport": {"state": TransportStatus.LOCAL_PENDING},
            }
            signature = self.signer(_signed_bytes(envelope))
            if not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{128}", signature):
                raise ValueError("signer must return a 64-byte Ed25519 signature as lowercase hex")
            envelope["authenticity"]["envelope_signature"] = signature
            self._write_json(staging / "envelope.json", envelope)
            os.rename(staging, final)
            _fsync_directory(final.parent)
            return TransportResult(TransportStatus.LOCAL_PENDING, final)
        except (OSError, ValueError, TypeError) as exc:
            if "staging" in locals() and staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            return TransportResult(TransportStatus.IO_FAILED, reason=str(exc))

    def cleanup_after_receipt(self, mobile_capture_id: str, terminal_state: str) -> bool:
        """Deletes only a durably acknowledged envelope; pending data is never reclaimed."""
        _validate_uuid(mobile_capture_id)
        if terminal_state not in {TransportStatus.MAC_ACCEPTED, TransportStatus.MAC_COMMITTED, TransportStatus.REJECTED_RESTRICTED}:
            return False
        path = self.root / "pending" / mobile_capture_id
        if path.is_symlink() or not path.exists():
            return False
        shutil.rmtree(path)
        _fsync_directory(path.parent)
        return True

    def _copy_payload(self, request: MobileShareRequest, destination: Path, kind: str) -> tuple[str, int]:
        digest = hashlib.sha256()
        total = 0
        if kind != "FILE":
            raw = request.content.encode("utf-8") if isinstance(request.content, str) else request.content
            if not isinstance(raw, bytes) or not raw or (kind == "URL" and not _valid_url(raw)):
                raise ValueError("invalid mobile share payload")
            chunks = (raw,)
        else:
            path = Path(request.content)
            if path.is_symlink() or not path.is_file():
                raise ValueError("FILE must be a regular non-symlink file")
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(path, flags)
            stream = os.fdopen(fd, "rb")
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                stream.close()
                raise ValueError("FILE must remain a regular file")
            chunks = iter(lambda: stream.read(65536), b"")
        try:
            with destination.open("xb") as output:
                for chunk in chunks:
                    total += len(chunk)
                    if total > self.max_file_bytes:
                        raise ValueError("mobile file exceeds limit")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        finally:
            if kind == "FILE":
                stream.close()
        if total < 1:
            raise ValueError("empty mobile share payload")
        return digest.hexdigest(), total

    def _layout(self) -> None:
        for path in (self.root, self.root / "staging", self.root / "pending"):
            if path.is_symlink():
                raise OSError("mobile outbox path is symlink")
            path.mkdir(parents=True, exist_ok=True, mode=0o700)

    @staticmethod
    def _write_json(path: Path, value: dict[str, object]) -> None:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())


class MacInboxConsumer:
    def __init__(self, queue_root: str | os.PathLike[str], locator: ActiveVaultLocator, *, verifier: Callable[[str, str, bytes, str], bool] | None = None):
        self.queue_root = Path(queue_root)
        self.locator = locator
        self.verifier = verifier

    def consume(self, envelope_dir: str | os.PathLike[str]) -> TransportResult:
        try:
            directory = Path(envelope_dir)
            if directory.is_symlink():
                raise ValueError("transport envelope is symlink")
            envelope = json.loads((directory / "envelope.json").read_text())
            _validate_envelope(envelope)
            payload_path = directory / envelope["payload"]["relative_path"]
            if payload_path.is_symlink():
                raise ValueError("transport payload is symlink")
            payload = payload_path.read_bytes()
            if len(payload) != envelope["payload"]["bytes"] or hashlib.sha256(payload).hexdigest() != envelope["payload"]["sha256"]:
                raise ValueError("transport payload integrity mismatch")
            auth = envelope["authenticity"]
            verifier = self.verifier or PairedKeyRegistry(self.locator.resolve_active_vault().root_ref / "system" / "paired-device-keys").verify
            if not verifier(auth["device_key_id"], auth["signature_algorithm"], _signed_bytes(envelope), auth["envelope_signature"]):
                raise ValueError("unpaired or invalid transport signature")
            _reserve_mobile_event(self.locator.resolve_active_vault().root_ref / "system" / "ios-share-event-receipts", envelope)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return TransportResult(TransportStatus.TRANSPORT_AUTHENTICITY_FAILED, reason=str(exc))
        input_data = envelope["input"]
        captured = CaptureService(self.queue_root).capture(CaptureRequest(
            request_id=envelope["mobile_capture_id"], idempotency_key=envelope["idempotency_key"], kind=input_data["kind"], content=payload,
            original_name=input_data["original_name"], requested_at=envelope["created_at"], capture_method=envelope["source_plan"]["capture_method"],
        ))
        if captured.status == CaptureStatus.REJECTED_RESTRICTED:
            return TransportResult(TransportStatus.REJECTED_RESTRICTED, source_id=captured.source_id)
        if captured.status not in {CaptureStatus.ACCEPTED, CaptureStatus.ALREADY_ACCEPTED}:
            return TransportResult(TransportStatus.IO_FAILED, reason=captured.reason)
        receipt = self.queue_root / "receipts" / f"{hashlib.sha256(envelope['idempotency_key'].encode()).hexdigest()}.json"
        if captured.status == CaptureStatus.ALREADY_ACCEPTED and receipt.exists() and not receipt.is_symlink():
            return TransportResult(TransportStatus.MAC_ACCEPTED, source_id=captured.source_id)
        result = SingleWriterWorker(self.queue_root, self.locator).run_once()
        if captured.status == CaptureStatus.ALREADY_ACCEPTED and result.status == WorkerStatus.IDLE:
            return TransportResult(TransportStatus.MAC_ACCEPTED, source_id=captured.source_id)
        if result.status in {WorkerStatus.COMMITTED, WorkerStatus.ALREADY_COMMITTED}:
            if result.source_id != captured.source_id:
                return TransportResult(TransportStatus.IO_FAILED, source_id=captured.source_id, reason="different queue job completed")
            return TransportResult(TransportStatus.MAC_COMMITTED if result.status == WorkerStatus.COMMITTED else TransportStatus.MAC_ACCEPTED, source_id=result.source_id or captured.source_id)
        return TransportResult(TransportStatus.IO_FAILED, source_id=captured.source_id, reason=result.reason)


def _signed_bytes(envelope: dict[str, object]) -> bytes:
    copy = json.loads(json.dumps(envelope))
    copy["authenticity"].pop("envelope_signature", None)
    copy.pop("transport", None)
    return json.dumps(copy, sort_keys=True, separators=(",", ":")).encode()


def _validate_envelope(value: object) -> None:
    fields = {"envelope_schema_version", "mobile_capture_id", "idempotency_key", "created_at", "input", "payload", "source_plan", "authenticity", "transport"}
    if not isinstance(value, dict) or set(value) != fields or value["envelope_schema_version"] != "1.0.0":
        raise ValueError("invalid transport envelope")
    _validate_uuid(value["mobile_capture_id"])
    _validate_uuid(value["idempotency_key"])
    _validate_timestamp(value["created_at"])
    created_at = datetime.fromisoformat(value["created_at"].replace("Z", "+00:00")).astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if created_at > now + _MAX_CLOCK_SKEW or created_at < now - _MAX_ENVELOPE_AGE:
        raise ValueError("transport envelope expired or from the future")
    input_data, payload, plan, auth, transport = value["input"], value["payload"], value["source_plan"], value["authenticity"], value["transport"]
    if not isinstance(input_data, dict) or set(input_data) != {"kind", "original_name", "media_type"} or input_data["kind"] not in {"TEXT", "URL", "FILE"} or input_data["media_type"] != _media_type(input_data["kind"]) or (input_data["original_name"] is not None and not isinstance(input_data["original_name"], str)):
        raise ValueError("invalid transport input")
    if not isinstance(payload, dict) or payload.get("relative_path") != "payload/original" or not isinstance(payload.get("bytes"), int) or payload["bytes"] < 1 or not isinstance(payload.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", payload["sha256"]):
        raise ValueError("invalid transport payload")
    if plan != {"capture_method": f"IOS_SHARE_{input_data['kind']}", "requested_scope": "GLOBAL", "sensitivity_hint": "PERSONAL"}:
        raise ValueError("invalid transport source plan")
    if not isinstance(auth, dict) or set(auth) != {"device_key_id", "signature_algorithm", "envelope_signature"} or not all(isinstance(auth[key], str) and auth[key] for key in auth) or auth["signature_algorithm"] != _SIGNATURE_ALGORITHM or not re.fullmatch(r"[0-9a-f]{128}", auth["envelope_signature"]):
        raise ValueError("invalid transport authenticity")
    if transport != {"state": TransportStatus.LOCAL_PENDING}:
        raise ValueError("invalid transport state")


def _media_type(kind: str) -> str:
    return {"TEXT": "text/plain", "URL": "text/uri-list", "FILE": "application/octet-stream"}[kind]


def _valid_url(raw: bytes) -> bool:
    parsed = urlparse(raw.decode("utf-8"))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class PairedKeyRegistry:
    """Vault-local public-key trust registry; private signing material never enters Core."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)
        self.path = self.root / "registry.json"

    def register(self, public_key_pem: bytes) -> str:
        der = _validate_ed25519_public_key(public_key_pem)
        key_id = "ed25519:" + hashlib.sha256(der).hexdigest()
        registry = self._read()
        existing = registry["keys"].get(key_id)
        if existing and existing["public_key_pem"] != public_key_pem.decode("ascii"):
            raise ValueError("paired key id collision")
        if existing and existing["revoked_at"] is not None:
            raise ValueError("revoked key cannot be reactivated")
        registry["keys"][key_id] = {"public_key_pem": public_key_pem.decode("ascii"), "revoked_at": None}
        self._write(registry)
        return key_id

    def revoke(self, key_id: str) -> bool:
        registry = self._read()
        entry = registry["keys"].get(key_id)
        if entry is None or entry["revoked_at"] is not None:
            return False
        entry["revoked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        self._write(registry)
        return True

    def verify(self, key_id: str, algorithm: str, message: bytes, signature: str) -> bool:
        if algorithm != _SIGNATURE_ALGORITHM or not re.fullmatch(r"ed25519:[0-9a-f]{64}", key_id) or not re.fullmatch(r"[0-9a-f]{128}", signature):
            return False
        try:
            entry = self._read()["keys"].get(key_id)
            if entry is None or entry["revoked_at"] is not None:
                return False
            der = _validate_ed25519_public_key(entry["public_key_pem"].encode("ascii"))
            if "ed25519:" + hashlib.sha256(der).hexdigest() != key_id:
                return False
            with tempfile.TemporaryDirectory(prefix="tsuzu-r4-") as tmp:
                root = Path(tmp)
                (root / "public.pem").write_bytes(entry["public_key_pem"].encode("ascii"))
                (root / "message").write_bytes(message)
                (root / "signature").write_bytes(bytes.fromhex(signature))
                result = subprocess.run(
                    [_openssl_path(), "pkeyutl", "-verify", "-pubin", "-inkey", str(root / "public.pem"), "-sigfile", str(root / "signature"), "-rawin", "-in", str(root / "message")],
                    capture_output=True, timeout=5, check=False,
                )
                return result.returncode == 0
        except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
            return False

    def _read(self) -> dict[str, object]:
        if not self.path.exists():
            return {"schema_version": "1.0.0", "keys": {}}
        if self.root.is_symlink() or self.root.parent.is_symlink() or self.path.is_symlink():
            raise ValueError("paired-key registry path is symlink")
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or set(value) != {"schema_version", "keys"} or value["schema_version"] != "1.0.0" or not isinstance(value["keys"], dict):
            raise ValueError("invalid paired-key registry")
        for key_id, entry in value["keys"].items():
            if not isinstance(key_id, str) or not isinstance(entry, dict) or set(entry) != {"public_key_pem", "revoked_at"} or not isinstance(entry["public_key_pem"], str) or (entry["revoked_at"] is not None and not isinstance(entry["revoked_at"], str)):
                raise ValueError("invalid paired-key entry")
        return value

    def _write(self, value: dict[str, object]) -> None:
        if self.root.is_symlink() or self.root.parent.is_symlink():
            raise ValueError("paired-key registry path is symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = self.root / f".registry-{uuid.uuid4()}.tmp"
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                os.chmod(temporary, 0o600)
                json.dump(value, stream, sort_keys=True, separators=(",", ":"))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            _fsync_directory(self.root)
        finally:
            temporary.unlink(missing_ok=True)


def _openssl_path() -> str:
    path = shutil.which("openssl")
    if not path:
        raise FileNotFoundError("OpenSSL executable is required for Ed25519 verification")
    return path


def _validate_ed25519_public_key(public_key_pem: bytes) -> bytes:
    if not isinstance(public_key_pem, bytes) or len(public_key_pem) > 4096 or not public_key_pem.startswith(b"-----BEGIN PUBLIC KEY-----"):
        raise ValueError("expected an Ed25519 SPKI public key in PEM format")
    with tempfile.TemporaryDirectory(prefix="tsuzu-r4-key-") as tmp:
        root = Path(tmp)
        pem, der_path = root / "public.pem", root / "public.der"
        pem.write_bytes(public_key_pem)
        result = subprocess.run([_openssl_path(), "pkey", "-pubin", "-in", str(pem), "-outform", "DER", "-out", str(der_path)], capture_output=True, timeout=5, check=False)
        if result.returncode != 0:
            raise ValueError("invalid Ed25519 SPKI public key")
        der = der_path.read_bytes()
        if not der.startswith(bytes.fromhex("302a300506032b6570032100")):
            raise ValueError("public key is not Ed25519 SPKI")
        return der


def _reserve_mobile_event(root: Path, envelope: dict[str, object]) -> None:
    if root.is_symlink() or root.parent.is_symlink():
        raise ValueError("mobile event receipt path is symlink")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    event_id = envelope["mobile_capture_id"]
    digest = hashlib.sha256(_signed_bytes(envelope)).hexdigest()
    record = json.dumps({"mobile_capture_id": event_id, "envelope_sha256": digest}, sort_keys=True, separators=(",", ":")) + "\n"
    path = root / f"{event_id}.json"
    if path.is_symlink():
        raise ValueError("mobile event receipt is symlink")
    temporary = root / f".{event_id}-{uuid.uuid4()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            os.chmod(temporary, 0o600)
            stream.write(record)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_symlink() or not path.is_file() or path.read_text(encoding="utf-8") != record:
                raise ValueError("mobile capture event id replay conflict")
            return
        _fsync_directory(root)
    finally:
        temporary.unlink(missing_ok=True)
