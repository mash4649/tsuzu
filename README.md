# TSUZU

TSUZU is a local-first runtime for grounded capture, recall, and later Derived processing.

## Quick start

This baseline requires Python 3.12 or newer and has no third-party runtime dependencies.

```sh
make test
```

The implementation starts with the Python standard library and SQLite. Contract-specific functionality is added in the dependency order recorded in Beads.

## Layout

- `src/tsuzu/` — runtime package
- `tests/` — deterministic tests
- `docs/decisions/` — implementation-time architecture decisions
- `docs/20260909/TSUZU_P0_Final_Documentation_20260909_v2_1/` — product and contract source of truth

See [ADR-001](docs/decisions/ADR-001-python-stdlib-sqlite.md) for the implementation baseline decision.

## Canonical ownership

Mac TSUZU Core is the sole mutable Canonical writer. In the current baseline,
that means Python `AtomicSourceWriter`/`SingleWriterWorker` owns the active
Vault; Codex is an adapter over it. The Tauri shell's local text capture is a
non-Canonical draft until `tsuzu desktop-ingress` gives it a Core receipt. It
must not be treated as recallable TSUZU memory before that receipt exists.

## Codex automatic memory and proposal

`.codex/hooks.json` registers a `UserPromptSubmit` hook. After you review and trust that hook in Codex, each clean user prompt is submitted through the local A3/A4 Core queue. A later decision prompt may receive up to three prior, policy-approved `UNTRUSTED_DATA` excerpts with a body-free trace; secrets, SENSITIVE, and RESTRICTED content are never injected.

The hook never reads `transcript_path`, calls a network service, or performs actions. Set `TSUZU_CODEX_PASSIVE_RECALL=0` before starting Codex to keep automatic capture while disabling proposal context. To share one selected Core with Tauri, set `TSUZU_CORE_ROOT` to an absolute, per-project local directory; its `control`, `queue`, `index`, and `runtime` paths are the values passed to `tsuzu desktop-ingress`. The first Codex use binds that root to a body-free project hash and another project is rejected. Leaving it unset preserves the legacy per-project `TSUZU_CODEX_DATA_ROOT` layout. Neither mode migrates or rewrites an existing Vault.
