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
