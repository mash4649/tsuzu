# TSUZU desktop shell

This directory is the first Tauri v2 / React / Vite / TypeScript migration slice.

Architecture: `React UI -> TypeScript application -> Tauri adapter -> Rust command`.

The Mac TSUZU Core is the sole mutable Canonical writer. In this migration slice,
that owner is the existing Python `AtomicSourceWriter`/`SingleWriterWorker` path.
The Tauri UI can persist a local **capture draft** under its app-local directory,
but that draft is not Canonical, indexed, or recallable TSUZU memory. It becomes
a SOURCE only when the Python Core writes `core-receipt.json` after its existing
A3 queue and A4 single writer commit it.

The native boundary exposes only runtime health and a fixed Rust command that
starts the bundled Core sidecar with app-local and Core paths. The WebView gets
no shell capability; filesystem access stays limited to app-local drafts.

## Commands

```sh
pnpm install
pnpm build
pnpm tauri dev
pnpm tauri build --config src-tauri/tauri.local-macos.conf.json --bundles app
```

`build:sidecar` uses `uvx`/PyInstaller to create a target-specific executable
from the existing Python Core. The local macOS config uses ad-hoc signing
(`-`): it is free and suitable for this Mac's verification only, not public
distribution. macOS may still require manually allowing the app in Privacy &
Security. This build defaults to `~/Desktop/++++TSUZU/Core` and
`~/Desktop/++++TSUZU/Vault`; set `TSUZU_CORE_ROOT` and `TSUZU_VAULT_ROOT` in
the launch environment to test another selection. Initial setup only binds an
empty Vault; an existing, unhealthy, or differently selected Core is left
untouched and reported as an error.

## Import a draft into the selected Core

From the repository root, set the same absolute `TSUZU_CORE_ROOT` and
`TSUZU_VAULT_ROOT` used by the Codex hook. `TSUZU_CORE_ROOT` selects `control`,
`queue`, `index`, and `runtime`; `TSUZU_VAULT_ROOT` selects the one Canonical
Vault. The command deliberately requires those paths: it never guesses or
migrates a second Vault.

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
