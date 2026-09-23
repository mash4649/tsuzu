"""Allowlisted Claude Code session observations (B1)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .canonical import CanonicalStore, CreateCanonicalIntent, ObjectRegistration, ObjectRegistry, _parse_manifest
from .capability import CapabilityRegistry, VERIFIED
from .capture import SecretScanner
from .vault import ActiveVaultLocator


class ChronicleStatus:
    CAPTURED = "CAPTURED"
    ALREADY_CAPTURED = "ALREADY_CAPTURED"
    NOT_CAPTURED_SCOPE = "NOT_CAPTURED_SCOPE"
    CHRONICLE_CAPTURE_UNAVAILABLE = "CHRONICLE_CAPTURE_UNAVAILABLE"
    INVALID_HOST_EVENT = "INVALID_HOST_EVENT"
    CONFLICTING_EVENT = "CONFLICTING_EVENT"
    SECRET_SCAN_UNAVAILABLE = "SECRET_SCAN_UNAVAILABLE"
    PERSISTENCE_FAILED = "PERSISTENCE_FAILED"
    PARTIAL_CAPTURED = "PARTIAL_CAPTURED"


@dataclass(frozen=True)
class AllowedObservation:
    host_id: str
    workspace: str
    session_id: str

    def __post_init__(self):
        if self.host_id != "CLAUDE_CODE" or not isinstance(self.workspace, str) or not Path(self.workspace).is_absolute():
            raise ValueError("observation scope must name an absolute Claude Code workspace")
        try:
            uuid.UUID(self.session_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("observation scope requires a session UUID") from exc


@dataclass(frozen=True)
class CapturedMessage:
    object_id: str
    actor: str
    sequence: int
    content_state: str


@dataclass(frozen=True)
class ChronicleResult:
    status: str
    messages: tuple[CapturedMessage, ...] = ()
    reason: str = ""


class SessionReader(Protocol):
    def read(self, session_id: str, workspace: str) -> list[object] | None: ...


class ClaudeAgentSessionReader:
    """Uses the official SDK's exact-session API; it never scans transcripts."""

    def read(self, session_id: str, workspace: str) -> list[object] | None:
        try:
            from claude_agent_sdk import get_session_info, get_session_messages
        except ImportError:
            return None
        try:
            if get_session_info(session_id, directory=workspace) is None:
                return None
            return list(get_session_messages(session_id, directory=workspace))
        except (OSError, ValueError):
            return None


