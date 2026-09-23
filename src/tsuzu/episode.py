"""B2 Derived Episode schema, conservative segmentation, and C1 persistence."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .canonical import CanonicalStore, CommitResult, CreateCanonicalIntent, ObjectRegistration
from .derived import DerivedJobQueue, DerivedJobRequest, DerivedJobResult, DerivedStatus


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


def persist_episode(
    store: CanonicalStore,
    episode: EpisodeDraft,
    input_refs: tuple[tuple[str, str, int, str], ...],
    *,
    policy_version: str,
) -> CommitResult:
    """Persist one immutable B2 generation under C1's derived storage root."""
    try:
        validate_episode(episode)
        refs = _normalize_input_refs(input_refs)
        if not isinstance(policy_version, str) or not policy_version:
            raise ValueError("Episode policy version is required")
        message_ids = {message_id for message_id, _ in episode.message_refs}
        if not message_ids <= {object_id for _, object_id, _, _ in refs}:
            raise ValueError("Episode messages must be covered by input refs")
    except ValueError as exc:
        return CommitResult("VALIDATION_FAILED", "EPISODE", "", reason=str(exc))

    registration = store.registry.get("EPISODE")
    if registration is None:
        store.registry.register(ObjectRegistration("EPISODE", "DERIVED", "IMMUTABLE", "NONE", "B2"))
    elif (registration.storage_class, registration.mutability, registration.body_mode) != ("DERIVED", "IMMUTABLE", "NONE"):
        return CommitResult("VALIDATION_FAILED", "EPISODE", "", reason="EPISODE must be immutable DERIVED storage")

    fingerprint = hashlib.sha256(json.dumps(refs, separators=(",", ":")).encode()).hexdigest()
    generation_key = f"{fingerprint}:{episode.algorithm_version}:{policy_version}"
    object_id = _stable_uuid(generation_key)
    created_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    fields = {
        "scope": {"scope_type": "GLOBAL", "scope_id": None},
        "provenance": {
            "origin": "SYSTEM_OBSERVED",
            "source_refs": [{"object_type": kind, "object_id": object_id, "revision": revision, "content_hash": digest} for kind, object_id, revision, digest in refs],
            "actor": "B2",
            "explicitness": "OBSERVED",
        },
        "trust": {"level": "INFERRED", "confidence": episode.confidence},
        "sensitivity": {"level": "PERSONAL"},
        "temporal": {"valid_from": episode.start_observed_at, "valid_until": episode.end_observed_at},
        "deletion": {"state": "LIVE", "tombstoned_at": None},
        "processing_state": "DERIVED",
        "conversation_refs": [episode.conversation_ref],
        "message_refs": [{"message_id": message_id, "actor": actor} for message_id, actor in episode.message_refs],
        "start_observed_at": episode.start_observed_at,
        "end_observed_at": episode.end_observed_at,
        "topic_label": episode.topic_label,
        "working_summary": episode.working_summary,
        "segmentation": {"algorithm_version": episode.algorithm_version, "confidence": episode.confidence},
        "evidence_coverage": {
            "included_message_count": episode.included_message_count,
            "excluded_restricted_count": episode.excluded_restricted_count,
        },
        "derivation": {
            "generation_id": object_id,
            "input_fingerprint": fingerprint,
            "algorithm_version": episode.algorithm_version,
            "policy_version": policy_version,
            "created_at": created_at,
            "stale": False,
        },
    }
    return store.create_canonical(CreateCanonicalIntent(
        "EPISODE", object_id, "1.0.0", created_at, f"b2-episode:{generation_key}", fields,
    ))


def complete_episode_job(
    queue: DerivedJobQueue,
    request: DerivedJobRequest,
    job_id: str,
    worker_id: str,
    store: CanonicalStore,
    build_episode,
    validate_inputs,
) -> DerivedJobResult:
    """Run B2 between C4 preflight checks, then persist and settle its generation."""
    try:
        refs = _normalize_input_refs(request.input_refs)
        if request.job_type != "EPISODE_SEGMENT" or not callable(build_episode) or not callable(validate_inputs):
            raise ValueError("invalid Episode job")
    except ValueError as exc:
        return DerivedJobResult(DerivedStatus.VALIDATION_FAILED, job_id, str(exc))
    job = queue.enqueue(request)
    if job.job_id != job_id or job.status not in {DerivedStatus.ENQUEUED, DerivedStatus.ALREADY_ENQUEUED}:
        return DerivedJobResult(job.status, job_id, job.reason)

    def validate_exact_inputs(queued_refs) -> bool:
        return queued_refs == refs and validate_inputs(queued_refs) is True

    preflight = queue.preflight(job_id, worker_id, validate_exact_inputs)
    if preflight.status != DerivedStatus.READY:
        return DerivedJobResult(preflight.status, job_id, preflight.reason)
    try:
        episode = build_episode(refs)
    except Exception:
        next_attempt = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        return queue.settle(job_id, worker_id, "RETRY_WAIT", failure_code="EPISODE_BUILD_FAILED", next_attempt_at=next_attempt)
    try:
        validate_episode(episode)
    except (AttributeError, TypeError, ValueError):
        return queue.settle(job_id, worker_id, "PERMANENT_FAILURE", failure_code="INVALID_EPISODE_OUTPUT")
    preflight = queue.preflight(job_id, worker_id, validate_exact_inputs)
    if preflight.status != DerivedStatus.READY:
        return DerivedJobResult(preflight.status, job_id, preflight.reason)
    persisted = persist_episode(store, episode, refs, policy_version=request.policy_version)
    if persisted.status not in {"COMMITTED_LOCAL", "ALREADY_COMMITTED"} or persisted.path is None or persisted.revision is None:
        return DerivedJobResult(persisted.status, job_id, persisted.reason)
    output_hash = hashlib.sha256((persisted.path / "object.md").read_bytes()).hexdigest()
    output_refs = (("EPISODE", persisted.object_id, persisted.revision, output_hash),)
    return queue.settle(job_id, worker_id, "SUCCEEDED", output_refs=output_refs)


def _normalize_input_refs(refs: tuple[tuple[str, str, int, str], ...]) -> tuple[tuple[str, str, int, str], ...]:
    if not isinstance(refs, tuple) or not refs:
        raise ValueError("Episode input refs are required")
    normalized = []
    for item in refs:
        if not isinstance(item, tuple) or len(item) != 4:
            raise ValueError("invalid Episode input ref")
        object_type, object_id, revision, digest = item
        if (object_type != "CONVERSATION_MESSAGE" or not _uuid(object_id)
                or isinstance(revision, bool) or not isinstance(revision, int) or revision < 1
                or not isinstance(digest, str) or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)):
            raise ValueError("invalid Episode input ref")
        normalized.append(item)
    return tuple(sorted(set(normalized)))


def _stable_uuid(value: str) -> str:
    raw = bytearray(hashlib.sha256(value.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))


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
