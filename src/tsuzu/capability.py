"""Fail-closed verified host capability registry (C6)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone


VERIFIED = "VERIFIED"
UNAVAILABLE = "UNAVAILABLE"
UNVERIFIED = "UNVERIFIED"
NO = "NO"
UNKNOWN = "UNKNOWN"
CAPABILITIES = frozenset({"READ_CONTEXT", "EXPLICIT_RECALL", "PASSIVE_CONTEXT_INJECTION", "CAPTURE_CONVERSATION", "CAPTURE_ARTIFACT", "PROPOSE_DERIVED", "WATCH_SCOPED_SESSION", "TOOL_READ"})


@dataclass(frozen=True)
class Capability:
    name: str
    state: str
    scope_types: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class CapabilityReport:
    adapter_id: str
    adapter_kind: str
    adapter_version: str
    verified_at: str
    verification_method: str
    capabilities: tuple[Capability, ...]
    destination_class: str
    report_hash: str = ""

    def __post_init__(self):
        if not self.report_hash:
            object.__setattr__(self, "report_hash", hashlib.sha256(json.dumps({"id": self.adapter_id, "kind": self.adapter_kind, "version": self.adapter_version, "capabilities": [item.__dict__ for item in self.capabilities]}, sort_keys=True).encode()).hexdigest())


class CapabilityRegistry:
    def __init__(self):
        self._reports: dict[str, CapabilityReport] = {}

    def publish(self, report: CapabilityReport) -> None:
        if not report.adapter_id or report.destination_class not in {"LOCAL", "TRUSTED_EXTERNAL", "UNKNOWN_EXTERNAL"}:
            raise ValueError("invalid capability report")
        if any(item.name not in CAPABILITIES or item.state not in {VERIFIED, UNAVAILABLE, UNVERIFIED} for item in report.capabilities):
            raise ValueError("invalid capability")
        self._reports[report.adapter_id] = report

    def get_capability_report(self, adapter_id: str) -> CapabilityReport | None:
        return self._reports.get(adapter_id)

    def supports(self, adapter_id: str, capability: str, scope_type: str = "GLOBAL") -> str:
        report = self._reports.get(adapter_id)
        if report is None:
            return UNKNOWN
        for item in report.capabilities:
            if item.name == capability:
                return VERIFIED if item.state == VERIFIED and (not item.scope_types or scope_type in item.scope_types) else NO
        return NO

    def route(self, capability: str, candidates: tuple[str, ...], scope_type: str = "GLOBAL") -> str | None:
        return next((adapter_id for adapter_id in candidates if self.supports(adapter_id, capability, scope_type) == VERIFIED), None)

    def invalidate_report(self, adapter_id: str, reason: str) -> None:
        report = self._reports.get(adapter_id)
        if report is None:
            return
        self._reports[adapter_id] = CapabilityReport(report.adapter_id, report.adapter_kind, report.adapter_version, _now(), f"INVALIDATED:{reason}", tuple(Capability(item.name, UNVERIFIED, item.scope_types, item.limitations) for item in report.capabilities), report.destination_class)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
