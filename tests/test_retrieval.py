import tempfile
import unittest
from pathlib import Path

from tsuzu.capture import SecretScanResult
from tsuzu.deletion import DeletionRequest, DeletionResolver
from tsuzu.index import IndexManager
from tsuzu.retrieval import RetrievalRequest, RetrievalService
from tsuzu.vault import ActiveVaultLocator
from tsuzu.writer import AtomicSourceWriter


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        vault = root / "vault"
        vault.mkdir()
        self.locator = ActiveVaultLocator(root / "control")
        self.locator.initialize(vault, operation_id="init")
        self.writer = AtomicSourceWriter(self.locator)
        self.index = IndexManager(root / "index", self.locator)
        self.index.open()

    def tearDown(self):
        self.index.close()
        self.temp.cleanup()

    def capture(self, source_id, body, sensitivity="PERSONAL"):
        self.writer.create_source(body, kind="TEXT", capture_method="LOCAL_TEXT", object_id=source_id, sensitivity=sensitivity)
        self.index.upsert_source(source_id)

    def request(self, query, destination="claude_code"):
        return RetrievalRequest("11111111-1111-4111-8111-111111111111", query, destination)

    def test_external_personal_is_approved_as_untrusted_data(self):
        source_id = "22222222-2222-4222-8222-222222222222"
        self.capture(source_id, "採用の面接設定率")
        result = RetrievalService(self.index).retrieve(self.request("面接設定率"))
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.approved[0].source_id, source_id)
        self.assertEqual(result.approved[0].content_role, "UNTRUSTED_DATA")

    def test_codex_personal_recall_uses_the_same_external_egress_policy(self):
        source_id = "23222222-2222-4222-8222-222222222222"
        self.capture(source_id, "Codex explicit recall fixture")

        result = RetrievalService(self.index).retrieve(self.request("explicit recall", "codex"))

        self.assertEqual(result.status, "OK")
        self.assertEqual(result.approved[0].destination_id, "codex")
        self.assertEqual(result.approved[0].destination_class, "TRUSTED_EXTERNAL")

    def test_cursor_personal_recall_uses_the_same_external_egress_policy(self):
        source_id = "24222222-2222-4222-8222-222222222222"
        self.capture(source_id, "Cursor explicit recall fixture")

        result = RetrievalService(self.index).retrieve(self.request("explicit recall", "cursor"))

        self.assertEqual(result.status, "OK")
        self.assertEqual(result.approved[0].destination_id, "cursor")
        self.assertEqual(result.approved[0].destination_class, "TRUSTED_EXTERNAL")

    def test_sensitive_external_and_unknown_destination_are_denied(self):
        source_id = "33333333-3333-4333-8333-333333333333"
        self.capture(source_id, "機密の予算資料", "SENSITIVE")
        external = RetrievalService(self.index).retrieve(self.request("予算資料"))
        self.assertEqual(external.status, "NO_ELIGIBLE_CONTEXT")
        self.assertIn((source_id, "DENY_SENSITIVE_EXTERNAL"), external.decisions)
        codex = RetrievalService(self.index).retrieve(self.request("予算資料", "codex"))
        self.assertEqual(codex.status, "NO_ELIGIBLE_CONTEXT")
        self.assertIn((source_id, "DENY_SENSITIVE_EXTERNAL"), codex.decisions)
        cursor = RetrievalService(self.index).retrieve(self.request("予算資料", "cursor"))
        self.assertEqual(cursor.status, "NO_ELIGIBLE_CONTEXT")
        self.assertIn((source_id, "DENY_SENSITIVE_EXTERNAL"), cursor.decisions)
        local = RetrievalService(self.index).retrieve(self.request("予算資料", "local_test"))
        self.assertEqual(local.status, "OK")
        unknown = RetrievalService(self.index).retrieve(self.request("予算資料", "spoofed_local"))
        self.assertEqual(unknown.status, "NO_ELIGIBLE_CONTEXT")
        self.assertEqual(unknown.decisions[0][1], "DENY_DESTINATION_UNKNOWN")

    def test_stale_index_candidate_is_denied_by_ledger(self):
        source_id = "44444444-4444-4444-8444-444444444444"
        self.capture(source_id, "削除される候補")
        resolver = DeletionResolver(self.locator, self.writer)
        self.assertEqual(resolver.delete_source(DeletionRequest.source(source_id, expected_revision=1)).status, "DELETED")
        result = RetrievalService(self.index, deletion_resolver=resolver).retrieve(self.request("削除される"))
        self.assertEqual(result.status, "NO_ELIGIBLE_CONTEXT")
        self.assertIn((source_id, "DENY_DELETED"), result.decisions)

    def test_short_like_query_treats_wildcards_as_data(self):
        source_id = "55555555-5555-4555-8555-555555555555"
        self.capture(source_id, "100%達成")
        result = RetrievalService(self.index).retrieve(self.request("%"))
        self.assertEqual([item.source_id for item in result.approved], [source_id])

    def test_current_secret_scan_denies_before_egress(self):
        source_id = "66666666-6666-4666-8666-666666666666"
        self.capture(source_id, "再分類対象")
        result = RetrievalService(self.index, scanner=BlockingScanner()).retrieve(self.request("再分類対象"))
        self.assertEqual(result.status, "NO_ELIGIBLE_CONTEXT")
        self.assertIn((source_id, "DENY_SECRET_RECLASSIFIED"), result.decisions)


class BlockingScanner:
    RULESET_VERSION = "test"

    def scan_bytes(self, payload):
        return SecretScanResult("BLOCKED_RESTRICTED", "test", ("TEST",), len(payload), "0" * 64)


if __name__ == "__main__":
    unittest.main()
