import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tsuzu.canonical import (
    CanonicalStore,
    CreateCanonicalIntent,
    ObjectRegistration,
    ObjectRegistry,
    UpdateCanonicalIntent,
)
from tsuzu.vault import ActiveVaultLocator, StaleGenerationError


def envelope():
    return {
        "scope": {"scope_type": "GLOBAL", "scope_id": None},
        "provenance": {"origin": "USER_EXPLICIT", "source_refs": [], "actor": "USER", "explicitness": "EXPLICIT"},
        "trust": {"level": "ASSERTED", "confidence": 1.0},
        "sensitivity": {"level": "PERSONAL"},
        "temporal": {"valid_from": None, "valid_until": None},
        "deletion": {"state": "LIVE", "tombstoned_at": None},
    }


class CanonicalStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "vault"
        root.mkdir()
        self.locator = ActiveVaultLocator(Path(self.temp.name) / "control")
        self.locator.initialize(root, operation_id="init")
        self.registry = ObjectRegistry()
        self.registry.register(
            ObjectRegistration(
                object_type="CONVERSATION_MESSAGE",
                storage_class="CANONICAL",
                mutability="REVISIONED",
                body_mode="PAYLOAD",
                schema_owner="B1",
                mutable_fields=frozenset({"sensitivity", "deletion"}),
            )
        )
        self.registry.register(
            ObjectRegistration(
                object_type="CORRECTION_EVENT",
                storage_class="CANONICAL",
                mutability="IMMUTABLE",
                body_mode="NONE",
                schema_owner="B5",
            )
        )
        self.store = CanonicalStore(self.locator, self.registry)

    def tearDown(self):
        self.temp.cleanup()

    def intent(self, source_id="11111111-1111-4111-8111-111111111111", key="event-1", payload=b"message"):
        return CreateCanonicalIntent(
            object_type="CONVERSATION_MESSAGE",
            object_id=source_id,
            schema_version="1.0.0",
            created_at="2026-09-12T00:00:00.000Z",
            idempotency_key=key,
            manifest_fields={**envelope(), "role": "user"},
            payload=payload,
        )

    def test_unknown_registration_and_source_specialization_fail_closed(self):
        unknown = self.intent()
        unknown = CreateCanonicalIntent("UNKNOWN", unknown.object_id, "1.0.0", unknown.created_at, "k", unknown.manifest_fields)
        self.assertEqual(self.store.create_canonical(unknown).status, "UNKNOWN_OBJECT_TYPE")
        self.assertEqual(self.store.create_canonical(CreateCanonicalIntent("SOURCE", unknown.object_id, "1.0.0", unknown.created_at, "k", unknown.manifest_fields)).status, "SPECIALIZED_WRITER_REQUIRED")

    def test_generic_create_payload_and_body_free_receipt(self):
        intent = self.intent()
        result = self.store.create_canonical(intent)
        self.assertEqual(result.status, "COMMITTED_LOCAL")
        self.assertEqual(self.store.inspect_canonical(intent.object_type, intent.object_id).status, "VALID")
        path = result.path
        self.assertEqual((path / "payload/original").read_bytes(), b"message")
        receipt = (self.locator.resolve_active_vault().root_ref / "system/c1-receipts.jsonl").read_text()
        self.assertNotIn("message", receipt)
        self.assertIn(hashlib.sha256(b"message").hexdigest(), receipt)

    def test_same_retry_is_idempotent_and_conflicting_replay_fails(self):
        first = self.store.create_canonical(self.intent())
        retry = self.store.create_canonical(self.intent())
        self.assertEqual(first.status, "COMMITTED_LOCAL")
        self.assertEqual(retry.status, "ALREADY_COMMITTED")
        conflict = self.store.create_canonical(self.intent(payload=b"different"))
        self.assertEqual(conflict.status, "IDEMPOTENCY_CONFLICT")

    def test_same_body_new_object_id_is_distinct(self):
        first = self.store.create_canonical(self.intent())
        second = self.store.create_canonical(self.intent(source_id="22222222-2222-4222-8222-222222222222", key="event-2"))
        self.assertNotEqual(first.path, second.path)

    def test_revision_update_and_immutable_fields(self):
        intent = self.intent()
        self.store.create_canonical(intent)
        conflict = self.store.update_canonical(UpdateCanonicalIntent(intent.object_type, intent.object_id, 2, "update-1", {"sensitivity": {"level": "SENSITIVE"}}))
        self.assertEqual(conflict.status, "REVISION_CONFLICT")
        updated = self.store.update_canonical(UpdateCanonicalIntent(intent.object_type, intent.object_id, 1, "update-1", {"sensitivity": {"level": "SENSITIVE"}}))
        self.assertEqual(updated.status, "COMMITTED_LOCAL")
        immutable = self.store.update_canonical(UpdateCanonicalIntent(intent.object_type, intent.object_id, 2, "update-2", {"object_id": "x"}))
        self.assertEqual(immutable.status, "VALIDATION_FAILED")

    def test_tombstoned_object_cannot_be_resurrected(self):
        intent = self.intent()
        self.store.create_canonical(intent)
        deleted = self.store.update_canonical(UpdateCanonicalIntent(intent.object_type, intent.object_id, 1, "delete-1", {"deletion": {"state": "TOMBSTONED", "tombstoned_at": "2026-09-12T00:01:00.000Z"}}))
        self.assertEqual(deleted.status, "COMMITTED_LOCAL")
        resurrect = self.store.update_canonical(UpdateCanonicalIntent(intent.object_type, intent.object_id, 2, "resurrect", {"deletion": {"state": "LIVE", "tombstoned_at": None}}))
        self.assertEqual(resurrect.status, "VALIDATION_FAILED")

    def test_immutable_event_can_be_created_but_not_updated(self):
        event = CreateCanonicalIntent("CORRECTION_EVENT", "33333333-3333-4333-8333-333333333333", "1.0.0", "2026-09-12T00:00:00.000Z", "correction-1", envelope())
        self.assertEqual(self.store.append_canonical_event(event).status, "COMMITTED_LOCAL")
        update = self.store.update_canonical(UpdateCanonicalIntent(event.object_type, event.object_id, 1, "u", {"sensitivity": {"level": "SENSITIVE"}}))
        self.assertEqual(update.status, "VALIDATION_FAILED")

    def test_restricted_and_stale_generation_are_rejected(self):
        restricted = self.intent()
        restricted = CreateCanonicalIntent(restricted.object_type, restricted.object_id, restricted.schema_version, restricted.created_at, restricted.idempotency_key, {**restricted.manifest_fields, "sensitivity": {"level": "RESTRICTED"}}, restricted.payload)
        self.assertEqual(self.store.create_canonical(restricted).status, "VALIDATION_FAILED")
        with mock.patch.object(self.locator, "assert_current", side_effect=StaleGenerationError("stale")):
            result = self.store.create_canonical(self.intent(source_id="44444444-4444-4444-8444-444444444444", key="stale"))
        self.assertEqual(result.status, "STALE_GENERATION")


if __name__ == "__main__":
    unittest.main()
