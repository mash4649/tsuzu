# ADR-013: Use the Claude Agent SDK exact-session reader for B1

- Status: Accepted
- Date: 2026-09-23
- Scope: B1 implementation choice

## Decision

B1 uses `claude-agent-sdk`'s `get_session_info(session_id, directory)` and
`get_session_messages(session_id, directory)` only after an exact
`CLAUDE_CODE × absolute workspace × session UUID` allowlist match and verified
C6 capture capabilities. It does not enumerate sessions or read transcript
paths directly. User, Assistant, and tool-result messages remain distinct;
message order is the SDK return order. Credentials become body-free
`EXCLUDED_RESTRICTED` Chronicle records.

## Consequences

- This requires Claude Code >= 2.1.269 and `claude-agent-sdk` >= 0.2.150.
- Chronicle is immutable Canonical observation only; it creates no derived
  decision, preference, candidate, promotion, or telemetry record.
- An unavailable SDK, unknown scope, or malformed record fails closed.
