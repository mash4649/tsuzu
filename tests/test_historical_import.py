import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tsuzu.historical_import import AppleNotesAdapter, HistoricalItem, HistoricalImporter, MacOSAppleNotesBridge, MarkdownFolderAdapter
from tsuzu.capture import CaptureRequest, CaptureService
from tsuzu.index import IndexManager
from tsuzu.worker import SingleWriterWorker, WorkerStatus
from tsuzu.vault import ActiveVaultLocator
from tsuzu.writer import AtomicSourceWriter
from tsuzu.__main__ import build_parser


class HistoricalImporterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        vault = Path(self.temp.name) / "vault"
        vault.mkdir()
        self.locator = ActiveVaultLocator(Path(self.temp.name) / "control")
        self.locator.initialize(vault, operation_id="init")
        self.queue = Path(self.temp.name) / "queue"
        self.index = IndexManager(Path(self.temp.name) / "index", self.locator)
        self.index.open()
        self.importer = HistoricalImporter(self.queue, self.locator, self.index)

    def tearDown(self):
        self.index.close()
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

    def test_apple_notes_selected_note_maps_through_a3_a4(self):
        calls = []
        bridge = MacOSAppleNotesBridge(lambda: calls.append("read") or json.dumps({
            "id": "note-id", "title": "Selected note", "body": "note", "created_at": "2026-09-21T00:00:00.000Z",
            "modified_at": "2026-09-22T00:00:00.000Z",
        }))
        adapter = AppleNotesAdapter(bridge)
        item = next(iter(adapter.enumerate()))
        self.assertEqual(calls, ["read"])
        self.assertEqual(item.original_name, "Selected note")
        self.assertEqual(item.source_url, "x-apple-notes://selected/" + hashlib.sha256(b"note-id").hexdigest())
        session = self.importer.import_items("APPLE_NOTES", [item])
        self.assertEqual(session.committed_count, 1)
        path = AtomicSourceWriter(self.locator).inspect_source(session.source_ids[0]).path / "source.md"
        manifest = json.loads(path.read_text().split("---\n", 2)[1])
        self.assertEqual(manifest["source"]["origin_locator"], {"type": "APPLE_NOTES", "value": item.source_url})
        self.assertEqual(manifest["source"]["original_name"], "Selected note")
        self.assertEqual(manifest["import"]["external_modified_at_observed"], "2026-09-22T00:00:00.000Z")
        self.assertIn(session.source_ids[0], self.index.search("Selected note"))
        self.assertEqual(self.importer.import_items("APPLE_NOTES", [item]).already_imported_count, 1)

    def test_index_failure_is_reported_and_duplicate_retry_repairs_projection(self):
        upsert = self.index.upsert_source
        self.index.upsert_source = lambda source_id: (_ for _ in ()).throw(OSError("index unavailable"))
        first = self.importer.import_items("APPLE_NOTES", [self.item(b"index repair")])
        self.assertEqual((first.committed_count, first.failed_count), (0, 1))
        self.assertEqual(self.index.search("index repair"), [])
        self.index.upsert_source = upsert
        retry = self.importer.import_items("APPLE_NOTES", [self.item(b"index repair")])
        self.assertEqual((retry.committed_count, retry.already_imported_count, retry.failed_count), (0, 1, 0))
        self.assertIn(retry.source_ids[0], self.index.search("index repair"))

    def test_apple_notes_bridge_unavailable_or_malformed_result_makes_no_writes(self):
        for runner in (
            lambda: json.dumps({"id": "note-id"}),
            lambda: (_ for _ in ()).throw(subprocess.CalledProcessError(1, "osascript")),
        ):
            with self.subTest(runner=runner), self.assertRaises(ValueError):
                self.importer.import_items("APPLE_NOTES", AppleNotesAdapter(MacOSAppleNotesBridge(runner)).enumerate())
            self.assertFalse((self.queue / "pending").exists())

    def test_apple_notes_secret_fixture_is_blocked_without_body_copy(self):
        bridge = MacOSAppleNotesBridge(lambda: json.dumps({
            "id": "note-id", "title": "Secret", "body": "-----BEGIN OPENSSH PRIVATE KEY-----",
            "created_at": "2026-09-21T00:00:00.000Z", "modified_at": "2026-09-22T00:00:00.000Z",
        }))
        session = self.importer.import_items("APPLE_NOTES", AppleNotesAdapter(bridge).enumerate())
        self.assertEqual(session.blocked_count, 1)
        receipts = self.locator.resolve_active_vault().root_ref / "system" / "import-receipts"
        self.assertNotIn("OPENSSH", "\n".join(path.read_text() for path in receipts.glob("*.json")))

    def test_apple_notes_cli_requires_only_the_core_queue_and_locator(self):
        args = build_parser().parse_args(["apple-notes-import", "--queue-root", "queue", "--control-root", "control"])
        self.assertEqual(args.command, "apple-notes-import")

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
