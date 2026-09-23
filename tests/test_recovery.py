import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tsuzu.capture import CaptureRequest, CaptureService
from tsuzu.deletion import DeletionRequest, DeletionResolver
from tsuzu.index import IndexManager
from tsuzu.recovery import RecoveryCoordinator
from tsuzu.vault import ActiveVaultLocator
from tsuzu.worker import SingleWriterWorker, WorkerStatus
from tsuzu.writer import AtomicSourceWriter, maintenance_lock


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

    def test_paired_device_keys_are_included_in_backup_and_restore(self):
        system = self.locator.resolve_active_vault().root_ref / "system"
        registry = system / "paired-device-keys" / "registry.json"
        registry.parent.mkdir(parents=True)
        registry.write_text('{"keys":{"ed25519:test":{"public_key_pem":"public-only","revoked_at":null}},"schema_version":"1.0.0"}\n')
        event_receipt = system / "ios-share-event-receipts" / "11111111-1111-4111-8111-111111111111.json"
        event_receipt.parent.mkdir()
        event_receipt.write_text('{"envelope_sha256":"abc","mobile_capture_id":"11111111-1111-4111-8111-111111111111"}\n')
        backup = self.recovery.create_backup(backup_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc")
        self.assertEqual(backup.status, "COMMITTED")
        self.assertTrue((backup.path / "protected/system/paired-device-keys/registry.json").is_file())
        self.assertTrue((backup.path / "protected/system/ios-share-event-receipts/11111111-1111-4111-8111-111111111111.json").is_file())

        self.index.close()
        restored = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored-paired")

        self.assertEqual(restored.status, "RESTORED")
        active_registry = self.locator.resolve_active_vault().root_ref / "system" / "paired-device-keys" / "registry.json"
        self.assertEqual(active_registry.read_text(), registry.read_text())
        active_event_receipt = self.locator.resolve_active_vault().root_ref / "system" / "ios-share-event-receipts" / event_receipt.name
        self.assertEqual(active_event_receipt.read_text(), event_receipt.read_text())
        rebuilt = IndexManager(self.index_root, self.locator)
        rebuilt.open()
        rebuilt.close()

    def test_interrupted_backup_has_no_restorable_snapshot(self):
        fail_once = {"pending": True}

        def interrupt(stage):
            if stage == "before_committed_marker" and fail_once.pop("pending", False):
                raise RuntimeError("stop")

        interrupted = RecoveryCoordinator(
            self.locator,
            Path(self.temp.name) / "backups",
            failure_injector=interrupt,
        )

        result = interrupted.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")

        self.assertEqual(result.status, "BACKUP_FAILED")
        snapshot = Path(self.temp.name) / "backups" / "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        self.assertTrue(snapshot.exists())
        self.assertFalse((snapshot / "COMMITTED").exists())
        self.assertEqual(interrupted.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb").status, "COMMITTED")

    def test_corrupt_backup_payload_is_rejected_before_cutover(self):
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        payload = backup.path / "protected/canonical/sources" / self.source_id / "payload/original"
        payload.write_bytes(b"corrupt")

        result = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(result.status, "BACKUP_INTEGRITY_FAILED")
        self.assertEqual(self.locator.resolve_active_vault().root_ref, (Path(self.temp.name) / "vault").resolve())

    def test_restore_failure_before_cutover_leaves_active_vault_unchanged(self):
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        before = self.locator.resolve_active_vault()
        self.recovery.failure_injector = lambda stage: (_ for _ in ()).throw(RuntimeError("stop")) if stage == "before_cutover" else None

        result = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(result.status, "RESTORE_FAILED")
        self.assertEqual(self.locator.resolve_active_vault().vault_id, before.vault_id)

    def test_n_minus_one_generic_schema_migrates_only_in_candidate(self):
        object_id = self._add_source_version("0.9.0")
        source_manifest = Path(self.temp.name) / "vault/canonical/sources" / self.source_id / "source.md"
        source = self._manifest(source_manifest)
        source["schema_version"] = "0.9.0"
        source_manifest.write_text(self._document(source))
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        self.index.close()

        result = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(result.status, "RESTORED")
        restored = self.locator.resolve_active_vault().root_ref / "canonical/objects/SOURCE_VERSION" / object_id / "object.md"
        self.assertEqual(self._manifest(restored)["schema_version"], "1.0.0")
        self.assertEqual(self._manifest(backup.path / "protected/canonical/objects/SOURCE_VERSION" / object_id / "object.md")["schema_version"], "0.9.0")
        self.assertEqual(self._manifest(self.locator.resolve_active_vault().root_ref / "canonical/sources" / self.source_id / "source.md")["schema_version"], "1.0.0")

    def test_newer_schema_is_rejected_without_cutover(self):
        object_id = self._add_source_version("1.0.0")
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        manifest_path = backup.path / "protected/canonical/objects/SOURCE_VERSION" / object_id / "object.md"
        manifest = self._manifest(manifest_path)
        manifest["schema_version"] = "2.0.0"
        self._rewrite_backup_file(backup.path, manifest_path, self._document(manifest))

        result = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(result.status, "RESTORE_REQUIRES_NEWER_APP")
        self.assertEqual(self.locator.resolve_active_vault().root_ref, (Path(self.temp.name) / "vault").resolve())

    def test_restore_does_not_start_when_pre_restore_backup_fails(self):
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        blocked = RecoveryCoordinator(
            self.locator,
            Path(self.temp.name) / "backups",
            index_root=self.index_root,
            failure_injector=lambda stage: (_ for _ in ()).throw(RuntimeError("stop")) if stage == "before_commit" else None,
        )

        result = blocked.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(result.status, "PRE_RESTORE_BACKUP_FAILED")
        self.assertEqual(self.locator.resolve_active_vault().root_ref, (Path(self.temp.name) / "vault").resolve())

    def test_migration_failure_rolls_back_before_cutover(self):
        self._add_source_version("0.9.0")
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        self.recovery.failure_injector = lambda stage: (_ for _ in ()).throw(RuntimeError("stop")) if stage == "during_migration" else None

        result = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(result.status, "RESTORE_FAILED")
        self.assertEqual(self.locator.resolve_active_vault().root_ref, (Path(self.temp.name) / "vault").resolve())

    def test_restore_discards_derived_sqlite_and_rebuilds_from_canonical(self):
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        self.assertFalse(list(backup.path.rglob("*.sqlite")))
        self.index.close()

        result = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(result.status, "RESTORED")
        rebuilt = IndexManager(self.index_root, self.locator)
        rebuilt.open()
        self.assertEqual(rebuilt.search("recoverable"), [self.source_id])
        rebuilt.close()

    def test_missing_current_ledger_fails_normal_restore_closed(self):
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        shutil.rmtree(Path(self.temp.name) / "vault/system/deletion-ledger")

        result = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(result.status, "DELETION_LEDGER_UNAVAILABLE")

    def test_unknown_persistent_object_type_blocks_backup(self):
        unknown = Path(self.temp.name) / "vault/canonical/objects/UNKNOWN"
        unknown.mkdir(parents=True)

        result = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")

        self.assertEqual(result.status, "BACKUP_CLASS_UNKNOWN")

    def test_unknown_system_state_blocks_backup_instead_of_silent_omission(self):
        (Path(self.temp.name) / "vault/system/unknown-state").mkdir()

        result = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")

        self.assertEqual(result.status, "BACKUP_CLASS_UNKNOWN")

    def test_backup_destination_cannot_be_index_or_control_state(self):
        for root in (self.index_root, Path(self.temp.name) / "control/backups"):
            blocked = RecoveryCoordinator(self.locator, root, index_root=self.index_root)
            self.assertEqual(
                blocked.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb").status,
                "BACKUP_DESTINATION_RECURSIVE",
            )

    def test_restore_candidate_cannot_be_nested_in_live_vault(self):
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")

        result = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "vault/restored")

        self.assertEqual(result.status, "CANDIDATE_INVALID")
        self.assertEqual(self.locator.resolve_active_vault().root_ref, (Path(self.temp.name) / "vault").resolve())

    def test_protected_system_receipts_survive_restore_without_body_in_manifest(self):
        receipt = Path(self.temp.name) / "vault/system/import-receipts/proof.json"
        receipt.parent.mkdir()
        receipt.write_text('{"snapshot_hash":"abc"}')
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        self.assertEqual(backup.status, "COMMITTED", backup.reason)
        self.index.close()

        result = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(result.status, "RESTORED")
        self.assertTrue((self.locator.resolve_active_vault().root_ref / "system/import-receipts/proof.json").is_file())
        self.assertNotIn("snapshot_hash", (backup.path / "backup.md").read_text())

    def test_cutover_health_failure_rolls_locator_back(self):
        backup = self.recovery.create_backup(backup_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        before = self.locator.resolve_active_vault()
        self.index.close()
        self.recovery.failure_injector = lambda stage: (_ for _ in ()).throw(RuntimeError("stop")) if stage == "after_cutover" else None

        result = self.recovery.restore(backup.backup_id, Path(self.temp.name) / "restored")

        self.assertEqual(result.status, "RESTORE_FAILED")
        self.assertEqual(self.locator.resolve_active_vault().vault_id, before.vault_id)

    def test_capture_is_queued_while_maintenance_blocks_commit(self):
        queue = Path(self.temp.name) / "queue"
        accepted = CaptureService(queue).capture(CaptureRequest(
            request_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            idempotency_key="queued-during-recovery",
            kind="TEXT",
            content=b"queued during recovery",
        ))
        self.assertEqual(accepted.status, "ACCEPTED")
        with maintenance_lock(self.locator):
            paused = SingleWriterWorker(queue, self.locator).run_once()
            self.assertEqual(paused.status, WorkerStatus.RETRY_WAIT)
        committed = SingleWriterWorker(queue, self.locator).run_once()
        self.assertEqual(committed.status, WorkerStatus.COMMITTED)

    def _add_source_version(self, schema_version):
        object_id = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
        path = Path(self.temp.name) / "vault/canonical/objects/SOURCE_VERSION" / object_id
        (path / "payload").mkdir(parents=True)
        payload = b"version payload"
        (path / "payload/original").write_bytes(payload)
        manifest = {
            "object_id": object_id,
            "object_type": "SOURCE_VERSION",
            "schema_version": schema_version,
            "created_at": "2026-09-23T00:00:00.000Z",
            "updated_at": "2026-09-23T00:00:00.000Z",
            "revision": 1,
            "scope": {"scope_type": "GLOBAL", "scope_id": None},
            "provenance": {"origin": "SYSTEM_OBSERVED", "source_refs": [], "actor": "SYSTEM", "explicitness": "OBSERVED"},
            "trust": {"level": "OBSERVED", "confidence": 1.0},
            "sensitivity": {"level": "PERSONAL"},
            "temporal": {"valid_from": None, "valid_until": None},
            "deletion": {"state": "LIVE", "tombstoned_at": None},
            "payload": {"path": "payload/original", "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)},
        }
        (path / "object.md").write_text(self._document(manifest))
        return object_id

    @staticmethod
    def _document(value):
        return "---\n" + json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n---\n"

    @staticmethod
    def _manifest(path):
        text = path.read_text()
        return json.loads(text[4:text.find("\n---\n", 4)])

    def _rewrite_backup_file(self, backup, path, text):
        path.write_text(text)
        manifest_path = backup / "backup.md"
        manifest = self._manifest(manifest_path)
        relative = str(path.relative_to(backup / "protected"))
        for entry in manifest["content_manifest"]["entries"]:
            if entry["relative_path"] == relative:
                entry["byte_length"] = path.stat().st_size
                entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        entries = manifest["content_manifest"]["entries"]
        manifest["content_manifest"]["manifest_hash"] = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        manifest_path.write_text(self._document(manifest))


if __name__ == "__main__":
    unittest.main()
