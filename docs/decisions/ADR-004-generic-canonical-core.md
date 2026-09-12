# ADR-004: Reuse A2's single writer authority for C1 generic objects

- Status: Accepted
- Date: 2026-09-12
- Scope: C1 implementation choice

## Decision

C1 uses the same C0-resolved Vault and `system/write.lock` as A2. Object types
must be registered before generic persistence; `SOURCE` remains routed to its
A1/A2 specialized writer. Generic objects use
`canonical/objects/<object_type>/<object_id>/object.md` and an optional raw
payload, with body-free idempotency receipts under `system`.

## Consequences

- A2 and C1 cannot silently create competing mutable writer authorities.
- Owner contracts provide object meaning and patch allowlists; C1 supplies
  envelope, revision, atomicity, and replay handling.
- Derived/object-specific semantics remain outside this core.
