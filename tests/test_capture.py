import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from tsuzu.capture import (
    CaptureRequest,
    CaptureService,
    CaptureStatus,
    SecretScanner,
)
from tsuzu.vault import ActiveVaultLocator


class CaptureServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "vault"
        root.mkdir()
        self.locator = ActiveVaultLocator(Path(self.temp.name) / "control")
        self.locator.initialize(root, operation_id="init")
        self.queue = Path(self.temp.name) / "queue"
        self.service = CaptureService(self.queue)

    def tearDown(self):
        self.temp.cleanup()

    def request(self, content, *, kind="TEXT", key="key-1", request_id="11111111-1111-4111-8111-111111111111", **kwargs):
        return CaptureRequest(request_id=request_id, idempotency_key=key, kind=kind, content=content, **kwargs)

    def test_text_is_durable_without_canonical_write(self):
        result = self.service.capture(self.request("hello", key="text-1"))
        self.assertEqual(result.status, CaptureStatus.ACCEPTED)
        self.assertTrue((self.queue / "pending" / result.job_id / "payload/original").exists())
        job = self.service.read_job(result.job_id)
        self.assertEqual(job["source_id"], result.source_id)
        self.assertEqual(job["payload"]["bytes"], 5)
        self.assertEqual(job["payload"]["sha256"], hashlib.sha256(b"hello").hexdigest())

    def test_url_is_preserved_without_fetch_or_query_telemetry(self):
        url = "https://example.com/article?x=1"
        result = self.service.capture(self.request(url, kind="URL", key="url-1"))
        self.assertEqual(result.status, CaptureStatus.ACCEPTED)
        job = self.service.read_job(result.job_id)
        self.assertEqual(job["source_plan"]["origin_locator"]["value"], url)
        self.assertNotIn("x=1", result.reason)

    def test_file_scans_and_copies_from_same_open_handle(self):
        path = Path(self.temp.name) / "note.txt"
        path.write_bytes(b"file bytes")
        result = self.service.capture(self.request(path, kind="FILE", key="file-1"))
        self.assertEqual(result.status, CaptureStatus.ACCEPTED)
        path.unlink()
        payload = (self.queue / "pending" / result.job_id / "payload/original").read_bytes()
        self.assertEqual(payload, b"file bytes")

    def test_private_key_and_credential_url_are_blocked_without_queue(self):
        private_key = "-----BEGIN OPENSSH PRIVATE KEY-----\nsecret-value\n-----END OPENSSH PRIVATE KEY-----"
        blocked = self.service.capture(self.request(private_key, key="secret-1"))
        self.assertEqual(blocked.status, CaptureStatus.REJECTED_RESTRICTED)
        self.assertEqual(list((self.queue / "pending").glob("*")), [])
        self.assertNotIn("secret-value", blocked.reason)
        credential_url = "https://user:password@example.com/a?access_token=abc123456789012345"
        blocked_url = self.service.capture(self.request(credential_url, kind="URL", key="secret-2"))
        self.assertEqual(blocked_url.status, CaptureStatus.REJECTED_RESTRICTED)
        self.assertNotIn("access_token", blocked_url.reason)

    def test_idempotency_and_duplicate_content_contract(self):
        first = self.service.capture(self.request("same", key="same-key"))
        retry = self.service.capture(self.request("same", key="same-key", request_id="22222222-2222-4222-8222-222222222222"))
        self.assertEqual(retry.status, CaptureStatus.ALREADY_ACCEPTED)
        self.assertEqual(retry.job_id, first.job_id)
        conflict = self.service.capture(self.request("different", key="same-key", request_id="33333333-3333-4333-8333-333333333333"))
        self.assertEqual(conflict.status, CaptureStatus.IDEMPOTENCY_CONFLICT)
        second = self.service.capture(self.request("same", key="new-key", request_id="44444444-4444-4444-8444-444444444444"))
        self.assertEqual(second.status, CaptureStatus.ACCEPTED)
        self.assertNotEqual(second.source_id, first.source_id)

    def test_sensitivity_floor_and_invalid_boundaries(self):
        sensitive = self.service.capture(self.request("normal", key="sensitive", sensitivity_override="SENSITIVE"))
        self.assertEqual(sensitive.status, CaptureStatus.ACCEPTED)
        self.assertEqual(self.service.read_job(sensitive.job_id)["source_plan"]["effective_sensitivity"], "SENSITIVE")
        restricted = self.service.capture(self.request("normal", key="restricted", sensitivity_override="RESTRICTED"))
        self.assertEqual(restricted.status, CaptureStatus.REJECTED_RESTRICTED)
        empty = self.service.capture(self.request("", key="empty"))
        self.assertEqual(empty.status, CaptureStatus.REJECTED_INVALID_INPUT)
        invalid = self.service.capture(self.request("normal", key="invalid", sensitivity_override="UNKNOWN"))
        self.assertEqual(invalid.status, CaptureStatus.REJECTED_INVALID_INPUT)

    def test_symlink_directory_special_file_and_size_are_rejected(self):
        target = Path(self.temp.name) / "target.txt"
        target.write_text("target")
        link = Path(self.temp.name) / "link.txt"
        link.symlink_to(target)
        self.assertEqual(self.service.capture(self.request(link, kind="FILE", key="link")).status, CaptureStatus.REJECTED_UNSUPPORTED_INPUT)
        directory = Path(self.temp.name) / "directory"
        directory.mkdir()
        self.assertEqual(self.service.capture(self.request(directory, kind="FILE", key="dir")).status, CaptureStatus.REJECTED_UNSUPPORTED_INPUT)
        huge = CaptureService(self.queue / "huge", max_text_bytes=3)
        self.assertEqual(huge.capture(self.request("four", key="huge")).status, CaptureStatus.REJECTED_TOO_LARGE)

    def test_fault_before_publish_leaves_no_pending_job(self):
        def fail(stage):
            if stage == "before_publish":
                raise OSError("injected")

        service = CaptureService(self.queue / "fault", failure_injector=fail)
        result = service.capture(self.request("no publish", key="fault"))
        self.assertEqual(result.status, CaptureStatus.IO_FAILED)
        self.assertEqual(list((self.queue / "fault" / "pending").glob("*")), [])

    def test_invalid_requested_timestamp_is_rejected(self):
        result = self.service.capture(self.request("time", key="time", requested_at="not-a-timestamp"))
        self.assertEqual(result.status, CaptureStatus.REJECTED_INVALID_INPUT)

    def test_scanner_is_deterministic_and_never_returns_body(self):
        scanner = SecretScanner()
        first = scanner.scan_bytes(b"token=ordinary")
        second = scanner.scan_bytes(b"token=ordinary")
        self.assertEqual(first, second)
        self.assertEqual(first.matched_rule_ids, ())
        self.assertNotIn("ordinary", repr(first))


if __name__ == "__main__":
    unittest.main()
