"""Truthful, bounded X acquisition route adapters (R2)."""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

from .acquisition import FetchRequest, FetchResult


OFFICIAL_API_BYOK = "OFFICIAL_API_BYOK"
PUBLIC_ORIGIN_FETCH = "PUBLIC_ORIGIN_FETCH"
AUTHORIZED_BROWSER_SESSION = "AUTHORIZED_BROWSER_SESSION"
GROK_ASSISTED_RESCUE = "GROK_ASSISTED_RESCUE"
UNAVAILABLE = "UNAVAILABLE"
ORIGIN_VERBATIM = "ORIGIN_VERBATIM"
ORIGIN_RENDERED = "ORIGIN_RENDERED"
INTERMEDIARY_RECONSTRUCTION = "INTERMEDIARY_RECONSTRUCTION"
METADATA_ONLY = "METADATA_ONLY"
COMPLETE = "COMPLETE"
PARTIAL = "PARTIAL"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class XLocator:
    captured_url: str
    item_type: str
    external_item_id: str | None
    author_hint: str | None
    canonical_public_url_hint: str | None


def parse_x_locator(url: str) -> XLocator:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    if host not in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        return XLocator(url, "UNKNOWN", None, None, None)
    if len(parts) == 3 and parts[1] in {"status", "article"} and parts[2].isdigit():
        item_type = "POST" if parts[1] == "status" else "ARTICLE"
        return XLocator(url, item_type, parts[2], parts[0] if parts[0] != "i" else None, f"https://x.com/{parts[0]}/{parts[1]}/{parts[2]}")
    return XLocator(url, "UNKNOWN", None, None, None)


@dataclass(frozen=True)
class XRoute:
    route_id: str
    route_class: str
    available: bool
    enabled: bool
    supports_post: bool
    supports_article: bool
    expected_fidelity: str
    verified_at: str
    implementation_version: str
    authorized_session_ref: str
    cost_class: str = "FREE_LOCAL"

    def __post_init__(self):
        if self.route_class not in {OFFICIAL_API_BYOK, PUBLIC_ORIGIN_FETCH, AUTHORIZED_BROWSER_SESSION, GROK_ASSISTED_RESCUE, UNAVAILABLE}:
            raise ValueError("invalid X route class")
        if self.expected_fidelity not in {ORIGIN_VERBATIM, ORIGIN_RENDERED, INTERMEDIARY_RECONSTRUCTION, METADATA_ONLY}:
            raise ValueError("invalid X route fidelity")
        if self.cost_class not in {"FREE_LOCAL", "USER_BYOK", "SUBSCRIPTION_INCLUDED", "METERED_EXTERNAL", "UNKNOWN"}:
            raise ValueError("invalid X route cost class")

    def usable_for(self, item_type: str) -> bool:
        return (
            self.available
            and self.enabled
            and bool(self.verified_at)
            and bool(self.implementation_version)
            and bool(self.authorized_session_ref)
            and self.expected_fidelity in {ORIGIN_VERBATIM, ORIGIN_RENDERED, INTERMEDIARY_RECONSTRUCTION, METADATA_ONLY}
            and ((item_type == "POST" and self.supports_post) or (item_type == "ARTICLE" and self.supports_article))
        )


class XRouteRegistry:
    def __init__(self, routes: tuple[XRoute, ...], *, allow_metered: bool = False):
        if len({route.route_id for route in routes}) != len(routes):
            raise ValueError("duplicate X route")
        self.routes = routes
        self.allow_metered = allow_metered

    def select(self, item_type: str) -> XRoute | None:
        preference = {OFFICIAL_API_BYOK: 0, PUBLIC_ORIGIN_FETCH: 1, AUTHORIZED_BROWSER_SESSION: 2, GROK_ASSISTED_RESCUE: 3}
        candidates = [route for route in self.routes if route.usable_for(item_type) and (self.allow_metered or route.cost_class not in {"METERED_EXTERNAL", "UNKNOWN"})]
        return min(candidates, key=lambda route: preference.get(route.route_class, 99), default=None)


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: bytes


