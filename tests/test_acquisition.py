import gzip
import http.server
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from pathlib import Path

from tsuzu.acquisition import AcquisitionService, FetchRequest, FetchResult, PublicWebFetcher, _http_transport
from tsuzu.capture import CaptureRequest, CaptureService
from tsuzu.deletion import DeletionRequest, DeletionResolver
from tsuzu.vault import ActiveVaultLocator
from tsuzu.worker import SingleWriterWorker
from tsuzu.writer import AtomicSourceWriter


class StaticAdapter:
    adapter_id = "fixture"
    adapter_version = "1.0"

    def __init__(self, result, before_return=None):
        self.result = result
        self.before_return = before_return

    def fetch(self, request):
        if self.before_return:
            self.before_return()
        return self.result


@contextmanager
def local_http_server():
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/final")
                self.end_headers()
                return
            if self.path == "/gzip":
                body = gzip.compress(b"x" * 64)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Encoding", "gzip")
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("X-Long", "x" * 64)
            self.end_headers()
            self.wfile.write(b"x" * 64)

        def log_message(self, *_):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "vault"
        root.mkdir()
        self.locator = ActiveVaultLocator(Path(self.temp.name) / "control")
        self.locator.initialize(root, operation_id="init")
        self.writer = AtomicSourceWriter(self.locator)
        self.service = AcquisitionService(
            self.locator,
            resolver=lambda host: {"public.test": ["8.8.8.8"], "private.test": ["127.0.0.1"]}[host],
        )

    def tearDown(self):
        self.temp.cleanup()

    def capture_url(self, source_id="11111111-1111-4111-8111-111111111111", url="https://public.test/page"):
        self.writer.create_source(
            url.encode(),
            kind="URL",
            capture_method="LOCAL_URL",
            object_id=source_id,
            created_at="2026-09-13T00:00:00.000Z",
            origin_locator={"type": "URL", "value": url},
        )
        return source_id

    def success(self, *, final_url="https://public.test/page", body=b"remote body", redirect_chain=()):
        return FetchResult.success(final_url=final_url, body=body, media_type="text/html", redirect_chain=redirect_chain)

    def test_public_fetch_creates_one_immutable_source_version(self):
        source_id = self.capture_url()
        first = self.service.acquire(source_id, StaticAdapter(self.success()))
        retry = self.service.acquire(source_id, StaticAdapter(self.success()))

        self.assertEqual(first.status, "ACQUIRED")
        self.assertEqual(retry.status, "ALREADY_ACQUIRED")
        self.assertEqual(first.source_version_id, retry.source_version_id)
        path = self.locator.resolve_active_vault().root_ref / "canonical" / "objects" / "SOURCE_VERSION" / first.source_version_id
        self.assertEqual((path / "payload" / "original").read_bytes(), b"remote body")
        receipt = (self.locator.resolve_active_vault().root_ref / "system" / "acquisition-receipts" / f"{first.acquisition_key}.json").read_text()
        self.assertNotIn("remote body", receipt)
        self.assertNotIn("https://public.test/page", receipt)

    def test_private_initial_or_redirect_destination_is_blocked_before_commit(self):
        source_id = self.capture_url(url="https://private.test/internal")
        blocked = self.service.acquire(source_id, StaticAdapter(self.success()))
        self.assertEqual(blocked.status, "POLICY_BLOCKED")

        source_id = self.capture_url("44444444-4444-4444-8444-444444444444")
        redirected = self.service.acquire(source_id, StaticAdapter(self.success(final_url="https://private.test/internal")))
        self.assertEqual(redirected.status, "POLICY_BLOCKED")

        chained = self.service.acquire(source_id, StaticAdapter(self.success(redirect_chain=("https://private.test/internal",))))
        self.assertEqual(chained.status, "POLICY_BLOCKED")

    def test_restricted_body_and_tombstoned_parent_never_commit_version(self):
        source_id = self.capture_url()
        restricted = self.service.acquire(source_id, StaticAdapter(self.success(body=b"api_key=abcdefghijklmnopqrstuvwxyz")))
        self.assertEqual(restricted.status, "BLOCKED_RESTRICTED")

        source_id = self.capture_url("22222222-2222-4222-8222-222222222222")
        delete = lambda: DeletionResolver(self.locator).delete_source(DeletionRequest.source(source_id, expected_revision=1))
        deleted = self.service.acquire(source_id, StaticAdapter(self.success(), before_return=delete))
        self.assertEqual(deleted.status, "SOURCE_DELETED")

    def test_auth_required_and_oversize_response_are_not_retried_or_committed(self):
        source_id = self.capture_url()
        auth = self.service.acquire(source_id, StaticAdapter(FetchResult.auth_required()))
        self.assertEqual(auth.status, "USER_ACTION_REQUIRED")

        source_id = self.capture_url("33333333-3333-4333-8333-333333333333")
        oversize = self.service.acquire(source_id, StaticAdapter(self.success(body=b"x" * 33)), max_response_bytes=32)
        self.assertEqual(oversize.status, "PERMANENT_FAILURE")

    def test_malformed_adapter_identity_or_unsupported_media_type_never_commit(self):
        source_id = self.capture_url()
        malformed = self.service.acquire(source_id, object())
        self.assertEqual(malformed.status, "PERMANENT_FAILURE")

        source_id = self.capture_url("66666666-6666-4666-8666-666666666666")
        unsupported = self.service.acquire(source_id, StaticAdapter(FetchResult.success(final_url="https://public.test/page", body=b"{}", media_type="image/png")))
        self.assertEqual(unsupported.status, "PERMANENT_FAILURE")

    def test_url_capture_is_committed_before_a_body_free_acquisition_job_is_scheduled(self):
        queue = Path(self.temp.name) / "queue"
        accepted = CaptureService(queue).capture(CaptureRequest(
            request_id="55555555-5555-4555-8555-555555555555",
            idempotency_key="url-capture",
            kind="URL",
            content="https://public.test/page",
        ))
        self.assertEqual(SingleWriterWorker(queue, self.locator).run_once().status, "COMMITTED")

        scheduled = self.service.schedule(accepted.source_id)
        self.assertEqual(scheduled.status, "ALREADY_SCHEDULED")
        job = (self.locator.resolve_active_vault().root_ref / "system" / "acquisition-jobs" / f"{scheduled.acquisition_key}.json").read_text()
        self.assertIn('"state": "PENDING"', job)
        self.assertNotIn("https://public.test/page", job)

    def test_scheduled_job_runs_to_one_body_free_terminal_effect(self):
        source_id = self.capture_url("77777777-7777-4777-8777-777777777777")
        scheduled = self.service.schedule(source_id)
        result = self.service.run_scheduled_once(StaticAdapter(self.success()))

        self.assertEqual(result.status, "ACQUIRED")
        job = (self.locator.resolve_active_vault().root_ref / "system" / "acquisition-jobs" / f"{scheduled.acquisition_key}.json").read_text()
        self.assertIn('"state": "ACQUIRED"', job)
        self.assertNotIn("remote body", job)

    def test_transient_job_stops_after_the_configured_attempt_bound(self):
        source_id = self.capture_url("88888888-8888-4888-8888-888888888888")
        scheduled = self.service.schedule(source_id)
        transient = StaticAdapter(FetchResult("TRANSIENT_FAILURE", failure_code="TIMEOUT"))
        self.assertEqual(self.service.run_scheduled_once(transient, max_attempts=2).status, "RETRY_WAIT")
        self.assertEqual(self.service.run_scheduled_once(transient, max_attempts=2).status, "PERMANENT_FAILURE")
        job = (self.locator.resolve_active_vault().root_ref / "system" / "acquisition-jobs" / f"{scheduled.acquisition_key}.json").read_text()
        self.assertIn('"state": "PERMANENT_FAILURE"', job)

    def test_public_fetcher_blocks_unsafe_url_before_transport(self):
        called = []
        fetcher = PublicWebFetcher(lambda request, address: called.append((request.url, address)), resolver=lambda host: ["127.0.0.1"])
        result = fetcher.fetch(FetchRequest("99999999-9999-4999-8999-999999999999", "11111111-1111-4111-8111-111111111111", "https://private.test/"))
        self.assertEqual(result.status, "POLICY_BLOCKED")
        self.assertEqual(called, [])

    def test_public_fetcher_rejects_credentialed_http_before_transport(self):
        called = []
        fetcher = PublicWebFetcher(lambda request, address: called.append(address), resolver=lambda host: ["8.8.8.8"])
        result = fetcher.fetch(FetchRequest("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "11111111-1111-4111-8111-111111111111", "http://public.test/", credential_ref="keychain:item"))
        self.assertEqual(result.status, "POLICY_BLOCKED")
        self.assertEqual(called, [])

    def test_public_fetcher_revalidates_each_redirect_before_next_hop(self):
        called = []
        fetcher = PublicWebFetcher(lambda request, address: called.append(request.url) or FetchResult("REDIRECT", final_url="https://private.test/"), resolver=lambda host: {"public.test": ["8.8.8.8"], "private.test": ["127.0.0.1"]}[host])
        result = fetcher.fetch(FetchRequest("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "11111111-1111-4111-8111-111111111111", "https://public.test/"))
        self.assertEqual(result.status, "POLICY_BLOCKED")
        self.assertEqual(called, ["https://public.test/"])

    def test_public_fetcher_follows_only_revalidated_public_redirect_hops(self):
        called = []

        def transport(request, _address):
            called.append(request.url)
            if request.url.endswith("/start"):
                return FetchResult("REDIRECT", final_url="https://public.test/final")
            return FetchResult.success(final_url=request.url, body=b"ok", media_type="text/plain")

        fetcher = PublicWebFetcher(transport, resolver=lambda host: ["8.8.8.8"])
        result = fetcher.fetch(FetchRequest("cccccccc-cccc-4ccc-8ccc-cccccccccccc", "11111111-1111-4111-8111-111111111111", "https://public.test/start"))

        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.final_url, "https://public.test/final")
        self.assertEqual(result.redirect_chain, ("https://public.test/start",))
        self.assertEqual(called, ["https://public.test/start", "https://public.test/final"])

    def test_public_fetcher_enforces_redirect_and_total_timeout_bounds(self):
        redirect = PublicWebFetcher(lambda request, address: FetchResult("REDIRECT", final_url="https://public.test/again"), resolver=lambda host: ["8.8.8.8"])
        too_many = redirect.fetch(FetchRequest("dddddddd-dddd-4ddd-8ddd-dddddddddddd", "11111111-1111-4111-8111-111111111111", "https://public.test/start", max_redirects=1))
        self.assertEqual(too_many.failure_code, "REDIRECT_LIMIT")

        malformed = PublicWebFetcher(lambda request, address: FetchResult("REDIRECT"), resolver=lambda host: ["8.8.8.8"]).fetch(FetchRequest("aaaaaaaa-eeee-4aaa-8aaa-aaaaaaaaaaaa", "11111111-1111-4111-8111-111111111111", "https://public.test/"))
        self.assertEqual(malformed.failure_code, "MALFORMED_REDIRECT")

        def slow_transport(request, address):
            time.sleep(0.03)
            return FetchResult.success(final_url=request.url, body=b"ok", media_type="text/plain")

        timed = PublicWebFetcher(slow_transport, resolver=lambda host: ["8.8.8.8"]).fetch(FetchRequest("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", "11111111-1111-4111-8111-111111111111", "https://public.test/", timeout_budget_ms=1))
        self.assertEqual(timed.failure_code, "TOTAL_TIMEOUT")

    def test_http_transport_does_not_follow_redirects_and_bounds_response_parts(self):
        with local_http_server() as port:
            request = FetchRequest("ffffffff-ffff-4fff-8fff-ffffffffffff", "11111111-1111-4111-8111-111111111111", f"http://public.test:{port}/redirect")
            redirected = _http_transport(request, "127.0.0.1")
            self.assertEqual(redirected.status, "REDIRECT")
            self.assertEqual(redirected.final_url, f"http://public.test:{port}/final")

            raw = _http_transport(FetchRequest("11111111-aaaa-4111-8111-111111111111", "11111111-1111-4111-8111-111111111111", f"http://public.test:{port}/final", max_response_bytes=8), "127.0.0.1")
            self.assertEqual(raw.failure_code, "RESPONSE_RAW_TOO_LARGE")

            expanded = _http_transport(FetchRequest("22222222-aaaa-4222-8222-222222222222", "11111111-1111-4111-8111-111111111111", f"http://public.test:{port}/gzip", max_response_bytes=8, max_raw_response_bytes=1024), "127.0.0.1")
            self.assertEqual(expanded.failure_code, "RESPONSE_DECOMPRESSED_TOO_LARGE")

            headers = _http_transport(FetchRequest("33333333-aaaa-4333-8333-333333333333", "11111111-1111-4111-8111-111111111111", f"http://public.test:{port}/final", max_header_bytes=32), "127.0.0.1")
            self.assertEqual(headers.failure_code, "RESPONSE_HEADERS_TOO_LARGE")


if __name__ == "__main__":
    unittest.main()
