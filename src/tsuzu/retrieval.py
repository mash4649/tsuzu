"""Explicit recall with Canonical revalidation and fixed P0 egress policy (A7)."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .capture import SecretScanner
from .deletion import DELETED, NOT_DELETED, DeletionResolver
from .index import IndexManager
from .source import SourceValidationError, parse_source, validate_payload, validate_source


POLICY_VERSION = "a7-p0-1"
CAPABILITY = "RECALL"
DESTINATION_LOCAL = "LOCAL"
DESTINATION_TRUSTED_EXTERNAL = "TRUSTED_EXTERNAL"
DESTINATION_UNKNOWN_EXTERNAL = "UNKNOWN_EXTERNAL"
MAX_QUERY_BYTES = 4096
MAX_TERMS = 16
INDEX_CANDIDATE_LIMIT = 50
FINAL_APPROVED_LIMIT = 10


@dataclass(frozen=True)
class Destination:
    destination_id: str
    destination_class: str
    capabilities: frozenset[str]
    enabled: bool = True
    policy_profile_version: str = POLICY_VERSION


class DestinationRegistry:
    def __init__(self, destinations: tuple[Destination, ...] | None = None):
        self._destinations = {item.destination_id: item for item in destinations or (
            Destination("local_test", DESTINATION_LOCAL, frozenset({CAPABILITY})),
            Destination("claude_code", DESTINATION_TRUSTED_EXTERNAL, frozenset({CAPABILITY})),
        )}

    def resolve(self, destination_id: str) -> Destination | None:
        return self._destinations.get(destination_id)


@dataclass(frozen=True)
class Scope:
    scope_type: str = "GLOBAL"
    scope_id: str | None = None


@dataclass(frozen=True)
class RetrievalRequest:
    request_id: str
    query: str
    destination_id: str
    capability: str = CAPABILITY
    granted_scope: Scope = Scope()
    requested_scope: Scope | None = None
    max_results: int = FINAL_APPROVED_LIMIT


@dataclass(frozen=True)
class ApprovedCandidate:
    request_id: str
    source_id: str
    source_revision: int
    payload_sha256: str
    query_mode: str
    rank: float | None
    destination_id: str
    destination_class: str
    sensitivity: str
    effective_scope: Scope
    content_mode: str
    content: str | dict[str, str]
    content_role: str = "UNTRUSTED_DATA"
    policy_version: str = POLICY_VERSION
    policy_decision_id: str = ""


@dataclass(frozen=True)
class RetrievalResult:
    status: str
    query: str
    destination_id: str
    destination_class: str
    effective_scope: Scope
    approved: tuple[ApprovedCandidate, ...]
    decisions: tuple[tuple[str, str], ...]
    policy_manifest: dict[str, object]


class RetrievalService:
    def __init__(
        self,
        index: IndexManager,
        *,
        destinations: DestinationRegistry | None = None,
        scanner: SecretScanner | None = None,
        deletion_resolver: DeletionResolver | None = None,
    ):
        self.index = index
        self.destinations = destinations or DestinationRegistry()
        self.scanner = scanner or SecretScanner()
        self.deletion = deletion_resolver or index.deletion

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        destination, error = self._validate_request(request)
        if error:
            return self._result("NO_ELIGIBLE_CONTEXT", (), (("REQUEST", error),), request, destination)
        terms = _terms(request.query)
        source_rows, query_mode = self._candidate_rows(terms)
        effective_scope = request.requested_scope or request.granted_scope
        approved: list[ApprovedCandidate] = []
        decisions: list[tuple[str, str]] = []
        for source_id, rank in source_rows:
            candidate, reason = self._evaluate(request, destination, effective_scope, source_id, rank, query_mode)
            if candidate is not None:
                approved.append(candidate)
                if len(approved) >= min(request.max_results, FINAL_APPROVED_LIMIT):
                    break
            else:
                decisions.append((source_id, reason))
        return self._result("OK" if approved else "NO_ELIGIBLE_CONTEXT", tuple(approved), tuple(decisions), request, destination)

    def _validate_request(self, request: RetrievalRequest) -> tuple[Destination | None, str]:
        try:
            value = uuid.UUID(request.request_id)
            if value.version != 4 or str(value) != request.request_id:
                return None, "DENY_REQUEST_INVALID"
        except (TypeError, ValueError, AttributeError):
            return None, "DENY_REQUEST_INVALID"
        if not isinstance(request.query, str) or not request.query.strip() or len(request.query.encode()) > MAX_QUERY_BYTES:
            return None, "DENY_REQUEST_INVALID"
        if len(_terms(request.query)) > MAX_TERMS or any(ord(char) < 32 and char not in "\t\n\r" for char in request.query):
            return None, "DENY_REQUEST_INVALID"
        if request.capability != CAPABILITY:
            return None, "DENY_CAPABILITY"
        if not isinstance(request.destination_id, str) or not isinstance(request.granted_scope, Scope) or (request.requested_scope is not None and not isinstance(request.requested_scope, Scope)):
            return None, "DENY_REQUEST_INVALID"
        destination = self.destinations.resolve(request.destination_id)
        if destination is None or not destination.enabled or destination.destination_class not in {DESTINATION_LOCAL, DESTINATION_TRUSTED_EXTERNAL}:
            return None, "DENY_DESTINATION_UNKNOWN"
        if CAPABILITY not in destination.capabilities:
            return destination, "DENY_CAPABILITY"
        if not _valid_scope(request.granted_scope) or (request.requested_scope and not _narrower(request.requested_scope, request.granted_scope)):
            return destination, "DENY_SCOPE"
        if not isinstance(request.max_results, int) or isinstance(request.max_results, bool) or not 1 <= request.max_results <= FINAL_APPROVED_LIMIT:
            return destination, "DENY_REQUEST_INVALID"
        return destination, ""

    def _candidate_rows(self, terms: tuple[str, ...]) -> tuple[list[tuple[str, float | None]], str]:
        connection = self.index.connection
        if connection is None:
            self.index.open()
            connection = self.index.connection
        if any(len(term) < 3 for term in terms):
            where, values = _like_where(terms)
            rows = connection.execute(
                f"SELECT source_id, NULL FROM source_fts WHERE {where} LIMIT ?", (*values, INDEX_CANDIDATE_LIMIT)
            ).fetchall()
            return [(row[0], None) for row in rows], "LIKE_SHORT"
        quoted = [f'"{term.replace(chr(34), chr(34) * 2)}"' for term in terms]
        rows = connection.execute(
            "SELECT f.source_id, f.rank FROM source_fts f JOIN source_index i ON i.source_id=f.source_id "
            "WHERE f.source_fts MATCH ? ORDER BY f.rank ASC, i.captured_at DESC, f.source_id ASC LIMIT ?",
            (" AND ".join(quoted), INDEX_CANDIDATE_LIMIT),
        ).fetchall()
        if rows or len(quoted) == 1:
            return [(row[0], row[1]) for row in rows], "FTS_AND"
        rows = connection.execute(
            "SELECT f.source_id, f.rank FROM source_fts f JOIN source_index i ON i.source_id=f.source_id "
            "WHERE f.source_fts MATCH ? ORDER BY f.rank ASC, i.captured_at DESC, f.source_id ASC LIMIT ?",
            (" OR ".join(quoted), INDEX_CANDIDATE_LIMIT),
        ).fetchall()
        return [(row[0], row[1]) for row in rows], "FTS_OR_FALLBACK"

    def _evaluate(self, request: RetrievalRequest, destination: Destination, scope: Scope, source_id: str, rank: float | None, query_mode: str) -> tuple[ApprovedCandidate | None, str]:
        try:
            handle = self.index.locator.resolve_active_vault()
            path = handle.root_ref / "canonical" / "sources" / source_id
            if path.is_symlink() or (path / "source.md").is_symlink() or (path / "payload/original").is_symlink():
                return None, "DENY_CANONICAL_INVALID"
            manifest = parse_source((path / "source.md").read_text())
            validate_source(manifest, expected_object_id=source_id)
            payload = (path / "payload/original").read_bytes()
            if not validate_payload(manifest, payload):
                return None, "DENY_CANONICAL_INVALID"
        except (OSError, ValueError, SourceValidationError, KeyError):
            return None, "DENY_CANONICAL_INVALID"
        deletion = self.deletion.resolve_source(source_id)
        if deletion.state == DELETED:
            return None, "DENY_DELETED"
        if deletion.state != NOT_DELETED:
            return None, "DENY_DELETION_UNKNOWN"
        source_scope = Scope(manifest["scope"]["scope_type"], manifest["scope"]["scope_id"])
        if not _scope_allows(scope, source_scope):
            return None, "DENY_SCOPE" if _valid_scope(source_scope) else "DENY_UNSUPPORTED_SCOPE"
        sensitivity = manifest["sensitivity"]["level"]
        if sensitivity == "RESTRICTED":
            return None, "DENY_RESTRICTED"
        if sensitivity not in {"PUBLIC", "PERSONAL", "SENSITIVE"}:
            return None, "DENY_SENSITIVITY_UNKNOWN"
        if sensitivity == "SENSITIVE" and destination.destination_class != DESTINATION_LOCAL:
            return None, "DENY_SENSITIVE_EXTERNAL"
        if self.scanner.scan_bytes(payload).outcome != "CLEAR":
            return None, "DENY_SECRET_RECLASSIFIED"
        source = manifest["source"]
        if source["kind"] in {"TEXT", "URL"}:
            content_mode, content = "TEXT_BODY", payload.decode("utf-8")
        else:
            content_mode = "METADATA_ONLY"
            content = {"original_name": source["original_name"] or "", "kind": source["kind"], "media_type": source["media_type"]}
        decision_id = hashlib.sha256(f"{request.request_id}:{source_id}:{manifest['revision']}:{POLICY_VERSION}".encode()).hexdigest()
        return ApprovedCandidate(request.request_id, source_id, manifest["revision"], source["payload_sha256"], query_mode, rank, destination.destination_id, destination.destination_class, sensitivity, scope, content_mode, content, policy_decision_id=decision_id), ""

    def _result(self, status: str, approved: tuple[ApprovedCandidate, ...], decisions: tuple[tuple[str, str], ...], request: RetrievalRequest, destination: Destination | None) -> RetrievalResult:
        manifest = {"request_id": request.request_id, "policy_version": POLICY_VERSION, "destination_id": request.destination_id, "destination_class": destination.destination_class if destination else DESTINATION_UNKNOWN_EXTERNAL, "capability": request.capability, "evaluated_at": _now(), "approved_count": len(approved), "decision_hash": hashlib.sha256(repr(decisions).encode()).hexdigest()}
        scope = request.requested_scope or request.granted_scope
        return RetrievalResult(status, request.query, request.destination_id, manifest["destination_class"], scope, approved, decisions, manifest)


def _terms(query: str) -> tuple[str, ...]:
    return tuple(term for term in re.split(r"\s+", query.strip()) if term)


def _like_where(terms: tuple[str, ...]) -> tuple[str, list[str]]:
    values: list[str] = []
    clauses: list[str] = []
    for term in terms:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("(name LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\')")
        values.extend((f"%{escaped}%", f"%{escaped}%"))
    return " AND ".join(clauses), values


def _valid_scope(scope: Scope) -> bool:
    return (scope.scope_type == "GLOBAL" and scope.scope_id is None) or (scope.scope_type == "PROJECT" and isinstance(scope.scope_id, str) and scope.scope_id)


def _narrower(requested: Scope, granted: Scope) -> bool:
    return requested == granted or (granted.scope_type == "PROJECT" and requested.scope_type == "GLOBAL")


def _scope_allows(granted: Scope, source: Scope) -> bool:
    if not _valid_scope(source):
        return False
    return source.scope_type == "GLOBAL" or (granted.scope_type == "PROJECT" and source == granted)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
