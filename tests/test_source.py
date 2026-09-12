import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tsuzu.source import (
    SourceValidationError,
    create_source,
    parse_source,
    serialize_source,
    update_source_metadata,
    validate_payload,
    validate_source,
)


class SourceSchemaTests(unittest.TestCase):
    def test_golden_fixtures_validate(self):
        fixtures = Path(__file__).parent / "fixtures"
        for name in ("source_text", "source_url", "source_file"):
            with self.subTest(name=name):
                directory = fixtures / name
                manifest = parse_source((directory / "source.md").read_text())
                validate_source(manifest)
                self.assertTrue(validate_payload(manifest, (directory / "payload" / "original").read_bytes()))

    def test_text_url_file_round_trip(self):
        cases = (
            ("TEXT", "LOCAL_TEXT", "hello\n".encode(), {}),
            ("URL", "LOCAL_URL", b"https://example.com/a?x=1", {}),
            (
                "FILE",
                "LOCAL_FILE",
                b"\x00\x01file",
                {"original_name": "sample.bin", "origin_locator": {"type": "PATH", "value": "sample.bin"}},
            ),
        )
        for kind, method, payload, extra in cases:
            with self.subTest(kind=kind):
                source = create_source(payload, kind=kind, capture_method=method, **extra)
                validate_source(source)
                self.assertEqual(parse_source(serialize_source(source)), source)
                self.assertTrue(validate_payload(source, payload))

    def test_text_preserves_bytes_without_normalization(self):
        payload = "  NFD e\u0301\r\n".encode("utf-8")
        source = create_source(payload, kind="TEXT", capture_method="LOCAL_TEXT")
        self.assertEqual(source["source"]["payload_bytes"], len(payload))
        self.assertEqual(source["source"]["payload_sha256"], hashlib.sha256(payload).hexdigest())

    def test_duplicate_capture_gets_new_uuid(self):
        first = create_source(b"same", kind="TEXT", capture_method="LOCAL_TEXT")
        second = create_source(b"same", kind="TEXT", capture_method="LOCAL_TEXT")
        self.assertNotEqual(first["object_id"], second["object_id"])
        self.assertEqual(first["source"]["payload_sha256"], second["source"]["payload_sha256"])

    def test_missing_envelope_fields_and_unknown_schema_fail(self):
        source = create_source(b"ok", kind="TEXT", capture_method="LOCAL_TEXT")
        for field in ("object_id", "object_type", "schema_version", "created_at", "updated_at", "revision", "scope", "provenance", "trust", "sensitivity", "temporal", "deletion"):
            with self.subTest(field=field):
                candidate = json.loads(json.dumps(source))
                del candidate[field]
                with self.assertRaises(SourceValidationError):
                    validate_source(candidate)
        unknown = json.loads(json.dumps(source))
        unknown["schema_version"] = "9.9.9"
        with self.assertRaises(SourceValidationError):
            validate_source(unknown)

    def test_invalid_enum_url_and_derived_field_fail_closed(self):
        source = create_source(b"https://example.com", kind="URL", capture_method="LOCAL_URL")
        bad_kind = json.loads(json.dumps(source))
        bad_kind["source"]["kind"] = "HTML"
        with self.assertRaises(SourceValidationError):
            validate_source(bad_kind)
        with self.assertRaises(SourceValidationError):
            create_source(b"not-a-url", kind="URL", capture_method="LOCAL_URL")
        with self.assertRaises(SourceValidationError):
            create_source("not-bytes", kind="FILE", capture_method="LOCAL_FILE")
        bad_media = json.loads(json.dumps(source))
        bad_media["source"]["media_type"] = "application/json"
        with self.assertRaises(SourceValidationError):
            validate_source(bad_media)
        derived = json.loads(json.dumps(source))
        derived["summary"] = "AI text"
        with self.assertRaises(SourceValidationError):
            validate_source(derived)

    def test_tamper_missing_and_object_identity_are_detected(self):
        source = create_source(b"original", kind="TEXT", capture_method="LOCAL_TEXT")
        self.assertFalse(validate_payload(source, b"changed"))
        self.assertFalse(validate_payload(source, None))
        with self.assertRaises(SourceValidationError):
            validate_source(source, expected_object_id="00000000-0000-4000-8000-000000000000")

    def test_revision_conflict_requires_expected_revision(self):
        source = create_source(b"ok", kind="TEXT", capture_method="LOCAL_TEXT")
        updated = update_source_metadata(source, expected_revision=1, sensitivity="SENSITIVE")
        self.assertEqual(updated["revision"], 2)
        self.assertEqual(updated["sensitivity"]["level"], "SENSITIVE")
        with self.assertRaises(SourceValidationError):
            update_source_metadata(updated, expected_revision=1, sensitivity="PUBLIC")
        with self.assertRaises(SourceValidationError):
            update_source_metadata(updated, expected_revision=True, sensitivity="PUBLIC")
        with self.assertRaises(SourceValidationError):
            update_source_metadata(source, expected_revision=1, payload=b"changed")

    def test_manifest_has_no_markdown_body_and_file_copy_is_independent(self):
        source = create_source(b"file", kind="FILE", capture_method="LOCAL_FILE", original_name="a.txt")
        encoded = serialize_source(source)
        self.assertTrue(encoded.startswith("---\n"))
        self.assertTrue(encoded.endswith("---\n"))
        self.assertNotIn("summary", encoded)
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "a.txt"
            original.write_bytes(b"file")
            payload = original.read_bytes()
            original.unlink()
            self.assertTrue(validate_payload(source, payload))


if __name__ == "__main__":
    unittest.main()
