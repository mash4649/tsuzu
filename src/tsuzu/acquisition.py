"""Bounded public-web acquisition for already committed URL Sources (R1)."""

from __future__ import annotations

import hashlib
import gzip
import http.client
import ipaddress
import io
import json
import os
import socket
import ssl
import time
import uuid
import zlib
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

from .canonical import CanonicalStore, CreateCanonicalIntent, ObjectRegistration, ObjectRegistry
from .capture import SecretScanner
from .deletion import NOT_DELETED, DeletionResolver
from .source import SourceValidationError, parse_source, validate_payload
from .vault import ActiveVaultLocator
from .writer import AtomicSourceWriter


@dataclass(frozen=True)
class FetchRequest:
    request_id: str
    source_id: str
    url: str
    timeout_budget_ms: int = 15_000
    max_response_bytes: int = 5 * 1024 * 1024
    max_raw_response_bytes: int | None = None
    max_header_bytes: int = 64 * 1024
    max_redirects: int = 5
    connect_timeout_ms: int = 5_000
    credential_ref: str | None = None


@dataclass(frozen=True)
class FetchResult:
    status: str
    final_url: str | None = None
    body: bytes | None = None
    media_type: str | None = None
    http_status: int | None = None
    failure_code: str | None = None
    redirect_chain: tuple[str, ...] = ()

    @classmethod
    def success(cls, *, final_url: str, body: bytes, media_type: str, http_status: int = 200, redirect_chain: tuple[str, ...] = ()) -> "FetchResult":
        return cls("SUCCESS", final_url, body, media_type, http_status, redirect_chain=redirect_chain)

    @classmethod
    def auth_required(cls) -> "FetchResult":
        return cls("AUTH_REQUIRED", failure_code="AUTH_REQUIRED")


@dataclass(frozen=True)
class AcquisitionResult:
    status: str
    source_id: str
    acquisition_key: str = ""
    source_version_id: str | None = None
    reason: str = ""


class PublicWebFetcher:
    """Fetch public URLs one pinned hop at a time, rechecking every redirect."""

    adapter_id = "public_web"
    adapter_version = "1.0"

    def __init__(self, transport=None, *, resolver: Callable[[str], list[str]] | None = None):
        self.transport = transport or _http_transport
        self.resolver = resolver or _resolve_host

    def fetch(self, request: FetchRequest) -> FetchResult:
        if request.credential_ref is not None and urlparse(request.url).scheme != "https":
            return FetchResult("POLICY_BLOCKED", failure_code="CREDENTIAL_REQUIRES_HTTPS")
        deadline = time.monotonic() + request.timeout_budget_ms / 1000
        current_url = request.url
        redirect_chain: list[str] = []
        while True:
            remaining_ms = int((deadline - time.monotonic()) * 1000)
            if remaining_ms <= 0:
                return FetchResult("TRANSIENT_FAILURE", failure_code="TOTAL_TIMEOUT")
            address = _public_address(current_url, self.resolver)
            if address is None:
                return FetchResult("POLICY_BLOCKED", failure_code="UNSAFE_DESTINATION" if not redirect_chain else "UNSAFE_REDIRECT_DESTINATION")
            result = self.transport(replace(request, url=current_url, timeout_budget_ms=remaining_ms), address)
            if not isinstance(result, FetchResult):
                return FetchResult("PERMANENT_FAILURE", failure_code="MALFORMED_TRANSPORT_RESULT")
            if result.redirect_chain:
                return FetchResult("PERMANENT_FAILURE", failure_code="TRANSPORT_FOLLOWED_REDIRECT")
            if time.monotonic() >= deadline:
                return FetchResult("TRANSIENT_FAILURE", failure_code="TOTAL_TIMEOUT")
            if result.status != "REDIRECT":
                if result.status == "SUCCESS" and urljoin(current_url, result.final_url or "") != current_url:
                    return FetchResult("PERMANENT_FAILURE", failure_code="TRANSPORT_CHANGED_DESTINATION")
                return replace(result, final_url=current_url, redirect_chain=tuple(redirect_chain))
            if len(redirect_chain) >= request.max_redirects:
                return FetchResult("PERMANENT_FAILURE", failure_code="REDIRECT_LIMIT")
            if not result.final_url:
                return FetchResult("PERMANENT_FAILURE", failure_code="MALFORMED_REDIRECT")
            target = urljoin(current_url, result.final_url)
            redirect_chain.append(current_url)
            current_url = target


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, *, address: str, timeout: float):
        super().__init__(host, port=port, timeout=timeout)
        self._address = address

    def connect(self) -> None:
        self.sock = self._create_connection((self._address, self.port), self.timeout, self.source_address)
        if self._tunnel_host:
            self._tunnel()


