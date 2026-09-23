"""Local Capture ingress, deterministic secret guard, and durable queue (A3)."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class CaptureStatus:
    ACCEPTED = "ACCEPTED"
    ALREADY_ACCEPTED = "ALREADY_ACCEPTED"
    REJECTED_RESTRICTED = "REJECTED_RESTRICTED"
    REJECTED_INVALID_INPUT = "REJECTED_INVALID_INPUT"
    REJECTED_TOO_LARGE = "REJECTED_TOO_LARGE"
    REJECTED_UNSUPPORTED_INPUT = "REJECTED_UNSUPPORTED_INPUT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    IO_FAILED = "IO_FAILED"
    COMMIT_UNCERTAIN = "COMMIT_UNCERTAIN"


@dataclass(frozen=True)
class CaptureRequest:
    request_id: str
    idempotency_key: str
    kind: str
    content: bytes | str | os.PathLike[str]
    original_name: str | None = None
    user_metadata: dict[str, object] | None = None
    sensitivity_override: str | None = None
    requested_at: str | None = None
    capture_method: str | None = None
    provenance: dict[str, object] | None = None
    import_metadata: dict[str, object] | None = None
    origin_locator: dict[str, object] | None = None


@dataclass(frozen=True)
class CaptureResult:
    status: str
    job_id: str | None = None
    source_id: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class SecretScanResult:
    outcome: str
    ruleset_version: str
    matched_rule_ids: tuple[str, ...]
    bytes_scanned: int
    payload_sha256: str


class SecretScanner:
    RULESET_VERSION = "a3-local-1.0"
    _rules = (
        ("PEM_PRIVATE_KEY", re.compile(rb"-----BEGIN(?: [A-Z0-9]+)* PRIVATE KEY-----")),
        ("OPENSSH_PRIVATE_KEY", re.compile(rb"-----BEGIN OPENSSH PRIVATE KEY-----")),
        ("KNOWN_TOKEN_PREFIX", re.compile(rb"(?:sk-|ghp_|xox[baprs]-|AKIA)[A-Za-z0-9_-]{16,}")),
        ("BEARER_TOKEN", re.compile(rb"\bBearer\s+[A-Za-z0-9._~-]{16,}")),
        ("JWT_CREDENTIAL", re.compile(rb"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
        ("SECRET_ASSIGNMENT", re.compile(rb"\b(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9_./+=:-]{16,}" , re.I)),
    )

    def scan_bytes(self, payload: bytes) -> SecretScanResult:
        return self.scan_stream(io.BytesIO(payload))

    def scan_stream(self, stream: io.BufferedIOBase, *, chunk_size: int = 65536) -> SecretScanResult:
        digest = hashlib.sha256()
        total = 0
        tail = b""
        matched: set[str] = set()
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            if not isinstance(chunk, bytes):
                raise ValueError("scanner requires a binary stream")
            total += len(chunk)
            digest.update(chunk)
            window = tail + chunk
            for rule_id, pattern in self._rules:
                if pattern.search(window):
                    matched.add(rule_id)
            matched.update(self._url_rule_ids(window))
            tail = window[-4096:]
        return SecretScanResult(
            "BLOCKED_RESTRICTED" if matched else "CLEAR",
            self.RULESET_VERSION,
            tuple(sorted(matched)),
            total,
            digest.hexdigest(),
        )

    @staticmethod
    def _url_rule_ids(window: bytes) -> set[str]:
        try:
            text = window.decode("utf-8")
        except UnicodeDecodeError:
            return set()
        ids: set[str] = set()
        for candidate in re.findall(r"https?://[^\s<>\"]+", text, flags=re.I):
            parsed = urlparse(candidate)
            if parsed.username or parsed.password:
                ids.add("URL_USERINFO_CREDENTIAL")
            for key, values in parse_qs(parsed.query, keep_blank_values=True).items():
                if key.lower() in {"access_token", "api_key", "apikey", "signature", "sig", "token"} and any(len(value) >= 16 for value in values):
                    ids.add("SIGNED_URL_CREDENTIAL")
        return ids


class CaptureService:
    def __init__(
        self,
        queue_root: str | os.PathLike[str],
        *,
        scanner: SecretScanner | None = None,
        max_text_bytes: int = 1 * 1024 * 1024,
        max_url_bytes: int = 16 * 1024,
        max_file_bytes: int = 100 * 1024 * 1024,
        failure_injector=None,
    ):
        self.root = Path(queue_root)
        self.scanner = scanner or SecretScanner()
        self.max_text_bytes = max_text_bytes
        self.max_url_bytes = max_url_bytes
        self.max_file_bytes = max_file_bytes
        self.failure_injector = failure_injector

    def capture(self, request: CaptureRequest) -> CaptureResult:
        try:
            _validate_request_identity(request)
        except ValueError as exc:
            return CaptureResult(CaptureStatus.REJECTED_INVALID_INPUT, reason=str(exc))
        if not isinstance(request.kind, str):
            return CaptureResult(CaptureStatus.REJECTED_INVALID_INPUT, reason="capture kind is required")
        kind = request.kind.upper()
        if kind not in {"TEXT", "URL", "FILE"}:
            return CaptureResult(CaptureStatus.REJECTED_INVALID_INPUT, reason="unsupported capture kind")
        try:
            if kind == "FILE":
                if isinstance(request.content, bytes):
                    if not request.content:
                        return CaptureResult(CaptureStatus.REJECTED_INVALID_INPUT, reason="empty input")
                    if len(request.content) > self.max_file_bytes:
                        return CaptureResult(CaptureStatus.REJECTED_TOO_LARGE, reason="file exceeds limit")
                    return self._accept(request, "FILE", request.content, self.scanner.scan_bytes(request.content), original_name=request.original_name)
                return self._capture_file(request)
            raw = _as_utf8_bytes(request.content)
            if not raw:
                return CaptureResult(CaptureStatus.REJECTED_INVALID_INPUT, reason="empty input")
            limit = self.max_url_bytes if kind == "URL" else self.max_text_bytes
            if len(raw) > limit:
                return CaptureResult(CaptureStatus.REJECTED_TOO_LARGE, reason="input exceeds limit")
            if kind == "URL" and not _valid_url(raw):
                return CaptureResult(CaptureStatus.REJECTED_INVALID_INPUT, reason="URL must be HTTP(S)")
            scan = self.scanner.scan_bytes(raw)
            return self._accept(request, kind, raw, scan)
        except UnicodeDecodeError:
            return CaptureResult(CaptureStatus.REJECTED_INVALID_INPUT, reason="input must be UTF-8")
        except ValueError as exc:
            return CaptureResult(CaptureStatus.REJECTED_INVALID_INPUT, reason=str(exc))
        except OSError as exc:
            return CaptureResult(CaptureStatus.IO_FAILED, reason=str(exc))

    def read_job(self, job_id: str) -> dict[str, object]:
        _validate_uuid(job_id)
        path = self.root / "pending" / job_id / "job.json"
        if path.is_symlink() or not path.exists():
            raise ValueError("job is missing")
        job = json.loads(path.read_text())
        _validate_job(job, job_id)
        return job

    def _capture_file(self, request: CaptureRequest) -> CaptureResult:
        path = Path(request.content)
        if path.is_symlink() or not path.exists() or not path.is_file():
            return CaptureResult(CaptureStatus.REJECTED_UNSUPPORTED_INPUT, reason="FILE must be a regular non-symlink file")
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(path, flags)
            with os.fdopen(fd, "rb") as stream:
                stat = os.fstat(stream.fileno())
                if not _is_regular(stat.st_mode):
                    return CaptureResult(CaptureStatus.REJECTED_UNSUPPORTED_INPUT, reason="FILE must be regular")
                if stat.st_size <= 0:
                    return CaptureResult(CaptureStatus.REJECTED_INVALID_INPUT, reason="empty input")
                if stat.st_size > self.max_file_bytes:
                    return CaptureResult(CaptureStatus.REJECTED_TOO_LARGE, reason="file exceeds limit")
                scan = self.scanner.scan_stream(stream)
                if scan.outcome != "CLEAR":
                    return CaptureResult(CaptureStatus.REJECTED_RESTRICTED, reason="secret guard blocked input")
                stream.seek(0)
                raw = stream.read()
                if len(raw) != scan.bytes_scanned or hashlib.sha256(raw).hexdigest() != scan.payload_sha256:
                    return CaptureResult(CaptureStatus.IO_FAILED, reason="file changed during capture")
                name = request.original_name or path.name
                return self._accept(request, "FILE", raw, scan, original_name=Path(name).name)
        except (OSError, TypeError, ValueError) as exc:
            return CaptureResult(CaptureStatus.REJECTED_UNSUPPORTED_INPUT, reason=str(exc))

    def _accept(
        self,
        request: CaptureRequest,
        kind: str,
        raw: bytes,
        scan: SecretScanResult,
        *,
        original_name: str | None = None,
    ) -> CaptureResult:
        if scan.outcome != "CLEAR":
            return CaptureResult(CaptureStatus.REJECTED_RESTRICTED, reason="secret guard blocked input")
        sensitivity = _effective_sensitivity(request.sensitivity_override)
        if sensitivity == "RESTRICTED":
            return CaptureResult(CaptureStatus.REJECTED_RESTRICTED, reason="restricted sensitivity is not queueable")
        scope = _scope(request.user_metadata)
        origin_locator = _origin_locator(request.origin_locator, kind, raw)
        method = request.capture_method or f"LOCAL_{kind}"
        provenance = request.provenance
        import_metadata = request.import_metadata
        _validate_ingress(kind, method, provenance, import_metadata)
        fingerprint = _fingerprint(
            kind, scan.payload_sha256, len(raw), sensitivity, original_name, scope, origin_locator,
            capture_method=method, provenance=provenance, import_metadata=import_metadata,
        )
        key_hash = hashlib.sha256(request.idempotency_key.encode()).hexdigest()
        if request.requested_at is not None:
            _validate_timestamp(request.requested_at)
        _ensure_queue_layout(self.root)
        existing = self._find_idempotency(key_hash, fingerprint)
        if existing:
            return existing
        job_id = str(uuid.uuid4())
        source_id = str(uuid.uuid4())
        requested_at = request.requested_at or _now()
        plan = {
            "kind": kind,
            "capture_method": method,
            "media_type": "text/plain" if kind == "TEXT" else "text/uri-list" if kind == "URL" else "application/octet-stream",
            "original_name": original_name,
            "origin_locator": origin_locator,
            "scope": scope,
            "effective_sensitivity": sensitivity,
            "captured_at": requested_at,
        }
        if provenance is not None:
            plan["provenance"] = provenance
        if import_metadata is not None:
            plan["import"] = import_metadata
        job = {
            "job_id": job_id,
            "job_schema_version": "1.0.0",
            "request_id": request.request_id,
            "idempotency_key_hash": key_hash,
            "source_id": source_id,
            "created_at": requested_at,
            "state": "PENDING",
            "source_plan": plan,
            "payload": {"relative_path": "payload/original", "sha256": scan.payload_sha256, "bytes": len(raw)},
            "guard": {"secret_ruleset_version": scan.ruleset_version, "matched_rule_ids": []},
            "fingerprint": fingerprint,
        }
        return self._publish(job, raw)

    def _find_idempotency(self, key_hash: str, fingerprint: str) -> CaptureResult | None:
        receipts = self.root / "receipts"
        if receipts.exists() and not receipts.is_symlink():
            receipt = receipts / f"{key_hash}.json"
            if receipt.exists() and not receipt.is_symlink():
                try:
                    record = json.loads(receipt.read_text())
                    if record.get("request_fingerprint") != fingerprint:
                        return CaptureResult(CaptureStatus.IDEMPOTENCY_CONFLICT, reason="idempotency key fingerprint differs")
                    if record.get("terminal_state") == "BLOCKED_RESTRICTED":
                        return CaptureResult(CaptureStatus.REJECTED_RESTRICTED, reason="secret guard receipt exists")
                    return CaptureResult(CaptureStatus.ALREADY_ACCEPTED, record.get("job_id"), record.get("source_id"))
                except (OSError, json.JSONDecodeError):
                    return CaptureResult(CaptureStatus.IO_FAILED, reason="capture receipt is unreadable")
        pending = self.root / "pending"
        if not pending.exists():
            return None
        for directory in pending.iterdir():
            if directory.is_symlink() or not directory.is_dir():
                continue
            path = directory / "job.json"
            try:
                job = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if job.get("idempotency_key_hash") == key_hash:
                if job.get("fingerprint") != fingerprint:
                    return CaptureResult(CaptureStatus.IDEMPOTENCY_CONFLICT, reason="idempotency key fingerprint differs")
                return CaptureResult(CaptureStatus.ALREADY_ACCEPTED, job["job_id"], job["source_id"])
        return None

    def _publish(self, job: dict[str, object], raw: bytes) -> CaptureResult:
        tx_root = self.root / "staging" / str(uuid.uuid4())
        final = self.root / "pending" / job["job_id"]
        published = False
        try:
            _ensure_queue_layout(self.root)
            tx_root.mkdir(parents=True, exist_ok=False, mode=0o700)
            payload = tx_root / "payload" / "original"
            payload.parent.mkdir(mode=0o700)
            _write_bytes(payload, raw)
            self._failure("payload_copied")
            _write_text(tx_root / "job.json", json.dumps(job, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
            self._failure("job_written")
            _validate_job(json.loads((tx_root / "job.json").read_text()), job["job_id"])
            self._failure("before_publish")
            if final.exists() or final.is_symlink():
                raise OSError("capture job destination already exists")
            os.rename(tx_root, final)
            published = True
            self._failure("after_publish")
            _fsync_directory(final.parent)
            _validate_job(json.loads((final / "job.json").read_text()), job["job_id"])
            return CaptureResult(CaptureStatus.ACCEPTED, job["job_id"], job["source_id"])
        except OSError as exc:
            return CaptureResult(CaptureStatus.COMMIT_UNCERTAIN if published else CaptureStatus.IO_FAILED, job["job_id"], job["source_id"], str(exc))
        except ValueError as exc:
            return CaptureResult(CaptureStatus.IO_FAILED, job["job_id"], job["source_id"], str(exc))
        finally:
            if tx_root.exists():
                shutil.rmtree(tx_root, ignore_errors=True)

    def _failure(self, stage: str) -> None:
        if self.failure_injector:
            self.failure_injector(stage)


def _validate_request_identity(request: CaptureRequest) -> None:
    _validate_uuid(request.request_id)
    if not isinstance(request.idempotency_key, str) or not request.idempotency_key:
        raise ValueError("idempotency key is required")


def _validate_uuid(value: str) -> None:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError("UUIDv4 is required") from exc
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("UUIDv4 is required")


def _as_utf8_bytes(content: bytes | str | os.PathLike[str]) -> bytes:
    if isinstance(content, bytes):
        content.decode("utf-8")
        return content
    if isinstance(content, str):
        return content.encode("utf-8")
    raise ValueError("TEXT and URL content must be text or bytes")


def _valid_url(raw: bytes) -> bool:
    parsed = urlparse(raw.decode("utf-8"))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _effective_sensitivity(override: str | None) -> str:
    if override is None:
        return "PERSONAL"
    if override not in {"PUBLIC", "PERSONAL", "SENSITIVE", "RESTRICTED"}:
        raise ValueError("invalid sensitivity override")
    return override


def _scope(metadata: dict[str, object] | None) -> dict[str, object]:
    if not metadata or "scope" not in metadata:
        return {"scope_type": "GLOBAL", "scope_id": None}
    value = metadata["scope"]
    if not isinstance(value, dict) or set(value) != {"scope_type", "scope_id"}:
        raise ValueError("invalid scope")
    if value["scope_type"] != "GLOBAL" or value["scope_id"] is not None:
        raise ValueError("A1 MVP scope is GLOBAL")
    return value


def _origin_locator(value: dict[str, object] | None, kind: str, raw: bytes) -> dict[str, str | None]:
    if value is None:
        return {"type": "URL", "value": raw.decode("utf-8")} if kind == "URL" else {"type": "NONE", "value": None}
    if set(value) != {"type", "value"} or not isinstance(value["type"], str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", value["type"]):
        raise ValueError("invalid origin locator")
    if value["value"] is not None and (not isinstance(value["value"], str) or len(value["value"]) > 512):
        raise ValueError("invalid origin locator")
    return {"type": value["type"], "value": value["value"]}


def _fingerprint(
    kind: str, digest: str, size: int, sensitivity: str, original_name: str | None, scope: dict[str, object], origin_locator: dict[str, object],
    *, capture_method: str | None = None, provenance: dict[str, object] | None = None, import_metadata: dict[str, object] | None = None,
) -> str:
    stable_import = None if import_metadata is None else {key: value for key, value in import_metadata.items() if key != "import_session_id"}
    value = {"kind": kind, "capture_method": capture_method or f"LOCAL_{kind}", "sha256": digest, "bytes": size, "sensitivity": sensitivity, "original_name": original_name, "scope": scope, "origin_locator": origin_locator, "provenance": provenance, "import": stable_import}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _ensure_queue_layout(root: Path) -> None:
    for path in (root, root / "pending", root / "staging"):
        if path.is_symlink():
            raise OSError("queue path is symlink")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)


def _validate_job(job: object, job_id: str) -> None:
    if not isinstance(job, dict) or job.get("job_id") != job_id or job.get("job_schema_version") != "1.0.0" or job.get("state") != "PENDING":
        raise ValueError("invalid capture job")
    _validate_uuid(job.get("source_id"))
    _validate_uuid(job.get("request_id"))
    if not re.fullmatch(r"[0-9a-f]{64}", str(job.get("idempotency_key_hash"))):
        raise ValueError("invalid idempotency hash")
    _validate_timestamp(job.get("created_at"))
    if not isinstance(job.get("payload"), dict) or job["payload"].get("relative_path") != "payload/original":
        raise ValueError("invalid capture payload metadata")
    if not re.fullmatch(r"[0-9a-f]{64}", str(job["payload"].get("sha256"))):
        raise ValueError("invalid capture payload hash")
    if not isinstance(job["payload"].get("bytes"), int) or job["payload"]["bytes"] < 1:
        raise ValueError("invalid capture payload size")
    guard = job.get("guard")
    if not isinstance(guard, dict) or not isinstance(guard.get("secret_ruleset_version"), str) or guard.get("matched_rule_ids") != []:
        raise ValueError("invalid guard metadata")
    plan = job.get("source_plan")
    if not isinstance(plan, dict):
        raise ValueError("invalid source plan")
    _validate_ingress(plan.get("kind"), plan.get("capture_method"), plan.get("provenance"), plan.get("import"))


def _validate_ingress(kind: object, capture_method: object, provenance: object, import_metadata: object) -> None:
    allowed = {
        "TEXT": {"LOCAL_TEXT", "CODEX_USER_PROMPT", "IMPORT_APPLE_NOTES", "IMPORT_MARKDOWN", "IOS_SHARE_TEXT"},
        "URL": {"LOCAL_URL", "IMPORT_APPLE_NOTES", "IMPORT_MARKDOWN", "IOS_SHARE_URL"},
        "FILE": {"LOCAL_FILE", "IMPORT_APPLE_NOTES", "IMPORT_MARKDOWN", "IOS_SHARE_FILE"},
    }
    if kind not in allowed or capture_method not in allowed[kind]:
        raise ValueError("invalid capture ingress")
    imported = str(capture_method).startswith("IMPORT_")
    if imported:
        if provenance != {"origin": "IMPORTED", "source_refs": [], "actor": "USER", "explicitness": "IMPORT_REQUESTED"} or not isinstance(import_metadata, dict):
            raise ValueError("invalid import ingress")
    elif provenance is not None or import_metadata is not None:
        raise ValueError("unexpected ingress metadata")


def _is_regular(mode: int) -> bool:
    import stat

    return stat.S_ISREG(mode)


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


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _validate_timestamp(value: object) -> None:
    from datetime import datetime

    if not isinstance(value, str):
        raise ValueError("timestamp must be text")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
