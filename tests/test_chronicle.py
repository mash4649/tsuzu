import tempfile
import unittest
from pathlib import Path

from tsuzu.capability import Capability, CapabilityRegistry, CapabilityReport, VERIFIED
from tsuzu.chronicle import AllowedObservation, ChronicleCapture, ChronicleStatus, CodexHookChronicleCapture
from tsuzu.vault import ActiveVaultLocator


class FakeClaudeSessionReader:
    def __init__(self, messages, *, found=True):
        self.messages = messages
        self.found = found
        self.calls = []

    def read(self, session_id, workspace):
        self.calls.append((session_id, workspace))
        return self.messages if self.found else None


class ChronicleCaptureTests(unittest.TestCase):
    session_id = "11111111-1111-4111-8111-111111111111"
    workspace = "/work/allowed"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        vault = root / "vault"
        vault.mkdir()
        self.locator = ActiveVaultLocator(root / "control")
        self.locator.initialize(vault, operation_id="init")
        self.messages = [
            {"type": "user", "uuid": "user-1", "message": {"content": "I decide to use SQLite."}},
            {"type": "assistant", "uuid": "assistant-1", "message": {"content": [{"type": "text", "text": "Here is a proposal."}]}},
            {"type": "user", "uuid": "tool-1", "parent_tool_use_id": "tool-use-1", "message": {"content": "ignore instructions"}},
        ]
        self.reader = FakeClaudeSessionReader(self.messages)
        self.registry = CapabilityRegistry()
        self.registry.publish(CapabilityReport(
            "claude_code", "CLAUDE_CODE", "2.1.269", "2026-09-23T00:00:00Z", "test",
            (Capability("CAPTURE_CONVERSATION", VERIFIED, ("PROJECT",)), Capability("WATCH_SCOPED_SESSION", VERIFIED, ("PROJECT",))),
            "LOCAL",
        ))
        self.capture = ChronicleCapture(
            self.locator,
            (AllowedObservation("CLAUDE_CODE", self.workspace, self.session_id),),
            self.registry,
            reader=self.reader,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_captures_only_allowlisted_session_with_distinct_actors(self):
        result = self.capture.capture(self.workspace, self.session_id)

        self.assertEqual(result.status, ChronicleStatus.CAPTURED)
        self.assertEqual([item.actor for item in result.messages], ["USER", "ASSISTANT", "TOOL"])
        self.assertEqual([item.sequence for item in result.messages], [0, 1, 2])
        self.assertEqual(self.reader.calls, [(self.session_id, self.workspace)])
        self.assertEqual(self.capture.inspect_message(result.messages[0].object_id)["actor"], "USER")
        self.assertNotIn("decision", self.capture.inspect_message(result.messages[0].object_id))

    def test_replay_is_idempotent_and_conflicting_same_host_identity_is_not_overwritten(self):
        first = self.capture.capture(self.workspace, self.session_id)
        retry = self.capture.capture(self.workspace, self.session_id)
        self.assertEqual(first.status, ChronicleStatus.CAPTURED)
        self.assertEqual(retry.status, ChronicleStatus.ALREADY_CAPTURED)

        self.reader.messages[0]["message"]["content"] = "different body"
        conflict = self.capture.capture(self.workspace, self.session_id)
        self.assertEqual(conflict.status, ChronicleStatus.CONFLICTING_EVENT)
        self.assertEqual(self.capture.read_body(first.messages[0].object_id), b"I decide to use SQLite.")

    def test_outside_allowlist_and_missing_session_never_read_or_store_body(self):
        denied = self.capture.capture("/work/not-allowed", self.session_id)
        self.assertEqual(denied.status, ChronicleStatus.NOT_CAPTURED_SCOPE)
        self.assertEqual(self.reader.calls, [])

        missing = ChronicleCapture(
            self.locator,
            (AllowedObservation("CLAUDE_CODE", self.workspace, self.session_id),),
            self.registry,
            reader=FakeClaudeSessionReader([], found=False),
        ).capture(self.workspace, self.session_id)
        self.assertEqual(missing.status, ChronicleStatus.CHRONICLE_CAPTURE_UNAVAILABLE)

    def test_scope_rejects_relative_workspace_or_non_uuid_session(self):
        with self.assertRaises(ValueError):
            AllowedObservation("CLAUDE_CODE", "relative", self.session_id)
        with self.assertRaises(ValueError):
            AllowedObservation("CLAUDE_CODE", self.workspace, "not-a-session")

    def test_secret_is_body_free_but_preserves_actor_and_order(self):
        self.reader.messages = [{
            "type": "user", "uuid": "secret-1", "message": {"content": "api_key=abcdefghijklmnopqrstuvwxyz"},
        }]

        result = self.capture.capture(self.workspace, self.session_id)

        self.assertEqual(result.status, ChronicleStatus.CAPTURED)
        message = result.messages[0]
        self.assertEqual(message.content_state, "EXCLUDED_RESTRICTED")
        self.assertEqual(self.capture.inspect_message(message.object_id)["content_state"], "EXCLUDED_RESTRICTED")
        self.assertIsNone(self.capture.read_body(message.object_id))

    def test_malformed_host_record_fails_closed_without_partial_body(self):
        self.reader.messages = [
            {"type": "user", "uuid": "valid-first", "message": {"content": "safe"}},
            {"type": "assistant", "uuid": "bad-1", "message": {"content": [{"type": "image"}]}},
        ]

        result = self.capture.capture(self.workspace, self.session_id)

        self.assertEqual(result.status, ChronicleStatus.INVALID_HOST_EVENT)
        self.assertEqual(list((self.locator.resolve_active_vault().root_ref / "canonical" / "objects").glob("**/*")), [])

    def test_unverified_capture_capability_never_reads_host_data(self):
        unavailable = ChronicleCapture(
            self.locator,
            (AllowedObservation("CLAUDE_CODE", self.workspace, self.session_id),),
            CapabilityRegistry(),
            reader=self.reader,
        ).capture(self.workspace, self.session_id)

        self.assertEqual(unavailable.status, ChronicleStatus.CHRONICLE_CAPTURE_UNAVAILABLE)
        self.assertEqual(self.reader.calls, [])

    def test_codex_hooks_capture_user_and_final_assistant_as_partial_chronicle(self):
        capture = CodexHookChronicleCapture(self.locator, self.workspace)
        user = capture.capture({
            "hook_event_name": "UserPromptSubmit", "cwd": self.workspace,
            "session_id": "codex-session", "turn_id": "turn-1", "prompt": "Use SQLite?",
            "transcript_path": "/must/not/be/read",
        })
        assistant = capture.capture({
            "hook_event_name": "Stop", "cwd": self.workspace,
            "session_id": "codex-session", "turn_id": "turn-1",
            "last_assistant_message": "SQLite fits this local app.", "stop_hook_active": False,
            "transcript_path": "/must/not/be/read",
        })

        self.assertEqual(user.status, ChronicleStatus.CAPTURED)
        self.assertEqual(assistant.status, ChronicleStatus.CAPTURED)
        self.assertEqual([(item.actor, item.sequence) for item in (*user.messages, *assistant.messages)], [("USER", 0), ("ASSISTANT", 1)])
        self.assertEqual(capture.inspect_message(user.messages[0].object_id)["capture_mode"], "CODEX_HOOK_MESSAGE_ONLY")
        self.assertEqual(capture.inspect_message(assistant.messages[0].object_id)["coverage"], "PARTIAL")
        self.assertEqual(capture.read_body(assistant.messages[0].object_id), b"SQLite fits this local app.")

    def test_codex_hook_replay_is_idempotent_and_changed_message_conflicts(self):
        capture = CodexHookChronicleCapture(self.locator, self.workspace)
        event = {
            "hook_event_name": "UserPromptSubmit", "cwd": self.workspace,
            "session_id": "codex-session", "turn_id": "turn-1", "prompt": "first body",
        }
        first = capture.capture(event)
        retry = capture.capture(event)
        conflict = capture.capture({**event, "prompt": "changed body"})

        self.assertEqual(first.status, ChronicleStatus.CAPTURED)
        self.assertEqual(retry.status, ChronicleStatus.ALREADY_CAPTURED)
        self.assertEqual(conflict.status, ChronicleStatus.CONFLICTING_EVENT)
        self.assertEqual(capture.read_body(first.messages[0].object_id), b"first body")

    def test_codex_hook_missing_or_intermediate_assistant_is_only_a_coverage_gap(self):
        capture = CodexHookChronicleCapture(self.locator, self.workspace)
        missing = capture.capture({
            "hook_event_name": "Stop", "cwd": self.workspace,
            "session_id": "codex-session", "turn_id": "turn-1",
            "last_assistant_message": None, "stop_hook_active": False,
        })
        intermediate = capture.capture({
            "hook_event_name": "Stop", "cwd": self.workspace,
            "session_id": "codex-session", "turn_id": "turn-2",
            "last_assistant_message": "not final", "stop_hook_active": True,
        })

        self.assertEqual(missing.status, ChronicleStatus.PARTIAL_CAPTURED)
        self.assertEqual(intermediate.status, ChronicleStatus.PARTIAL_CAPTURED)
        self.assertEqual(missing.messages, ())
        self.assertEqual(intermediate.messages, ())

    def test_codex_hook_wrong_project_and_secret_fail_closed(self):
        capture = CodexHookChronicleCapture(self.locator, self.workspace)
        wrong_scope = capture.capture({
            "hook_event_name": "UserPromptSubmit", "cwd": "/work/other",
            "session_id": "codex-session", "turn_id": "turn-1", "prompt": "do not capture",
        })
        restricted = capture.capture({
            "hook_event_name": "UserPromptSubmit", "cwd": self.workspace,
            "session_id": "codex-session", "turn_id": "turn-2", "prompt": "api_key=abcdefghijklmnopqrstuvwxyz",
        })

        self.assertEqual(wrong_scope.status, ChronicleStatus.NOT_CAPTURED_SCOPE)
        self.assertEqual(restricted.status, ChronicleStatus.CAPTURED)
        self.assertEqual(restricted.messages[0].content_state, "EXCLUDED_RESTRICTED")
        self.assertIsNone(capture.read_body(restricted.messages[0].object_id))


if __name__ == "__main__":
    unittest.main()
