# TSUZU desktop shell

This directory is the first Tauri v2 / React / Vite / TypeScript migration slice.

Architecture: `React UI -> TypeScript application -> Tauri adapter -> Rust command`.

The only native operation is `runtime_health`; `build.rs` generates and grants its
`allow-runtime-health` permission explicitly. It has no filesystem, shell, network,
storage, or external-content access. Existing Python code and its persistent format
remain unchanged until a separate migration task defines and verifies them.

## Commands

```sh
pnpm install
pnpm build
pnpm tauri build --bundles app
```