class _PinnedHTTPSConnection(_PinnedHTTPConnection):
    def __init__(self, host: str, port: int, *, address: str, timeout: float):
        super().__init__(host, port, address=address, timeout=timeout)
        self._context = ssl.create_default_context()

    def connect(self) -> None:
        super().connect()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def _http_transport(request: FetchRequest, address: str) -> FetchResult:
    """Execute exactly one HTTP(S) hop against the resolver-approved address."""
    started = time.monotonic()
    raw_limit = request.max_raw_response_bytes if request.max_raw_response_bytes is not None else request.max_response_bytes
    if min(request.timeout_budget_ms, request.connect_timeout_ms, request.max_response_bytes, raw_limit, request.max_header_bytes) <= 0:
        return FetchResult("PERMANENT_FAILURE", failure_code="INVALID_FETCH_LIMIT")
    try:
        parsed = urlparse(request.url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return FetchResult("PERMANENT_FAILURE", failure_code="MALFORMED_URL")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        timeout = min(request.connect_timeout_ms, request.timeout_budget_ms) / 1000
        connection = (_PinnedHTTPSConnection if parsed.scheme == "https" else _PinnedHTTPConnection)(parsed.hostname, port, address=address, timeout=timeout)
        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"
        connection.request("GET", target, headers={"Host": parsed.netloc, "Accept-Encoding": "gzip, deflate", "Connection": "close"})
        response = connection.getresponse()
        _set_remaining_timeout(connection, started, request.timeout_budget_ms)
        if len(response.headers.as_bytes()) > request.max_header_bytes:
            return FetchResult("PERMANENT_FAILURE", failure_code="RESPONSE_HEADERS_TOO_LARGE")
        if 300 <= response.status < 400:
            location = response.getheader("Location")
            return FetchResult("REDIRECT", final_url=urljoin(request.url, location) if location else None, http_status=response.status, failure_code=None if location else "MALFORMED_REDIRECT")
        if not 200 <= response.status < 300:
            return FetchResult("TRANSIENT_FAILURE" if response.status in {408, 429} or response.status >= 500 else "PERMANENT_FAILURE", http_status=response.status, failure_code=f"HTTP_{response.status}")
        content_length = response.getheader("Content-Length")
        if content_length is not None and int(content_length) > raw_limit:
            return FetchResult("PERMANENT_FAILURE", failure_code="RESPONSE_RAW_TOO_LARGE")
        raw = response.read(raw_limit + 1)
        if len(raw) > raw_limit:
            return FetchResult("PERMANENT_FAILURE", failure_code="RESPONSE_RAW_TOO_LARGE")
        body = _decompress_limited(raw, response.getheader("Content-Encoding"), request.max_response_bytes)
        if body is None:
            return FetchResult("PERMANENT_FAILURE", failure_code="RESPONSE_DECOMPRESSED_TOO_LARGE")
        if time.monotonic() - started >= request.timeout_budget_ms / 1000:
            return FetchResult("TRANSIENT_FAILURE", failure_code="TOTAL_TIMEOUT")
        media_type = response.get_content_type().lower()
        return FetchResult.success(final_url=request.url, body=body, media_type=media_type, http_status=response.status)
    except (OSError, ValueError, http.client.HTTPException, zlib.error):
        if time.monotonic() - started >= request.timeout_budget_ms / 1000:
            return FetchResult("TRANSIENT_FAILURE", failure_code="TOTAL_TIMEOUT")
        return FetchResult("TRANSIENT_FAILURE", failure_code="TRANSPORT_FAILURE")
    finally:
        if "connection" in locals():
            connection.close()


def _set_remaining_timeout(connection: http.client.HTTPConnection, started: float, total_ms: int) -> None:
    remaining = total_ms / 1000 - (time.monotonic() - started)
    if remaining <= 0:
        raise TimeoutError
    if connection.sock is not None:
        connection.sock.settimeout(remaining)


def _decompress_limited(raw: bytes, content_encoding: str | None, limit: int) -> bytes | None:
    encoding = (content_encoding or "identity").lower().strip()
    if encoding in {"", "identity"}:
        return raw if len(raw) <= limit else None
    if encoding == "gzip":
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            body = stream.read(limit + 1)
    elif encoding == "deflate":
        decoder = zlib.decompressobj()
        body = decoder.decompress(raw, limit + 1)
        if decoder.unconsumed_tail:
            return None
        body += decoder.flush(limit + 1 - len(body))
    else:
        return None
    return body if len(body) <= limit else None


class AcquisitionService:
    """Materialize one immutable, body-checked remote representation per URL Source."""

    def __init__(
        self,
        locator: ActiveVaultLocator,
        *,
        scanner: SecretScanner | None = None,
        resolver: Callable[[str], list[str]] | None = None,
    ):
        self.locator = locator
        self.scanner = scanner or SecretScanner()
        self.resolver = resolver or _resolve_host
        registry = ObjectRegistry()
        registry.register(ObjectRegistration("SOURCE_VERSION", "CANONICAL", "IMMUTABLE", "PAYLOAD", "R1"))
        self.store = CanonicalStore(locator, registry)

    def acquire(self, source_id: str, adapter, *, max_response_bytes: int = 5 * 1024 * 1024) -> AcquisitionResult:
        parent = self._live_url_source(source_id)
        if parent is None:
            return AcquisitionResult("SOURCE_NOT_ELIGIBLE", source_id)
        url, manifest = parent
        acquisition_key = _acquisition_key(source_id, manifest)
        version_id = _version_id(acquisition_key)
        if self.store.inspect_canonical("SOURCE_VERSION", version_id).status == "VALID":
            return self._record(AcquisitionResult("ALREADY_ACQUIRED", source_id, acquisition_key, version_id))
        if not self._public_url(url):
            return self._record(AcquisitionResult("POLICY_BLOCKED", source_id, acquisition_key, reason="unsafe URL"))
        if not callable(getattr(adapter, "fetch", None)) or not isinstance(getattr(adapter, "adapter_id", None), str) or not getattr(adapter, "adapter_id") or not isinstance(getattr(adapter, "adapter_version", None), str) or not getattr(adapter, "adapter_version"):
            return self._record(AcquisitionResult("PERMANENT_FAILURE", source_id, acquisition_key, reason="malformed adapter"))
        request = FetchRequest(str(uuid.uuid4()), source_id, url, max_response_bytes=max_response_bytes)
        try:
            fetched = adapter.fetch(request)
        except Exception:
            return self._record(AcquisitionResult("RETRY_WAIT", source_id, acquisition_key, reason="adapter failure"))
        if not isinstance(fetched, FetchResult):
            return self._record(AcquisitionResult("PERMANENT_FAILURE", source_id, acquisition_key, reason="malformed adapter result"))
        if fetched.status == "AUTH_REQUIRED":
            return self._record(AcquisitionResult("USER_ACTION_REQUIRED", source_id, acquisition_key, reason="AUTH_REQUIRED"))
        if fetched.status != "SUCCESS":
            return self._record(AcquisitionResult("RETRY_WAIT" if fetched.status == "TRANSIENT_FAILURE" else "PERMANENT_FAILURE", source_id, acquisition_key, reason=fetched.failure_code or fetched.status))
        if not isinstance(fetched.final_url, str) or not isinstance(fetched.redirect_chain, tuple) or not all(isinstance(url, str) and self._public_url(url) for url in fetched.redirect_chain) or not self._public_url(fetched.final_url):
            return self._record(AcquisitionResult("POLICY_BLOCKED", source_id, acquisition_key, reason="unsafe redirect"))
        if not isinstance(fetched.body, bytes) or fetched.media_type not in {"text/plain", "text/html", "text/markdown", "application/json"}:
            return self._record(AcquisitionResult("PERMANENT_FAILURE", source_id, acquisition_key, reason="malformed success result"))
        if len(fetched.body) > max_response_bytes:
            return self._record(AcquisitionResult("PERMANENT_FAILURE", source_id, acquisition_key, reason="TOO_LARGE"))
        if self.scanner.scan_bytes(fetched.body).outcome != "CLEAR":
            return self._record(AcquisitionResult("BLOCKED_RESTRICTED", source_id, acquisition_key, reason="ACQUISITION_BLOCKED_RESTRICTED"))
        if self._live_url_source(source_id) is None:
            return self._record(AcquisitionResult("SOURCE_DELETED", source_id, acquisition_key))
        intent = CreateCanonicalIntent(
            "SOURCE_VERSION", version_id, "1.0.0", _now(), acquisition_key,
            {
                "scope": manifest["scope"],
                "provenance": {"origin": "EXTERNAL_SOURCE", "source_refs": [source_id], "actor": "EXTERNAL", "explicitness": "OBSERVED"},
                "trust": {"level": "UNTRUSTED", "confidence": 0.0},
                "sensitivity": manifest["sensitivity"],
                "temporal": {"valid_from": None, "valid_until": None},
                "deletion": {"state": "LIVE", "tombstoned_at": None},
                "parent_source_id": source_id,
                "version_kind": "ACQUIRED_REMOTE",
                "acquisition": {"adapter_id": adapter.adapter_id, "adapter_version": adapter.adapter_version, "requested_url_hash": _hash(url), "final_url_hash": _hash(fetched.final_url), "http_status": fetched.http_status, "media_type": fetched.media_type, "fidelity": "ORIGIN_RESPONSE", "acquisition_key_hash": acquisition_key},
            },
            fetched.body,
        )
        committed = self.store.create_canonical(intent)
        status = "ACQUIRED" if committed.status == "COMMITTED_LOCAL" else "ALREADY_ACQUIRED" if committed.status == "ALREADY_COMMITTED" else "PERMANENT_FAILURE"
        return self._record(AcquisitionResult(status, source_id, acquisition_key, version_id if status != "PERMANENT_FAILURE" else None, committed.reason))

    def schedule(self, source_id: str) -> AcquisitionResult:
        parent = self._live_url_source(source_id)
        if parent is None:
            return AcquisitionResult("SOURCE_NOT_ELIGIBLE", source_id)
        _, manifest = parent
        acquisition_key = _acquisition_key(source_id, manifest)
        root = self.locator.resolve_active_vault().root_ref / "system" / "acquisition-jobs"
        if root.is_symlink():
            return AcquisitionResult("PAUSED_ENVIRONMENT", source_id, acquisition_key, reason="job root is symlink")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = root / f"{acquisition_key}.json"
        if path.exists() and not path.is_symlink():
            return AcquisitionResult("ALREADY_SCHEDULED", source_id, acquisition_key)
        if path.is_symlink():
            return AcquisitionResult("PAUSED_ENVIRONMENT", source_id, acquisition_key, reason="job path is symlink")
        _write_json_atomic(path, {
            "job_id": _version_id(acquisition_key),
            "source_id": source_id,
            "source_revision": manifest["revision"],
            "acquisition_key_hash": acquisition_key,
            "state": "PENDING",
            "attempt_count": 0,
            "next_attempt_at": None,
            "terminal_reason": None,
        })
        return AcquisitionResult("SCHEDULED", source_id, acquisition_key)

    def run_scheduled_once(self, adapter, *, max_response_bytes: int = 5 * 1024 * 1024, max_attempts: int = 5) -> AcquisitionResult:
        root = self.locator.resolve_active_vault().root_ref / "system" / "acquisition-jobs"
        if root.is_symlink() or not root.exists():
            return AcquisitionResult("IDLE", "")
        for path in sorted(root.glob("*.json")):
            if path.is_symlink():
                continue
            try:
                job = json.loads(path.read_text())
                if job.get("state") not in {"PENDING", "RETRY_WAIT"}:
                    continue
                result = self.acquire(job["source_id"], adapter, max_response_bytes=max_response_bytes)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
            attempts = int(job.get("attempt_count", 0)) + 1
            if result.status == "RETRY_WAIT" and attempts >= max_attempts:
                result = AcquisitionResult("PERMANENT_FAILURE", result.source_id, result.acquisition_key, reason="retry limit reached")
            state = "ACQUIRED" if result.status in {"ACQUIRED", "ALREADY_ACQUIRED"} else result.status
            _write_json_atomic(path, {**job, "state": state, "attempt_count": attempts, "next_attempt_at": None, "terminal_reason": result.status})
            return result
        return AcquisitionResult("IDLE", "")

    def _live_url_source(self, source_id: str):
        if DeletionResolver(self.locator).resolve_source(source_id).state != NOT_DELETED:
            return None
        inspected = AtomicSourceWriter(self.locator).inspect_source(source_id)
        if inspected.status != "VALID":
            return None
        try:
            payload = (inspected.path / "payload" / "original").read_bytes()
            manifest = parse_source((inspected.path / "source.md").read_text())
            if manifest["source"]["kind"] != "URL" or manifest["deletion"]["state"] != "LIVE" or not validate_payload(manifest, payload):
                return None
            return payload.decode("utf-8"), manifest
        except (OSError, UnicodeDecodeError, SourceValidationError):
            return None

    def _public_url(self, raw: str) -> bool:
        return _public_address(raw, self.resolver) is not None

    def _record(self, result: AcquisitionResult) -> AcquisitionResult:
        root = self.locator.resolve_active_vault().root_ref / "system" / "acquisition-receipts"
        if root.is_symlink():
            return result
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = root / f"{result.acquisition_key}.json"
        if result.acquisition_key and not path.is_symlink():
            staged = root / f".{result.acquisition_key}.{uuid.uuid4().hex}.tmp"
            _write_json_atomic(path, {"source_id": result.source_id, "acquisition_key_hash": result.acquisition_key, "terminal_status": result.status, "source_version_id": result.source_version_id, "failure_code": result.status, "completed_at": _now()}, staged=staged)
        return result


def _resolve_host(host: str) -> list[str]:
    return sorted({item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})


def _public_address(raw: str, resolver: Callable[[str], list[str]]) -> str | None:
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return None
    try:
        addresses = [parsed.hostname] if _is_ip(parsed.hostname) else resolver(parsed.hostname)
        return addresses[0] if addresses and all(ipaddress.ip_address(address).is_global for address in addresses) else None
    except (OSError, ValueError):
        return None


def _acquisition_key(source_id: str, manifest: dict[str, object]) -> str:
    source = manifest["source"]
    return _hash(f"{source_id}:{manifest['revision']}:{source['payload_sha256']}:r1-public-web-1")


def _version_id(key: str) -> str:
    raw = bytearray(bytes.fromhex(key[:32]))
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _write_json_atomic(path: Path, value: dict[str, object], *, staged: Path | None = None) -> None:
    staged = staged or path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with staged.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(staged, path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
