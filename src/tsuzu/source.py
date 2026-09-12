"""Canonical Source schema, codec, and payload integrity checks (A1)."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse


SCHEMA_VERSION = "1.0.0"
_SOURCE_METHODS = {"TEXT": "LOCAL_TEXT", "URL": "LOCAL_URL", "FILE": "LOCAL_FILE"}
_TOP_LEVEL = {
    "object_id",
    "object_type",
    "schema_version",
    "created_at",
    "updated_at",
    "revision",
    "scope",
    "provenance",
    "trust",
    "sensitivity",
    "temporal",
    "deletion",
    "source",
}
_SOURCE_FIELDS = {
    "kind",
    "capture_method",
    "media_type",
    "encoding",
    "original_name",
    "origin_locator",
    "payload_path",
    "payload_sha256",
    "payload_bytes",
    "captured_at",
}


class SourceValidationError(ValueError):
    """A Source manifest or payload does not satisfy the A1 contract."""


def create_source(
    payload: bytes | str,
    *,
    kind: str,
    capture_method: str,
    object_id: str | None = None,
    original_name: str | None = None,
    origin_locator: dict[str, object] | None = None,
    sensitivity: str = "PERSONAL",
    captured_at: str | None = None,
) -> dict[str, object]:
    if kind not in _SOURCE_METHODS or capture_method != _SOURCE_METHODS[kind]:
        raise SourceValidationError("source kind and capture method do not match")
    if kind == "FILE" and isinstance(payload, str):
        raise SourceValidationError("FILE payload must be bytes")
    raw = payload.encode("utf-8") if isinstance(payload, str) else payload
    if not isinstance(raw, bytes):
        raise SourceValidationError("payload must be bytes or text")
    if kind in {"TEXT", "URL"}:
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SourceValidationError("text and URL payloads must be UTF-8") from exc
        if kind == "URL" and not _is_http_url(decoded):
            raise SourceValidationError("URL payload must be an HTTP(S) URL")
    if sensitivity not in {"PUBLIC", "PERSONAL", "SENSITIVE", "RESTRICTED"}:
        raise SourceValidationError("invalid sensitivity level")
    now = captured_at or _now()
    source = {
        "object_id": object_id or str(uuid.uuid4()),
        "object_type": "SOURCE",
        "schema_version": SCHEMA_VERSION,
        "created_at": now,
        "updated_at": now,
        "revision": 1,
        "scope": {"scope_type": "GLOBAL", "scope_id": None},
        "provenance": {
            "origin": "USER_EXPLICIT",
            "source_refs": [],
            "actor": "USER",
            "explicitness": "EXPLICIT",
        },
        "trust": {"level": "ASSERTED", "confidence": 1.0},
        "sensitivity": {"level": sensitivity},
        "temporal": {"valid_from": None, "valid_until": None},
        "deletion": {"state": "LIVE", "tombstoned_at": None},
        "source": {
            "kind": kind,
            "capture_method": capture_method,
            "media_type": "text/plain" if kind == "TEXT" else "text/uri-list" if kind == "URL" else "application/octet-stream",
            "encoding": "utf-8" if kind != "FILE" else "binary",
            "original_name": original_name,
            "origin_locator": origin_locator or {"type": "NONE", "value": None},
            "payload_path": "payload/original",
            "payload_sha256": hashlib.sha256(raw).hexdigest(),
            "payload_bytes": len(raw),
            "captured_at": now,
        },
    }
    validate_source(source)
    return source


def validate_source(
    manifest: object, *, expected_object_id: str | None = None
) -> None:
    if not isinstance(manifest, dict) or set(manifest) != _TOP_LEVEL:
        raise SourceValidationError("Source envelope fields are invalid")
    if manifest["object_type"] != "SOURCE" or manifest["schema_version"] != SCHEMA_VERSION:
        raise SourceValidationError("unsupported Source type or schema version")
    object_id = manifest["object_id"]
    try:
        parsed_id = uuid.UUID(str(object_id))
    except (ValueError, AttributeError) as exc:
        raise SourceValidationError("object_id must be a UUID") from exc
    if parsed_id.version != 4 or str(parsed_id) != object_id:
        raise SourceValidationError("object_id must be a canonical UUIDv4")
    if expected_object_id is not None and object_id != expected_object_id:
        raise SourceValidationError("object_id does not match expected identity")
    for key in ("created_at", "updated_at"):
        _timestamp(manifest[key])
    if isinstance(manifest["revision"], bool) or not isinstance(manifest["revision"], int) or manifest["revision"] < 1:
        raise SourceValidationError("revision must be a positive integer")

    scope = _mapping(manifest["scope"], {"scope_type", "scope_id"})
    if scope["scope_type"] != "GLOBAL" or scope["scope_id"] is not None:
        raise SourceValidationError("A1 Source scope must be GLOBAL")
    provenance = _mapping(manifest["provenance"], {"origin", "source_refs", "actor", "explicitness"})
    if provenance["origin"] not in {"USER_EXPLICIT", "IMPORTED"}:
        raise SourceValidationError("invalid provenance origin")
    if not isinstance(provenance["source_refs"], list) or any(not isinstance(item, str) for item in provenance["source_refs"]):
        raise SourceValidationError("source_refs must be a string list")
    if not isinstance(provenance["actor"], str) or not provenance["actor"]:
        raise SourceValidationError("invalid provenance actor")
    if provenance["explicitness"] not in {"EXPLICIT", "IMPORTED"}:
        raise SourceValidationError("invalid provenance explicitness")

    trust = _mapping(manifest["trust"], {"level", "confidence"})
    if trust["level"] not in {"UNTRUSTED", "INFERRED", "ASSERTED", "OBSERVED"}:
        raise SourceValidationError("invalid trust level")
    if isinstance(trust["confidence"], bool) or not isinstance(trust["confidence"], (int, float)) or not 0 <= trust["confidence"] <= 1:
        raise SourceValidationError("invalid trust confidence")

    sensitivity = _mapping(manifest["sensitivity"], {"level"})
    if sensitivity["level"] not in {"PUBLIC", "PERSONAL", "SENSITIVE", "RESTRICTED"}:
        raise SourceValidationError("invalid sensitivity level")
    temporal = _mapping(manifest["temporal"], {"valid_from", "valid_until"})
    for value in temporal.values():
        if value is not None:
            _timestamp(value)
    deletion = _mapping(manifest["deletion"], {"state", "tombstoned_at"})
    if deletion["state"] not in {"LIVE", "TOMBSTONED"}:
        raise SourceValidationError("invalid deletion state")
    if deletion["tombstoned_at"] is not None:
        _timestamp(deletion["tombstoned_at"])

    source = _mapping(manifest["source"], _SOURCE_FIELDS)
    kind = source["kind"]
    if kind not in _SOURCE_METHODS or source["capture_method"] != _SOURCE_METHODS[kind]:
        raise SourceValidationError("invalid source kind or capture method")
    expected_media = {"TEXT": "text/plain", "URL": "text/uri-list", "FILE": "application/octet-stream"}[kind]
    expected_encoding = "binary" if kind == "FILE" else "utf-8"
    if source["media_type"] != expected_media or source["encoding"] != expected_encoding:
        raise SourceValidationError("source media metadata does not match kind")
    for field in ("media_type", "encoding", "payload_path", "captured_at"):
        if not isinstance(source[field], str) or not source[field]:
            raise SourceValidationError("invalid source metadata")
    if source["payload_path"] != "payload/original" or ".." in source["payload_path"].split("/"):
        raise SourceValidationError("invalid payload path")
    if source["original_name"] is not None and not isinstance(source["original_name"], str):
        raise SourceValidationError("invalid original name")
    origin_locator = _mapping(source["origin_locator"], {"type", "value"})
    if not isinstance(origin_locator["type"], str) or (origin_locator["value"] is not None and not isinstance(origin_locator["value"], str)):
        raise SourceValidationError("invalid origin locator")
    if not isinstance(source["payload_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", source["payload_sha256"]):
        raise SourceValidationError("invalid payload hash")
    if isinstance(source["payload_bytes"], bool) or not isinstance(source["payload_bytes"], int) or source["payload_bytes"] < 0:
        raise SourceValidationError("invalid payload length")
    _timestamp(source["captured_at"])
def validate_payload(manifest: object, payload: bytes | None) -> bool:
    try:
        validate_source(manifest)
    except SourceValidationError:
        return False
    if payload is None or not isinstance(payload, bytes):
        return False
    source = manifest["source"]
    return len(payload) == source["payload_bytes"] and hashlib.sha256(payload).hexdigest() == source["payload_sha256"]


def serialize_source(manifest: object) -> str:
    validate_source(manifest)
    frontmatter = json.dumps(manifest, ensure_ascii=False, indent=2, separators=(",", ": "))
    return f"---\n{frontmatter}\n---\n"


def parse_source(document: str) -> dict[str, object]:
    if not isinstance(document, str) or not document.startswith("---\n"):
        raise SourceValidationError("Source manifest must start with frontmatter")
    end = document.find("\n---\n", 4)
    if end < 0 or document[end + 5 :].strip():
        raise SourceValidationError("Source Markdown body must be empty")
    try:
        manifest = json.loads(document[4:end])
    except json.JSONDecodeError as exc:
        raise SourceValidationError("invalid Source frontmatter") from exc
    validate_source(manifest)
    return manifest


def update_source_metadata(
    manifest: object, *, expected_revision: int, **changes: object
) -> dict[str, object]:
    validate_source(manifest)
    if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or manifest["revision"] != expected_revision:
        raise SourceValidationError("Source revision conflict")
    allowed = {"scope", "provenance", "sensitivity", "temporal", "deletion"}
    if not changes or set(changes) - allowed:
        raise SourceValidationError("only explicit Source metadata may be updated")
    updated = copy.deepcopy(manifest)
    for key, value in changes.items():
        if key == "sensitivity" and isinstance(value, str):
            value = {"level": value}
        updated[key] = value
    updated["revision"] += 1
    updated["updated_at"] = _now()
    validate_source(updated)
    return updated


def _mapping(value: object, keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise SourceValidationError("invalid nested Source object")
    return value


def _timestamp(value: object) -> None:
    if not isinstance(value, str):
        raise SourceValidationError("timestamp must be text")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceValidationError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise SourceValidationError("timestamp must include timezone")


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
