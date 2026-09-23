"""Bounded, read-only historical snapshot import (R3)."""

from __future__ import annotations

import hashlib
import heapq
import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from .capture import CaptureRequest, CaptureService, CaptureStatus, _fsync_directory, _validate_timestamp
from .vault import ActiveVaultLocator
from .worker import SingleWriterWorker, WorkerStatus


@dataclass(frozen=True)
class HistoricalItem:
    external_item_key: str
    content: bytes | None
    modified_at_observed: str
    title_hint: str | None = None
    original_name: str | None = None
    source_url: str | None = None
    skip_reason: str | None = None


@dataclass(frozen=True)
class ImportSessionResult:
    import_session_id: str
    committed_count: int
    already_imported_count: int
    blocked_count: int
    skipped_count: int
    failed_count: int
    cancelled: bool
    source_ids: tuple[str, ...]
    skipped_items: tuple[dict[str, str], ...] = ()
    enumerated_count: int = 0
    eligible_count: int = 0


class MarkdownFolderAdapter:
    """Reads Markdown below one selected root; never follows links."""

    adapter_id = "MARKDOWN_FOLDER"
    _excluded = {".git", "node_modules", "__pycache__", "dist", "build", ".cache"}

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)

    def enumerate(self) -> Iterable[HistoricalItem]:
        if self.root.is_symlink() or not self.root.is_dir():
            raise ValueError("Markdown root must be a regular directory")
        selected = self.root.resolve()
        for path in sorted(self.root.rglob("*.md")):
            if path.is_symlink() or any(part.startswith(".") or part in self._excluded for part in path.relative_to(self.root).parts):
                continue
            try:
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(selected) or not resolved.is_file():
                    continue
                before = resolved.stat()
                content = resolved.read_bytes()
                after = resolved.stat()
                if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                    continue
            except OSError:
                continue
            yield HistoricalItem(path.relative_to(self.root).as_posix(), content, _timestamp(after.st_mtime), title_hint=path.stem, original_name=path.name)


_APPLE_NOTES_SELECTED_NOTE_SCRIPT = r'''
const notes = Application("Notes");
const selected = notes.selection();
if (selected.length !== 1) {
  throw new Error("Select exactly one Apple Note before importing.");
}
const note = selected[0];
JSON.stringify({
  id: note.id(),
  title: note.name(),
  body: note.body(),
  created_at: note.creationDate().toISOString(),
  modified_at: note.modificationDate().toISOString(),
});
'''


class MacOSAppleNotesBridge:
    """Reads exactly one already-selected Note via the macOS Automation prompt."""

    def __init__(self, runner: Callable[[], str] | None = None):
        self._runner = runner or self._run_selection_script

    def read_selected_item(self) -> HistoricalItem:
        try:
            value = json.loads(self._runner())
            if not isinstance(value, dict) or set(value) != {"id", "title", "body", "created_at", "modified_at"}:
                raise ValueError("Apple Notes bridge returned an invalid selected note")
            note_id, title, body = (value[name] for name in ("id", "title", "body"))
            if not isinstance(note_id, str) or not note_id or not isinstance(title, str) or not title or not isinstance(body, str):
                raise ValueError("Apple Notes bridge returned an invalid selected note")
            _validate_timestamp(value["created_at"])
            _validate_timestamp(value["modified_at"])
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError("Apple Notes selected-note bridge is unavailable or invalid") from exc
        locator = "x-apple-notes://selected/" + hashlib.sha256(note_id.encode()).hexdigest()
        return HistoricalItem(note_id, body.encode("utf-8"), value["modified_at"], title_hint=title, original_name=title, source_url=locator)

    @staticmethod
    def _run_selection_script() -> str:
        result = subprocess.run(
            ("/usr/bin/osascript", "-l", "JavaScript", "-e", _APPLE_NOTES_SELECTED_NOTE_SCRIPT),
            check=True, capture_output=True, text=True, timeout=10,
        )
        return result.stdout


class AppleNotesAdapter:
    """Read-only adapter for one note explicitly selected in Apple Notes."""

    adapter_id = "APPLE_NOTES"

    def __init__(self, bridge: MacOSAppleNotesBridge | None = None):
        self.bridge = bridge or MacOSAppleNotesBridge()

    def enumerate(self) -> Iterable[HistoricalItem]:
        yield self.bridge.read_selected_item()


