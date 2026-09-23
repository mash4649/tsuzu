import json
import unittest
import tempfile
from dataclasses import replace
from pathlib import Path

from tsuzu.canonical import CanonicalStore, ObjectRegistration, ObjectRegistry, _parse_manifest
from tsuzu.chronicle import CodexHookChronicleCapture
from tsuzu.derived import DerivedJobQueue, DerivedJobRequest, DerivedStatus
from tsuzu.episode import EpisodeDraft, EpisodeMessage, build_episode_inputs, complete_episode_job, persist_episode, segment_messages, validate_episode
from tsuzu.vault import ActiveVaultLocator


class EpisodeTests(unittest.TestCase):
    def test_codex_chronicle_inputs_rebuild_episode_messages_and_refs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            vault.mkdir()
            locator = ActiveVaultLocator(root / "control")
            locator.initialize(vault, operation_id="init")
            capture = CodexHookChronicleCapture(locator, "/work/allowed")
            user = capture.capture({
                "hook_event_name": "UserPromptSubmit", "cwd": "/work/allowed", "session_id": "codex-session",
                "turn_id": "turn-1", "prompt": "Use SQLite?",
            })
            assistant = capture.capture({
                "hook_event_name": "Stop", "cwd": "/work/allowed", "session_id": "codex-session",
                "turn_id": "turn-1", "last_assistant_message": "SQLite fits here.", "stop_hook_active": False,
            })
            conversation_ref = capture.inspect_message(user.messages[0].object_id)["conversation_id"]

            messages, refs = build_episode_inputs(locator, conversation_ref)
            episodes = segment_messages(messages, "b2-rules-v1")

            self.assertEqual([(item.actor, item.text) for item in messages], [("USER", "Use SQLite?"), ("ASSISTANT", "SQLite fits here.")])
            self.assertEqual({item[1] for item in refs}, {user.messages[0].object_id, assistant.messages[0].object_id})
            self.assertEqual([item.sequence for item in messages], [0, 1])
            self.assertTrue(all(item.observed_at.endswith("Z") for item in messages))
            self.assertEqual(len(episodes), 1)
            self.assertEqual(episodes[0].message_refs, ((user.messages[0].object_id, "USER"), (assistant.messages[0].object_id, "ASSISTANT")))

    def test_episode_job_requires_c4_preflight_then_settles_with_derived_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            vault.mkdir()
            locator = ActiveVaultLocator(root / "control")
            locator.initialize(vault, operation_id="init")

            class LiveDeletion:
                def resolve(self, object_type, object_id):
                    return type("Resolution", (), {"state": "NOT_DELETED"})()

            refs = (("CONVERSATION_MESSAGE", "22222222-2222-4222-8222-222222222222", 1, "a" * 64),)
            request = DerivedJobRequest("EPISODE_SEGMENT", refs, "b2-rules-v1", "local-v1", "GLOBAL", "session-1")
            queue = DerivedJobQueue(root / "runtime", deletion_resolver=LiveDeletion())
            job = queue.enqueue(request)
            queue.claim("worker", now="2026-09-23T00:00:00.000Z")
            store = CanonicalStore(locator)
            episode = EpisodeDraft(
                "11111111-1111-4111-8111-111111111111", ((refs[0][1], "USER"),),
                "2026-09-23T00:00:00.000Z", "2026-09-23T00:00:00.000Z", "UNRESOLVED",
                "1 Chronicle messages", "b2-rules-v1", 0.8, 1, 0,
            )

            result = complete_episode_job(queue, request, job.job_id, "worker", store, lambda actual: episode, lambda actual: actual == refs)

            self.assertEqual(result.status, DerivedStatus.SUCCEEDED)
            record = json.loads((root / "runtime" / "jobs" / f"{job.job_id}.json").read_text())
            self.assertEqual(record["state"], "SUCCEEDED")
            self.assertEqual(record["output_refs"][0][0], "EPISODE")
            self.assertTrue(record["output_refs"][0][1])
            self.assertEqual(record["output_refs"][0][2], 1)
            self.assertTrue((vault / "derived" / "objects" / "EPISODE" / record["output_refs"][0][1] / "object.md").exists())

    def test_deletion_during_episode_build_blocks_materialization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            vault.mkdir()
            locator = ActiveVaultLocator(root / "control")
            locator.initialize(vault, operation_id="init")

            class DeletionChangesDuringBuild:
                deleted = False

                def resolve(self, object_type, object_id):
                    return type("Resolution", (), {"state": "DELETED" if self.deleted else "NOT_DELETED"})()

            deletion = DeletionChangesDuringBuild()
            refs = (("CONVERSATION_MESSAGE", "22222222-2222-4222-8222-222222222222", 1, "a" * 64),)
            request = DerivedJobRequest("EPISODE_SEGMENT", refs, "b2-rules-v1", "local-v1", "GLOBAL", "session-1")
            queue = DerivedJobQueue(root / "runtime", deletion_resolver=deletion)
            job = queue.enqueue(request)
            queue.claim("worker", now="2026-09-23T00:00:00.000Z")
            episode = EpisodeDraft(
                "11111111-1111-4111-8111-111111111111", ((refs[0][1], "USER"),),
                "2026-09-23T00:00:00.000Z", "2026-09-23T00:00:00.000Z", "UNRESOLVED",
                "1 Chronicle messages", "b2-rules-v1", 0.8, 1, 0,
            )

            def build(_):
                deletion.deleted = True
                return episode

            result = complete_episode_job(queue, request, job.job_id, "worker", CanonicalStore(locator), build, lambda actual: actual == refs)

            self.assertEqual(result.status, DerivedStatus.BLOCKED_STALE)
            self.assertFalse((vault / "derived" / "objects" / "EPISODE").exists())

    def test_persistence_is_derived_traceable_and_idempotent_per_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vault = root / "vault"
            vault.mkdir()
            locator = ActiveVaultLocator(root / "control")
            locator.initialize(vault, operation_id="init")
            registry = ObjectRegistry()
            registry.register(ObjectRegistration("EPISODE", "DERIVED", "IMMUTABLE", "NONE", "B2"))
            store = CanonicalStore(locator, registry)
            message_id = "22222222-2222-4222-8222-222222222222"
            episode = EpisodeDraft(
                "11111111-1111-4111-8111-111111111111", ((message_id, "USER"),),
                "2026-09-23T00:00:00.000Z", "2026-09-23T00:00:00.000Z", "UNRESOLVED",
                "1 Chronicle messages", "b2-rules-v1", 0.8, 1, 0,
            )

            refs = (("CONVERSATION_MESSAGE", message_id, 1, "a" * 64),)
            first = persist_episode(store, episode, refs, policy_version="local-v1")
            replay = persist_episode(store, episode, refs, policy_version="local-v1")
            next_generation = persist_episode(store, replace(episode, algorithm_version="b2-rules-v2"), refs, policy_version="local-v1")
            next_policy = persist_episode(store, episode, refs, policy_version="local-v2")
            invalid = persist_episode(store, episode, (("CONVERSATION_MESSAGE", "33333333-3333-4333-8333-333333333333", 1, "a" * 64),), policy_version="local-v1")
            path = vault / "derived" / "objects" / "EPISODE" / first.object_id / "object.md"
            manifest = _parse_manifest(path.read_text())

            self.assertEqual(first.status, "COMMITTED_LOCAL")
            self.assertEqual(replay.status, "ALREADY_COMMITTED")
            self.assertEqual(next_generation.status, "COMMITTED_LOCAL")
            self.assertNotEqual(first.object_id, next_generation.object_id)
            self.assertEqual(next_policy.status, "COMMITTED_LOCAL")
            self.assertNotEqual(first.object_id, next_policy.object_id)
            self.assertEqual(invalid.status, "VALIDATION_FAILED")
            self.assertEqual(manifest["processing_state"], "DERIVED")
            self.assertEqual(manifest["message_refs"], [{"message_id": message_id, "actor": "USER"}])
            self.assertTrue(manifest["derivation"]["input_fingerprint"])
            self.assertFalse((vault / "canonical" / "objects" / "EPISODE").exists())

    def test_multi_message_episode_keeps_actor_aware_trace_and_derived_fields(self):
        episode = EpisodeDraft(
            "11111111-1111-4111-8111-111111111111",
            (("22222222-2222-4222-8222-222222222222", "USER"), ("33333333-3333-4333-8333-333333333333", "ASSISTANT")),
            "2026-09-23T00:00:00.000Z", "2026-09-23T00:01:00.000Z", "storage choice", "Compared local storage options.", "b2-rules-v1", 0.8, 2, 0,
        )

        validate_episode(episode)
        self.assertEqual(episode.processing_state, "DERIVED")
        self.assertEqual(len(episode.message_refs), 2)

    def test_episode_rejects_invalid_trace_or_coverage(self):
        episode = EpisodeDraft(
            "11111111-1111-4111-8111-111111111111",
            (("not-a-uuid", "USER"),),
            "2026-09-23T00:01:00.000Z", "2026-09-23T00:00:00.000Z", "topic", "summary", "b2-rules-v1", 1.2, 1, 0,
        )

        with self.assertRaises(ValueError):
            validate_episode(episode)

    def test_explicit_topic_change_splits_derived_episodes_and_keeps_restricted_gap(self):
        messages = (
            EpisodeMessage("11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", "USER", "2026-09-23T00:00:00.000Z", "AVAILABLE", "Compare SQLite options"),
            EpisodeMessage("11111111-1111-4111-8111-111111111111", "33333333-3333-4333-8333-333333333333", "ASSISTANT", "2026-09-23T00:01:00.000Z", "EXCLUDED_RESTRICTED", None),
            EpisodeMessage("11111111-1111-4111-8111-111111111111", "44444444-4444-4444-8444-444444444444", "USER", "2026-09-23T00:02:00.000Z", "AVAILABLE", "New topic: deployment"),
        )

        episodes = segment_messages(messages, "b2-rules-v1")

        self.assertEqual([len(item.message_refs) for item in episodes], [2, 1])
        self.assertEqual(episodes[0].excluded_restricted_count, 1)
        self.assertEqual(episodes[0].working_summary, "2 Chronicle messages")

    def test_all_unavailable_messages_do_not_create_an_episode(self):
        messages = (EpisodeMessage("11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", "ASSISTANT", "2026-09-23T00:00:00.000Z", "EXCLUDED_RESTRICTED", None),)

        self.assertEqual(segment_messages(messages, "b2-rules-v1"), ())


if __name__ == "__main__":
    unittest.main()
