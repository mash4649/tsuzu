import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tsuzu.vault import ActiveVaultLocator
from tsuzu.writer import AtomicSourceWriter, WriterError


class AtomicSourceWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "vault"
        root.mkdir()
        self.locator = ActiveVaultLocator(Path(self.temp.name) / "control")
        self.locator.initialize(root, operation_id="init")
        self.writer = AtomicSourceWriter(self.locator)

    def tearDown(self):
        self.temp.cleanup()

    def test_create_publishes_one_complete_directory_and_inspects(self):
        result = self.writer.create_source(
            b"hello", kind="TEXT", capture_method="LOCAL_TEXT", object_id="11111111-1111-4111-8111-111111111111"
        )
        self.assertEqual(result.status, "COMMITTED_LOCAL")
        source_dir = result.path
        self.assertEqual((source_dir / "payload" / "original").read_bytes(), b"hello")
        self.assertEqual(self.writer.inspect_source(result.source_id).status, "VALID")
        self.assertFalse(list((source_dir.parent.parent / "system" / "staging").glob("*")))

    def test_create_retry_is_idempotent_and_collision_does_not_overwrite(self):
        source_id = "22222222-2222-4222-8222-222222222222"
        first = self.writer.create_source(b"same", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id, created_at="2026-09-12T00:00:00.000Z")
        retry = self.writer.create_source(b"same", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id, created_at="2026-09-12T00:00:00.000Z")
        self.assertEqual(retry.status, "ALREADY_COMMITTED")
        collision = self.writer.create_source(b"different", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id, created_at="2026-09-12T00:00:00.000Z")
        self.assertEqual(collision.status, "OBJECT_ID_COLLISION")
        self.assertEqual(first.path.joinpath("payload/original").read_bytes(), b"same")

    def test_metadata_update_requires_revision_and_preserves_payload(self):
        source_id = "33333333-3333-4333-8333-333333333333"
        created = self.writer.create_source(b"immutable", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id)
        conflict = self.writer.update_source_metadata(source_id, expected_revision=2, patch={"sensitivity": "SENSITIVE"})
        self.assertEqual(conflict.status, "REVISION_CONFLICT")
        updated = self.writer.update_source_metadata(source_id, expected_revision=1, patch={"sensitivity": "SENSITIVE"})
        self.assertEqual(updated.status, "COMMITTED_LOCAL")
        self.assertEqual(updated.revision, 2)
        self.assertEqual((created.path / "payload/original").read_bytes(), b"immutable")
        with self.assertRaises(WriterError):
            self.writer.update_source_metadata(source_id, expected_revision=2, patch={"payload": b"changed"})

    def test_restricted_source_is_rejected_before_publish(self):
        result = self.writer.create_source(b"secret", kind="TEXT", capture_method="LOCAL_TEXT", object_id="44444444-4444-4444-8444-444444444444", sensitivity="RESTRICTED")
        self.assertEqual(result.status, "VALIDATION_FAILED")
        self.assertFalse((self.writer._canonical_root() / "sources" / result.source_id).exists())

    def test_publish_failure_leaves_no_canonical_object(self):
        def fail(stage):
            if stage == "before_publish":
                raise OSError("injected")

        writer = AtomicSourceWriter(self.locator, failure_injector=fail)
        source_id = "55555555-5555-4555-8555-555555555555"
        result = writer.create_source(b"not published", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id)
        self.assertEqual(result.status, "IO_FAILED")
        self.assertFalse((writer._canonical_root() / "sources" / source_id).exists())
        self.assertFalse(list((writer._system_root() / "staging").glob("*")))

    def test_layout_symlink_is_rejected(self):
        canonical = self.writer._canonical_root()
        canonical.mkdir()
        (canonical / "sources").symlink_to(Path(self.temp.name))
        result = self.writer.create_source(b"escape", kind="TEXT", capture_method="LOCAL_TEXT")
        self.assertEqual(result.status, "FILESYSTEM_UNSUPPORTED")

    def test_recovery_never_promotes_or_repairs_staging(self):
        staging = self.writer._system_root() / "staging" / "tx-incomplete" / "create"
        staging.mkdir(parents=True)
        (staging / "source.md").write_text("incomplete")
        report = self.writer.recover_staging()
        self.assertEqual(report.removed, 1)
        self.assertFalse((staging.parent.parent / "tx-incomplete").exists())

    def test_tampered_payload_blocks_metadata_update(self):
        source_id = "66666666-6666-4666-8666-666666666666"
        result = self.writer.create_source(b"original", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id)
        (result.path / "payload/original").write_bytes(b"tampered")
        inspected = self.writer.inspect_source(source_id)
        self.assertEqual(inspected.status, "CORRUPT")
        blocked = self.writer.update_source_metadata(source_id, expected_revision=1, patch={"sensitivity": "SENSITIVE"})
        self.assertEqual(blocked.status, "CANONICAL_CORRUPT")

    def test_failure_after_publish_is_uncertain_but_retry_reconciles(self):
        source_id = "77777777-7777-4777-8777-777777777777"
        created_at = "2026-09-12T00:00:00.000Z"

        def fail(stage):
            if stage == "after_publish":
                raise OSError("injected")

        writer = AtomicSourceWriter(self.locator, failure_injector=fail)
        uncertain = writer.create_source(b"once", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id, created_at=created_at)
        self.assertEqual(uncertain.status, "COMMIT_UNCERTAIN")
        retry = self.writer.create_source(b"once", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id, created_at=created_at)
        self.assertEqual(retry.status, "ALREADY_COMMITTED")

    def test_failure_after_metadata_replace_is_uncertain(self):
        source_id = "88888888-8888-4888-8888-888888888888"
        self.writer.create_source(b"update", kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id)

        def fail(stage):
            if stage == "after_replace":
                raise OSError("injected")

        writer = AtomicSourceWriter(self.locator, failure_injector=fail)
        result = writer.update_source_metadata(source_id, expected_revision=1, patch={"sensitivity": "SENSITIVE"})
        self.assertEqual(result.status, "COMMIT_UNCERTAIN")

    def test_writer_lock_is_bounded(self):
        with mock.patch.object(self.writer, "_locked", side_effect=WriterError("WRITER_BUSY", "busy")):
            result = self.writer.create_source(b"busy", kind="TEXT", capture_method="LOCAL_TEXT")
            self.assertEqual(result.status, "WRITER_BUSY")


if __name__ == "__main__":
    unittest.main()
