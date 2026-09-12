# ADR-009: Generic deletion facts and best-effort purge

- Status: Accepted
- Date: 2026-09-12
- Scope: C3 implementation choice

## Decision

C3 extends the A6 ledger key to `(object_type, object_id)`. Generic records use
the v2 body-free schema and become effective immediately after atomic commit.
C1 checks that ledger before any revision update, so a later update cannot
resurrect a deleted object.

Payload purge is a separate, best-effort operation. A purge failure, missing
payload, or unsafe symlink never reverses the ledger fact and is reported as a
non-success status. It is not a forensic-erasure claim.

## Consequences

- Source keeps its A6 v1 record while new persistent object types use v2.
- Corrupt or unavailable ledger state excludes the target from further use.
- Downstream owners can reuse the same resolver without new deletion truth.
