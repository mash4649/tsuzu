# ADR-001: Use Python standard library and SQLite for the MVP baseline

## Status

Accepted

## Date

2026-09-12

## Context

The P0 contracts require a local-first runtime, durable filesystem writes, SQLite/FTS derived indexing, deterministic tests, and later stdio/host adapters. The repository did not contain an implementation stack, and the P0 execution plan explicitly leaves that choice to implementation time.

## Decision

Use Python 3.12 or newer with standard-library modules as the initial runtime. Use `sqlite3` for the local database boundary, `pathlib` for filesystem paths, `unittest` for deterministic tests, and a `src/` package layout. Keep `dependencies = []` until a contract proves that a third-party dependency is required.

## Alternatives considered

### TypeScript/Node

Node is available, but the MVP would need to select and maintain an SQLite package and a test/build tool before implementing the required local persistence boundaries.

### Rust

Rust would provide strong systems guarantees, but it adds compiler/toolchain and crate selection overhead before the contract behavior is proven.

## Consequences

- The baseline is reproducible with the system Python runtime and no dependency download.
- SQLite and filesystem behavior remain explicit and locally testable.
- Third-party libraries may be added later only through a focused ADR/task when the standard library no longer meets a named contract.
- Host adapters and any UI/API surface must preserve the same local-first boundaries.
