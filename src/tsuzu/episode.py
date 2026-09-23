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
