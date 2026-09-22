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


class DerivedStatus:
    ENQUEUED = "ENQUEUED"
    ALREADY_ENQUEUED = "ALREADY_ENQUEUED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    CLAIMED = "CLAIMED"
    NO_READY_JOB = "NO_READY_JOB"
    CORRUPT_QUEUE = "CORRUPT_QUEUE"


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


class DerivedJobQueue:
    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)

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
            _atomic_json(jobs / f"{job['job_id']}.json", job)
            return DerivedClaim(DerivedStatus.CLAIMED, str(job["job_id"]), int(job["attempt_count"]))

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
    refs = []
    for item in request.input_refs:
        if not isinstance(item, tuple) or len(item) != 4:
            raise ValueError("invalid input reference")
        object_type, object_id, revision, content_hash = item
        try:
            parsed = uuid.UUID(object_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid input object id") from exc
        if not isinstance(object_type, str) or not object_type or parsed.version != 4 or str(parsed) != object_id or not isinstance(revision, int) or isinstance(revision, bool) or revision < 1 or not isinstance(content_hash, str) or len(content_hash) != 64 or any(char not in "0123456789abcdef" for char in content_hash):
            raise ValueError("invalid input reference")
        refs.append((object_type, object_id, revision, content_hash))
    if not refs:
        raise ValueError("input references are required")
    return {"job_type": request.job_type, "input_refs": sorted(refs), "algorithm_version": request.algorithm_version, "policy_version": request.policy_version, "scope": request.scope}


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
