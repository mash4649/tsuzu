# ADR-007: Disposable SQLite/FTS projection

- Status: Accepted
- Date: 2026-09-12
- Scope: A5 implementation choice

## Decision

A5 owns a SQLite database outside the Canonical Vault. It requires SQLite
transactions, `trusted_schema=OFF`, and the FTS5 `trigram` tokenizer at runtime.
Only valid, live, non-restricted Sources that pass the current Secret Guard are
projected. Text and URL payloads are indexed exactly as UTF-8; unsupported or
oversize file bodies remain metadata-only.

Incremental updates use one transaction and an index-only lock, so a failed
projection cannot roll back Canonical data. Full rebuilds create a side-by-side
candidate, run `integrity_check`, atomically replace the active database, and
reconcile against the current Vault. Schema or capability mismatches are
rejected instead of silently migrated.

## Consequences

- SQLite/FTS can be deleted and rebuilt without treating it as authority.
- Japanese substring search works without a third-party tokenizer.
- Index failures leave Canonical success intact and are recoverable by reconcile.
