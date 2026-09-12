# ADR-006: One process-wide A4 worker with durable receipts

- Status: Accepted
- Date: 2026-09-12
- Scope: A4 implementation choice

## Decision

A4 uses one non-blocking POSIX `worker.lock` per runtime queue. It atomically
claims `pending/<job_id>` into `processing/`, validates immutable job/payload
integrity, rescans with the current local ruleset, and calls only A2 for Source
materialization. A body-free receipt is written before successful queue
cleanup; orphan processing directories are retried/reconciled on the next run.

## Consequences

- Multiple worker starts cannot create competing Canonical mutations.
- Canonical publish, receipt, and cleanup can be interrupted and resumed
  without generating a second Source identity.
- Transient writer failures move jobs to bounded retry; integrity/conflict
  failures quarantine without automatic repair.
