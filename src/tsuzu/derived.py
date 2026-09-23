"""Durable, local-only C4 job identity and lease queue."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from .deletion import DeletionResolver, NOT_DELETED


class DerivedStatus:
    ENQUEUED = "ENQUEUED"
    ALREADY_ENQUEUED = "ALREADY_ENQUEUED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    CLAIMED = "CLAIMED"
    NO_READY_JOB = "NO_READY_JOB"
    CORRUPT_QUEUE = "CORRUPT_QUEUE"
    READY = "READY"
    BLOCKED_STALE = "BLOCKED_STALE"
    RETRY_WAIT = "RETRY_WAIT"
    SUCCEEDED = "SUCCEEDED"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
    CLAIM_MISMATCH = "CLAIM_MISMATCH"


JOB_TYPES = frozenset({
    "EPISODE_SEGMENT", "CANDIDATE_EXTRACT", "DECISION_RECONCILE", "EXPERIENCE_TRACE_RECOMPUTE",
    "DEPENDENCY_INVALIDATE", "PATTERN_RECOMPUTE", "DISCOVERY_PRECOMPUTE", "DERIVED_INDEX_REPROJECT",
})
_HIGH_PRIORITY = frozenset({"DEPENDENCY_INVALIDATE"})


@dataclass(frozen=True)
class DerivedJobRequest:
    job_type: str
    input_refs: tuple[tuple[str, str, int, str], ...]
    algorithm_version: str
    policy_version: str
    scope: str
    trigger_ref: str


@dataclass(frozen=True)
class DerivedJobResult:
    status: str
    job_id: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class DerivedClaim:
    status: str
    job_id: str | None = None
    attempt_count: int = 0


@dataclass(frozen=True)
class DerivedPreflight:
    status: str
    job_id: str | None = None
    reason: str = ""


class DerivedJobQueue:
    def __init__(self, root: str | os.PathLike[str], *, deletion_resolver: DeletionResolver | None = None):
        self.root = Path(root)
        self.deletion_resolver = deletion_resolver

    def enqueue(self, request: DerivedJobRequest) -> DerivedJobResult:
        try:
            normalized = _normalize(request)
        except ValueError as exc:
            return DerivedJobResult(DerivedStatus.VALIDATION_FAILED, reason=str(exc))
        key = hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        job_id = _stable_uuid(key)
        with self._locked_jobs() as jobs:
            path = jobs / f"{job_id}.json"
            if path.exists():
                try:
                    current = _read(path)
                except ValueError as exc:
                    return DerivedJobResult(DerivedStatus.CORRUPT_QUEUE, reason=str(exc))
                return DerivedJobResult(DerivedStatus.ALREADY_ENQUEUED if current.get("job_key_hash") == key else DerivedStatus.CORRUPT_QUEUE, job_id)
            _atomic_json(path, {
                "job_id": job_id,
                "job_type": request.job_type,
                "job_key_hash": key,
                "input_refs": normalized["input_refs"],
                "input_fingerprint": hashlib.sha256(json.dumps(normalized["input_refs"], separators=(",", ":")).encode()).hexdigest(),
                "algorithm_version": request.algorithm_version,
                "policy_version": request.policy_version,
                "scope": request.scope,
                "trigger_ref_hash": hashlib.sha256(request.trigger_ref.encode()).hexdigest(),
                "created_at": _now(),
                "attempt_count": 0,
                "state": "PENDING",
                "next_attempt_at": None,
                "output_refs": [],
                "last_failure_code": None,
                "lease_owner": None,
                "lease_expires_at": None,
            })
        return DerivedJobResult(DerivedStatus.ENQUEUED, job_id)

    def claim(self, worker_id: str, *, now: str | None = None, lease_seconds: int = 60) -> DerivedClaim:
        if not isinstance(worker_id, str) or not worker_id or not isinstance(lease_seconds, int) or lease_seconds < 1:
            return DerivedClaim(DerivedStatus.VALIDATION_FAILED)
        moment = _parse_time(now) if now else datetime.now(timezone.utc)
        with self._locked_jobs() as jobs:
            candidates: list[dict[str, object]] = []
            for path in jobs.glob("*.json"):
                try:
                    job = _read(path)
                    if _claimable(job, moment):
                        candidates.append(job)
                except (TypeError, ValueError):
                    return DerivedClaim(DerivedStatus.CORRUPT_QUEUE)
            if not candidates:
                return DerivedClaim(DerivedStatus.NO_READY_JOB)
            job = min(candidates, key=lambda item: (0 if item["job_type"] in _HIGH_PRIORITY else 1, item["created_at"], item["job_id"]))
            job["state"] = "RUNNING"
            job["attempt_count"] = int(job["attempt_count"]) + 1
            job["lease_owner"] = worker_id
            job["lease_expires_at"] = _format_time(moment + timedelta(seconds=lease_seconds))
            job.pop("preflight_fingerprint", None)
            job.pop("preflight_at", None)
            _atomic_json(jobs / f"{job['job_id']}.json", job)
            return DerivedClaim(DerivedStatus.CLAIMED, str(job["job_id"]), int(job["attempt_count"]))

    def preflight(self, job_id: str, worker_id: str, validate_inputs: Callable[[tuple[tuple[str, str, int, str], ...]], bool]) -> DerivedPreflight:
        """Recheck C3; the owner callback re-reads hashes/schema/sensitivity and applies A3/A7."""
        if not _valid_worker(worker_id) or not callable(validate_inputs):
            return DerivedPreflight(DerivedStatus.VALIDATION_FAILED, job_id)
        with self._locked_jobs() as jobs:
            job = _job_for_worker(jobs, job_id, worker_id)
            if job is None:
                return DerivedPreflight(DerivedStatus.CLAIM_MISMATCH, job_id)
            if self.deletion_resolver is None:
                return self._block(jobs, job, "DELETION_RESOLVER_REQUIRED")
            try:
                refs = tuple(_normalize_refs(tuple(tuple(item) for item in job["input_refs"])))
            except (KeyError, TypeError, ValueError):
                return DerivedPreflight(DerivedStatus.CORRUPT_QUEUE, job_id, "invalid input references")
            for object_type, object_id, _, _ in refs:
                if self.deletion_resolver.resolve(object_type, object_id).state != NOT_DELETED:
                    return self._block(jobs, job, "INPUT_NOT_ELIGIBLE")
            try:
                valid = validate_inputs(refs)
            except Exception:
                valid = False
            if valid is not True:
                return self._block(jobs, job, "INPUT_STALE_OR_INVALID")
            job["preflight_fingerprint"] = job["input_fingerprint"]
            job["preflight_at"] = _now()
            _atomic_json(jobs / f"{job_id}.json", job)
            return DerivedPreflight(DerivedStatus.READY, job_id)

    def settle(self, job_id: str, worker_id: str, state: str, *, output_refs: tuple[tuple[str, str, int, str], ...] = (), failure_code: str | None = None, next_attempt_at: str | None = None) -> DerivedJobResult:
        """Record an owner materialization result; SUCCEEDED requires current preflight."""
        if state not in {"SUCCEEDED", "RETRY_WAIT", "PERMANENT_FAILURE"}:
            return DerivedJobResult(DerivedStatus.VALIDATION_FAILED, job_id, "invalid terminal state")
        with self._locked_jobs() as jobs:
            job = _job_for_worker(jobs, job_id, worker_id)
            if job is None:
                return DerivedJobResult(DerivedStatus.CLAIM_MISMATCH, job_id)
            if state == "SUCCEEDED" and job.get("preflight_fingerprint") != job.get("input_fingerprint"):
                return self._block_result(jobs, job, "PREFLIGHT_REQUIRED")
            if state == "RETRY_WAIT":
                try:
                    _parse_time(next_attempt_at or "")
                except (TypeError, ValueError):
                    return DerivedJobResult(DerivedStatus.VALIDATION_FAILED, job_id, "retry time is required")
                job["next_attempt_at"] = next_attempt_at
            else:
                job["next_attempt_at"] = None
            if state == "SUCCEEDED":
                try:
                    job["output_refs"] = _normalize_refs(output_refs)
                except ValueError as exc:
                    return DerivedJobResult(DerivedStatus.VALIDATION_FAILED, job_id, str(exc))
            job["state"] = state
            job["last_failure_code"] = failure_code
            job["lease_owner"] = None
            job["lease_expires_at"] = None
            _atomic_json(jobs / f"{job_id}.json", job)
            return DerivedJobResult(state, job_id)

    def _block(self, jobs: Path, job: dict[str, object], reason: str) -> DerivedPreflight:
        self._block_result(jobs, job, reason)
        return DerivedPreflight(DerivedStatus.BLOCKED_STALE, str(job["job_id"]), reason)

    def _block_result(self, jobs: Path, job: dict[str, object], reason: str) -> DerivedJobResult:
        job["state"] = "BLOCKED_STALE"
        job["last_failure_code"] = reason
        job["lease_owner"] = None
        job["lease_expires_at"] = None
        _atomic_json(jobs / f"{job['job_id']}.json", job)
        return DerivedJobResult(DerivedStatus.BLOCKED_STALE, str(job["job_id"]), reason)

    def _locked_jobs(self):
        return _JobLock(self.root)


class _JobLock:
    def __init__(self, root: Path):
        self.root = root

    def __enter__(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.handle = (self.root / "queue.lock").open("a+")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        jobs = self.root / "jobs"
        jobs.mkdir(exist_ok=True, mode=0o700)
        return jobs

    def __exit__(self, *_):
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


def _normalize(request: DerivedJobRequest) -> dict[str, object]:
    if request.job_type not in JOB_TYPES or (request.scope != "GLOBAL" and not request.scope.startswith("PROJECT:")) or not all(isinstance(value, str) and value for value in (request.algorithm_version, request.policy_version, request.trigger_ref)):
        raise ValueError("invalid job request")
    refs = _normalize_refs(request.input_refs)
    if not refs:
        raise ValueError("input references are required")
    return {"job_type": request.job_type, "input_refs": refs, "algorithm_version": request.algorithm_version, "policy_version": request.policy_version, "scope": request.scope}


def _normalize_refs(refs: object) -> list[tuple[str, str, int, str]]:
    if not isinstance(refs, tuple):
        raise ValueError("invalid input reference")
    normalized = []
    for item in refs:
        if not isinstance(item, tuple) or len(item) != 4:
            raise ValueError("invalid input reference")
        object_type, object_id, revision, content_hash = item
        try:
            parsed = uuid.UUID(object_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid input object id") from exc
        if not isinstance(object_type, str) or not object_type or parsed.version != 4 or str(parsed) != object_id or not isinstance(revision, int) or isinstance(revision, bool) or revision < 1 or not isinstance(content_hash, str) or len(content_hash) != 64 or any(char not in "0123456789abcdef" for char in content_hash):
            raise ValueError("invalid input reference")
        normalized.append((object_type, object_id, revision, content_hash))
    return sorted(normalized)


def _valid_worker(worker_id: object) -> bool:
    return isinstance(worker_id, str) and bool(worker_id)


def _job_for_worker(jobs: Path, job_id: str, worker_id: str) -> dict[str, object] | None:
    if not _valid_worker(worker_id) or not isinstance(job_id, str):
        return None
    try:
        job = _read(jobs / f"{job_id}.json")
    except ValueError:
        return None
    return job if job.get("state") == "RUNNING" and job.get("lease_owner") == worker_id else None


def _claimable(job: dict[str, object], now: datetime) -> bool:
    if job.get("state") in {"PENDING", "RETRY_WAIT"}:
        return job.get("next_attempt_at") is None or _parse_time(str(job["next_attempt_at"])) <= now
    return job.get("state") == "RUNNING" and isinstance(job.get("lease_expires_at"), str) and _parse_time(str(job["lease_expires_at"])) <= now


def _read(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("invalid job record") from exc
    if not isinstance(value, dict) or not isinstance(value.get("job_id"), str) or not isinstance(value.get("job_type"), str) or not isinstance(value.get("created_at"), str) or not isinstance(value.get("attempt_count"), int):
        raise ValueError("invalid job record")
    return value


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4()}.tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _stable_uuid(value: str) -> str:
    raw = bytearray(hashlib.sha256(value.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _format_time(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _now() -> str:
    return _format_time(datetime.now(timezone.utc))
