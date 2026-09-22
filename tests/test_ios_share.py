import tempfile
import unittest
from pathlib import Path

from tsuzu.capture import CaptureRequest, CaptureService, SecretScanResult, SecretScanner
from tsuzu.ios_share import MacInboxConsumer, MobileOutbox, MobileShareRequest, TransportStatus
from tsuzu.vault import ActiveVaultLocator
from tsuzu.writer import AtomicSourceWriter


class IosShareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        vault = Path(self.temp.name) / "vault"
        vault.mkdir()
        self.locator = ActiveVaultLocator(Path(self.temp.name) / "control")
        self.locator.initialize(vault, operation_id="init")
        self.outbox = MobileOutbox(Path(self.temp.name) / "mobile", signer=lambda value: "signed:" + value.hex()[:16])
        self.queue = Path(self.temp.name) / "queue"

    def tearDown(self):
        self.temp.cleanup()

    def request(self, key="22222222-2222-4222-8222-222222222222"):
        return MobileShareRequest(
            mobile_capture_id="11111111-1111-4111-8111-111111111111",
            idempotency_key=key,
            kind="URL",
            content="https://example.com/a",
            created_at="2026-09-22T00:00:00.000Z",
            device_key_id="phone-1",
            signature_algorithm="test",
        )

    def consumer(self, *, trusted=True):
        return MacInboxConsumer(
            self.queue,
            self.locator,
            verifier=lambda key_id, algorithm, signed, signature: trusted and key_id == "phone-1" and algorithm == "test" and signature.startswith("signed:"),
        )

    def test_signed_delivery_commits_once_and_replay_after_delete_does_not_resurrect(self):
        accepted = self.outbox.accept(self.request())
        self.assertEqual(accepted.status, TransportStatus.LOCAL_PENDING)
        first = self.consumer().consume(accepted.envelope_dir)
        self.assertEqual(first.status, TransportStatus.MAC_COMMITTED)
        second = self.consumer().consume(accepted.envelope_dir)
        self.assertEqual(second.status, TransportStatus.MAC_ACCEPTED)
        writer = AtomicSourceWriter(self.locator)
        writer.update_source_metadata(first.source_id, expected_revision=1, patch={"deletion": {"state": "TOMBSTONED", "tombstoned_at": "2026-09-22T00:01:00.000Z"}})
        replay = self.consumer().consume(accepted.envelope_dir)
        self.assertEqual(replay.status, TransportStatus.MAC_ACCEPTED)
        self.assertEqual(writer.inspect_source(first.source_id).revision, 2)

    def test_unpaired_or_tampered_delivery_is_rejected_before_capture(self):
        accepted = self.outbox.accept(self.request())
        denied = self.consumer(trusted=False).consume(accepted.envelope_dir)
        self.assertEqual(denied.status, TransportStatus.TRANSPORT_AUTHENTICITY_FAILED)
        self.assertFalse((self.queue / "pending").exists())
        payload = accepted.envelope_dir / "payload/original"
        payload.write_bytes(b"tampered")
        tampered = self.consumer().consume(accepted.envelope_dir)
        self.assertEqual(tampered.status, TransportStatus.TRANSPORT_AUTHENTICITY_FAILED)

    def test_secret_is_not_durably_accepted(self):
        request = MobileShareRequest(
            mobile_capture_id="33333333-3333-4333-8333-333333333333",
            idempotency_key="44444444-4444-4444-8444-444444444444",
            kind="TEXT", content="sk-abcdefghijklmnopqrstuvwxyz", created_at="2026-09-22T00:00:00.000Z",
            device_key_id="phone-1", signature_algorithm="test",
        )
        self.assertEqual(self.outbox.accept(request).status, TransportStatus.REJECTED_RESTRICTED)

    def test_mac_rechecks_a_signed_mobile_payload(self):
        class PermissiveMobileScanner(SecretScanner):
            def scan_stream(self, stream, **kwargs):
                raw = stream.read()
                return SecretScanResult("CLEAR", self.RULESET_VERSION, (), len(raw), __import__("hashlib").sha256(raw).hexdigest())

        outbox = MobileOutbox(Path(self.temp.name) / "permissive-mobile", signer=lambda value: "signed:" + value.hex()[:16], scanner=PermissiveMobileScanner())
        request = MobileShareRequest(
            mobile_capture_id="77777777-7777-4777-8777-777777777777",
            idempotency_key="88888888-8888-4888-8888-888888888888",
            kind="TEXT", content="sk-abcdefghijklmnopqrstuvwxyz", created_at="2026-09-22T00:00:00.000Z",
            device_key_id="phone-1", signature_algorithm="test",
        )
        accepted = outbox.accept(request)
        self.assertEqual(self.consumer().consume(accepted.envelope_dir).status, TransportStatus.REJECTED_RESTRICTED)
        self.assertEqual(list((self.locator.resolve_active_vault().root_ref / "canonical" / "sources").glob("*")), [])

    def test_unrelated_worker_completion_is_not_acknowledged_for_this_envelope(self):
        unrelated = CaptureService(self.queue).capture(CaptureRequest(
            request_id="99999999-9999-4999-8999-999999999999", idempotency_key="unrelated", kind="TEXT", content="other",
        ))
        processing = self.queue / "processing" / unrelated.job_id
        processing.parent.mkdir(exist_ok=True)
        (self.queue / "pending" / unrelated.job_id).rename(processing)
        accepted = self.outbox.accept(self.request())
        self.assertEqual(self.consumer().consume(accepted.envelope_dir).status, TransportStatus.IO_FAILED)
        self.assertEqual(self.consumer().consume(accepted.envelope_dir).status, TransportStatus.MAC_COMMITTED)

    def test_file_is_copied_before_provider_disappears(self):
        provider_file = Path(self.temp.name) / "provider.txt"
        provider_file.write_bytes(b"copied file")
        request = MobileShareRequest(
            mobile_capture_id="55555555-5555-4555-8555-555555555555",
            idempotency_key="66666666-6666-4666-8666-666666666666",
            kind="FILE", content=provider_file, created_at="2026-09-22T00:00:00.000Z",
            device_key_id="phone-1", signature_algorithm="test", original_name="provider.txt",
        )
        accepted = self.outbox.accept(request)
        provider_file.unlink()
        self.assertEqual((accepted.envelope_dir / "payload/original").read_bytes(), b"copied file")
        self.assertEqual(self.consumer().consume(accepted.envelope_dir).status, TransportStatus.MAC_COMMITTED)
        self.assertTrue(self.outbox.cleanup_after_receipt(request.mobile_capture_id, TransportStatus.MAC_COMMITTED))
        self.assertFalse(accepted.envelope_dir.exists())


if __name__ == "__main__":
    unittest.main()
