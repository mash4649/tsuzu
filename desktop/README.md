# TSUZU desktop shell

This directory is the first Tauri v2 / React / Vite / TypeScript migration slice.

Architecture: `React UI -> TypeScript application -> Tauri adapter -> Rust command`.

The Mac TSUZU Core is the sole mutable Canonical writer. In this migration slice,
that owner is the existing Python `AtomicSourceWriter`/`SingleWriterWorker` path.
The Tauri UI can persist a local **capture draft** under its app-local directory,
but that draft is not Canonical, indexed, or recallable TSUZU memory. It must be
handed to the Core by a separate adapter before it can become a SOURCE.

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
