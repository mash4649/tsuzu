"""C2 deterministic effective Source representation and safe text projection."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Callable

from .canonical import CanonicalStore, ObjectRegistration, ObjectRegistry, _parse_manifest
from .deletion import NOT_DELETED, DeletionResolver
from .source import SourceValidationError, parse_source, validate_payload
from .vault import ActiveVaultLocator
from .writer import AtomicSourceWriter


RESOLVER_VERSION = "c2-1.0"
_SENSITIVITY = {"PUBLIC": 0, "PERSONAL": 1, "SENSITIVE": 2, "RESTRICTED": 3}


@dataclass(frozen=True)
class EffectiveRepresentation:
    root_source_id: str
    kind: str
    object_type: str
    object_id: str
    payload: bytes | None
    content_sha256: str | None
    media_type: str
    fidelity: str
    sensitivity: str
    scope_type: str
    scope_id: str | None
    root_manifest: dict[str, object]


@dataclass(frozen=True)
class TextProjection:
    status: str
    text: str = ""
    extractor_id: str | None = None
    extractor_version: str | None = None


@dataclass(frozen=True)
class PdfTextExtractor:
    extractor_id: str
    extractor_version: str
    extract: Callable[[bytes], str]


class RepresentationResolver:
    def __init__(self, locator: ActiveVaultLocator, *, deletion_resolver: DeletionResolver | None = None, pdf_extractor: PdfTextExtractor | None = None):
        self.locator = locator
        self.deletion = deletion_resolver or DeletionResolver(locator)
        self.pdf_extractor = pdf_extractor
        registry = ObjectRegistry()
        registry.register(ObjectRegistration("SOURCE_VERSION", "CANONICAL", "IMMUTABLE", "PAYLOAD", "R1"))
        self.store = CanonicalStore(locator, registry)

    def resolve(self, source_id: str) -> EffectiveRepresentation | None:
        root = self._root(source_id)
        if root is None or self.deletion.resolve_source(source_id).state != NOT_DELETED:
            return None
        manifest, payload = root
        source = manifest["source"]
        if source["kind"] == "URL":
            return self._current_version(source_id, manifest) or self._locator(source_id, manifest)
        return EffectiveRepresentation(source_id, "ROOT_PAYLOAD", "SOURCE", source_id, payload, source["payload_sha256"], source["media_type"], "DIRECT_USER", manifest["sensitivity"]["level"], manifest["scope"]["scope_type"], manifest["scope"]["scope_id"], manifest)

    def project(self, representation: EffectiveRepresentation) -> TextProjection:
        if representation.kind == "LOCATOR_ONLY" or representation.payload is None:
            return TextProjection("METADATA_ONLY")
        if representation.media_type in {"text/plain", "text/markdown", "application/json"}:
            try:
                return TextProjection("READY", _normalize(representation.payload.decode("utf-8")), "utf8", "1")
            except UnicodeDecodeError:
                return TextProjection("METADATA_ONLY")
        if representation.media_type == "text/html":
            try:
                parser = _VisibleText()
                parser.feed(representation.payload.decode("utf-8"))
                parser.close()
                return TextProjection("READY", _normalize(" ".join(parser.parts)), "html-visible-text", "1")
            except (UnicodeDecodeError, ValueError):
                return TextProjection("METADATA_ONLY")
        if representation.media_type == "application/pdf":
            if self.pdf_extractor is None:
                return TextProjection("EXTRACTION_UNAVAILABLE")
            try:
                text = self.pdf_extractor.extract(representation.payload)
                if not isinstance(text, str):
                    return TextProjection("EXTRACTION_UNAVAILABLE")
                return TextProjection("READY", _normalize(text), self.pdf_extractor.extractor_id, self.pdf_extractor.extractor_version)
            except Exception:
                return TextProjection("EXTRACTION_UNAVAILABLE")
        return TextProjection("METADATA_ONLY")

    def _root(self, source_id: str):
        inspected = AtomicSourceWriter(self.locator).inspect_source(source_id)
        if inspected.status != "VALID" or inspected.path is None:
            return None
        try:
            manifest = parse_source((inspected.path / "source.md").read_text())
            payload = (inspected.path / "payload" / "original").read_bytes()
            return (manifest, payload) if validate_payload(manifest, payload) else None
        except (OSError, SourceValidationError):
            return None

    def _current_version(self, source_id: str, root: dict[str, object]) -> EffectiveRepresentation | None:
        objects = self.locator.resolve_active_vault().root_ref / "canonical" / "objects" / "SOURCE_VERSION"
        if objects.is_symlink() or not objects.exists():
            return None
        candidates = []
        for path in objects.iterdir():
            if not path.is_dir() or path.is_symlink():
                continue
            checked = self.store.inspect_canonical("SOURCE_VERSION", path.name)
            if checked.status != "VALID" or checked.path is None or self.deletion.resolve("SOURCE_VERSION", path.name).state != NOT_DELETED:
                continue
            try:
                manifest = _parse_manifest((checked.path / "object.md").read_text())
                acquisition = manifest["acquisition"]
                if manifest.get("parent_source_id") != source_id or acquisition.get("http_status") not in range(200, 300):
                    continue
                sensitivity = manifest["sensitivity"]["level"]
                if sensitivity not in _SENSITIVITY or _SENSITIVITY[sensitivity] < _SENSITIVITY[root["sensitivity"]["level"]]:
                    continue
                payload = (checked.path / "payload" / "original").read_bytes()
                details = manifest["payload"]
                if hashlib.sha256(payload).hexdigest() != details["sha256"] or len(payload) != details["bytes"]:
                    continue
                candidates.append((manifest["created_at"], path.name, manifest, payload))
            except (OSError, KeyError, TypeError, SourceValidationError):
                continue
        if not candidates:
            return None
        _, object_id, manifest, payload = max(candidates)
        acquisition = manifest["acquisition"]
        return EffectiveRepresentation(source_id, "SOURCE_VERSION", "SOURCE_VERSION", object_id, payload, manifest["payload"]["sha256"], acquisition["media_type"], acquisition["fidelity"], manifest["sensitivity"]["level"], root["scope"]["scope_type"], root["scope"]["scope_id"], root)

    @staticmethod
    def _locator(source_id: str, root: dict[str, object]) -> EffectiveRepresentation:
        source = root["source"]
        return EffectiveRepresentation(source_id, "LOCATOR_ONLY", "SOURCE", source_id, None, None, source["media_type"], "LOCATOR_ONLY", root["sensitivity"]["level"], root["scope"]["scope_type"], root["scope"]["scope_id"], root)


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "template", "noscript"}:
            self._ignored += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "template", "noscript"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data):
        if not self._ignored:
            self.parts.append(data)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
