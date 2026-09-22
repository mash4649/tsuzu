import tempfile
import unittest
from pathlib import Path

from tsuzu.deletion import DeletionRequest, DeletionResolver
from tsuzu.index import IndexManager
from tsuzu.recovery import RecoveryCoordinator
from tsuzu.vault import ActiveVaultLocator
from tsuzu.writer import AtomicSourceWriter


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        vault = root / "vault"
        vault.mkdir()
        self.locator = ActiveVaultLocator(root / "control")
        self.locator.initialize(vault, operation_id="init")
        self.writer = AtomicSourceWriter(self.locator)
        self.source_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        self.writer.create_source(b"recoverable source", kind="TEXT", capture_method="LOCAL_TEXT", object_id=self.source_id)
        self.index_root = root / "index"
        self.index = IndexManager(self.index_root, self.locator)
        self.index.open()
        self.index.upsert_source(self.source_id)
        self.recovery = RecoveryCoordinator(self.locator, root / "backups", index_root=self.index_root)

    def tearDown(self):
        self.index.close()
        self.temp.cleanup()

    def test_healthy_backup_restore_round_trip_rebuilds_index(self):
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        self.assertEqual(backup.status, "COMMITTED")
        self.assertTrue((backup.path / "COMMITTED").is_file())
        self.assertNotIn("recoverable source", (backup.path / "backup.md").read_text())

        self.index.close()
        restored = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(restored.status, "RESTORED")
        self.assertNotEqual(self.locator.resolve_active_vault().root_ref, Path(self.temp.name) / "vault")
        rebuilt = IndexManager(self.index_root, self.locator)
        rebuilt.open()
        self.assertEqual(rebuilt.search("recoverable"), [self.source_id])
        rebuilt.close()

    def test_current_tombstone_wins_over_old_backup(self):
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        self.assertEqual(DeletionResolver(self.locator).delete_source(DeletionRequest.source(self.source_id, expected_revision=1)).status, "DELETED")
        self.index.close()

        restored = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(restored.status, "RESTORED")
        self.assertEqual(DeletionResolver(self.locator).resolve_source(self.source_id).state, "DELETED")
        rebuilt = IndexManager(self.index_root, self.locator)
        rebuilt.open()
        self.assertEqual(rebuilt.search("recoverable"), [])
        rebuilt.close()


if __name__ == "__main__":
    unittest.main()
