# ADR-008: Mac TSUZU Core is the sole Canonical writer

## Status

Accepted

## Context

TSUZU has three current surfaces: the Python runtime, the Codex host hook, and
the Tauri desktop shell. The P0 contract requires one mutable Canonical writer;
an adapter, queue, or UI must not become a second writer.

The Python runtime already owns the verified A2/C1 writer, worker, deletion,
index, recovery, and host-adapter paths. The Tauri C2 slice currently persists
an app-local source-shaped object, but it has no shared worker, retrieval, or
recovery connection to that runtime.

## Decision

- **Canonical owner:** Mac TSUZU Core.
- **Current implementation of that owner:** Python
  `AtomicSourceWriter`/`SingleWriterWorker` over the active Vault.
- **Codex:** a host adapter. Its automatic capture submits a typed
  `CaptureRequest(CODEX_USER_PROMPT)` to A3 and lets A4 materialize it; recall
  uses the same Python Core path. It does not call A2 or create a separate
  Canonical store.
- **Tauri:** a desktop UI and native boundary. It persists an explicitly
  non-Canonical capture draft and must not write `canonical/` or claim
  indexed/recallable state before a Core receipt.
- **Tauri Core adapter:** `tsuzu desktop-ingress` validates that app-local draft
  as untrusted input, submits `CaptureRequest(LOCAL_TEXT)` to the existing
  Python queue, and lets the existing single writer materialize and index it.
  The receipt is written only after Core commit. The Tauri shell does not invoke
  Python directly and has no shell or network permission.

## Consequences

- There is one authority for Canonical mutation and recovery.
- Tauri drafts are durable local input, not TSUZU memory; they become recallable
  only after the Core receipt is present.
- Existing app-local or Python data is not deleted, overwritten, or migrated by
  this decision.
- `TSUZU_CORE_ROOT` selects one Core root (`control`, `queue`, `index`, and
  `runtime`) for a configured project. The hook binds that root to a
  body-free project hash and rejects another Codex project. It initializes only
  an empty selected root; it never discovers, rewrites, or migrates a legacy
  Vault.
- A future TypeScript Core migration may replace the Python implementation,
  but it must replace the owner as one atomic ownership decision rather than
  adding a second writer.

## Verification boundary

The owner is considered preserved only when every new ingress path proves that
it reaches the existing single writer and that close/reopen, idempotency,
deletion, and recovery remain covered. A passing UI write alone is not proof of
Canonical ownership.
