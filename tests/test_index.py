import json
import tempfile
import unittest
from pathlib import Path

from tsuzu.index import IndexCapabilityError, IndexManager, probe_sqlite
from tsuzu.vault import ActiveVaultLocator
from tsuzu.writer import AtomicSourceWriter


class IndexManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "vault"
        root.mkdir()
        self.locator = ActiveVaultLocator(Path(self.temp.name) / "control")
        self.locator.initialize(root, operation_id="init")
        self.writer = AtomicSourceWriter(self.locator)
        self.manager = IndexManager(Path(self.temp.name) / "index", self.locator)
        self.manager.open()

    def tearDown(self):
        self.manager.close()
        self.temp.cleanup()

    def test_capability_probe_and_japanese_text_search(self):
        probe_sqlite()
        source_id = "11111111-1111-4111-8111-111111111111"
        self.writer.create_source("面接設定率を優先して判断する", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id)
        self.assertEqual(self.manager.upsert_source(source_id), "INDEXED")
        self.assertEqual(self.manager.search("面接設定率"), [source_id])
        self.assertEqual(self.manager.health().status, "HEALTHY")

    def test_url_and_duplicate_sources_are_not_fetched_or_merged(self):
        first = "22222222-2222-4222-8222-222222222222"
        second = "33333333-3333-4333-8333-333333333333"
        for source_id in (first, second):
            self.writer.create_source(b"https://example.com/article", kind="URL", capture_method="LOCAL_URL", object_id=source_id)
            self.manager.upsert_source(source_id)
        self.assertEqual(self.manager.connection.execute("SELECT count(*) FROM source_index").fetchone()[0], 2)
        self.assertEqual(set(self.manager.search("example.com")), {first, second})

    def test_binary_file_is_metadata_only(self):
        source_id = "44444444-4444-4444-8444-444444444444"
        self.writer.create_source(b"\x00\x01\xff", kind="FILE", capture_method="LOCAL_FILE", object_id=source_id, original_name="photo.bin")
        self.manager.upsert_source(source_id)
        row = self.manager.connection.execute("SELECT projection_mode, projection_reason FROM source_index WHERE source_id=?", (source_id,)).fetchone()
        self.assertEqual(row, ("METADATA_ONLY", "UNSUPPORTED_BODY_PROJECTION"))
        self.assertEqual(self.manager.search("photo.bin"), [source_id])

    def test_tombstone_corrupt_and_secret_are_excluded(self):
        tombstone = "55555555-5555-4555-8555-555555555555"
        corrupt = "66666666-6666-4666-8666-666666666666"
        secret = "77777777-7777-4777-8777-777777777777"
        self.writer.create_source(b"live", kind="TEXT", capture_method="LOCAL_TEXT", object_id=tombstone)
        self.manager.upsert_source(tombstone)
        self.writer.update_source_metadata(tombstone, expected_revision=1, patch={"deletion": {"state": "TOMBSTONED", "tombstoned_at": "2026-09-12T00:01:00.000Z"}})
        self.assertEqual(self.manager.upsert_source(tombstone), "EXCLUDED")
        self.writer.create_source(b"good", kind="TEXT", capture_method="LOCAL_TEXT", object_id=corrupt)
        (self.writer.inspect_source(corrupt).path / "payload/original").write_bytes(b"bad")
        self.assertEqual(self.manager.upsert_source(corrupt), "EXCLUDED")
        self.writer.create_source(b"normal", kind="TEXT", capture_method="LOCAL_TEXT", object_id=secret)
        blocked = IndexManager(Path(self.temp.name) / "index-secret", self.locator, scanner=BlockScanner())
        blocked.open()
        self.assertEqual(blocked.upsert_source(secret), "EXCLUDED")
        blocked.close()

    def test_tombstone_stays_excluded_after_full_rebuild(self):
        source_id = "99999999-9999-4999-8999-999999999999"
        self.writer.create_source(b"forget me", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id)
        self.manager.upsert_source(source_id)
        self.writer.update_source_metadata(
            source_id,
            expected_revision=1,
            patch={"deletion": {"state": "TOMBSTONED", "tombstoned_at": "2026-09-12T00:01:00.000Z"}},
        )
        self.manager.full_rebuild()
        self.assertEqual(self.manager.search("forget"), [])
        self.assertEqual(
            self.manager.connection.execute(
                "SELECT reason_code FROM index_exclusion WHERE source_id=?", (source_id,)
            ).fetchone()[0],
            "TOMBSTONED",
        )

    def test_reconcile_and_full_rebuild_restore_deleted_database(self):
        source_id = "88888888-8888-4888-8888-888888888888"
        self.writer.create_source(b"rebuildable", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id)
        self.assertEqual(self.manager.reconcile()["indexed"], 1)
        self.manager.close()
        self.manager.path.unlink()
        self.manager.open()
        self.manager.full_rebuild()
        self.assertEqual(self.manager.search("rebuildable"), [source_id])

    def test_unsupported_schema_is_rejected_without_silent_migration(self):
        self.manager.close()
        import sqlite3

        connection = sqlite3.connect(Path(self.temp.name) / "index" / "tsuzu.sqlite")
        connection.execute("PRAGMA user_version=99")
        connection.commit()
        connection.close()
        with self.assertRaises(IndexCapabilityError):
            self.manager.open()


class BlockScanner:
    RULESET_VERSION = "test"

    def scan_bytes(self, payload):
        from tsuzu.capture import SecretScanResult

        return SecretScanResult("BLOCKED_RESTRICTED", "test", ("TEST",), len(payload), "0" * 64)


if __name__ == "__main__":
    unittest.main()
