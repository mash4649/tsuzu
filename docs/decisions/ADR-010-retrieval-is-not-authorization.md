# ADR-010: SQLite retrieval is not authorization

- Status: Accepted
- Date: 2026-09-12
- Scope: A7 implementation choice

## Decision

A7 uses A5 only to generate a bounded candidate list. Every candidate is read
again from Canonical storage and evaluated in a fixed order: deletion, scope,
destination/capability, sensitivity, current Secret Guard, and content mode.
Unknown state denies. `claude_code` is a registered `TRUSTED_EXTERNAL`
destination, so SENSITIVE content remains denied with no request override.

## Consequences

- Stale FTS rows cannot bypass a later deletion or policy change.
- Returned content is marked `UNTRUSTED_DATA`; it never gains instruction
  authority merely because it was recalled.
- Policy metadata is body-free and A8 receives only approved candidates.
