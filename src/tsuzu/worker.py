"""Single Writer Worker that materializes A3 jobs through A2 (A4)."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .capture import (
    CaptureStatus,
    SecretScanner,
    _ensure_queue_layout,
    _fingerprint,
    _validate_job,
    _validate_uuid,
)
from .vault import ActiveVaultLocator, StaleGenerationError
from .writer import AtomicSourceWriter, WriteResult, WriterError


class WorkerStatus:
    IDLE = "IDLE"
    WORKER_BUSY = "WORKER_BUSY"
    COMMITTED = "COMMITTED"
    ALREADY_COMMITTED = "ALREADY_COMMITTED"
    BLOCKED_RESTRICTED = "BLOCKED_RESTRICTED"
    RETRY_WAIT = "RETRY_WAIT"
    PAUSED_ENVIRONMENT = "PAUSED_ENVIRONMENT"
    QUARANTINED = "QUARANTINED"
    COMMIT_UNCERTAIN = "COMMIT_UNCERTAIN"


@dataclass(frozen=True)
class WorkerResult:
    status: str
    job_id: str | None = None
    source_id: str | None = None
    reason: str = ""


class SingleWriterWorker:
    def __init__(
        self,
        queue_root: str | os.PathLike[str],
        locator: ActiveVaultLocator,
        *,
        writer: AtomicSourceWriter | None = None,
        scanner: SecretScanner | None = None,
        failure_injector=None,
        max_attempts: int = 5,
    ):
        self.root = Path(queue_root)
        self.locator = locator
        self.writer = writer or AtomicSourceWriter(locator)
        self.scanner = scanner or SecretScanner()
        self.worker_instance_id = str(uuid.uuid4())
        self.failure_injector = failure_injector
        self.max_attempts = max_attempts

    def run_once(self) -> WorkerResult:
        try:
            with self._worker_lock():
                _ensure_queue_layout(self.root)
                for state in ("processing", "retry", "quarantine", "receipts"):
                    path = self.root / state
                    if path.is_symlink():
                        raise WriterError("FILESYSTEM_UNSUPPORTED", "worker queue path is symlink")
                    path.mkdir(parents=True, exist_ok=True, mode=0o700)
                job_dir = self._next_job()
                if job_dir is None:
                    return WorkerResult(WorkerStatus.IDLE)
                if job_dir.parent == self.root / "pending":
                    claimed = self.root / "processing" / job_dir.name
                    if claimed.exists() or claimed.is_symlink():
                        return self._quarantine(job_dir, "claim destination exists")
                    os.rename(job_dir, claimed)
                    job_dir = claimed
                return self._process(job_dir)
        except WriterError as exc:
            if exc.status == "WRITER_BUSY":
                return WorkerResult(WorkerStatus.WORKER_BUSY, reason=exc.reason)
            return WorkerResult(WorkerStatus.PAUSED_ENVIRONMENT, reason=exc.reason)
        except OSError as exc:
            return WorkerResult(WorkerStatus.PAUSED_ENVIRONMENT, reason=str(exc))

    def _next_job(self) -> Path | None:
        for state in ("processing", "pending", "retry"):
            directory = self.root / state
            if not directory.exists() or directory.is_symlink():
                continue
            for child in sorted(directory.iterdir(), key=lambda item: item.name):
                if child.is_dir() and not child.is_symlink():
                    return child
        return None

    def _process(self, job_dir: Path) -> WorkerResult:
        job_id = job_dir.name
        previous_runtime = self._read_runtime(job_dir)
        self._runtime(job_dir, "PROCESSING", None, int(previous_runtime.get("attempt", 0)))
        try:
            job = json.loads((job_dir / "job.json").read_text())
            _validate_job(job, job_id)
            payload_path = job_dir / job["payload"]["relative_path"]
            if payload_path.is_symlink() or not payload_path.exists():
                return self._quarantine(job_dir, "payload missing")
            payload = payload_path.read_bytes()
            if len(payload) != job["payload"]["bytes"] or hashlib.sha256(payload).hexdigest() != job["payload"]["sha256"]:
                return self._quarantine(job_dir, "payload integrity mismatch")
            plan = job["source_plan"]
            expected_fingerprint = _fingerprint(
                plan["kind"],
                job["payload"]["sha256"],
                job["payload"]["bytes"],
                plan["effective_sensitivity"],
                plan.get("original_name"),
                plan["scope"],
                plan["origin_locator"],
            )
            if expected_fingerprint != job["fingerprint"]:
                return self._quarantine(job_dir, "request fingerprint mismatch")
            scan = self.scanner.scan_bytes(payload)
            if scan.outcome != "CLEAR":
                self._write_receipt(job, "BLOCKED_RESTRICTED", None)
                shutil.rmtree(job_dir, ignore_errors=True)
                return WorkerResult(WorkerStatus.BLOCKED_RESTRICTED, job_id, job["source_id"])
            self._failure("before_materialize")
            result = self.writer.create_source(
                payload,
                kind=plan["kind"],
                capture_method=plan["capture_method"],
                object_id=job["source_id"],
                created_at=job["created_at"],
                original_name=plan.get("original_name"),
                origin_locator=plan.get("origin_locator"),
                sensitivity=plan["effective_sensitivity"],
            )
            try:
                self._failure("after_canonical")
            except OSError as exc:
                return WorkerResult(WorkerStatus.COMMIT_UNCERTAIN, job_id, job["source_id"], str(exc))
            if result.status in {"COMMITTED_LOCAL", "ALREADY_COMMITTED"}:
                try:
                    self._write_receipt(job, "COMMITTED", result.revision)
                except OSError as exc:
                    return WorkerResult(WorkerStatus.COMMIT_UNCERTAIN, job_id, job["source_id"], str(exc))
                try:
                    self._failure("after_receipt")
                except OSError as exc:
                    return WorkerResult(WorkerStatus.COMMIT_UNCERTAIN, job_id, job["source_id"], str(exc))
                shutil.rmtree(job_dir, ignore_errors=True)
                status = WorkerStatus.COMMITTED if result.status == "COMMITTED_LOCAL" else WorkerStatus.ALREADY_COMMITTED
                return WorkerResult(status, job_id, job["source_id"])
            if result.status == "COMMIT_UNCERTAIN":
                checked = self.writer.inspect_source(job["source_id"])
                if checked.status == "VALID":
                    try:
                        self._write_receipt(job, "COMMITTED", checked.revision)
                    except OSError as exc:
                        return WorkerResult(WorkerStatus.COMMIT_UNCERTAIN, job_id, job["source_id"], str(exc))
                    try:
                        self._failure("after_receipt")
                    except OSError as exc:
                        return WorkerResult(WorkerStatus.COMMIT_UNCERTAIN, job_id, job["source_id"], str(exc))
                    shutil.rmtree(job_dir, ignore_errors=True)
                    return WorkerResult(WorkerStatus.ALREADY_COMMITTED, job_id, job["source_id"])
            if result.status in {"IO_FAILED", "STALE_GENERATION"}:
                return self._retry(job_dir, job, result.reason)
            return self._quarantine(job_dir, result.reason or result.status)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            return self._quarantine(job_dir, str(exc))
        except StaleGenerationError as exc:
            return self._retry(job_dir, None, str(exc))

    def _retry(self, job_dir: Path, job: dict[str, object] | None, reason: str) -> WorkerResult:
        if job is None:
            try:
                job = json.loads((job_dir / "job.json").read_text())
            except (OSError, json.JSONDecodeError):
                return self._quarantine(job_dir, "retry job unreadable")
        runtime = self._read_runtime(job_dir)
        attempt = int(runtime.get("attempt", 0)) + 1
        if attempt >= self.max_attempts:
            return self._quarantine(job_dir, "retry limit reached")
        self._runtime(job_dir, "RETRY_WAIT", reason, attempt)
        target = self.root / "retry" / job_dir.name
        if target.exists() or target.is_symlink():
            return self._quarantine(job_dir, "retry destination exists")
        os.rename(job_dir, target)
        return WorkerResult(WorkerStatus.RETRY_WAIT, job["job_id"], job["source_id"], reason)

    def _quarantine(self, job_dir: Path, reason: str) -> WorkerResult:
        job_id = job_dir.name
        source_id = None
        try:
            job = json.loads((job_dir / "job.json").read_text())
            source_id = job.get("source_id")
            self._runtime(job_dir, "QUARANTINED", reason)
        except (OSError, json.JSONDecodeError):
            pass
        target = self.root / "quarantine" / job_id
        if target.exists() or target.is_symlink():
            shutil.rmtree(job_dir, ignore_errors=True)
        else:
            os.rename(job_dir, target)
        return WorkerResult(WorkerStatus.QUARANTINED, job_id, source_id, reason)

    def _write_receipt(self, job: dict[str, object], terminal_state: str, revision: int | None) -> None:
        receipts = self.root / "receipts"
        receipts.mkdir(parents=True, exist_ok=True, mode=0o700)
        key_hash = job["idempotency_key_hash"]
        path = receipts / f"{key_hash}.json"
        if path.is_symlink():
            raise OSError("receipt path is symlink")
        record = {
            "receipt_schema_version": "1.0.0",
            "idempotency_key_hash": key_hash,
            "request_fingerprint": job["fingerprint"],
            "job_id": job["job_id"],
            "source_id": job["source_id"],
            "terminal_state": terminal_state,
            "canonical_revision": revision,
            "created_at": job["created_at"],
            "updated_at": job["created_at"],
        }
        if path.exists() and not path.is_symlink():
            existing = json.loads(path.read_text())
            if existing.get("request_fingerprint") != record["request_fingerprint"]:
                raise ValueError("receipt idempotency conflict")
            return
        staged = receipts / f".{key_hash}.{uuid.uuid4().hex}.tmp"
        _write_text(staged, json.dumps(record, sort_keys=True) + "\n")
        os.replace(staged, path)
        _fsync_directory(receipts)

    def _runtime(self, job_dir: Path, state: str, error: str | None, attempt: int = 0) -> None:
        record = {
            "state": state,
            "worker_instance_id": self.worker_instance_id,
            "attempt": attempt,
            "last_error_code": error,
            "claimed_at": _now(),
            "next_retry_at": None,
        }
        _write_text_atomic(job_dir / "runtime.json", record)

    @staticmethod
    def _read_runtime(job_dir: Path) -> dict[str, object]:
        try:
            return json.loads((job_dir / "runtime.json").read_text())
        except (OSError, json.JSONDecodeError):
            return {"attempt": 0}

    def _failure(self, stage: str) -> None:
        if self.failure_injector:
            self.failure_injector(stage)

    @contextlib.contextmanager
    def _worker_lock(self) -> Iterator[None]:
        worker_root = self.root / "worker"
        if worker_root.is_symlink():
            raise WriterError("FILESYSTEM_UNSUPPORTED", "worker root is symlink")
        worker_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = worker_root / "worker.lock"
        if lock_path.is_symlink():
            raise WriterError("FILESYSTEM_UNSUPPORTED", "worker lock is symlink")
        with lock_path.open("a+") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise WriterError("WRITER_BUSY", "worker lock is busy") from exc
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _write_text(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())


def _write_text_atomic(path: Path, value: dict[str, object]) -> None:
    staged = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    _write_text(staged, json.dumps(value, sort_keys=True) + "\n")
    os.replace(staged, path)


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
