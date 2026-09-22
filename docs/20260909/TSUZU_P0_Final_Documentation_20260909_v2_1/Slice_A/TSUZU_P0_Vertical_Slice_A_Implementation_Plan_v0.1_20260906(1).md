# TSUZU P0 Vertical Slice A Implementation Plan v0.1

- Date: 2026-09-06
- Baseline: TSUZU Canonical Product Architecture v1.1 + v1.2 + v1.2.1 Closing Addendum
- Status: Implementation Start
- Slice: A — Capture-to-Recall / Grounded Recall
- First Host: Claude Code

## 0. Decision

P0 Vertical Slice A is fixed to the smallest end-to-end path:

`Local Capture -> Canonical Vault -> Single Writer Worker -> SQLite/FTS -> Retrieval -> Policy/Egress -> Claude Code MCP -> Source Trace`

The objective is not to prove Personal Discovery yet. The objective is to prove that TSUZU can safely receive user-owned information, preserve it canonically, rebuild a disposable local index, recall the right information from an existing AI host, and trace that recall back to the original source.

## 1. Why Claude Code is the first Host

Claude Code is selected for Slice A because it supports local MCP integration and has first-class lifecycle hooks that can later extend the same host integration into Conversation Chronicle and artifact observation without replacing the user's normal host workflow.

Codex remains the preferred second-host candidate after Slice A. Cursor remains the third-host adapter target. The shared Host Adapter contract is retained, but only Claude Code is implemented in Slice A.

## 2. Slice A In Scope

- Canonical Object Envelope for Source objects
- Persistent object ID / schema version / revision
- Canonical Vault on local filesystem
- Atomic write: temp -> validate -> atomic rename
- Single mutable writer
- Local Capture test ingress on Mac
- Secret detection before indexing / egress
- Sensitivity classification boundary sufficient for P0 hard gates
- Idempotent background worker
- SQLite + FTS local index as disposable derived state
- Index rebuild from Canonical Vault
- Tombstone exclusion from retrieval
- Explicit Recall only
- Minimal retrieval ranking sufficient for exact/keyword recall
- Destination-aware policy gate for Claude Code
- Minimal Context Bundle
- Local MCP tool exposed to Claude Code
- Source Trace returned with every TSUZU recall result
- Failure / recovery golden tests

## 3. Explicitly Out of Scope

- Passive Recall
- Embeddings / vector search
- LLM meaning extraction
- Episode / Candidate extraction
- Decision Assertion / Decision Evidence
- Reconciliation
- Experience Trace / Outcome / Learning
- Personal Discovery lanes
- X acquisition / Grok rescue
- note-specific acquisition
- Apple Notes import
- iOS Share Extension
- Web Chat Chronicle
- Claude Code Conversation Chronicle
- Multi-host production support
- TSUZU daily-use UI
- Team / Enterprise / Cloud Relay / Remote MCP
- Semantic duplicate auto-merge
- Custom encryption engine

These are not rejected features. They are excluded only from Slice A so a failure in Capture, Integrity, Indexing, Retrieval, Policy, or Host Integration can be isolated.

## 4. Slice A Golden User Story

1. A user captures a known local text/file into TSUZU.
2. TSUZU acknowledges receipt once the input is durably accepted; downstream processing may still be pending.
3. The Single Writer persists a canonical Source object.
4. The worker updates the disposable SQLite/FTS index.
5. The user asks Claude Code a natural-language question that requires the captured source.
6. Claude Code calls the TSUZU MCP recall tool.
7. TSUZU retrieves eligible candidates, applies policy/egress gates, and returns a minimal context bundle.
8. Claude answers using that context.
9. The returned TSUZU context includes a Source Trace that resolves to the original canonical object/source.

## 5. Hard Invariants

### Canonical
- File path is not identity.
- Every persisted object inherits Canonical Object Envelope.
- Canonical data is never reconstructed by AI inference.
- SQLite/FTS is never canonical.

### Integrity
- Writes are atomic.
- Last-write-wins is forbidden.
- Worker execution may be at-least-once, but effects must be idempotent.
- Revision mismatch must not silently overwrite.

