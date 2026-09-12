# ADR-005: Keep A3 capture jobs outside Canonical Vault

- Status: Accepted
- Date: 2026-09-12
- Scope: A3 implementation choice

## Decision

A3 accepts validated TEXT, URL, and regular FILE inputs only after a local,
deterministic ruleset scan. CLEAR inputs are copied into an atomic runtime
queue directory outside the Canonical Vault; A4 will materialize them through
A2. FILE scanning and copying use the same open handle. Secret values are never
returned in results or stored in guard metadata.

## Consequences

- A3 acceptance means durable pending work, not Canonical or indexed state.
- Strong credential signals are rejected before any queue copy is made.
- Queue storage is runtime state and can be retried/cleaned by A4 without
  becoming a second Canonical writer.
- The MVP scanner is intentionally local and high-confidence; egress gates
  must provide later defense in depth.
