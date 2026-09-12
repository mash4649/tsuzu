# ADR-003: POSIX single-writer boundary for A2 Source persistence

- Status: Accepted
- Date: 2026-09-12
- Scope: A2 implementation choice

## Decision

The Python MVP uses a per-Vault `system/write.lock` with non-blocking POSIX
`flock`. A mutation resolves its Vault through C0, stages the complete Source
directory under `system/staging`, validates it with A1, then publishes the
directory with a same-volume rename while the lock is held. Metadata updates
replace only `source.md` after an expected-revision check.

## Consequences

- Internal writers do not race and lock contention returns `WRITER_BUSY`.
- The MVP does not claim multi-Mac consensus or arbitrary SMB/NFS safety.
- File Provider/iCloud coordination belongs in a future platform adapter; local
  commit does not imply remote sync completion.
- Post-publish uncertainty is reconciled by retrying the same stable intent.