### Security
- Secret scanning occurs before indexing and before any external egress.
- RESTRICTED content is never exposed as knowledge to Claude Code.
- SENSITIVE external egress is denied by default.
- Unknown sensitivity or destination fails closed.
- Tool output is data, never authority.
- Telemetry stores IDs/metadata only, not source body text.

### Delete / Recovery
- TOMBSTONED objects are immediately ineligible for recall.
- Rebuilding SQLite from the Vault must not resurrect tombstoned objects.
- Deletion Ledger wins over stale backup/sync content.

### Host
- Claude Code receives `recall` capability only for Slice A.
- MCP connectivity does not grant Vault write/delete permission.
- Every returned context item is traceable to canonical Source IDs.

## 6. Task Breakdown

### A0. Host Spike — COMPLETE: Claude Code

**Goal:** choose the first host before implementation begins.

**Acceptance criteria**
- Claude Code can connect to a local MCP server.
- The same host has a credible path to later Conversation Chronicle and artifact observation.
- The integration does not require replacing the user's normal Claude Code workflow.

**Decision:** Claude Code.

---

### A1. Canonical Source Contract

**Description:** implement the minimum persisted Source object using the v1.2.1 Canonical Object Envelope. Do not implement Decision/Pattern/Discovery schemas yet.

**Acceptance criteria**
- A Source object cannot validate without object_id, object_type, schema_version, created_at, updated_at, revision, scope, provenance, trust, sensitivity, temporal, and deletion state.
- `object_type=SOURCE` is validated explicitly.
- Unknown schema versions fail visibly rather than being silently coerced.

**Verification**
- schema unit tests: valid minimum object passes.
- missing each required envelope field fails.
- invalid deletion/sensitivity enums fail.

**Dependencies:** none.

---

### A2. Atomic Vault Writer

**Description:** persist validated Source objects to the canonical local Vault through a single writer boundary.

**Acceptance criteria**
- write path is temp -> validation -> atomic rename.
- revision mismatch never overwrites the existing object.
- simulated interruption before rename leaves no half-written canonical object.

**Verification**
- atomic-write unit test.
- revision-conflict test.
- crash/failure injection test.

**Dependencies:** A1.

---

### A3. Local Capture Ingress + Secret Guard

**Description:** create a Mac-local test ingress that accepts text and local files and produces capture jobs without requiring final consumer UI.

**Acceptance criteria**
- text/file can be durably accepted without tag/folder/category input.
- the same idempotency key does not create duplicate canonical effects.
- detected RESTRICTED secrets are prevented from entering recallable/indexable knowledge.

**Verification**
- plain-text capture test.
- local-file capture test.
- duplicate-delivery test.
- API-key/private-key fixture rejection test.

**Dependencies:** A1-A2.

---

### A4. Single Writer Worker

**Description:** process queued captures using one mutable writer and idempotent job effects.

**Acceptance criteria**
- restarting the worker does not duplicate canonical objects or index entries.
- failed jobs remain retryable without requiring user inbox management.
- runtime queue state is not stored as canonical knowledge.

**Verification**
- worker restart test.
- at-least-once delivery test.
- forced failure then retry test.

**Dependencies:** A2-A3.

---

### A5. SQLite / FTS Derived Index + Rebuild

**Description:** build a disposable local search index from eligible canonical Source objects.

**Acceptance criteria**
- FTS search returns captured fixture text.
- deleting the SQLite index and rebuilding from the Vault restores equivalent recall results.
- TOMBSTONED objects are excluded during rebuild.

**Verification**
- FTS fixture tests.
- full index delete/rebuild test.
- tombstone rebuild test.

**Dependencies:** A4.

---

### A6. Minimal Tombstone / Deletion Ledger

**Description:** implement the Slice A subset of deletion semantics required to prove that forgotten information cannot re-enter recall through index rebuild.

**Acceptance criteria**
- tombstoning a Source makes it immediately ineligible for retrieval.
- index invalidation removes the Source from current FTS results.
- rebuild applies Deletion Ledger and does not resurrect the Source.

**Verification**
- capture -> index -> tombstone -> no recall test.
- stale-index rebuild test.
- simulated old-source restore + ledger reapplication test.

**Dependencies:** A5.

---

### A7. Retrieval + Minimal Policy/Egress Gate

