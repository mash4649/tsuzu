import tempfile
import unittest
from pathlib import Path

from tsuzu.clip_digest import ClipDigestAdapter, ClipNote, ClipDigestError
from tsuzu.claude_adapter import ClaudeMcpServer
from tsuzu.acquisition import FetchResult, PublicWebFetcher
from tsuzu.vault import ActiveVaultLocator


class Notes:
    def __init__(self, items):
        self.items = items

    def list_clips(self):
        return list(self.items)


class Fetcher:
    def __init__(self):
        self.urls = []

    def fetch(self, request):
        self.urls.append(request.url)
        return FetchResult.success(final_url=request.url, body=b"<html><title>Useful</title><p>Evidence</p></html>", media_type="text/html")


class ClipDigestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.vault = root / "vault"
        self.vault.mkdir()
        self.locator = ActiveVaultLocator(root / "control")
        self.locator.initialize(self.vault, operation_id="init")
        self.notes = Notes([ClipNote("note-1", "Read this", "<a href=\"https://example.test/post\">Article</a>")])
        self.fetcher = Fetcher()
        self.adapter = ClipDigestAdapter(self.notes, self.locator, fetcher=self.fetcher)

    def tearDown(self):
        self.temp.cleanup()

    def test_lists_new_clips_with_opaque_ids_and_untrusted_note_content(self):
        result = self.adapter.list_clips({})["structuredContent"]
        self.assertEqual(len(result["items"]), 1)
        item = result["items"][0]
        self.assertNotEqual(item["candidateId"], "note-1")
        self.assertEqual(item["urls"], ["https://example.test/post"])
        self.assertEqual(item["contentRole"], "UNTRUSTED_DATA")
        self.assertNotIn("noteText", item)

    def test_list_returns_a_bounded_batch_with_truncation_signal(self):
        self.notes.items = [ClipNote(f"note-{index}", f"clip {index}", f"https://example.test/{index}") for index in range(27)]
        result = self.adapter.list_clips({})["structuredContent"]
        self.assertEqual(len(result["items"]), 25)
        self.assertTrue(result["truncated"])

    def test_inspection_only_fetches_a_url_attached_to_a_pending_note(self):
        item = self.adapter.list_clips({})["structuredContent"]["items"][0]
        inspected = self.adapter.inspect_url({"candidateId": item["candidateId"], "url": item["urls"][0]})["structuredContent"]
        self.assertEqual(inspected["status"], "OK")
        self.assertIn("Evidence", inspected["content"])
        self.assertEqual(self.fetcher.urls, ["https://example.test/post"])
        with self.assertRaises(ClipDigestError):
            self.adapter.inspect_url({"candidateId": item["candidateId"], "url": "https://other.test/"})

    def test_import_writes_idempotent_draft_and_marks_candidate_processed(self):
        candidate = self.adapter.list_clips({})["structuredContent"]["items"][0]
        args = {
            "candidateId": candidate["candidateId"], "sourceUrl": candidate["urls"][0],
            "contentStatus": "FULL",
            "title": "A useful principle", "description": "How to evaluate decisions.",
            "category": "AI運用 / 自動化", "theme": "decision-quality",
            "oneLine": "Check evidence before acting.", "whenUseful": "When deciding whether to automate.",
            "howToUse": "Use as a preflight checklist.",
        }
        self.adapter.inspect_url({"candidateId": candidate["candidateId"], "url": candidate["urls"][0]})
        first = self.adapter.import_draft(args)["structuredContent"]
        second = self.adapter.import_draft(args)["structuredContent"]
        self.assertEqual(first["status"], "IMPORTED")
        self.assertEqual(second["status"], "ALREADY_IMPORTED")
        self.assertEqual(first["path"], second["path"])
        self.assertTrue((self.vault / first["path"]).is_file())
        self.assertEqual(self.adapter.list_clips({})["structuredContent"]["items"], [])

    def test_rejects_unlinked_url_invalid_category_and_unknown_arguments(self):
        candidate = self.adapter.list_clips({})["structuredContent"]["items"][0]
        with self.assertRaises(ClipDigestError):
            self.adapter.inspect_url({"candidateId": candidate["candidateId"], "url": "http://127.0.0.1/"})
        with self.assertRaises(ClipDigestError):
            self.adapter.import_draft({"candidateId": candidate["candidateId"], "extra": True})

    def test_secret_notes_and_secret_page_content_never_reach_chatgpt(self):
        self.notes.items.append(ClipNote("note-2", "Secret", "api_key=abcdefghijklmnop https://example.test/private"))
        self.assertEqual(len(self.adapter.list_clips({})["structuredContent"]["items"]), 1)
        self.fetcher.fetch = lambda request: FetchResult.success(final_url=request.url, body=b"password=abcdefghijklmnop", media_type="text/plain")
        candidate = self.adapter.list_clips({})["structuredContent"]["items"][0]
        result = self.adapter.inspect_url({"candidateId": candidate["candidateId"], "url": candidate["urls"][0]})["structuredContent"]
        self.assertEqual(result, {"status": "BLOCKED_RESTRICTED", "contentRole": "UNTRUSTED_DATA"})

    def test_r1_blocks_a_public_hostname_resolving_to_loopback(self):
        guarded = ClipDigestAdapter(self.notes, self.locator, fetcher=PublicWebFetcher(resolver=lambda host: ["127.0.0.1"]))
        candidate = guarded.list_clips({})["structuredContent"]["items"][0]
        result = guarded.inspect_url({"candidateId": candidate["candidateId"], "url": candidate["urls"][0]})["structuredContent"]
        self.assertEqual(result["status"], "BLOCKED_POLICY")

    def test_existing_wiki_source_is_not_listed_again(self):
        card = self.vault / "wiki" / "cards" / "already.md"
        card.parent.mkdir(parents=True)
        card.write_text('---\nsource: "https://example.test/post"\n---\n')
        self.assertEqual(self.adapter.list_clips({})["structuredContent"]["items"], [])

    def test_each_link_in_a_multi_link_note_is_tracked_separately(self):
        self.notes.items[0] = ClipNote("note-1", "Read these", '<a href="https://example.test/post">One</a> <a href="https://example.test/other">Two</a>')
        items = self.adapter.list_clips({})["structuredContent"]["items"]
        self.assertEqual(len(items), 2)
        self.adapter.inspect_url({"candidateId": items[0]["candidateId"], "url": items[0]["urls"][0]})
        args = {
            "candidateId": items[0]["candidateId"], "sourceUrl": items[0]["urls"][0], "contentStatus": "FULL",
            "title": "First", "description": "Description", "category": "ツール", "theme": "test",
            "oneLine": "A point.", "whenUseful": "When needed.", "howToUse": "Use it.",
        }
        self.adapter.import_draft(args)
        remaining = self.adapter.list_clips({})["structuredContent"]["items"]
        self.assertEqual([item["urls"] for item in remaining], [["https://example.test/other"]])

    def test_import_requires_link_inspection(self):
        candidate = self.adapter.list_clips({})["structuredContent"]["items"][0]
        args = {
            "candidateId": candidate["candidateId"], "sourceUrl": candidate["urls"][0], "contentStatus": "FULL",
            "title": "Title", "description": "Description", "category": "ツール", "theme": "test",
            "oneLine": "A point.", "whenUseful": "When needed.", "howToUse": "Use it.",
        }
        with self.assertRaises(ClipDigestError):
            self.adapter.import_draft(args)
        with self.assertRaises(ClipDigestError):
            self.adapter.reject_clip({"candidateId": candidate["candidateId"], "reason": "duplicate"})

    def test_reject_marks_only_a_link_that_was_inspected(self):
        candidate = self.adapter.list_clips({})["structuredContent"]["items"][0]
        self.adapter.inspect_url({"candidateId": candidate["candidateId"], "url": candidate["urls"][0]})
        result = self.adapter.reject_clip({"candidateId": candidate["candidateId"], "reason": "not useful"})["structuredContent"]
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(self.adapter.list_clips({})["structuredContent"]["items"], [])

    def test_permanent_fetch_failure_can_only_create_a_thin_draft(self):
        candidate = self.adapter.list_clips({})["structuredContent"]["items"][0]
        self.fetcher.fetch = lambda request: FetchResult("PERMANENT_FAILURE", failure_code="HTTP_403")
        result = self.adapter.inspect_url({"candidateId": candidate["candidateId"], "url": candidate["urls"][0]})["structuredContent"]
        self.assertEqual(result["status"], "UNAVAILABLE")
        args = {
            "candidateId": candidate["candidateId"], "sourceUrl": candidate["urls"][0], "contentStatus": "THIN",
            "title": "Title", "description": "Description", "category": "ツール", "theme": "test",
            "oneLine": "A point.", "whenUseful": "When needed.", "howToUse": "Use it.",
        }
        draft = self.adapter.import_draft(args)["structuredContent"]
        self.assertEqual(draft["status"], "IMPORTED")
        self.assertIn('source_status: "thin"', (self.vault / draft["path"]).read_text())

    def test_mcp_server_exposes_clip_actions_without_changing_recall_hosts(self):
        server = ClaudeMcpServer(self.adapter)
        listed = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = [tool["name"] for tool in listed["result"]["tools"]]
        self.assertEqual(names, ["tsuzu_clip_list", "tsuzu_clip_inspect", "tsuzu_clip_import", "tsuzu_clip_reject"])
        self.assertTrue(listed["result"]["tools"][2]["annotations"]["readOnlyHint"] is False)
        invalid = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "tsuzu_recall", "arguments": {}}})
        self.assertEqual(invalid["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
