"""Bounded public-web acquisition for already committed URL Sources (R1)."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

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
    max_redirects: int = 5


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
        parsed = urlparse(raw)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return False
        try:
            addresses = [parsed.hostname] if _is_ip(parsed.hostname) else self.resolver(parsed.hostname)
            return bool(addresses) and all(ipaddress.ip_address(address).is_global for address in addresses)
        except (OSError, ValueError):
            return False

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
