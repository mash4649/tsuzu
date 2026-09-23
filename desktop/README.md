# TSUZU desktop shell

This directory is the first Tauri v2 / React / Vite / TypeScript migration slice.

Architecture: `React UI -> TypeScript application -> Tauri adapter -> Rust command`.

The Mac TSUZU Core is the sole mutable Canonical writer. In this migration slice,
that owner is the existing Python `AtomicSourceWriter`/`SingleWriterWorker` path.
The Tauri UI can persist a local **capture draft** under its app-local directory,
but that draft is not Canonical, indexed, or recallable TSUZU memory. It becomes
a SOURCE only when the Python Core writes `core-receipt.json` after its existing
A3 queue and A4 single writer commit it.

The only native command is `runtime_health`; `build.rs` grants its
`allow-runtime-health` permission explicitly. Filesystem access is limited to
the app-local draft area. There is no shell, network, or external-content access.

## Commands

```sh
pnpm install
pnpm build
pnpm tauri dev
pnpm tauri build --bundles app
```

## Import a draft into the selected Core

From the repository root, set the same absolute `TSUZU_CORE_ROOT` used by the
Codex hook, then use its `control`, `queue`, and `index` paths. The command
deliberately requires those paths: it never creates, guesses, or migrates a
second Vault.

```sh
PYTHONPATH=src python3 -m tsuzu desktop-ingress \
  --app-local-root "<Tauri AppLocalData root>" \
  --queue-root "$TSUZU_CORE_ROOT/queue" \
  --control-root "$TSUZU_CORE_ROOT/control" \
  --index-root "$TSUZU_CORE_ROOT/index"
```

`QUEUED` means the durable draft has entered Core ingress but is not yet
Canonical. `COMMITTED` means the Core receipt exists and the SOURCE was indexed.
The desktop shell has no shell or network permission, so it does not invoke
Python itself; packaging a signed Core sidecar is a separate distribution step.
