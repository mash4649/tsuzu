import json
import tempfile
import unittest
from pathlib import Path

from tsuzu.acquisition import AcquisitionService, FetchResult
from tsuzu.claude_adapter import ClaudeMcpServer
from tsuzu.clip_digest import ChatGPTNotesAdapter, ClipDigestAdapter, SelectedNoteBridge, SelectedNoteLinkAdapter
from tsuzu.historical_import import MacOSAppleNotesBridge
from tsuzu.index import IndexManager
from tsuzu.vault import ActiveVaultLocator


class Fetcher:
    adapter_id = "public_web"
    adapter_version = "1.0"

    def __init__(self):
        self.calls = 0
        self.requests = []
        self.result = FetchResult.success(
            final_url="https://example.test/post",
            body=b"<html><p>Searchable public evidence</p></html>",
            media_type="text/html",
        )

    def fetch(self, request):
        self.calls += 1
        self.requests.append(request)
        return self.result


class SelectedNoteLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.vault = root / "vault"
        self.vault.mkdir()
        self.locator = ActiveVaultLocator(root / "control")
        self.locator.initialize(self.vault, operation_id="init")
        self.index = IndexManager(root / "index", self.locator)
        self.index.open()
        self.queue = root / "runtime" / "queue"
        self.fetcher = Fetcher()
        self.note = {
            "id": "private-note-id", "title": "Selected article",
            "body": '<a href="https://example.test/post">Article</a>',
            "created_at": "2026-09-24T00:00:00.000Z", "modified_at": "2026-09-24T00:00:00.000Z",
        }
        bridge = SelectedNoteBridge(MacOSAppleNotesBridge(lambda: json.dumps(self.note)))
        self.adapter = SelectedNoteLinkAdapter(
            bridge, self.locator, self.queue, self.index, fetcher=self.fetcher,
            acquisition=AcquisitionService(self.locator, resolver=lambda host: ["8.8.8.8"]),
        )

    def tearDown(self):
        self.index.close()
        self.temp.cleanup()

    def test_selected_note_attachment_and_inline_url_are_candidates_without_fetch(self):
        self.note["body"] += " https://example.test/inline"
        items = self.adapter.list_clips({})["structuredContent"]["items"]
        self.assertEqual({item["urls"][0] for item in items}, {"https://example.test/post", "https://example.test/inline"})
        self.assertEqual(self.fetcher.calls, 0)
        self.assertFalse((self.vault / "canonical").exists())

    def test_reviewed_public_page_is_acquired_and_searchable_once(self):
        item = self.adapter.list_clips({})["structuredContent"]["items"][0]
        args = {"candidateId": item["candidateId"], "url": item["urls"][0]}
        with self.assertRaises(ValueError):
            self.adapter.import_source(args)
        inspected = self.adapter.inspect_url(args)["structuredContent"]
        self.assertEqual(inspected["status"], "OK")
        self.assertIn("Searchable public evidence", inspected["content"])
        self.assertEqual(inspected["sourceUrl"], args["url"])
        first = self.adapter.import_source(args)["structuredContent"]
        second = self.adapter.import_source(args)["structuredContent"]
        self.assertEqual(first["status"], "IMPORTED")
        self.assertEqual(second["status"], "ALREADY_IMPORTED")
        self.assertEqual(first["sourceId"], second["sourceId"])
        self.assertEqual(first["sourceId"], self.index.search("Searchable public evidence")[0])
        self.assertEqual(self.fetcher.calls, 1)
        self.assertEqual(len(list((self.vault / "canonical" / "sources").iterdir())), 1)
        self.assertEqual(len(list((self.vault / "canonical" / "objects" / "SOURCE_VERSION").iterdir())), 1)
        self.index.close()
        self.index.open()
        restarted = SelectedNoteLinkAdapter(
            SelectedNoteBridge(MacOSAppleNotesBridge(lambda: json.dumps(self.note))),
            self.locator, self.queue, self.index, fetcher=self.fetcher,
            acquisition=AcquisitionService(self.locator, resolver=lambda host: ["8.8.8.8"]),
        )
        restarted.inspect_url(args)
        self.assertEqual(restarted.import_source(args)["structuredContent"]["status"], "ALREADY_IMPORTED")
        self.assertEqual(len(list((self.vault / "canonical" / "sources").iterdir())), 1)

    def test_large_x_article_fits_bounded_review_and_acquisition_limits(self):
        self.note["body"] = '<a href="https://x.com/example/status/1">X post</a>'
        item = self.adapter.list_clips({})["structuredContent"]["items"][0]
        args = {"candidateId": item["candidateId"], "url": item["urls"][0]}
        body = ("x" * 25_000).encode()
        self.fetcher.result = FetchResult.success(final_url=args["url"], body=body, media_type="text/plain")
        acquisition_limits = []
        original_acquire = self.adapter.acquisition.acquire

        def record_limit(source_id, adapter, *, max_response_bytes=5 * 1024 * 1024):
            acquisition_limits.append(max_response_bytes)
            return original_acquire(source_id, adapter, max_response_bytes=max_response_bytes)

        self.adapter.acquisition.acquire = record_limit
        inspected = self.adapter.inspect_url(args)["structuredContent"]
        self.assertEqual(inspected["status"], "OK")
        self.assertEqual(self.fetcher.requests[-1].max_response_bytes, 5 * 1024 * 1024)
        self.assertEqual(len(inspected["content"]), 25_000)
        self.adapter.import_source(args)
        self.assertEqual(acquisition_limits, [5 * 1024 * 1024])

    def test_failed_or_unsafe_fetch_cannot_be_imported(self):
        item = self.adapter.list_clips({})["structuredContent"]["items"][0]
        args = {"candidateId": item["candidateId"], "url": item["urls"][0]}
        self.fetcher.result = FetchResult("TRANSIENT_FAILURE", failure_code="TOTAL_TIMEOUT")
        self.assertEqual(self.adapter.inspect_url(args)["structuredContent"]["status"], "RETRY_LATER")
        with self.assertRaises(ValueError):
            self.adapter.import_source(args)
        self.note["body"] = "http://127.0.0.1/internal"
        item = self.adapter.list_clips({})["structuredContent"]["items"][0]
        unsafe = {"candidateId": item["candidateId"], "url": item["urls"][0]}
        self.assertEqual(self.adapter.inspect_url(unsafe)["structuredContent"]["status"], "BLOCKED_POLICY")
        with self.assertRaises(ValueError):
            self.adapter.import_source(unsafe)
        self.assertFalse((self.vault / "canonical").exists())

    def test_mcp_keeps_clip_tools_and_adds_selected_note_tools(self):
        combined = ChatGPTNotesAdapter(ClipDigestAdapter(self.adapter.notes, self.locator, fetcher=self.fetcher), self.adapter)
        names = [tool["name"] for tool in ClaudeMcpServer(combined).handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]]
        self.assertEqual(names[:4], ["tsuzu_clip_list", "tsuzu_clip_inspect", "tsuzu_clip_import", "tsuzu_clip_reject"])
        self.assertEqual(names[4:], ["tsuzu_note_list", "tsuzu_note_inspect", "tsuzu_note_import", "tsuzu_note_reject"])


if __name__ == "__main__":
    unittest.main()
