import tempfile
import unittest
from pathlib import Path

from tsuzu.derived import DerivedJobQueue, DerivedJobRequest, DerivedStatus


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


if __name__ == "__main__":
    unittest.main()
