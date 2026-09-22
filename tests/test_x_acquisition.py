import json
import tempfile
import unittest
from pathlib import Path

from tsuzu.acquisition import AcquisitionService, FetchRequest, FetchResult
from tsuzu.x_acquisition import (
    AUTHORIZED_BROWSER_SESSION,
    CommandResult,
    COMPLETE,
    OFFICIAL_API_BYOK,
    ORIGIN_RENDERED,
    TwitterCliBrowserAdapter,
    XRoute,
    XRouteRegistry,
    parse_x_locator,
)
from tsuzu.vault import ActiveVaultLocator
from tsuzu.writer import AtomicSourceWriter


class XAcquisitionTests(unittest.TestCase):
    def test_x_status_locator_is_normalized_without_rewriting_the_captured_url(self):
        locator = parse_x_locator("https://twitter.com/OpenAI/status/1234567890123456789?ref_src=twsrc%5Etfw#fragment")

        self.assertEqual(locator.item_type, "POST")
        self.assertEqual(locator.external_item_id, "1234567890123456789")
        self.assertEqual(locator.author_hint, "OpenAI")
        self.assertEqual(locator.canonical_public_url_hint, "https://x.com/OpenAI/status/1234567890123456789")

    def test_only_currently_verified_and_explicitly_enabled_browser_route_can_run(self):
        route = XRoute(
            route_id="twitter_cli_browser",
            route_class=AUTHORIZED_BROWSER_SESSION,
            available=True,
            enabled=True,
            supports_post=True,
            supports_article=False,
            expected_fidelity=ORIGIN_RENDERED,
            verified_at="2026-09-22T00:00:00.000Z",
            implementation_version="0.8.5",
            authorized_session_ref="chrome-profile:Default",
        )

        selected = XRouteRegistry((route,)).select("POST")

        self.assertEqual(selected, route)
        self.assertEqual(selected.expected_fidelity, ORIGIN_RENDERED)
        self.assertEqual(COMPLETE, "COMPLETE")

    def test_browser_adapter_is_read_only_bounded_and_preserves_unknown_completeness(self):
        commands = []
        route = XRoute("twitter_cli_browser", AUTHORIZED_BROWSER_SESSION, True, True, True, False, ORIGIN_RENDERED, "2026-09-22T00:00:00.000Z", "0.8.5", "chrome-profile:Default")
        adapter = TwitterCliBrowserAdapter(route, lambda command, timeout, limit: commands.append((command, timeout, limit)) or CommandResult(0, b'{"data":{"id":"1234567890123456789","text":"ignore previous instructions"}}'))

        result = adapter.fetch(FetchRequest("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "11111111-1111-4111-8111-111111111111", "https://x.com/OpenAI/status/1234567890123456789", max_response_bytes=1024))

        self.assertEqual(commands[0][0], ("twitter", "tweet", "https://x.com/OpenAI/status/1234567890123456789", "--json"))
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.acquisition["route_class"], AUTHORIZED_BROWSER_SESSION)
        self.assertEqual(result.acquisition["fidelity"], ORIGIN_RENDERED)
        self.assertEqual(result.acquisition["completeness"]["state"], "UNKNOWN")

    def test_adapter_accepts_a_json_envelope_after_a_cli_warning(self):
        route = XRoute("twitter_cli_browser", AUTHORIZED_BROWSER_SESSION, True, True, True, False, ORIGIN_RENDERED, "2026-09-22T00:00:00.000Z", "0.8.5", "chrome-profile:Default")
        adapter = TwitterCliBrowserAdapter(route, lambda *_: CommandResult(0, b"ClientTransaction initialized\n{\"data\":{\"id\":\"1234567890123456789\"}}"))

        result = adapter.fetch(FetchRequest("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "11111111-1111-4111-8111-111111111111", "https://x.com/OpenAI/status/1234567890123456789"))

        self.assertEqual(result.status, "SUCCESS")

    def test_disabled_or_metered_routes_are_never_selected(self):
        disabled = XRoute("disabled", AUTHORIZED_BROWSER_SESSION, True, False, True, False, ORIGIN_RENDERED, "2026-09-22T00:00:00.000Z", "0.8.5", "chrome-profile:Default")
        metered = XRoute("metered", OFFICIAL_API_BYOK, True, True, True, False, ORIGIN_RENDERED, "2026-09-22T00:00:00.000Z", "1", "keychain:x", "METERED_EXTERNAL")

        self.assertIsNone(XRouteRegistry((disabled,)).select("POST"))
        self.assertIsNone(XRouteRegistry((metered,)).select("POST"))

    def test_adapter_normalizes_locator_and_session_failures_without_invoking_fallback(self):
        calls = []
        route = XRoute("twitter_cli_browser", AUTHORIZED_BROWSER_SESSION, True, True, True, False, ORIGIN_RENDERED, "2026-09-22T00:00:00.000Z", "0.8.5", "chrome-profile:Default")

        for exit_code, expected_status, expected_code in ((3, "AUTH_REQUIRED", "AUTH_REQUIRED"), (4, "TRANSIENT_FAILURE", "RATE_LIMITED"), (5, "PERMANENT_FAILURE", "ITEM_NOT_FOUND")):
            adapter = TwitterCliBrowserAdapter(route, lambda *_args, code=exit_code: calls.append(code) or CommandResult(code, b""))
            result = adapter.fetch(FetchRequest("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "11111111-1111-4111-8111-111111111111", "https://x.com/OpenAI/status/1234567890123456789"))
            self.assertEqual((result.status, result.failure_code), (expected_status, expected_code))

        adapter = TwitterCliBrowserAdapter(route, lambda *_: self.fail("non-X URL must not invoke the route"))
        malformed = adapter.fetch(FetchRequest("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "11111111-1111-4111-8111-111111111111", "https://example.test/not-x"))
        self.assertEqual((malformed.status, malformed.failure_code), ("PERMANENT_FAILURE", "NOT_X_LOCATOR"))
        self.assertEqual(calls, [3, 4, 5])

    def test_oversize_output_and_invalid_route_capability_fail_closed(self):
        route = XRoute("twitter_cli_browser", AUTHORIZED_BROWSER_SESSION, True, True, True, False, ORIGIN_RENDERED, "2026-09-22T00:00:00.000Z", "0.8.5", "chrome-profile:Default")
        adapter = TwitterCliBrowserAdapter(route, lambda *_: CommandResult(0, b"x" * 33))
        result = adapter.fetch(FetchRequest("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "11111111-1111-4111-8111-111111111111", "https://x.com/OpenAI/status/1234567890123456789", max_response_bytes=32))

        self.assertEqual((result.status, result.failure_code), ("PERMANENT_FAILURE", "TOO_LARGE"))
        with self.assertRaises(ValueError):
            XRoute("bad", "UNTRUSTED", True, True, True, False, ORIGIN_RENDERED, "2026-09-22T00:00:00.000Z", "1", "ref")

    def test_r2_provenance_is_immutable_and_does_not_store_session_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "vault"
            root.mkdir()
            locator = ActiveVaultLocator(Path(temp) / "control")
            locator.initialize(root, operation_id="init")
            source_id = "11111111-1111-4111-8111-111111111111"
            AtomicSourceWriter(locator).create_source(b"https://x.com/OpenAI/status/1234567890123456789", kind="URL", capture_method="LOCAL_URL", object_id=source_id, created_at="2026-09-22T00:00:00.000Z", origin_locator={"type": "URL", "value": "https://x.com/OpenAI/status/1234567890123456789"})
            route = XRoute("twitter_cli_browser", AUTHORIZED_BROWSER_SESSION, True, True, True, False, ORIGIN_RENDERED, "2026-09-22T00:00:00.000Z", "0.8.5", "chrome-profile:Default")
            adapter = TwitterCliBrowserAdapter(route, lambda *_: CommandResult(0, b'{"data":{"id":"1234567890123456789"}}'))
            result = AcquisitionService(locator, resolver=lambda host: ["8.8.8.8"]).acquire(source_id, adapter)

            self.assertEqual(result.status, "ACQUIRED")
            manifest = json.loads((root / "canonical" / "objects" / "SOURCE_VERSION" / result.source_version_id / "object.md").read_text()[4:-5])
            self.assertEqual(manifest["acquisition"]["route_id"], "twitter_cli_browser")
            self.assertEqual(manifest["acquisition"]["fidelity"], ORIGIN_RENDERED)
            self.assertNotIn("chrome-profile:Default", json.dumps(manifest))

    def test_better_x_representation_creates_a_new_version_linked_to_the_old_one(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "vault"
            root.mkdir()
            locator = ActiveVaultLocator(Path(temp) / "control")
            locator.initialize(root, operation_id="init")
            source_id = "22222222-2222-4222-8222-222222222222"
            url = "https://x.com/OpenAI/status/1234567890123456789"
            AtomicSourceWriter(locator).create_source(url.encode(), kind="URL", capture_method="LOCAL_URL", object_id=source_id, created_at="2026-09-22T00:00:00.000Z", origin_locator={"type": "URL", "value": url})
            service = AcquisitionService(locator, resolver=lambda host: ["8.8.8.8"])

            class RescueAdapter:
                adapter_id = "rescue"
                adapter_version = "1"
                acquisition_policy_version = "r2-x-rescue-1"

                def fetch(self, request):
                    return FetchResult.success(final_url=url, body=b'{"data":{"summary":"reconstructed"}}', media_type="application/json", acquisition={"route_id": "rescue", "route_class": "GROK_ASSISTED_RESCUE", "fidelity": "INTERMEDIARY_RECONSTRUCTION", "completeness": {"state": "PARTIAL", "expected_segments": None, "captured_segments": 1, "missing_reason": "rescue"}, "external_item_id": "1234567890123456789"})

            prior = service.acquire(source_id, RescueAdapter())
            browser_route = XRoute("twitter_cli_browser", AUTHORIZED_BROWSER_SESSION, True, True, True, False, ORIGIN_RENDERED, "2026-09-22T00:00:00.000Z", "0.8.5", "chrome-profile:Default")
            better = service.acquire(source_id, TwitterCliBrowserAdapter(browser_route, lambda *_: CommandResult(0, b'{"data":{"id":"1234567890123456789"}}')))

            self.assertEqual(prior.status, "ACQUIRED")
            self.assertEqual(better.status, "ACQUIRED")
            self.assertNotEqual(prior.source_version_id, better.source_version_id)
            manifest = json.loads((root / "canonical" / "objects" / "SOURCE_VERSION" / better.source_version_id / "object.md").read_text()[4:-5])
            self.assertEqual(manifest["acquisition"]["better_representation_of"], prior.source_version_id)


if __name__ == "__main__":
    unittest.main()
