# ADR-011: Trace before context egress

- Status: Accepted
- Date: 2026-09-12
- Scope: A8 implementation choice

## Decision

A8 rereads only A7-approved Canonical Sources, rejects changed or deleted
revisions, and constructs deterministic bounded excerpts. It writes a body-free
technical context trace before returning a bundle; a trace failure returns no
bundle.

## Consequences

- FTS content is never the final context body.
- Every delivered item is `UNTRUSTED_DATA` with a Canonical source reference.
- Runtime traces contain hashes and counts, not query or excerpt bodies.
