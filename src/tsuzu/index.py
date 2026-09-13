"""Disposable SQLite/FTS projection rebuilt from Canonical Source (A5)."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

from .capture import SecretScanner
from .deletion import DELETED, NOT_DELETED, UNKNOWN_FAIL_CLOSED, DeletionResolver
from .representation import RepresentationResolver
from .source import SourceValidationError, parse_source, validate_payload, validate_source
from .vault import ActiveVaultLocator


APPLICATION_ID = 0x5453555A
SCHEMA_GENERATION = 2
PROJECTION_VERSION = "c2-1.0"


class IndexCapabilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class IndexHealth:
    status: str
    reason: str = ""


def probe_sqlite() -> None:
    try:
        connection = sqlite3.connect(":memory:")
        connection.execute("PRAGMA trusted_schema=OFF")
        if connection.execute("PRAGMA trusted_schema").fetchone()[0] != 0:
            raise IndexCapabilityError("trusted_schema unavailable")
        connection.execute("CREATE VIRTUAL TABLE temp.__tsuzu_fts_probe USING fts5(x, tokenize='trigram')")
        connection.execute("DROP TABLE temp.__tsuzu_fts_probe")
        connection.execute("BEGIN")
        connection.execute("COMMIT")
    except (sqlite3.Error, IndexError) as exc:
        raise IndexCapabilityError("INDEX_CAPABILITY_UNAVAILABLE") from exc
    finally:
        try:
            connection.close()
        except UnboundLocalError:
            pass


class IndexManager:
    def __init__(
        self,
        index_root: str | os.PathLike[str],
        locator: ActiveVaultLocator,
        *,
        scanner: SecretScanner | None = None,
        deletion_resolver: DeletionResolver | None = None,
        max_text_file_bytes: int = 4 * 1024 * 1024,
    ):
        probe_sqlite()
        self.root = Path(index_root)
        self.locator = locator
        self.scanner = scanner or SecretScanner()
        self.deletion = deletion_resolver or DeletionResolver(locator)
        self.representations = RepresentationResolver(locator, deletion_resolver=self.deletion)
        self.max_text_file_bytes = max_text_file_bytes
        self.path = self.root / "tsuzu.sqlite"
        self.lock_path = self.root / "index.lock"
        self.connection: sqlite3.Connection | None = None
        active_root = self.locator.resolve_active_vault().root_ref.resolve()
        candidate_root = self.root.resolve()
        if candidate_root == active_root or active_root in candidate_root.parents:
            raise IndexCapabilityError("INDEX_MUST_BE_OUTSIDE_VAULT")

    def open(self) -> None:
        if self.root.is_symlink():
            raise IndexCapabilityError("index root is symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink() or self.lock_path.is_symlink():
            raise IndexCapabilityError("index path is symlink")
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA busy_timeout=5000")
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if application_id not in {0, APPLICATION_ID} or user_version not in {0, SCHEMA_GENERATION}:
            connection.close()
            raise IndexCapabilityError("INDEX_SCHEMA_UNSUPPORTED")
        connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version={SCHEMA_GENERATION}")
        self._create_schema(connection)
        expected_meta = {
            "index_contract_version": "1.0.0",
            "index_schema_generation": str(SCHEMA_GENERATION),
            "tokenizer": "trigram",
            "projection_version": PROJECTION_VERSION,
        }
        for key, expected in expected_meta.items():
            actual = connection.execute("SELECT value FROM index_meta WHERE key=?", (key,)).fetchone()
            if actual and actual[0] != expected:
                connection.close()
                raise IndexCapabilityError("INDEX_SCHEMA_UNSUPPORTED")
        self._set_meta(connection)
        connection.commit()
        self.connection = connection

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def health(self) -> IndexHealth:
        try:
            self._require_open()
            result = self.connection.execute("PRAGMA quick_check").fetchone()[0]
            return IndexHealth("HEALTHY" if result == "ok" else "CORRUPT", result)
        except (sqlite3.Error, IndexCapabilityError) as exc:
            return IndexHealth("CORRUPT", str(exc))

    def upsert_source(self, source_id: str) -> str:
        connection = self._require_open()
        projection = self._project(source_id)
        with self._index_lock():
            connection.execute("BEGIN")
            try:
                self._remove_rows(connection, source_id)
                if projection["eligible"]:
                    connection.execute(
                        "INSERT INTO source_index VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        projection["row"],
                    )
                    connection.execute("INSERT INTO source_fts(source_id,name,body) VALUES(?,?,?)", (source_id, projection["name"], projection["body"]))
                    status = "INDEXED"
                else:
                    connection.execute(
                        "INSERT INTO index_exclusion(source_id,source_revision,reason_code,observed_at) VALUES(?,?,?,?)",
                        (source_id, projection.get("revision"), projection["reason"], _now()),
                    )
                    status = "EXCLUDED"
                connection.commit()
                return status
            except Exception:
                connection.rollback()
                raise

    def reconcile(self) -> dict[str, int]:
        handle = self.locator.resolve_active_vault()
        source_root = handle.root_ref / "canonical" / "sources"
        canonical_ids: set[str] = set()
        indexed = excluded = removed = 0
        if source_root.exists() and not source_root.is_symlink():
            for path in sorted(source_root.iterdir(), key=lambda item: item.name):
                if not path.is_dir() or path.is_symlink() or not re.fullmatch(r"[0-9a-f-]{36}", path.name):
                    continue
                canonical_ids.add(path.name)
                status = self.upsert_source(path.name)
                indexed += status == "INDEXED"
                excluded += status == "EXCLUDED"
        connection = self._require_open()
        existing = {row[0] for row in connection.execute("SELECT source_id FROM source_index")}
        existing.update(row[0] for row in connection.execute("SELECT source_id FROM index_exclusion"))
        with self._index_lock():
            connection.execute("BEGIN")
            try:
                for source_id in existing - canonical_ids:
                    self._remove_rows(connection, source_id)
                    removed += 1
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return {"indexed": indexed, "excluded": excluded, "removed": removed}

    def search(self, query: str) -> list[str]:
        connection = self._require_open()
        if not isinstance(query, str) or not query:
            return []
        if len(query) >= 3:
            fts_query = '"' + query.replace('"', '""') + '"'
            rows = connection.execute("SELECT source_id FROM source_fts WHERE source_fts MATCH ?", (fts_query,)).fetchall()
        else:
            rows = connection.execute("SELECT source_id FROM source_fts WHERE name LIKE ? OR body LIKE ?", (f"%{query}%", f"%{query}%")).fetchall()
        return [source_id for row in rows if (source_id := row[0]) and self.deletion.resolve_source(source_id).state == NOT_DELETED]

    def indexed_representation(self, source_id: str) -> tuple[str, str, str | None] | None:
        row = self._require_open().execute(
            "SELECT representation_object_type, representation_object_id, representation_sha256 FROM source_index WHERE source_id=?",
            (source_id,),
        ).fetchone()
        return tuple(row) if row else None

    def full_rebuild(self) -> None:
        self._require_open()
        candidate = self.root / f"tsuzu.rebuild.{uuid.uuid4().hex}.sqlite"
        candidate_connection: sqlite3.Connection | None = None
        try:
            candidate_connection = sqlite3.connect(candidate)
            candidate_connection.execute("PRAGMA journal_mode=DELETE")
            candidate_connection.execute("PRAGMA synchronous=FULL")
            self._create_schema(candidate_connection)
            self._set_meta(candidate_connection)
            self._populate_candidate(candidate_connection)
            if candidate_connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise IndexCapabilityError("candidate integrity check failed")
            candidate_connection.commit()
            candidate_connection.close()
            candidate_connection = None
            with self._index_lock():
                self.close()
                for sidecar in (Path(str(self.path) + "-wal"), Path(str(self.path) + "-shm")):
                    if sidecar.exists():
                        sidecar.unlink()
                os.replace(candidate, self.path)
                self.open()
            self.reconcile()
        finally:
            if candidate_connection is not None:
                candidate_connection.close()
            if candidate.exists():
                candidate.unlink()

    def discard_and_rebuild(self) -> None:
        self.close()
        for path in (self.path, Path(str(self.path) + "-wal"), Path(str(self.path) + "-shm")):
            if path.exists() and not path.is_symlink():
                path.unlink()
        self.open()
        self.full_rebuild()

    def _project(self, source_id: str) -> dict[str, object]:
        try:
            if not isinstance(source_id, str):
                return {"eligible": False, "revision": None, "reason": "CORRUPT_CANONICAL"}
            parsed_id = uuid.UUID(source_id)
            if parsed_id.version != 4 or str(parsed_id) != source_id:
                return {"eligible": False, "revision": None, "reason": "CORRUPT_CANONICAL"}
            handle = self.locator.resolve_active_vault()
            path = handle.root_ref / "canonical" / "sources" / source_id
            if path.is_symlink() or (path / "source.md").is_symlink() or (path / "payload").is_symlink() or (path / "payload" / "original").is_symlink():
                return {"eligible": False, "revision": None, "reason": "CORRUPT_CANONICAL"}
            deletion = self.deletion.resolve_source(source_id)
            if deletion.state == DELETED:
                reason = "DELETION_LEDGER" if deletion.reason == "DELETION_LEDGER" else "TOMBSTONED"
                return {"eligible": False, "revision": None, "reason": reason}
            if deletion.state == UNKNOWN_FAIL_CLOSED:
                return {"eligible": False, "revision": None, "reason": deletion.reason or "DELETION_LEDGER_UNAVAILABLE"}
            manifest = parse_source((path / "source.md").read_text())
            validate_source(manifest, expected_object_id=source_id)
            payload = (path / "payload" / "original").read_bytes()
            if not validate_payload(manifest, payload):
                return {"eligible": False, "revision": manifest["revision"], "reason": "CORRUPT_CANONICAL"}
            source = manifest["source"]
            if manifest["deletion"]["state"] == "TOMBSTONED":
                return {"eligible": False, "revision": manifest["revision"], "reason": "TOMBSTONED"}
            if manifest["sensitivity"]["level"] == "RESTRICTED":
                return {"eligible": False, "revision": manifest["revision"], "reason": "RESTRICTED"}
            scan = self.scanner.scan_bytes(payload)
            if scan.outcome != "CLEAR":
                return {"eligible": False, "revision": manifest["revision"], "reason": "SECRET_RECLASSIFIED"}
            representation = self.representations.resolve(source_id)
            if representation is None:
                return {"eligible": False, "revision": manifest["revision"], "reason": "REPRESENTATION_UNAVAILABLE"}
            projected = self.representations.project(representation)
            name = source["original_name"] or (payload.decode("utf-8") if source["kind"] == "URL" else "") or ""
            body = projected.text
            mode = "BODY" if projected.status == "READY" else "METADATA_ONLY"
            reason = None if projected.status == "READY" else "UNSUPPORTED_BODY_PROJECTION" if projected.status == "METADATA_ONLY" else projected.status
            fingerprint = _fingerprint(manifest, mode, representation, projected)
            row = (
                source_id,
                manifest["revision"],
                manifest["schema_version"],
                source["kind"],
                source["media_type"],
                manifest["scope"]["scope_type"],
                manifest["scope"]["scope_id"],
                manifest["sensitivity"]["level"],
                manifest["deletion"]["state"],
                source["captured_at"],
                source["payload_sha256"],
                source["payload_bytes"],
                name,
                f"canonical/sources/{source_id}",
                mode,
                reason,
                hashlib.sha256(body.encode()).hexdigest() if body else None,
                fingerprint,
                _now(),
                representation.object_type,
                representation.object_id,
                representation.content_sha256,
                representation.fidelity,
                projected.extractor_id,
                projected.extractor_version,
            )
            return {"eligible": True, "revision": manifest["revision"], "row": row, "name": name, "body": body}
        except (OSError, ValueError, SourceValidationError, KeyError):
            return {"eligible": False, "revision": None, "reason": "CORRUPT_CANONICAL"}

    def _populate_candidate(self, connection: sqlite3.Connection) -> None:
        handle = self.locator.resolve_active_vault()
        source_root = handle.root_ref / "canonical" / "sources"
        if not source_root.exists():
            return
        for path in sorted(source_root.iterdir(), key=lambda item: item.name):
            if not path.is_dir() or path.is_symlink():
                continue
            projection = self._project(path.name)
            self._remove_rows(connection, path.name)
            if projection["eligible"]:
                connection.execute("INSERT INTO source_index VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", projection["row"])
                connection.execute("INSERT INTO source_fts(source_id,name,body) VALUES(?,?,?)", (path.name, projection["name"], projection["body"]))
            else:
                connection.execute("INSERT INTO index_exclusion(source_id,source_revision,reason_code,observed_at) VALUES(?,?,?,?)", (path.name, projection.get("revision"), projection["reason"], _now()))
        connection.commit()

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS index_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS source_index(
              source_id TEXT PRIMARY KEY, source_revision INTEGER NOT NULL, source_schema_version TEXT NOT NULL,
              source_kind TEXT NOT NULL, media_type TEXT NOT NULL, scope_type TEXT NOT NULL, scope_id TEXT,
              sensitivity TEXT NOT NULL, deletion_state TEXT NOT NULL, captured_at TEXT NOT NULL,
              payload_sha256 TEXT NOT NULL, payload_bytes INTEGER NOT NULL, original_name TEXT,
              canonical_relpath TEXT NOT NULL, projection_mode TEXT NOT NULL, projection_reason TEXT,
              index_text_sha256 TEXT, index_fingerprint TEXT NOT NULL, indexed_at TEXT NOT NULL,
              representation_object_type TEXT NOT NULL, representation_object_id TEXT NOT NULL,
              representation_sha256 TEXT, representation_fidelity TEXT NOT NULL,
              extractor_id TEXT, extractor_version TEXT
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS source_fts USING fts5(source_id UNINDEXED, name, body, tokenize='trigram');
            CREATE TABLE IF NOT EXISTS index_exclusion(source_id TEXT PRIMARY KEY, source_revision INTEGER, reason_code TEXT NOT NULL, observed_at TEXT NOT NULL);
            """
        )

    def _set_meta(self, connection: sqlite3.Connection) -> None:
        handle = self.locator.resolve_active_vault()
        values = {
            "index_contract_version": "1.0.0",
            "index_schema_generation": str(SCHEMA_GENERATION),
            "tokenizer": "trigram",
            "projection_version": PROJECTION_VERSION,
            "vault_locator_hash": hashlib.sha256(f"{handle.vault_id}:{handle.generation}".encode()).hexdigest(),
            "generation_id": str(handle.generation),
            "built_at": _now(),
        }
        connection.executemany("INSERT OR REPLACE INTO index_meta(key,value) VALUES(?,?)", values.items())

    def _remove_rows(self, connection: sqlite3.Connection, source_id: str) -> None:
        connection.execute("DELETE FROM source_fts WHERE source_id=?", (source_id,))
        connection.execute("DELETE FROM source_index WHERE source_id=?", (source_id,))
        connection.execute("DELETE FROM index_exclusion WHERE source_id=?", (source_id,))

    def _require_open(self) -> sqlite3.Connection:
        if self.connection is None:
            self.open()
        return self.connection

    @contextlib.contextmanager
    def _index_lock(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _fingerprint(manifest: dict[str, object], projection_mode: str, representation=None, projected=None) -> str:
    source = manifest["source"]
    value = {
        "object_id": manifest["object_id"],
        "revision": manifest["revision"],
        "schema_version": manifest["schema_version"],
        "payload_sha256": source["payload_sha256"],
        "kind": source["kind"],
        "media_type": source["media_type"],
        "scope": manifest["scope"],
        "sensitivity": manifest["sensitivity"],
        "deletion": manifest["deletion"],
        "projection_version": PROJECTION_VERSION,
        "projection_mode": projection_mode,
        "representation": None if representation is None else (representation.object_type, representation.object_id, representation.content_sha256, representation.fidelity),
        "extractor": None if projected is None else (projected.extractor_id, projected.extractor_version),
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
