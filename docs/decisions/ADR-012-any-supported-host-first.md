# ADR-012: Any supported host may establish the first recall baseline

- Status: Accepted
- Date: 2026-09-13
- Scope: P0 host sequencing

## Decision

P0 does not require Claude Code to be the first verified Host. Codex, Claude
Code, or Cursor may establish the first Host baseline when its current runtime
can prove the same A7/A8 egress boundary, explicit per-call user approval, and
body-free trace requirements.

The Claude-specific A10 Host Gate remains deferred until its subscription and
login are available. It is not a prerequisite for capture, acquisition, or
historical-import work. Claude/Codex/Cursor parity remains a later expansion
requirement; no Slice A or cross-host parity claim is made until an eligible
Host-specific gate passes.

## Consequences

- Core tasks R1, R3, and R4 may proceed without a Claude login.
- A new host-neutral gate records which one Host proved the baseline and the
  exact runtime evidence.
- An unverified Host cannot authorize egress or be treated as parity evidence.