class TwitterCliBrowserAdapter:
    """Explicitly enabled, read-only bridge to an already-authorized twitter-cli session."""

    adapter_id = "twitter_cli_browser"
    acquisition_policy_version = "r2-x-browser-1"

    def __init__(self, route: XRoute, runner: Callable[[tuple[str, ...], int, int], CommandResult] | None = None):
        if route.route_id != self.adapter_id or route.route_class != AUTHORIZED_BROWSER_SESSION:
            raise ValueError("twitter-cli requires its authorized browser route")
        self.route = route
        self.adapter_version = route.implementation_version
        self.runner = runner or _run_readonly_twitter_cli

    def fetch(self, request: FetchRequest) -> FetchResult:
        locator = parse_x_locator(request.url)
        if locator.item_type == "UNKNOWN" or locator.canonical_public_url_hint is None:
            return FetchResult("PERMANENT_FAILURE", failure_code="NOT_X_LOCATOR")
        if not self.route.usable_for(locator.item_type):
            return FetchResult("POLICY_BLOCKED", failure_code="ROUTE_UNAVAILABLE")
        command = ("twitter", "article" if locator.item_type == "ARTICLE" else "tweet", locator.canonical_public_url_hint, "--json")
        try:
            result = self.runner(command, request.timeout_budget_ms, request.max_response_bytes)
        except TimeoutError:
            return FetchResult("TRANSIENT_FAILURE", failure_code="TIMEOUT")
        except OSError:
            return FetchResult("PERMANENT_FAILURE", failure_code="ROUTE_UNAVAILABLE")
        if not isinstance(result, CommandResult):
            return FetchResult("PERMANENT_FAILURE", failure_code="MALFORMED_ROUTE_OUTPUT")
        if result.exit_code == 3:
            return FetchResult.auth_required()
        if result.exit_code == 4:
            return FetchResult("TRANSIENT_FAILURE", failure_code="RATE_LIMITED")
        if result.exit_code == 5:
            return FetchResult("PERMANENT_FAILURE", failure_code="ITEM_NOT_FOUND")
        if len(result.stdout) > request.max_response_bytes:
            return FetchResult("PERMANENT_FAILURE", failure_code="TOO_LARGE")
        if result.exit_code != 0:
            return FetchResult("PERMANENT_FAILURE", failure_code="MALFORMED_ROUTE_OUTPUT")
        try:
            payload, body = _json_envelope(result.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return FetchResult("PERMANENT_FAILURE", failure_code="MALFORMED_ROUTE_OUTPUT")
        if not isinstance(payload, dict) or "data" not in payload:
            return FetchResult("PERMANENT_FAILURE", failure_code="MALFORMED_ROUTE_OUTPUT")
        return FetchResult.success(
            final_url=locator.canonical_public_url_hint,
            body=body,
            media_type="application/json",
            acquisition={
                "route_id": self.route.route_id,
                "route_class": self.route.route_class,
                "fidelity": self.route.expected_fidelity,
                "completeness": {"state": UNKNOWN, "expected_segments": None, "captured_segments": None, "missing_reason": "route does not prove full thread/article coverage"},
                "external_item_id": locator.external_item_id,
            },
        )


def _run_readonly_twitter_cli(command: tuple[str, ...], timeout_ms: int, max_bytes: int) -> CommandResult:
    """Run one fixed read command; no shell, credentials, stdin, or output file."""
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=False)
    assert process.stdout is not None
    output = bytearray()
    deadline = time.monotonic() + timeout_ms / 1000
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            for key, _ in selector.select(remaining):
                chunk = os.read(key.fd, min(64 * 1024, max_bytes + 1 - len(output)))
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                output.extend(chunk)
                if len(output) > max_bytes:
                    process.kill()
                    process.wait()
                    return CommandResult(1, bytes(output))
        return CommandResult(process.wait(timeout=max(0, deadline - time.monotonic())), bytes(output))
    except TimeoutError:
        process.kill()
        process.wait()
        raise
    finally:
        selector.close()


def _json_envelope(raw: bytes) -> tuple[object, bytes]:
    text = raw.decode("utf-8")
    decoder = json.JSONDecoder()
    starts = [0, *(index for index, value in enumerate(text) if value == "{" and index and text[index - 1] == "\n")]
    for start in reversed(starts):
        try:
            value, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if not text[start + end :].strip():
            return value, text[start : start + end].encode("utf-8")
    raise json.JSONDecodeError("missing JSON envelope", text, 0)
