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
- **Codex:** a host adapter. Its automatic capture and recall use the Python
  Core path; it does not create a separate Canonical store.
- **Tauri:** a desktop UI and native boundary. Until its Core adapter exists,
  its local text capture is an explicitly non-Canonical capture draft. It must
  not write `canonical/`, claim indexed/recallable state, or silently import
  existing Vaults.
- **Future Tauri integration:** submit a typed ingress request to the Python
  Core/queue, then let the existing single writer materialize Canonical state.

## Consequences

- There is one authority for Canonical mutation and recovery.
- Tauri drafts are durable local input, not TSUZU memory; they require a
  follow-up Core adapter before they become Canonical.
- Existing app-local or Python data is not deleted, overwritten, or migrated by
  this decision.
- A future TypeScript Core migration may replace the Python implementation,
  but it must replace the owner as one atomic ownership decision rather than
  adding a second writer.

## Verification boundary

The owner is considered preserved only when every new ingress path proves that
it reaches the existing single writer and that close/reopen, idempotency,
deletion, and recovery remain covered. A passing UI write alone is not proof of
Canonical ownership.
