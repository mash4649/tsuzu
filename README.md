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

`.codex/hooks.json` registers `UserPromptSubmit` and `Stop` hooks. After you review and trust these project hooks in Codex, each clean user prompt is submitted through the local A3/A4 Core queue and Chronicle; a final assistant message is recorded when Codex supplies it. Chronicle is deliberately partial (`CODEX_HOOK_MESSAGE_ONLY`): it keeps user/assistant roles and turn order, but excludes tools and does not read `transcript_path` because Codex documents that transcript format as unstable. Secrets are persisted body-free. A later decision prompt may receive up to three prior, policy-approved `UNTRUSTED_DATA` excerpts with a body-free trace; secrets, SENSITIVE, and RESTRICTED content are never injected.

The hook never reads `transcript_path`, calls a network service, or performs actions. Set `TSUZU_CODEX_PASSIVE_RECALL=0` before starting Codex to keep automatic capture while disabling proposal context. To share the local Tauri Core and selected Vault, set `TSUZU_CORE_ROOT` to `/Users/mbp/Library/Application Support/TSUZU` and `TSUZU_VAULT_ROOT` to `/Users/mbp/Library/Mobile Documents/com~apple~CloudDocs/TSUZU/Vault` before starting Codex. The first Codex use binds that Core to a body-free project hash and another project is rejected. Leaving `TSUZU_CORE_ROOT` unset preserves the legacy per-project `TSUZU_CODEX_DATA_ROOT` layout. Neither mode migrates or rewrites an existing Vault.

## Apple Notes selected-note import

Select exactly one note in the macOS Notes app, then run the user-initiated command below. It asks macOS for Notes Automation permission if needed, reads only that selection, and passes it through the existing local secret guard and single-writer queue. It never scans accounts, folders, or unselected notes; cancellation, denial, or malformed bridge output makes no Canonical write.

```sh
PYTHONPATH=src python3 -m tsuzu apple-notes-import --queue-root /absolute/core/runtime/queue --control-root /absolute/core/control
```

The receipt summary is body-free. The Canonical Source retains the note title, observed modification time, and a hashed `x-apple-notes://selected/...` locator; the raw Notes identifier is kept only in the body-free import identity hash. Re-run the command for a changed selected note; an identical snapshot is idempotent.

## ChatGPT Clip digest (developer mode)

The separate `chatgpt` MCP host implements the `clip-digest` flow without changing the read-only historical importer above. On an explicit ChatGPT request it lists unprocessed links in Apple Notes `📥Clip`, lets ChatGPT inspect each linked public page through the bounded R1 fetcher, then writes a distilled draft to `<active-vault>/wiki/_inbox`. Only the Note title and link (not the Note body) and fetched public page text are returned to ChatGPT; known credential patterns are withheld. Drafts are not promoted to `wiki/cards`; low-value items can be marked processed without a card. A body-free local receipt prevents repeat work. Apple Notes itself is never edited, consistent with R3.

Run the local stdio server with the same Core paths used by the other TSUZU hosts:

```sh
/absolute/path/to/tsuzu-main/bin/tsuzu-mcp mcp serve --host chatgpt \
  --control-root /absolute/core/control \
  --index-root /absolute/core/index \
  --runtime-root /absolute/core/runtime
```

ChatGPT cannot connect directly to a local MCP process. For private use, connect this stdio command through OpenAI Secure MCP Tunnel and create a Developer Mode custom app in ChatGPT. That requires an OpenAI Platform tunnel, runtime API key, and workspace permissions; TSUZU does not create or store them. Full write-action support is currently plan-gated (Business/Enterprise/Edu beta); Pro connections are read/fetch only. Until the app and tunnel are configured and tested from ChatGPT, this is locally verified MCP functionality, not a completed ChatGPT end-to-end integration.

Ask ChatGPT to list unprocessed `📥Clip` links, inspect each public page, and import useful findings as drafts or reject reviewed low-value links. `tsuzu_clip_list` returns at most 25 candidates; when `truncated` is true, call it again with `cursor` set to `nextCursor` until `truncated` is false. A fresh scan without a cursor includes any new candidates added during that review.
