import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tsuzu.capture import CaptureRequest, CaptureService, SecretScanResult, SecretScanner
from tsuzu.vault import ActiveVaultLocator
from tsuzu.worker import SingleWriterWorker, WorkerResult, WorkerStatus
from tsuzu.writer import AtomicSourceWriter, WriterError


class BlockScanner(SecretScanner):
    def scan_bytes(self, payload):
        return SecretScanResult("BLOCKED_RESTRICTED", self.RULESET_VERSION, ("TEST_BLOCK",), len(payload), "0" * 64)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "vault"
        root.mkdir()
        self.locator = ActiveVaultLocator(Path(self.temp.name) / "control")
        self.locator.initialize(root, operation_id="init")
        self.queue = Path(self.temp.name) / "queue"
        self.capture = CaptureService(self.queue)

    def tearDown(self):
        self.temp.cleanup()

    def request(self, content="hello", key="key-1", request_id="11111111-1111-4111-8111-111111111111"):
        return CaptureRequest(request_id=request_id, idempotency_key=key, kind="TEXT", content=content)

    def test_happy_path_receipt_before_cleanup_and_capture_reconcile(self):
        accepted = self.capture.capture(self.request())
        worker = SingleWriterWorker(self.queue, self.locator)
        result = worker.run_once()
        self.assertEqual(result.status, WorkerStatus.COMMITTED)
        self.assertFalse((self.queue / "pending" / accepted.job_id).exists())
        receipt = json.loads((self.queue / "receipts" / f"{self._key_hash('key-1')}.json").read_text())
        self.assertEqual(receipt["source_id"], accepted.source_id)
        self.assertEqual(self.capture.capture(self.request(request_id="22222222-2222-4222-8222-222222222222")).status, "ALREADY_ACCEPTED")
        self.assertEqual(AtomicSourceWriter(self.locator).inspect_source(accepted.source_id).status, "VALID")

    def test_same_job_reprocesses_as_already_committed(self):
        accepted = self.capture.capture(self.request(key="replay"))
        original = self.queue / "pending" / accepted.job_id
        backup = Path(self.temp.name) / "backup-job"
        shutil.copytree(original, backup)
        worker = SingleWriterWorker(self.queue, self.locator)
        self.assertEqual(worker.run_once().status, WorkerStatus.COMMITTED)
        (self.queue / "pending").mkdir(exist_ok=True)
        shutil.copytree(backup, self.queue / "processing" / accepted.job_id)
        result = worker.run_once()
        self.assertEqual(result.status, WorkerStatus.ALREADY_COMMITTED)

    def test_payload_tamper_is_quarantined_without_canonical(self):
        accepted = self.capture.capture(self.request(key="tamper"))
        pending = self.queue / "pending" / accepted.job_id
        os_processing = self.queue / "processing" / accepted.job_id
        os_processing.parent.mkdir(exist_ok=True)
        pending.rename(os_processing)
        (os_processing / "payload/original").write_bytes(b"tampered")
        result = SingleWriterWorker(self.queue, self.locator).run_once()
        self.assertEqual(result.status, WorkerStatus.QUARANTINED)
        self.assertEqual(AtomicSourceWriter(self.locator).inspect_source(accepted.source_id).status, "MISSING")

    def test_secret_ruleset_upgrade_blocks_and_deletes_queue_payload(self):
        accepted = self.capture.capture(self.request(key="upgrade"))
        result = SingleWriterWorker(self.queue, self.locator, scanner=BlockScanner()).run_once()
        self.assertEqual(result.status, WorkerStatus.BLOCKED_RESTRICTED)
        self.assertFalse((self.queue / "pending" / accepted.job_id).exists())
        self.assertFalse((self.queue / "processing" / accepted.job_id).exists())
        receipt = json.loads((self.queue / "receipts" / f"{self._key_hash('upgrade')}.json").read_text())
        self.assertEqual(receipt["terminal_state"], "BLOCKED_RESTRICTED")
        self.assertEqual(AtomicSourceWriter(self.locator).inspect_source(accepted.source_id).status, "MISSING")

    def test_crash_after_canonical_before_receipt_recovers(self):
        accepted = self.capture.capture(self.request(key="crash"))

        def fail(stage):
            if stage == "after_canonical":
                raise OSError("crash")

        first = SingleWriterWorker(self.queue, self.locator, failure_injector=fail).run_once()
        self.assertEqual(first.status, WorkerStatus.COMMIT_UNCERTAIN)
        self.assertTrue((self.queue / "processing" / accepted.job_id).exists())
        second = SingleWriterWorker(self.queue, self.locator).run_once()
        self.assertEqual(second.status, WorkerStatus.ALREADY_COMMITTED)
        self.assertFalse((self.queue / "processing" / accepted.job_id).exists())

    def test_crash_after_receipt_only_requires_cleanup_recovery(self):
        accepted = self.capture.capture(self.request(key="receipt-crash"))

        def fail(stage):
            if stage == "after_receipt":
                raise OSError("crash")

        first = SingleWriterWorker(self.queue, self.locator, failure_injector=fail).run_once()
        self.assertEqual(first.status, WorkerStatus.COMMIT_UNCERTAIN)
        self.assertTrue((self.queue / "processing" / accepted.job_id).exists())
        second = SingleWriterWorker(self.queue, self.locator).run_once()
        self.assertEqual(second.status, WorkerStatus.ALREADY_COMMITTED)
        self.assertFalse((self.queue / "processing" / accepted.job_id).exists())

    def test_source_id_collision_is_quarantined(self):
        accepted = self.capture.capture(self.request(key="collision"))
        AtomicSourceWriter(self.locator).create_source(b"other", kind="TEXT", capture_method="LOCAL_TEXT", object_id=accepted.source_id, created_at="2026-09-12T00:00:00.000Z")
        result = SingleWriterWorker(self.queue, self.locator).run_once()
        self.assertEqual(result.status, WorkerStatus.QUARANTINED)
        self.assertEqual(AtomicSourceWriter(self.locator).inspect_source(accepted.source_id).status, "VALID")

    def test_second_worker_does_not_process(self):
        self.capture.capture(self.request(key="busy"))
        worker = SingleWriterWorker(self.queue, self.locator)
        with mock.patch.object(worker, "_worker_lock", side_effect=WriterError("WRITER_BUSY", "busy")):
            self.assertEqual(worker.run_once().status, WorkerStatus.WORKER_BUSY)

    @staticmethod
    def _key_hash(value):
        import hashlib

        return hashlib.sha256(value.encode()).hexdigest()


if __name__ == "__main__":
    unittest.main()