class ChronicleCapture:
    def __init__(
        self,
        locator: ActiveVaultLocator,
        allowed: tuple[AllowedObservation, ...],
        registry: CapabilityRegistry,
        *,
        reader: SessionReader | None = None,
        scanner: SecretScanner | None = None,
    ):
        self.locator = locator
        self.allowed = frozenset(allowed)
        self.capabilities = registry
        self.reader = reader or ClaudeAgentSessionReader()
        self.scanner = scanner or SecretScanner()
        objects = ObjectRegistry()
        objects.register(ObjectRegistration("CONVERSATION_SESSION", "CANONICAL", "IMMUTABLE", "NONE", "B1"))
        objects.register(ObjectRegistration("CONVERSATION_MESSAGE", "CANONICAL", "IMMUTABLE", "OPTIONAL_PAYLOAD", "B1"))
        self.store = CanonicalStore(locator, objects)

    def capture(self, workspace: str, session_id: str) -> ChronicleResult:
        scope = AllowedObservation("CLAUDE_CODE", workspace, session_id)
        if scope not in self.allowed:
            return ChronicleResult(ChronicleStatus.NOT_CAPTURED_SCOPE)
        if any(self.capabilities.supports("claude_code", capability, "PROJECT") != VERIFIED for capability in ("CAPTURE_CONVERSATION", "WATCH_SCOPED_SESSION")):
            return ChronicleResult(ChronicleStatus.CHRONICLE_CAPTURE_UNAVAILABLE, reason="host capability is unverified")
        records = self.reader.read(session_id, workspace)
        if records is None:
            return ChronicleResult(ChronicleStatus.CHRONICLE_CAPTURE_UNAVAILABLE)
        try:
            normalized = tuple(_normalize(record, index) for index, record in enumerate(records))
            prepared = tuple(_prepare(record, self.scanner) for record in normalized)
        except ValueError as exc:
            return ChronicleResult(ChronicleStatus.INVALID_HOST_EVENT, reason=str(exc))
        except Exception:
            return ChronicleResult(ChronicleStatus.SECRET_SCAN_UNAVAILABLE)
        session_object_id = _stable_uuid(f"B1/session/v1/CLAUDE_CODE/{workspace}/{session_id}")
        session = self.store.append_canonical_event(CreateCanonicalIntent(
            "CONVERSATION_SESSION", session_object_id, "1.0.0", _now(), f"b1-session:{session_id}",
            _envelope("SYSTEM_OBSERVED", "OBSERVED", "OBSERVED", "claude_code", {"host_id": "CLAUDE_CODE", "host_session_ref": session_id, "workspace": workspace, "source_order": "SDK_SESSION_MESSAGES_V1"}),
        ))
        if session.status not in {"COMMITTED_LOCAL", "ALREADY_COMMITTED"}:
            return ChronicleResult(ChronicleStatus.PERSISTENCE_FAILED, reason=session.status)
        results: list[CapturedMessage] = []
        statuses: list[str] = [session.status]
        for event, content_state, payload in prepared:
            object_id = _stable_uuid(f"B1/message/v1/CLAUDE_CODE/{workspace}/{session_id}/{event.message_ref}")
            outcome = self.store.append_canonical_event(CreateCanonicalIntent(
                "CONVERSATION_MESSAGE", object_id, "1.0.0", _now(), f"b1-message:{session_id}:{event.message_ref}",
                _envelope("SYSTEM_OBSERVED", "OBSERVED", "OBSERVED", event.actor, {
                    "conversation_id": session_object_id,
                    "host_id": "CLAUDE_CODE",
                    "host_session_ref": session_id,
                    "host_message_ref": event.message_ref,
                    "workspace": workspace,
                    "sequence": event.sequence,
                    "actor": event.actor,
                    "observed_at": None,
                    "content_state": content_state,
                    "source_refs": [],
                }),
                payload,
            ))
            if outcome.status == "IDEMPOTENCY_CONFLICT":
                return ChronicleResult(ChronicleStatus.CONFLICTING_EVENT, tuple(results), outcome.reason)
            if outcome.status not in {"COMMITTED_LOCAL", "ALREADY_COMMITTED"}:
                return ChronicleResult(ChronicleStatus.PERSISTENCE_FAILED, tuple(results), outcome.status)
            statuses.append(outcome.status)
            results.append(CapturedMessage(object_id, event.actor, event.sequence, content_state))
        status = ChronicleStatus.ALREADY_CAPTURED if all(value == "ALREADY_COMMITTED" for value in statuses) else ChronicleStatus.CAPTURED
        return ChronicleResult(status, tuple(results))

    def inspect_message(self, object_id: str) -> dict[str, object]:
        inspected = self.store.inspect_canonical("CONVERSATION_MESSAGE", object_id)
        if inspected.status != "VALID" or inspected.path is None:
            raise ValueError("message is unavailable")
        return _parse_manifest((inspected.path / "object.md").read_text())

    def read_body(self, object_id: str) -> bytes | None:
        inspected = self.store.inspect_canonical("CONVERSATION_MESSAGE", object_id)
        if inspected.status != "VALID" or inspected.path is None:
            return None
        payload = inspected.path / "payload" / "original"
        return payload.read_bytes() if payload.exists() and not payload.is_symlink() else None


