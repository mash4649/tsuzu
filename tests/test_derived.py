import json
import tempfile
import unittest
from pathlib import Path

from tsuzu.canonical import CanonicalStore, CreateCanonicalIntent, ObjectRegistration, ObjectRegistry
from tsuzu.deletion import DeletionRequest, DeletionResolver
from tsuzu.derived import DerivedJobQueue, DerivedJobRequest, DerivedStatus
from tsuzu.vault import ActiveVaultLocator


class DerivedJobQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.queue = DerivedJobQueue(Path(self.temp.name) / "runtime")
        self.request = DerivedJobRequest(
            "EPISODE_SEGMENT",
            (("CONVERSATION_MESSAGE", "11111111-1111-4111-8111-111111111111", 1, "a" * 64),),
            "b2-v1",
            "local-only-v1",
            "GLOBAL",
            "trigger-1",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_duplicate_enqueue_converges_and_algorithm_change_creates_new_generation(self):
        first = self.queue.enqueue(self.request)
        duplicate = self.queue.enqueue(self.request)
        changed = self.queue.enqueue(DerivedJobRequest(
            self.request.job_type, self.request.input_refs, "b2-v2", self.request.policy_version, self.request.scope, "trigger-2",
        ))

        self.assertEqual(first.status, DerivedStatus.ENQUEUED)
        self.assertEqual(duplicate.status, DerivedStatus.ALREADY_ENQUEUED)
        self.assertEqual(first.job_id, duplicate.job_id)
        self.assertNotEqual(first.job_id, changed.job_id)
        self.assertNotIn("trigger-1", (self.queue.root / "jobs" / f"{first.job_id}.json").read_text())

    def test_claim_lease_recovery_and_higher_priority_invalidation(self):
        normal = self.queue.enqueue(self.request)
        invalidation = self.queue.enqueue(DerivedJobRequest(
            "DEPENDENCY_INVALIDATE", self.request.input_refs, "b7-v1", "local-only-v1", "GLOBAL", "trigger-3",
        ))

        claimed = self.queue.claim("worker-a", now="2026-09-23T00:00:00.000Z", lease_seconds=1)
        recovered = self.queue.claim("worker-b", now="2026-09-23T00:00:02.000Z", lease_seconds=10)

        self.assertEqual(claimed.job_id, invalidation.job_id)
        self.assertEqual(recovered.job_id, invalidation.job_id)
        self.assertEqual(recovered.attempt_count, 2)
        self.assertNotEqual(normal.job_id, invalidation.job_id)

    def test_invalid_input_is_rejected_before_runtime_state(self):
        result = self.queue.enqueue(DerivedJobRequest(
            "UNREGISTERED", self.request.input_refs, "b2-v1", "local-only-v1", "GLOBAL", "trigger-4",
        ))

        self.assertEqual(result.status, DerivedStatus.VALIDATION_FAILED)
        self.assertFalse((self.queue.root / "jobs").exists())

    def test_preflight_is_fail_closed_without_a_deletion_resolver(self):
        job = self.queue.enqueue(self.request)
        claim = self.queue.claim("worker-a", now="2026-09-23T00:00:00.000Z")

        result = self.queue.preflight(job.job_id, "worker-a", lambda refs: True)

        self.assertEqual(claim.job_id, job.job_id)
        self.assertEqual(result.status, DerivedStatus.BLOCKED_STALE)
        record = (self.queue.root / "jobs" / f"{job.job_id}.json").read_text()
        self.assertIn('"state":"BLOCKED_STALE"', record)
        self.assertIn('"last_failure_code":"DELETION_RESOLVER_REQUIRED"', record)

    def test_completion_and_retry_require_current_preflight(self):
        job = self.queue.enqueue(self.request)
        self.queue.claim("worker-a", now="2026-09-23T00:00:00.000Z")

        retry = self.queue.settle(job.job_id, "worker-a", "RETRY_WAIT", failure_code="TEMPORARY_ADAPTER", next_attempt_at="2026-09-23T00:01:00.000Z")
        self.assertEqual(retry.status, DerivedStatus.RETRY_WAIT)
        claimed_again = self.queue.claim("worker-b", now="2026-09-23T00:01:01.000Z")
        self.assertEqual(claimed_again.job_id, job.job_id)
        no_preflight = self.queue.settle(job.job_id, "worker-b", "SUCCEEDED", output_refs=(("DERIVED_EPISODE", "22222222-2222-4222-8222-222222222222", 1, "b" * 64),))
        self.assertEqual(no_preflight.status, DerivedStatus.BLOCKED_STALE)

    def test_c3_deletion_blocks_a_claimed_job_before_processing(self):
        vault_root = Path(self.temp.name) / "vault"
        vault_root.mkdir()
        locator = ActiveVaultLocator(Path(self.temp.name) / "control")
        locator.initialize(vault_root, operation_id="init")
        registry = ObjectRegistry()
        registry.register(ObjectRegistration("CONVERSATION_MESSAGE", "CANONICAL", "REVISIONED", "PAYLOAD", "B1"))
        store = CanonicalStore(locator, registry)
        fields = {
            "scope": {"scope_type": "GLOBAL", "scope_id": None},
            "provenance": {"origin": "SYSTEM_OBSERVED", "source_refs": [], "actor": "B1", "explicitness": "OBSERVED"},
            "trust": {"level": "OBSERVED", "confidence": 1.0},
            "sensitivity": {"level": "PERSONAL"},
            "temporal": {"valid_from": None, "valid_until": None},
            "deletion": {"state": "LIVE", "tombstoned_at": None},
        }
        object_id = self.request.input_refs[0][1]
        self.assertEqual(store.create_canonical(CreateCanonicalIntent("CONVERSATION_MESSAGE", object_id, "1.0.0", "2026-09-23T00:00:00.000Z", "message", fields, b"message")).status, "COMMITTED_LOCAL")
        queue = DerivedJobQueue(Path(self.temp.name) / "with-c3", deletion_resolver=DeletionResolver(locator))
        job = queue.enqueue(self.request)
        queue.claim("worker-a", now="2026-09-23T00:00:00.000Z")
        deleted = DeletionResolver(locator).delete(DeletionRequest("CONVERSATION_MESSAGE", object_id, 1, "22222222-2222-4222-8222-222222222222", "delete", "2026-09-23T00:01:00.000Z"))

        result = queue.preflight(job.job_id, "worker-a", lambda refs: True)

        self.assertEqual(deleted.status, "DELETED")
        self.assertEqual(result.status, DerivedStatus.BLOCKED_STALE)
        self.assertEqual(result.reason, "INPUT_NOT_ELIGIBLE")

    def test_live_c3_preflight_allows_one_traceable_derived_completion(self):
        vault_root = Path(self.temp.name) / "vault-live"
        vault_root.mkdir()
        locator = ActiveVaultLocator(Path(self.temp.name) / "control-live")
        locator.initialize(vault_root, operation_id="init")
        registry = ObjectRegistry()
        registry.register(ObjectRegistration("CONVERSATION_MESSAGE", "CANONICAL", "REVISIONED", "PAYLOAD", "B1"))
        fields = {
            "scope": {"scope_type": "GLOBAL", "scope_id": None},
            "provenance": {"origin": "SYSTEM_OBSERVED", "source_refs": [], "actor": "B1", "explicitness": "OBSERVED"},
            "trust": {"level": "OBSERVED", "confidence": 1.0},
            "sensitivity": {"level": "PERSONAL"},
            "temporal": {"valid_from": None, "valid_until": None},
            "deletion": {"state": "LIVE", "tombstoned_at": None},
        }
        object_id = self.request.input_refs[0][1]
        store = CanonicalStore(locator, registry)
        store.create_canonical(CreateCanonicalIntent("CONVERSATION_MESSAGE", object_id, "1.0.0", "2026-09-23T00:00:00.000Z", "message", fields, b"message"))
        queue = DerivedJobQueue(Path(self.temp.name) / "with-live-c3", deletion_resolver=DeletionResolver(locator))
        job = queue.enqueue(self.request)
        queue.claim("worker-a", now="2026-09-23T00:00:00.000Z")

        ready = queue.preflight(job.job_id, "worker-a", lambda refs: refs == self.request.input_refs)
        completed = queue.settle(job.job_id, "worker-a", "SUCCEEDED", output_refs=(("DERIVED_EPISODE", "22222222-2222-4222-8222-222222222222", 1, "b" * 64),))

        self.assertEqual(ready.status, DerivedStatus.READY)
        self.assertEqual(completed.status, DerivedStatus.SUCCEEDED)

    def test_reclaimed_lease_requires_a_new_preflight(self):
        class LiveDeletion:
            def resolve(self, object_type, object_id):
                return type("Resolution", (), {"state": "NOT_DELETED"})()

        queue = DerivedJobQueue(Path(self.temp.name) / "reclaimed", deletion_resolver=LiveDeletion())
        job = queue.enqueue(self.request)
        queue.claim("worker-a", now="2026-09-23T00:00:00.000Z", lease_seconds=1)
        self.assertEqual(queue.preflight(job.job_id, "worker-a", lambda refs: True).status, DerivedStatus.READY)
        queue.claim("worker-b", now="2026-09-23T00:00:02.000Z")

        result = queue.settle(job.job_id, "worker-b", "SUCCEEDED")

        self.assertEqual(result.status, DerivedStatus.BLOCKED_STALE)

    def test_deleted_input_after_preflight_cannot_complete(self):
        class ChangingDeletion:
            deleted = False

            def resolve(self, object_type, object_id):
                return type("Resolution", (), {"state": "DELETED" if self.deleted else "NOT_DELETED"})()

        deletion = ChangingDeletion()
        queue = DerivedJobQueue(Path(self.temp.name) / "deleted-after-preflight", deletion_resolver=deletion)
        job = queue.enqueue(self.request)
        queue.claim("worker-a")
        self.assertEqual(queue.preflight(job.job_id, "worker-a", lambda refs: True).status, DerivedStatus.READY)

        deletion.deleted = True
        result = queue.settle(job.job_id, "worker-a", "SUCCEEDED")

        self.assertEqual(result.status, DerivedStatus.BLOCKED_STALE)
        self.assertEqual(result.reason, "INPUT_NOT_ELIGIBLE")

    def test_corrupt_claimed_input_references_cannot_reach_the_owner_callback(self):
        class LiveDeletion:
            def resolve(self, object_type, object_id):
                return type("Resolution", (), {"state": "NOT_DELETED"})()

        queue = DerivedJobQueue(Path(self.temp.name) / "corrupt", deletion_resolver=LiveDeletion())
        job = queue.enqueue(self.request)
        queue.claim("worker-a", now="2026-09-23T00:00:00.000Z")
        path = queue.root / "jobs" / f"{job.job_id}.json"
        record = json.loads(path.read_text())
        del record["input_refs"]
        path.write_text(json.dumps(record))

        result = queue.preflight(job.job_id, "worker-a", lambda refs: self.fail("must not run"))

        self.assertEqual(result.status, DerivedStatus.CORRUPT_QUEUE)

    def test_changed_claimed_input_fingerprint_cannot_reach_the_owner_callback(self):
        class LiveDeletion:
            def resolve(self, object_type, object_id):
                return type("Resolution", (), {"state": "NOT_DELETED"})()

        queue = DerivedJobQueue(Path(self.temp.name) / "changed-refs", deletion_resolver=LiveDeletion())
        job = queue.enqueue(self.request)
        queue.claim("worker-a")
        path = queue.root / "jobs" / f"{job.job_id}.json"
        record = json.loads(path.read_text())
        record["input_refs"][0][1] = "22222222-2222-4222-8222-222222222222"
        path.write_text(json.dumps(record))

        result = queue.preflight(job.job_id, "worker-a", lambda refs: self.fail("must not run"))

        self.assertEqual(result.status, DerivedStatus.CORRUPT_QUEUE)


if __name__ == "__main__":
    unittest.main()
