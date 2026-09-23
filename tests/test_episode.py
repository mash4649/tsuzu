import unittest

from tsuzu.episode import EpisodeDraft, EpisodeMessage, segment_messages, validate_episode


class EpisodeTests(unittest.TestCase):
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