class CodexHookChronicleCapture:
    """Captures only stable, project-scoped Codex hook message fields; never reads transcripts."""

    def __init__(self, locator: ActiveVaultLocator, workspace: str | Path, *, scanner: SecretScanner | None = None):
        self.locator = locator
        self.workspace = str(Path(workspace).resolve())
        if not Path(self.workspace).is_absolute():
            raise ValueError("workspace must be absolute")
        self.scanner = scanner or SecretScanner()
        objects = ObjectRegistry()
        objects.register(ObjectRegistration("CONVERSATION_SESSION", "CANONICAL", "IMMUTABLE", "NONE", "B1N"))
        objects.register(ObjectRegistration("CONVERSATION_MESSAGE", "CANONICAL", "IMMUTABLE", "OPTIONAL_PAYLOAD", "B1N"))
        self.store = CanonicalStore(locator, objects)

    def capture(self, raw_event: object) -> ChronicleResult:
        if not isinstance(raw_event, dict):
            return ChronicleResult(ChronicleStatus.INVALID_HOST_EVENT)
        event_name = raw_event.get("hook_event_name")
        session_id, turn_id, cwd = (raw_event.get(key) for key in ("session_id", "turn_id", "cwd"))
        if event_name not in {"UserPromptSubmit", "Stop"} or not all(isinstance(value, str) and value.strip() for value in (session_id, turn_id, cwd)):
            return ChronicleResult(ChronicleStatus.INVALID_HOST_EVENT)
        try:
            if str(Path(cwd).resolve()) != self.workspace:
                return ChronicleResult(ChronicleStatus.NOT_CAPTURED_SCOPE)
        except OSError:
            return ChronicleResult(ChronicleStatus.NOT_CAPTURED_SCOPE)

        session_id = str(session_id)
        turn_id = str(turn_id)
        session_object_id = _stable_uuid(f"B1N/session/v1/CODEX/{self.workspace}/{session_id}")
        session = self.store.append_canonical_event(CreateCanonicalIntent(
            "CONVERSATION_SESSION", session_object_id, "1.0.0", _now(), f"b1n-session:{self.workspace}:{session_id}",
            _envelope("SYSTEM_OBSERVED", "OBSERVED", "OBSERVED", "SYSTEM_OBSERVED", {
                "host_id": "CODEX", "host_session_ref": session_id, "workspace": self.workspace,
                "source_order": "CODEX_HOOKS_V1", "capture_mode": "CODEX_HOOK_MESSAGE_ONLY", "coverage": "PARTIAL",
            }),
        ))
        if session.status not in {"COMMITTED_LOCAL", "ALREADY_COMMITTED"}:
            return ChronicleResult(ChronicleStatus.PERSISTENCE_FAILED, reason=session.status)

        if event_name == "UserPromptSubmit":
            actor, sequence, text = "USER", 0, raw_event.get("prompt")
        else:
            if not isinstance(raw_event.get("stop_hook_active"), bool):
                return ChronicleResult(ChronicleStatus.INVALID_HOST_EVENT)
            if raw_event["stop_hook_active"]:
                return ChronicleResult(ChronicleStatus.PARTIAL_CAPTURED)
            actor, sequence, text = "ASSISTANT", 1, raw_event.get("last_assistant_message")
            if not isinstance(text, str) or not text.strip():
                return ChronicleResult(ChronicleStatus.PARTIAL_CAPTURED)
        if not isinstance(text, str) or not text.strip() or len(text) > 12_000:
            return ChronicleResult(ChronicleStatus.INVALID_HOST_EVENT)

        message_ref = f"{turn_id}:{actor.lower()}"
        event = _HostEvent(message_ref, actor, sequence, text.encode("utf-8"))
        try:
            _, content_state, payload = _prepare(event, self.scanner)
        except ValueError as exc:
            return ChronicleResult(ChronicleStatus.INVALID_HOST_EVENT, reason=str(exc))
        except Exception:
            return ChronicleResult(ChronicleStatus.SECRET_SCAN_UNAVAILABLE)
        object_id = _stable_uuid(f"B1N/message/v1/CODEX/{self.workspace}/{session_id}/{message_ref}")
        outcome = self.store.append_canonical_event(CreateCanonicalIntent(
            "CONVERSATION_MESSAGE", object_id, "1.0.0", _now(), f"b1n-message:{self.workspace}:{session_id}:{message_ref}",
            _envelope("SYSTEM_OBSERVED", "OBSERVED", "OBSERVED", actor, {
                "conversation_id": session_object_id, "host_id": "CODEX", "host_session_ref": session_id,
                "host_message_ref": message_ref, "workspace": self.workspace, "sequence": sequence, "actor": actor,
                "observed_at": None, "content_state": content_state, "capture_mode": "CODEX_HOOK_MESSAGE_ONLY",
                "coverage": "PARTIAL", "source_refs": [],
            }),
            payload,
        ))
        if outcome.status == "IDEMPOTENCY_CONFLICT":
            return ChronicleResult(ChronicleStatus.CONFLICTING_EVENT)
        if outcome.status not in {"COMMITTED_LOCAL", "ALREADY_COMMITTED"}:
            return ChronicleResult(ChronicleStatus.PERSISTENCE_FAILED, reason=outcome.status)
        status = ChronicleStatus.ALREADY_CAPTURED if outcome.status == "ALREADY_COMMITTED" else ChronicleStatus.CAPTURED
        return ChronicleResult(status, (CapturedMessage(object_id, actor, sequence, content_state),))

    def inspect_message(self, object_id: str) -> dict[str, object]:
        inspected = self.store.inspect_canonical("CONVERSATION_MESSAGE", object_id)
        if inspected.status != "VALID" or inspected.path is None:
            raise ValueError("message is unavailable")
        return _parse_manifest((inspected.path / "object.md").read_text())

    def read_body(self, object_id: str) -> bytes | None:
        inspected = self.store.inspect_canonical("CONVERSATION_MESSAGE", object_id)
        if inspected.status != "VALID" or inspected.path is None:
            return None
        payload = inspected.path / "payload" / "original"
        return payload.read_bytes() if payload.exists() and not payload.is_symlink() else None


