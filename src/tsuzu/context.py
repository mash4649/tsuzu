"""Bounded, trace-committed runtime context bundles (A8)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .deletion import DELETED, NOT_DELETED, DeletionResolver
from .retrieval import ApprovedCandidate, RetrievalResult
from .source import SourceValidationError, parse_source, validate_payload, validate_source
from .vault import ActiveVaultLocator


MAX_ITEMS = 5
MAX_TOTAL_CONTEXT_CHARS = 8_000
MAX_ITEM_FULL_CHARS = 3_000
MAX_ITEM_EXCERPT_CHARS = 2_000


@dataclass(frozen=True)
class ContextItem:
    ordinal: int
    source_id: str
    source_revision: int
    content_role: str
    text: str
    excerpt_kind: str
    truncated_before: bool
    truncated_after: bool
    source_trace: dict[str, object]


@dataclass(frozen=True)
class ContextBundle:
    bundle_id: str
    request_id: str
    created_at: str
    destination_id: str
    destination_class: str
    scope_type: str
    scope_id: str | None
    query_hash: str
    items: tuple[ContextItem, ...]
    max_items: int
    max_total_chars: int
    used_chars: int
    truncated: bool
    context_trace_id: str


@dataclass(frozen=True)
class ContextResult:
    status: str
    bundle: ContextBundle | None = None
    reason: str = ""


class ContextBundleBuilder:
    def __init__(
        self,
        locator: ActiveVaultLocator,
        runtime_root: str | os.PathLike[str],
        *,
        deletion_resolver: DeletionResolver | None = None,
        failure_injector=None,
    ):
        self.locator = locator
        self.root = Path(runtime_root) / "context-traces"
        self.deletion = deletion_resolver or DeletionResolver(locator)
        self.failure_injector = failure_injector

    def build(self, result: RetrievalResult) -> ContextResult:
        if result.status != "OK" or not result.approved:
            return ContextResult("NO_ELIGIBLE_CONTEXT")
        bundle_id, trace_id = str(uuid.uuid4()), str(uuid.uuid4())
        items: list[ContextItem] = []
        used = 0
        truncated = False
        for candidate in result.approved[:MAX_ITEMS]:
            item, reason = self._item(candidate, result.query, len(items) + 1)
            if item is None:
                continue
            remaining = MAX_TOTAL_CONTEXT_CHARS - used
            if remaining <= 0:
                truncated = True
                break
            if len(item.text) > remaining:
                if remaining < 64:
                    truncated = True
                    break
                item = ContextItem(item.ordinal, item.source_id, item.source_revision, item.content_role, item.text[:remaining], "WINDOW", item.truncated_before, True, item.source_trace)
                truncated = True
            items.append(item)
            used += len(item.text)
        if len(result.approved) > len(items):
            truncated = True
        if not items:
            return ContextResult("NO_ELIGIBLE_CONTEXT")
        bundle = ContextBundle(bundle_id, result.approved[0].request_id, _now(), result.destination_id, result.destination_class, result.effective_scope.scope_type, result.effective_scope.scope_id, _hash(result.query), tuple(items), MAX_ITEMS, MAX_TOTAL_CONTEXT_CHARS, used, truncated, trace_id)
        try:
            self._validate(bundle)
            self._write_trace(bundle, result.approved)
        except (OSError, ValueError):
            return ContextResult("CONTEXT_TRACE_UNAVAILABLE")
        return ContextResult("APPROVED_CONTEXT_BUNDLE", bundle)

    def _item(self, candidate: ApprovedCandidate, query: str, ordinal: int) -> tuple[ContextItem | None, str]:
        try:
            handle = self.locator.resolve_active_vault()
            path = handle.root_ref / "canonical" / "sources" / candidate.source_id
            if path.is_symlink() or (path / "source.md").is_symlink() or (path / "payload/original").is_symlink():
                return None, "CANONICAL_INVALID"
            manifest = parse_source((path / "source.md").read_text())
            validate_source(manifest, expected_object_id=candidate.source_id)
            payload = (path / "payload/original").read_bytes()
            if not validate_payload(manifest, payload) or manifest["revision"] != candidate.source_revision or manifest["source"]["payload_sha256"] != candidate.payload_sha256:
                return None, "POLICY_REEVALUATION_REQUIRED"
        except (OSError, ValueError, SourceValidationError, KeyError):
            return None, "CANONICAL_INVALID"
        state = self.deletion.resolve_source(candidate.source_id)
        if state.state != NOT_DELETED:
            return None, "DELETED" if state.state == DELETED else "DELETION_UNKNOWN"
        source = manifest["source"]
        if candidate.content_mode == "METADATA_ONLY":
            name = Path(source["original_name"] or "").name
            text, kind, before, after = f"{source['kind']}: {name} ({source['media_type']})", "METADATA_ONLY", False, False
        else:
            text, kind, before, after = _excerpt(payload.decode("utf-8"), query)
            if kind == "STALE":
                return None, "INDEX_RECONCILE_NEEDED"
        trace = {"trace_id": str(uuid.uuid4()), "source_kind": source["kind"], "capture_method": source["capture_method"], "captured_at": source["captured_at"], "original_name": source["original_name"], "origin_locator": source["origin_locator"] if source["kind"] == "URL" else {"type": "NONE", "value": None}}
        return ContextItem(ordinal, candidate.source_id, candidate.source_revision, "UNTRUSTED_DATA", text, kind, before, after, trace), ""

    def _write_trace(self, bundle: ContextBundle, candidates: tuple[ApprovedCandidate, ...]) -> None:
        if self.root.is_symlink():
            raise OSError("trace root is symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = self.root / f"{bundle.context_trace_id}.json"
        record = {"context_trace_id": bundle.context_trace_id, "bundle_id": bundle.bundle_id, "request_id": bundle.request_id, "created_at": bundle.created_at, "host": {"destination_id": bundle.destination_id, "destination_class": bundle.destination_class}, "scope": {"scope_type": bundle.scope_type, "scope_id": bundle.scope_id}, "query_hash": bundle.query_hash, "source_refs": [{"source_id": item.source_id, "revision": item.source_revision, "payload_sha256": next(c.payload_sha256 for c in candidates if c.source_id == item.source_id), "policy_decision_id": next(c.policy_decision_id for c in candidates if c.source_id == item.source_id), "excerpt_kind": item.excerpt_kind, "excerpt_chars": len(item.text)} for item in bundle.items], "bundle_chars": bundle.used_chars, "item_count": len(bundle.items), "truncated": bundle.truncated}
        self._failure("before_trace")
        staged = path.with_suffix(".staged")
        with staged.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
        self._failure("after_trace")

    @staticmethod
    def _validate(bundle: ContextBundle) -> None:
        if not bundle.items or len(bundle.items) > MAX_ITEMS or bundle.used_chars > MAX_TOTAL_CONTEXT_CHARS or not bundle.context_trace_id:
            raise ValueError("invalid bundle budget")
        if any(item.ordinal != index or item.content_role != "UNTRUSTED_DATA" or not item.source_id for index, item in enumerate(bundle.items, 1)):
            raise ValueError("invalid context item")
        if any("/" in str(item.source_trace.get("original_name") or "") and item.excerpt_kind == "METADATA_ONLY" for item in bundle.items):
            raise ValueError("unsafe file trace")

    def _failure(self, stage: str) -> None:
        if self.failure_injector:
            self.failure_injector(stage)


def _excerpt(text: str, query: str) -> tuple[str, str, bool, bool]:
    if len(text) <= MAX_ITEM_FULL_CHARS:
        return text, "FULL", False, False
    terms = sorted((term for term in re.split(r"\s+", query) if term), key=len, reverse=True)
    position = next((text.find(term) for term in terms if text.find(term) >= 0), -1)
    if position < 0:
        return "", "STALE", False, False
    start = max(0, position - MAX_ITEM_EXCERPT_CHARS // 2)
    end = min(len(text), start + MAX_ITEM_EXCERPT_CHARS)
    start = max(0, end - MAX_ITEM_EXCERPT_CHARS)
    return text[start:end], "WINDOW", start > 0, end < len(text)


def _hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
