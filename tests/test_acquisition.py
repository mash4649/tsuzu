import tempfile
import unittest
from pathlib import Path

from tsuzu.acquisition import AcquisitionService, FetchResult
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


if __name__ == "__main__":
    unittest.main()