@dataclass(frozen=True)
class _HostEvent:
    message_ref: str
    actor: str
    sequence: int
    content: bytes


def _normalize(record: object, sequence: int) -> _HostEvent:
    kind = _field(record, "type")
    message_ref = _field(record, "uuid")
    message = _field(record, "message")
    if not isinstance(kind, str) or not isinstance(message_ref, str) or not message_ref or not isinstance(message, dict):
        raise ValueError("missing host message identity")
    if kind == "assistant":
        actor = "ASSISTANT"
    elif kind == "user":
        actor = "TOOL" if _field(record, "parent_tool_use_id") else "USER"
    elif kind == "system":
        actor = "SYSTEM_OBSERVED"
    else:
        raise ValueError("unsupported host actor")
    content = message.get("content")
    raw = _content_bytes(content)
    if not raw:
        raise ValueError("empty host content")
    return _HostEvent(message_ref, actor, sequence, raw)


def _content_bytes(content: object) -> bytes:
    if isinstance(content, str):
        return content.encode("utf-8")
    blocks = content if isinstance(content, list) else [content]
    if not blocks or any(not isinstance(block, dict) or block.get("type") not in {"text", "tool_use", "tool_result"} for block in blocks):
        raise ValueError("unsupported host content")
    return json.dumps(blocks, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _prepare(event: _HostEvent, scanner: SecretScanner) -> tuple[_HostEvent, str, bytes | None]:
    scan = scanner.scan_bytes(event.content)
    if scan.outcome == "BLOCKED_RESTRICTED":
        return event, "EXCLUDED_RESTRICTED", None
    if scan.outcome != "CLEAR":
        raise ValueError("secret scanner did not clear content")
    return event, "AVAILABLE", event.content


def _field(record: object, name: str) -> Any:
    return record.get(name) if isinstance(record, dict) else getattr(record, name, None)


def _stable_uuid(value: str) -> str:
    raw = bytearray(hashlib.sha256(value.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))


def _envelope(origin: str, explicitness: str, trust: str, actor: str, fields: dict[str, object]) -> dict[str, object]:
    return {
        "scope": {"scope_type": "GLOBAL", "scope_id": None},
        "provenance": {"origin": origin, "source_refs": [], "actor": actor, "explicitness": explicitness},
        "trust": {"level": trust, "confidence": 1.0},
        "sensitivity": {"level": "PERSONAL"},
        "temporal": {"valid_from": None, "valid_until": None},
        "deletion": {"state": "LIVE", "tombstoned_at": None},
        **fields,
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
