import json
import tempfile
import unittest
from pathlib import Path

from tsuzu.historical_import import AppleNotesAdapter, HistoricalItem, HistoricalImporter, MarkdownFolderAdapter
from tsuzu.capture import CaptureRequest, CaptureService
from tsuzu.worker import SingleWriterWorker, WorkerStatus
from tsuzu.vault import ActiveVaultLocator
from tsuzu.writer import AtomicSourceWriter


class HistoricalImporterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        vault = Path(self.temp.name) / "vault"
        vault.mkdir()
        self.locator = ActiveVaultLocator(Path(self.temp.name) / "control")
        self.locator.initialize(vault, operation_id="init")
        self.queue = Path(self.temp.name) / "queue"
        self.importer = HistoricalImporter(self.queue, self.locator)

    def tearDown(self):
        self.temp.cleanup()

    def item(self, body=b"first", modified="2026-09-22T00:00:00.000Z"):
        return HistoricalItem("note-1", body, modified, title_hint="Note")

    def test_same_snapshot_is_idempotent_and_changed_snapshot_is_immutable(self):
        first = self.importer.import_items("MARKDOWN_FOLDER", [self.item()])
        self.assertEqual(first.committed_count, 1)
        same = self.importer.import_items("MARKDOWN_FOLDER", [self.item()])
        self.assertEqual(same.already_imported_count, 1)
        changed = self.importer.import_items("MARKDOWN_FOLDER", [self.item(b"second", "2026-09-23T00:00:00.000Z")])
        self.assertEqual(changed.committed_count, 1)
        self.assertNotEqual(changed.source_ids[0], first.source_ids[0])
        path = AtomicSourceWriter(self.locator).inspect_source(changed.source_ids[0]).path / "source.md"
        manifest = json.loads(path.read_text().split("---\n", 2)[1])
        self.assertEqual(manifest["provenance"], {"origin": "IMPORTED", "source_refs": [], "actor": "USER", "explicitness": "IMPORT_REQUESTED"})
        self.assertEqual(manifest["import"]["previous_snapshot_ref"], first.source_ids[0])

        direct = CaptureService(self.queue).capture(CaptureRequest(
            request_id="55555555-5555-4555-8555-555555555555", idempotency_key="direct-capture", kind="TEXT", content=b"second",
        ))
        self.assertEqual(SingleWriterWorker(self.queue, self.locator).run_once().status, WorkerStatus.COMMITTED)
        self.assertNotEqual(direct.source_id, changed.source_ids[0])
        coverage = (self.locator.resolve_active_vault().root_ref / "system" / "history-coverage" / f"{changed.import_session_id}.json").read_text()
        self.assertNotIn("second", coverage)

    def test_secret_is_body_free_block_and_cancel_preserves_prior_commits(self):
        items = [
            HistoricalItem("one", b"safe", "2026-09-22T00:00:00.000Z"),
            HistoricalItem("two", b"-----BEGIN OPENSSH PRIVATE KEY-----", "2026-09-22T00:00:00.000Z"),
            HistoricalItem("three", b"later", "2026-09-22T00:00:00.000Z"),
        ]
        checks = 0
        def cancelled():
            nonlocal checks
            checks += 1
            return checks > 2

        session = self.importer.import_items("MARKDOWN_FOLDER", items, cancelled=cancelled)
        self.assertTrue(session.cancelled)
        self.assertEqual(session.committed_count, 1)
        self.assertEqual(session.blocked_count, 1)
        receipt_text = "\n".join(path.read_text() for path in (self.locator.resolve_active_vault().root_ref / "system" / "import-receipts").glob("*.json"))
        self.assertNotIn("OPENSSH", receipt_text)

    def test_markdown_adapter_skips_symlink_and_hidden_paths(self):
        root = Path(self.temp.name) / "markdown"
        root.mkdir()
        (root / "keep.md").write_text("keep")
        (root / ".hidden.md").write_text("hidden")
        outside = Path(self.temp.name) / "outside.md"
        outside.write_text("outside")
        (root / "escape.md").symlink_to(outside)
        items = list(MarkdownFolderAdapter(root).enumerate())
        self.assertEqual([item.external_item_key for item in items], ["keep.md"])

    def test_apple_notes_boundary_only_reads_permissioned_selection(self):
        calls = []
        adapter = AppleNotesAdapter(lambda: calls.append("read") or [self.item(b"note")])
        self.assertEqual([item.content for item in adapter.enumerate()], [b"note"])
        self.assertEqual(calls, ["read"])

    def test_recent_selection_and_attachment_skip_are_recorded_without_body(self):
        session = self.importer.import_items("MARKDOWN_FOLDER", [
            HistoricalItem("old", b"old", "2026-09-20T00:00:00.000Z"),
            HistoricalItem("new", b"new", "2026-09-22T00:00:00.000Z"),
            HistoricalItem("attachment", None, "2026-09-23T00:00:00.000Z", skip_reason="SKIPPED_ATTACHMENT"),
        ], recent_n=2)
        self.assertEqual(session.committed_count, 1)
        self.assertEqual(session.skipped_items[0]["reason"], "SKIPPED_ATTACHMENT")
        coverage = (self.locator.resolve_active_vault().root_ref / "system" / "history-coverage" / f"{session.import_session_id}.json").read_text()
        self.assertIn("SKIPPED_ATTACHMENT", coverage)
        self.assertNotIn("attachment", coverage)


if __name__ == "__main__":
    unittest.main()
