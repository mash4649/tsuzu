import json
import tempfile
import unittest
from pathlib import Path

from tsuzu.acquisition import AcquisitionService, FetchResult
from tsuzu.context import ContextBundleBuilder
from tsuzu.index import IndexManager
from tsuzu.retrieval import RetrievalRequest, RetrievalService
from tsuzu.representation import EffectiveRepresentation, PdfTextExtractor, RepresentationResolver
from tsuzu.vault import ActiveVaultLocator
from tsuzu.writer import AtomicSourceWriter


class _Adapter:
    adapter_id = "fixture"
    adapter_version = "1"

    def fetch(self, request):
        return FetchResult.success(
            final_url=request.url,
            body=b"<html><head><script>never-index-this</script></head><body>visible acquisition body</body></html>",
            media_type="text/html",
        )


class RepresentationTests(unittest.TestCase):
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

    def test_url_version_html_is_indexed_revalidated_and_traced_without_scripts(self):
        source_id = "11111111-1111-4111-8111-111111111111"
        self.writer.create_source("https://public.test/article", kind="URL", capture_method="LOCAL_URL", object_id=source_id)
        acquired = AcquisitionService(self.locator, resolver=lambda host: ["8.8.8.8"]).acquire(source_id, _Adapter())
        self.assertEqual(acquired.status, "ACQUIRED")
        self.assertEqual(self.index.upsert_source(source_id), "INDEXED")
        self.assertEqual(self.index.search("visible acquisition"), [source_id])
        self.assertEqual(self.index.search("never-index-this"), [])

        recalled = RetrievalService(self.index).retrieve(RetrievalRequest("22222222-2222-4222-8222-222222222222", "visible acquisition", "local_test"))
        self.assertEqual(recalled.status, "OK")
        candidate = recalled.approved[0]
        self.assertEqual(candidate.representation_object_type, "SOURCE_VERSION")
        self.assertEqual(candidate.representation_object_id, acquired.source_version_id)
        self.assertEqual(candidate.content, "visible acquisition body")

        built = ContextBundleBuilder(self.locator, Path(self.temp.name) / "runtime").build(recalled)
        self.assertEqual(built.status, "APPROVED_CONTEXT_BUNDLE")
        trace = json.loads((Path(self.temp.name) / "runtime" / "context-traces" / f"{built.bundle.context_trace_id}.json").read_text())
        self.assertEqual(trace["source_refs"][0]["representation"]["object_id"], acquired.source_version_id)

    def test_pdf_without_registered_extractor_is_metadata_only(self):
        representation = EffectiveRepresentation("11111111-1111-4111-8111-111111111111", "SOURCE_VERSION", "SOURCE_VERSION", "22222222-2222-4222-8222-222222222222", b"%PDF", "0" * 64, "application/pdf", "ORIGIN_RESPONSE", "PERSONAL", "GLOBAL", None, {})
        self.assertEqual(RepresentationResolver(self.locator).project(representation).status, "EXTRACTION_UNAVAILABLE")
        projected = RepresentationResolver(self.locator, pdf_extractor=PdfTextExtractor("fixture-pdf", "1", lambda payload: "adapter text")).project(representation)
        self.assertEqual((projected.status, projected.extractor_id, projected.extractor_version), ("READY", "fixture-pdf", "1"))


if __name__ == "__main__":
    unittest.main()
