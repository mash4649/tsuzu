import json
import tempfile
import unittest
from pathlib import Path

from tsuzu.deletion import DELETED, NOT_DELETED, UNKNOWN_FAIL_CLOSED, DeletionRequest, DeletionResolver
from tsuzu.index import IndexManager
from tsuzu.vault import ActiveVaultLocator
from tsuzu.writer import AtomicSourceWriter


class DeletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        vault = root / "vault"
        vault.mkdir()
        self.locator = ActiveVaultLocator(root / "control")
        self.locator.initialize(vault, operation_id="init")
        self.writer = AtomicSourceWriter(self.locator)
        self.resolver = DeletionResolver(self.locator, self.writer)
        self.index = IndexManager(root / "index", self.locator, deletion_resolver=self.resolver)
        self.index.open()
        self.source_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        self.writer.create_source(b"deletion target", kind="TEXT", capture_method="LOCAL_TEXT", object_id=self.source_id)
        self.index.upsert_source(self.source_id)

    def tearDown(self):
        self.index.close()
        self.temp.cleanup()

    def test_delete_commits_ledger_before_index_invalidation_and_is_idempotent(self):
        self.assertEqual(self.resolver.resolve_source(self.source_id).state, NOT_DELETED)
        result = self.resolver.delete_source(DeletionRequest.source(self.source_id, expected_revision=1), index=self.index)
        self.assertEqual(result.status, "DELETED")
        self.assertEqual(self.resolver.resolve_source(self.source_id).state, DELETED)
        self.assertEqual(self.index.search("deletion"), [])
        self.assertEqual(self.index.connection.execute("SELECT reason_code FROM index_exclusion").fetchone()[0], "DELETION_LEDGER")
        self.assertEqual(self.resolver.delete_source(DeletionRequest.source(self.source_id, expected_revision=1)).status, "ALREADY_DELETED")

    def test_ledger_wins_over_stale_live_manifest_and_reconcile_restores_tombstone(self):
        source_path = self.writer.inspect_source(self.source_id).path
        old_manifest = (source_path / "source.md").read_text()
        result = self.resolver.delete_source(DeletionRequest.source(self.source_id, expected_revision=1))
        self.assertEqual(result.status, "DELETED")
        (source_path / "source.md").write_text(old_manifest)
        self.assertEqual(self.resolver.resolve_source(self.source_id).state, DELETED)
        self.assertEqual(self.index.search("deletion"), [])
        self.assertEqual(self.resolver.reconcile_source(self.source_id).status, "COMMITTED_LOCAL")
        self.assertEqual(self.resolver.resolve_source(self.source_id).state, DELETED)

    def test_corrupt_ledger_fails_closed(self):
        ledger = self.locator.resolve_active_vault().root_ref / "system/deletion-ledger/SOURCE"
        ledger.mkdir(parents=True)
        (ledger / f"{self.source_id}.md").write_text("not a record")
        self.assertEqual(self.resolver.resolve_source(self.source_id).state, UNKNOWN_FAIL_CLOSED)
        self.assertEqual(self.index.search("deletion"), [])

    def test_revision_conflict_does_not_create_ledger(self):
        result = self.resolver.delete_source(DeletionRequest.source(self.source_id, expected_revision=2))
        self.assertEqual(result.status, "REVISION_CONFLICT")
        self.assertFalse((self.locator.resolve_active_vault().root_ref / "system/deletion-ledger").exists())


if __name__ == "__main__":
    unittest.main()
