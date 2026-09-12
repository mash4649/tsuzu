import json
import tempfile
import unittest
from pathlib import Path

from tsuzu.canonical import CanonicalStore, CreateCanonicalIntent, ObjectRegistration, ObjectRegistry, UpdateCanonicalIntent
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

    def test_purge_failure_cannot_reverse_deletion_truth(self):
        self.assertEqual(self.resolver.delete_source(DeletionRequest.source(self.source_id, expected_revision=1)).status, "DELETED")
        payload = self.writer.inspect_source(self.source_id).path / "payload/original"
        payload.unlink()
        payload.symlink_to("missing")
        result = self.resolver.purge_source_payload(self.source_id)
        self.assertEqual(result.status, "PURGE_FAILED")
        self.assertEqual(self.resolver.resolve_source(self.source_id).state, DELETED)

    def test_generic_ledger_blocks_c1_update_without_resurrecting_object(self):
        object_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        registry = ObjectRegistry()
        registry.register(
            ObjectRegistration(
                object_type="EVIDENCE",
                storage_class="CANONICAL",
                mutability="REVISIONED",
                body_mode="NONE",
                schema_owner="B4",
                mutable_fields=frozenset({"sensitivity"}),
            )
        )
        store = CanonicalStore(self.locator, registry)
        fields = {
            "scope": {"scope_type": "GLOBAL", "scope_id": None},
            "provenance": {"origin": "USER_EXPLICIT", "source_refs": [], "actor": "USER", "explicitness": "EXPLICIT"},
            "trust": {"level": "ASSERTED", "confidence": 1.0},
            "sensitivity": {"level": "PERSONAL"},
            "temporal": {"valid_from": None, "valid_until": None},
            "deletion": {"state": "LIVE", "tombstoned_at": None},
        }
        created = store.create_canonical(CreateCanonicalIntent("EVIDENCE", object_id, "1.0.0", "2026-09-12T00:00:00.000Z", "create-evidence", fields))
        self.assertEqual(created.status, "COMMITTED_LOCAL")
        deleted = self.resolver.delete(DeletionRequest("EVIDENCE", object_id, 1, "cccccccc-cccc-4ccc-8ccc-cccccccccccc", "delete-evidence", "2026-09-12T00:01:00.000Z"))
        self.assertEqual(deleted.status, "DELETED")
        self.assertEqual(self.resolver.resolve("EVIDENCE", object_id).state, DELETED)
        update = store.update_canonical(UpdateCanonicalIntent("EVIDENCE", object_id, 1, "update-evidence", {"sensitivity": {"level": "SENSITIVE"}}))
        self.assertEqual(update.status, "DELETED")


if __name__ == "__main__":
    unittest.main()