class HistoricalImporter:
    def __init__(self, queue_root: str | os.PathLike[str], locator: ActiveVaultLocator):
        self.queue_root = Path(queue_root)
        self.locator = locator
        self.last_source_ids: list[str] = []

    def import_items(
        self,
        adapter_id: str,
        items: Iterable[HistoricalItem],
        *,
        recent_n: int = 50,
        from_at: str | None = None,
        to_at: str | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> ImportSessionResult:
        if adapter_id not in {"APPLE_NOTES", "MARKDOWN_FOLDER"} or not isinstance(recent_n, int) or recent_n < 1:
            raise ValueError("invalid historical import selection")
        for value in (from_at, to_at):
            if value is not None:
                _validate_timestamp(value)
        if from_at and to_at and _parse_timestamp(from_at) > _parse_timestamp(to_at):
            raise ValueError("invalid historical import date window")
        session_id = str(uuid.uuid4())
        selected, enumerated, eligible = _select_items(items, recent_n, from_at, to_at)
        committed = already = blocked = skipped = failed = 0
        source_ids: list[str] = []
        skipped_items: list[dict[str, str]] = []
        cancelled_result = False
        self.last_source_ids = []
        for item in selected:
            if cancelled and cancelled():
                cancelled_result = True
                break
            try:
                _validate_timestamp(item.modified_at_observed)
                if item.skip_reason == "SKIPPED_ATTACHMENT":
                    skipped += 1
                    skipped_items.append({"external_item_key_hash": hashlib.sha256(item.external_item_key.encode()).hexdigest(), "reason": item.skip_reason})
                    continue
                if not item.external_item_key or not isinstance(item.content, bytes):
                    raise ValueError("invalid historical item")
                fingerprint = _snapshot_fingerprint(adapter_id, item)
                receipt = self._read_receipt(fingerprint)
                if receipt:
                    if receipt["terminal_state"] == "COMMITTED":
                        already += 1
                        source_ids.append(receipt["source_id"])
                    else:
                        blocked += 1
                    continue
                previous = self._read_head(adapter_id, item.external_item_key)
                request = CaptureRequest(
                    request_id=str(uuid.uuid4()), idempotency_key=fingerprint, kind="TEXT", content=item.content,
                    original_name=item.original_name, requested_at=item.modified_at_observed,
                    capture_method="IMPORT_" + ("APPLE_NOTES" if adapter_id == "APPLE_NOTES" else "MARKDOWN"),
                    provenance={"origin": "IMPORTED", "source_refs": [], "actor": "USER", "explicitness": "IMPORT_REQUESTED"},
                    import_metadata={
                        "adapter_id": adapter_id,
                        "external_item_key_hash": hashlib.sha256(item.external_item_key.encode()).hexdigest(),
                        "external_modified_at_observed": item.modified_at_observed,
                        "import_session_id": session_id,
                        "previous_snapshot_ref": previous,
                    },
                    origin_locator={"type": "APPLE_NOTES", "value": item.source_url} if adapter_id == "APPLE_NOTES" and item.source_url else None,
                )
                captured = CaptureService(self.queue_root).capture(request)
                if captured.status == CaptureStatus.REJECTED_RESTRICTED:
                    self._write_receipt(fingerprint, None, "BLOCKED_RESTRICTED")
                    blocked += 1
                    continue
                if captured.status not in {CaptureStatus.ACCEPTED, CaptureStatus.ALREADY_ACCEPTED}:
                    failed += 1
                    continue
                result = SingleWriterWorker(self.queue_root, self.locator).run_once()
                if result.status in {WorkerStatus.COMMITTED, WorkerStatus.ALREADY_COMMITTED}:
                    if result.source_id != captured.source_id:
                        failed += 1
                        continue
                    source_id = result.source_id or captured.source_id
                    if not source_id:
                        failed += 1
                        continue
                    self._write_receipt(fingerprint, source_id, "COMMITTED")
                    self._write_head(adapter_id, item.external_item_key, source_id)
                    if captured.status == CaptureStatus.ALREADY_ACCEPTED or result.status == WorkerStatus.ALREADY_COMMITTED:
                        already += 1
                    else:
                        committed += 1
                    source_ids.append(source_id)
                    self.last_source_ids.append(source_id)
                elif result.status == WorkerStatus.BLOCKED_RESTRICTED:
                    self._write_receipt(fingerprint, None, "BLOCKED_RESTRICTED")
                    blocked += 1
                else:
                    failed += 1
            except (OSError, ValueError):
                skipped += 1
        result = ImportSessionResult(session_id, committed, already, blocked, skipped, failed, cancelled_result, tuple(source_ids), tuple(skipped_items), enumerated, eligible)
        self._write_session(adapter_id, recent_n, from_at, to_at, result)
        return result

    def _root(self, name: str) -> Path:
        path = self.locator.resolve_active_vault().root_ref / "system" / name
        if path.is_symlink():
            raise OSError("import metadata path is symlink")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path

    def _read_receipt(self, fingerprint: str) -> dict[str, object] | None:
        path = self._root("import-receipts") / f"{fingerprint}.json"
        if path.is_symlink() or not path.exists():
            return None
        return json.loads(path.read_text())

    def _write_receipt(self, fingerprint: str, source_id: str | None, terminal_state: str) -> None:
        self._write_json(self._root("import-receipts") / f"{fingerprint}.json", {"fingerprint": fingerprint, "source_id": source_id, "terminal_state": terminal_state})

    def _read_head(self, adapter_id: str, external_key: str) -> str | None:
        key = hashlib.sha256((adapter_id + "\0" + external_key).encode()).hexdigest()
        path = self._root("import-heads") / f"{key}.json"
        if path.is_symlink() or not path.exists():
            return None
        value = json.loads(path.read_text()).get("source_id")
        return value if isinstance(value, str) else None

    def _write_head(self, adapter_id: str, external_key: str, source_id: str) -> None:
        key = hashlib.sha256((adapter_id + "\0" + external_key).encode()).hexdigest()
        self._write_json(self._root("import-heads") / f"{key}.json", {"source_id": source_id})

    def _write_session(self, adapter_id: str, recent_n: int, from_at: str | None, to_at: str | None, result: ImportSessionResult) -> None:
        mode = "DATE_WINDOW" if from_at or to_at else "RECENT_N"
        selection = {"mode": mode, "recent_n": recent_n if mode == "RECENT_N" else None, "from": from_at, "to": to_at, "container_ref": None}
        session = {"import_session_id": result.import_session_id, "adapter_id": adapter_id, "selection": selection, "enumerated_count": result.enumerated_count, "eligible_count": result.eligible_count, "committed_count": result.committed_count, "skipped_count": result.skipped_count, "blocked_count": result.blocked_count, "failed_count": result.failed_count, "cancelled": result.cancelled, "skipped_items": list(result.skipped_items)}
        self._write_json(self._root("import-sessions") / f"{result.import_session_id}.json", session)
        reasons = ["CANCELLED"] if result.cancelled else []
        if result.skipped_items:
            reasons.append("SKIPPED_ATTACHMENT")
        self._write_json(self._root("history-coverage") / f"{result.import_session_id}.json", {"source_type": adapter_id, "import_session_id": result.import_session_id, "selection_mode": mode, "enumerated_count": result.enumerated_count, "committed_count": result.committed_count, "incomplete_reasons": reasons, "skipped_items": list(result.skipped_items)})

    @staticmethod
    def _write_json(path: Path, value: dict[str, object]) -> None:
        staged = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with staged.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(value, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
        _fsync_directory(path.parent)


def _snapshot_fingerprint(adapter_id: str, item: HistoricalItem) -> str:
    value = adapter_id + "\0" + item.external_item_key + "\0" + hashlib.sha256(item.content).hexdigest() + "\0" + item.modified_at_observed
    return hashlib.sha256(value.encode()).hexdigest()


def _timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _in_window(item: HistoricalItem, from_at: str | None, to_at: str | None) -> bool:
    if not isinstance(item, HistoricalItem):
        return False
    try:
        observed = _parse_timestamp(item.modified_at_observed)
    except ValueError:
        return False
    return (from_at is None or observed >= _parse_timestamp(from_at)) and (to_at is None or observed <= _parse_timestamp(to_at))


def _select_items(items: Iterable[HistoricalItem], recent_n: int, from_at: str | None, to_at: str | None) -> tuple[list[HistoricalItem], int, int]:
    enumerated = eligible = 0
    selected: list[tuple[float, int, HistoricalItem]] = []
    for index, item in enumerate(items):
        enumerated += 1
        if not _in_window(item, from_at, to_at):
            continue
        eligible += 1
        candidate = (_parse_timestamp(item.modified_at_observed).timestamp(), index, item)
        if len(selected) < recent_n:
            heapq.heappush(selected, candidate)
        elif candidate[:2] > selected[0][:2]:
            heapq.heapreplace(selected, candidate)
    return [item for _, _, item in sorted(selected, reverse=True)], enumerated, eligible


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
