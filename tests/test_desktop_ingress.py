import json
import tempfile
import unittest
from pathlib import Path

from tsuzu.desktop_ingress import DesktopDraftIngress, DesktopIngressStatus
from tsuzu.deletion import DeletionRequest, DeletionResolver
from tsuzu.index import IndexManager
from tsuzu.source import create_source
from tsuzu.vault import ActiveVaultLocator
from tsuzu.worker import SingleWriterWorker, WorkerStatus
from tsuzu.writer import AtomicSourceWriter


class DesktopDraftIngressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.app_local = self.root / "app-local"
        self.vault = self.root / "vault"
        self.vault.mkdir()
        self.locator = ActiveVaultLocator(self.root / "control")
        self.locator.initialize(self.vault)
        self.index = IndexManager(self.root / "index", self.locator)
        self.index.open()
        self.ingress = DesktopDraftIngress(self.app_local, self.root / "queue", self.locator, self.index)

    def tearDown(self):
        self.index.close()
        self.temp.cleanup()

    def write_tauri_draft(self, text, *, object_id="00000000-0000-4000-8000-000000000001"):
        manifest = create_source(
            text,
            kind="TEXT",
            capture_method="LOCAL_TEXT",
            object_id=object_id,
            captured_at="2026-09-23T00:00:00.000Z",
        )
        root = self.app_local / "capture-drafts"
        source_root = root / "sources" / object_id
        (source_root / "payload").mkdir(parents=True)
        (root / "layout.json").write_text('{"format":"tsuzu-capture-draft-v1"}')
        # Match the TypeScript envelope codec; the Python Core must accept it as untrusted ingress.
        (source_root / "source.md").write_text("---\n" + json.dumps(manifest, indent=2) + "\n---\n")
        (source_root / "payload" / "original").write_bytes(text.encode())
        return object_id

    def test_durable_draft_is_only_materialized_by_core_and_survives_reopen(self):
        draft_id = self.write_tauri_draft("Tauri からの記録")

        submitted = self.ingress.submit(draft_id)

        self.assertEqual(submitted.status, DesktopIngressStatus.QUEUED)
        self.assertEqual(AtomicSourceWriter(self.locator).inspect_source(submitted.source_id).status, "MISSING")
        self.assertFalse((self.app_local / "capture-drafts" / "sources" / draft_id / "core-receipt.json").exists())

        self.index.close()
        self.index = IndexManager(self.root / "index", self.locator)
        self.index.open()
        reopened = DesktopDraftIngress(self.app_local, self.root / "queue", self.locator, self.index)
        self.assertEqual(reopened.materialize().status, DesktopIngressStatus.COMMITTED)
        receipt = json.loads((self.app_local / "capture-drafts" / "sources" / draft_id / "core-receipt.json").read_text())
        self.assertEqual(receipt["source_id"], submitted.source_id)
        self.assertEqual(AtomicSourceWriter(self.locator).inspect_source(submitted.source_id).status, "VALID")
        self.assertIn(submitted.source_id, self.index.search("Tauri"))

    def test_repeated_ingress_is_idempotent_after_a_core_receipt(self):
        draft_id = self.write_tauri_draft("同じ下書きを二度送らない")
        first = self.ingress.submit(draft_id)
        self.ingress.materialize()

        replay = self.ingress.submit(draft_id)

        self.assertEqual(replay.status, DesktopIngressStatus.ALREADY_COMMITTED)
        self.assertEqual(replay.source_id, first.source_id)
        sources = list((self.vault / "canonical" / "sources").iterdir())
        self.assertEqual([path.name for path in sources], [first.source_id])

    def test_copied_core_receipt_is_rejected_for_a_different_draft(self):
        first_id = self.write_tauri_draft("最初の下書き")
        self.ingress.submit(first_id)
        self.ingress.materialize()
        second_id = self.write_tauri_draft("別の下書き", object_id="00000000-0000-4000-8000-000000000002")
        first_receipt = self.app_local / "capture-drafts" / "sources" / first_id / "core-receipt.json"
        second_receipt = self.app_local / "capture-drafts" / "sources" / second_id / "core-receipt.json"
        second_receipt.write_text(first_receipt.read_text())

        self.assertEqual(self.ingress.submit(second_id).status, DesktopIngressStatus.REJECTED_INVALID_DRAFT)

    def test_secret_and_tampered_drafts_never_reach_canonical(self):
        secret_id = self.write_tauri_draft("api_key=abcdefghijklmnopqrstuvwxyz")
        tampered_id = self.write_tauri_draft("intact", object_id="00000000-0000-4000-8000-000000000002")
        (self.app_local / "capture-drafts" / "sources" / tampered_id / "payload" / "original").write_text("tampered")

        self.assertEqual(self.ingress.submit(secret_id).status, DesktopIngressStatus.REJECTED_RESTRICTED)
        self.assertEqual(self.ingress.submit(tampered_id).status, DesktopIngressStatus.REJECTED_INVALID_DRAFT)
        self.assertFalse((self.vault / "canonical" / "sources").exists())

    def test_recovery_after_core_crash_writes_receipt_only_after_commit(self):
        draft_id = self.write_tauri_draft("復旧可能な下書き")
        submitted = self.ingress.submit(draft_id)

        def fail(stage):
            if stage == "after_canonical":
                raise OSError("simulated crash")

        self.assertEqual(SingleWriterWorker(self.root / "queue", self.locator, failure_injector=fail).run_once().status, WorkerStatus.COMMIT_UNCERTAIN)
        self.assertFalse((self.app_local / "capture-drafts" / "sources" / draft_id / "core-receipt.json").exists())

        reopened = DesktopDraftIngress(self.app_local, self.root / "queue", self.locator, self.index)
        self.assertEqual(reopened.materialize().status, DesktopIngressStatus.COMMITTED)
        self.assertEqual(AtomicSourceWriter(self.locator).inspect_source(submitted.source_id).status, "VALID")

    def test_core_deletion_does_not_allow_a_draft_receipt_to_resurrect_memory(self):
        draft_id = self.write_tauri_draft("削除対象の下書き")
        submitted = self.ingress.submit(draft_id)
        self.ingress.materialize()

        self.assertEqual(DeletionResolver(self.locator).delete_source(DeletionRequest.source(submitted.source_id, expected_revision=1), index=self.index).status, "DELETED")
        self.assertEqual(self.ingress.submit(draft_id).status, DesktopIngressStatus.ALREADY_COMMITTED)
        self.assertEqual(self.index.search("削除対象"), [])


if __name__ == "__main__":
    unittest.main()
