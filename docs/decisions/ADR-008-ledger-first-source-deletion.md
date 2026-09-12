# ADR-008: Ledger-first Source deletion

- Status: Accepted
- Date: 2026-09-12
- Scope: A6 implementation choice

## Decision

A6 writes and validates one immutable, body-free deletion ledger record before
changing a Source manifest or its derived index. The resolver checks that ledger
first and returns `UNKNOWN_FAIL_CLOSED` for inaccessible or invalid records.
The later manifest tombstone is a convergence step, not the deletion authority.

## Consequences

- A stale `LIVE` Source cannot return to index search while its ledger survives.
- Index invalidation or manifest-update failures leave deletion logically active.
- A6 does not claim forensic erasure or remove the raw payload; C3 owns any
  best-effort active-store purge policy.
