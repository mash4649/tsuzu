"""B2 Derived Episode schema; segmentation and persistence remain owner work."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EpisodeDraft:
    conversation_ref: str
    message_refs: tuple[tuple[str, str], ...]
    start_observed_at: str
    end_observed_at: str
    topic_label: str
    working_summary: str
    algorithm_version: str
    confidence: float
    included_message_count: int
    excluded_restricted_count: int
    processing_state: str = "DERIVED"


@dataclass(frozen=True)
class EpisodeMessage:
    conversation_ref: str
    message_id: str
    actor: str
    observed_at: str
    content_state: str
    text: str | None


def segment_messages(messages: tuple[EpisodeMessage, ...], algorithm_version: str) -> tuple[EpisodeDraft, ...]:
    """Conservative local baseline: only an explicit user topic marker creates a boundary."""
    if not messages or not isinstance(algorithm_version, str) or not algorithm_version:
        return ()
    if len({item.conversation_ref for item in messages}) != 1:
        raise ValueError("Episode cannot merge host sessions")
    groups: list[list[EpisodeMessage]] = [[]]
    for message in messages:
        if message.content_state not in {"AVAILABLE", "EXCLUDED_RESTRICTED"} or message.actor not in {"USER", "ASSISTANT", "TOOL", "SYSTEM_OBSERVED"}:
            raise ValueError("invalid Chronicle message")
        if groups[-1] and message.actor == "USER" and isinstance(message.text, str) and message.text.lower().startswith("new topic:"):
            groups.append([])
        groups[-1].append(message)
    return tuple(_draft(group, algorithm_version) for group in groups if any(item.content_state == "AVAILABLE" and item.text for item in group))


def _draft(messages: list[EpisodeMessage], algorithm_version: str) -> EpisodeDraft:
    restricted = sum(item.content_state == "EXCLUDED_RESTRICTED" for item in messages)
    return EpisodeDraft(messages[0].conversation_ref, tuple((item.message_id, item.actor) for item in messages), messages[0].observed_at, messages[-1].observed_at, "UNRESOLVED", f"{len(messages)} Chronicle messages", algorithm_version, 0.5 if restricted else 0.8, len(messages) - restricted, restricted)


def validate_episode(episode: EpisodeDraft) -> None:
    if episode.processing_state != "DERIVED" or not episode.message_refs or not all(_uuid(message_id) and actor in {"USER", "ASSISTANT", "TOOL", "SYSTEM_OBSERVED"} for message_id, actor in episode.message_refs):
        raise ValueError("invalid Episode trace")
    if not all(isinstance(value, str) and value for value in (episode.conversation_ref, episode.topic_label, episode.working_summary, episode.algorithm_version)) or not _uuid(episode.conversation_ref):
        raise ValueError("invalid Episode fields")
    start, end = _time(episode.start_observed_at), _time(episode.end_observed_at)
    if start > end or not isinstance(episode.confidence, float) or not 0 <= episode.confidence <= 1 or episode.included_message_count < 0 or episode.excluded_restricted_count < 0 or episode.included_message_count + episode.excluded_restricted_count != len(episode.message_refs):
        raise ValueError("invalid Episode coverage")


def _uuid(value: object) -> bool:
    try:
        parsed = uuid.UUID(str(value))
        return parsed.version == 4 and str(parsed) == value
    except (ValueError, TypeError):
        return False


def _time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError("invalid Episode time") from exc
    if parsed.tzinfo is None:
        raise ValueError("invalid Episode time")
    return parsed