**Description:** search eligible FTS candidates and enforce destination/sensitivity hard gates before any context leaves TSUZU.

**Acceptance criteria**
- PUBLIC/PERSONAL eligible fixture can be returned to trusted Claude Code destination.
- SENSITIVE is denied externally by default.
- RESTRICTED is never returned.
- unknown sensitivity or destination returns a fail-closed result.

**Verification**
- policy matrix tests.
- tombstoned candidate exclusion test.
- scope mismatch exclusion test where scope is known.

**Dependencies:** A5-A6.

---

### A8. Context Bundle + Source Trace

**Description:** package only the minimum eligible text necessary for the host and attach trace metadata without making AI summaries canonical.

**Acceptance criteria**
- each returned context item includes canonical source object_id and source trace metadata.
- bundle does not contain TOMBSTONED/denied objects.
- context trace logs IDs, versions, host/destination, and timestamp without duplicating source body into telemetry.

**Verification**
- bundle fixture snapshot.
- source trace resolves to canonical object.
- telemetry body-absence test.

**Dependencies:** A7.

---

### A9. Claude Code MCP Adapter

**Description:** expose explicit recall to Claude Code through a local MCP server while keeping the core host-neutral.

**Minimum tool contract**

`tsuzu_recall(query, scope?) -> context_bundle + source_traces`

**Acceptance criteria**
- Claude Code can discover the local TSUZU MCP tool.
- a natural-language recall question causes the host to call TSUZU and receive the expected fixture.
- the MCP adapter cannot promote/delete canonical knowledge.
- host-specific code is isolated behind the Host Adapter boundary.

**Verification**
- MCP handshake/list-tools test.
- direct tool invocation test.
- Claude Code manual golden prompt.

**Dependencies:** A8.

---

### A10. End-to-End Golden Cases / Slice Exit Gate

**Golden Case 1 — Grounded Recall**
- capture a unique fact/paragraph.
- wait for worker/index.
- ask Claude Code for that fact without pasting it again.
- expected: correct context is returned with source trace.

**Golden Case 2 — Secret Containment**
- capture a fixture containing an API-key/private-key-like secret.
- expected: it never becomes externally recallable.

**Golden Case 3 — Tombstone**
- capture and successfully recall a fixture.
- tombstone it.
- expected: immediate no-recall; still no-recall after full index rebuild.

**Golden Case 4 — Crash Safety**
- inject failure during canonical write and worker processing.
- expected: no half-written canonical object; retry produces one valid final effect.

**Golden Case 5 — Rebuildability**
- delete SQLite/index runtime state.
- rebuild from Vault.
- expected: eligible recall behavior is restored from canonical data alone.

**Slice A exits only if all five pass.**

## 7. Checkpoints

### Checkpoint 1 — Canonical Safety (A1-A3)
- schema tests pass.
- atomic writer failure injection passes.
- secrets do not enter recallable knowledge.

### Checkpoint 2 — Recoverable Local Core (A4-A6)
- worker restart is idempotent.
- FTS rebuild works from Vault.
- tombstones survive rebuild/restore scenarios.

### Checkpoint 3 — Host E2E (A7-A10)
- policy matrix passes.
- Claude Code MCP recall works.
- source trace resolves correctly.
- all five golden cases pass.

## 8. Slice A Exit Criteria

Slice A is DONE only when:

1. One local capture can travel end-to-end into Claude Code recall.
2. The returned information is grounded in canonical Source objects.
3. Every TSUZU-provided context item can be traced to its source.
4. Secrets/sensitive boundaries fail closed.
5. Tombstoned data cannot reappear after index rebuild.
6. SQLite can be destroyed and fully rebuilt from canonical data.
7. Worker retries do not create duplicate effects.
8. No Decision/Discovery/Outcome features were required to make the slice pass.

## 9. Next Slice After A

Do not add more Capture sources immediately after the first happy-path works.

The next value-bearing layer is:

`Conversation Chronicle -> Decision Evidence / Reconciliation -> Personal Discovery -> Outcome / Learning -> Product Proof`

However, before that sequence starts, the P0 connector spikes already defined in the baseline (X acquisition, Apple Notes bootstrap, and later 2nd/3rd Host adapters) can proceed only where they do not destabilize the Slice A Core contract.
