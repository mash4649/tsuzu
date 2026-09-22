# TSUZU P0 Final Implementation Execution Plan v2.0

- Date: 2026-09-09
- Status: **Implementation Order / Ready to execute**
- Replaces: v1.0 execution plan
- Source of truth: Canonical v1.1 -> v1.2 -> v1.2.1 -> v1.2.2, Contract Index v2.1
- Objective: implement in dependency order while proving integrity/security gates before expanding into Discovery and Founder testing.

---

# 0. Rule of execution

Implementation follows vertical, testable increments. No phase may silently weaken a previous gate.

Each task must:

- implement one named Contract responsibility;
- have deterministic tests for Hard Invariants;
- leave Canonical state recoverable;
- avoid unrelated refactors;
- document implementation-time API/library decisions separately from Product Constitution.

---

# Phase 0 — Storage authority foundation

## P0-0.1 C0 Active Vault Locator

Implement before any production writer path.

Acceptance:
- one active `vault_id`/generation;
- fail closed on corrupt/missing locator;
- filesystem capability preflight;
- generation-safe handle and CAS cutover.

## P0-0.2 A1 Canonical Source schema

Implement SOURCE schema/validator and fixed identity rules.

## P0-0.3 A2 SOURCE Atomic Writer

Implement SOURCE-specific staging/no-clobber/revision logic using C0.

## P0-0.4 C1 Generic Persistent/Canonical Mutation core

Extract/generalize the shared safe persistence primitives without creating a second writer lock.

Required first consumers:
- B1 Chronicle Canonical objects;
- B5 Correction Event;
- R1 SOURCE_VERSION.

### Checkpoint F0-A

- C0 Golden cases pass.
- A1/A2 core tests pass.
- C1 generic create/revision/idempotency tests pass.
- stale Vault generation cannot commit.

---

# Phase 1 — Durable capture and Source integrity

## P0-1.1 A3 Capture / Secret Guard

- local validation;
- pre-durable secret block;
- stable IDs/idempotency.

## P0-1.2 A4 Single Writer Capture Worker

- durable queue;
- at-least-once scheduling;
- one Canonical effect.

## P0-1.3 A5 SQLite/FTS Derived Index

Initial direct Source projection + rebuild.
C2 acquired-representation extension comes later.

## P0-1.4 A6 SOURCE Deletion specialization

Implement Source-level logical deletion and no-resurrection.

## P0-1.5 C3 Generic Deletion

Generalize A6 deletion truth across persistent object types and add best-effort active-store purge boundary.

### Checkpoint F0-B

- Secret containment deterministic.
- duplicate Capture converges.
- Source delete survives stale index/rebuild.
- generic Decision/Conversation fixture deletion works.
- purge failure does not reverse logical deletion.

---

# Phase 2 — Explicit Recall core

## P0-2.1 A7 Retrieval / Egress Gate

Implement candidate hard gates and destination policy.

P0 rule:
- SENSITIVE external = deny.
- no one-time SENSITIVE override.

## P0-2.2 A8 Context Bundle / Trace

Bounded context and body-free trace.

## P0-2.3 C6 Capability Registry — initial Claude record

Implement common registry/router and register verified A9 capabilities.

## P0-2.4 A9 Claude Code Adapter

Use current implementation-time official/runtime verification.

## P0-2.5 A10 Slice A Golden Gate

Run all mandatory deterministic cases.

### Checkpoint Slice A

Do not proceed with a “Slice A PASS” claim until A10 passes in real runtime.

---

# Phase 3 — Acquisition and historical corpus

## P0-3.1 R1 generic Acquisition v0.2

- public-web SSRF boundary;
- credentialed requests HTTPS-only;
- immutable SOURCE_VERSION through C1;
- no Capture blocking.

## P0-3.2 C2 Effective Source Representation

Wire:

```text
SOURCE + SOURCE_VERSION -> A5 -> A7 -> A8
```

Extend A5 rebuild/projection fixtures. Implement registered local deterministic HTML/text projection and PDF text-extractor adapter boundary; unsupported extraction remains metadata-only rather than fabricated.

## P0-3.3 R2 X Acquisition / Rescue

Verify current supported route(s), preserve fidelity/provenance.

## P0-3.4 R3 Historical Bootstrap

Apple Notes/Markdown implementation-time adapter choice; import idempotency.

## P0-3.5 R4 iOS Share create-only Capture v0.2

Transport only; Mac remains mutable writer.

Implement the paired-device transport-authenticity boundary before accepting a synced/shared mobile envelope as `IOS_SHARE_*` user-originated provenance:

- device private signing material remains in Keychain/Secure Enclave-class storage;
- Mac trusts an explicitly paired public verification identity;
- immutable envelope identity/payload fields are signed and verified before A3 acceptance;
- unknown/revoked key, signature failure, hash mismatch or malformed canonicalization fail closed;
- replay still converges through A3/A4 idempotency and does not become a second Canonical capture.

### Checkpoint Acquisition

- captured URL recalls acquired page content with root+version trace;
- deleted Source/Version cannot return through stale FTS;
- credential never travels over HTTP;
- X reconstructed route is visibly lower-fidelity;
- repeated import is deterministic;
- forged/unpaired/revoked mobile envelopes are denied before user-originated provenance;
- a valid signed mobile-envelope replay remains idempotent.

---

# Phase 4 — Recovery before compounding memory

## P0-4.1 R5 Backup/Restore/Migration v0.2

Uses:
- C0 locator/cutover;
- C3 generic deletion union;
- A5 rebuild.

Run R5 Golden/fault matrix before external Founder data is trusted.

### Checkpoint Recovery

- restore from committed backup succeeds;
- stale backup cannot resurrect deleted objects across object types;
- N-1 migration works in Temporary Vault;
- cutover rollback works;
- unknown/corrupt ledger fails closed.

---

# Phase 5 — Conversation and Derived processing foundation

## P0-5.1 B1 Claude Code Chronicle

Canonical raw allowed conversation through C1.

## P0-5.2 C4 Derived Processing Orchestrator

Implement job registry/queue/fingerprint/generation before B2/B5/B7 depend on ad-hoc queues.

## P0-5.3 B2 Episode

Derived via C4.

## P0-5.4 B3 Experience Candidate

Derived via C4; no self-promotion.

## P0-5.5 B4 Decision Case / Assertions / Evidence

Preserve STATED vs REVEALED and observation boundaries.

## P0-5.6 B5 Reconciliation / Correction

Correction Canonical through C1; recompute through C4.

## P0-5.7 B6 Experience / Outcome / Learning

No causal overclaim.

## P0-5.8 B7 Promotion / Dependency

Integrate C3 deletion + C4 invalidation.

### Checkpoint Knowledge Integrity

- model output cannot become USER_EXPLICIT;
- correction survives recompute crash;
- deleted evidence is synchronously ineligible even if queue is down;
- all jobs are idempotent/generation-traceable.

---

# Phase 6 — Personal Discovery and Product events

## P0-6.1 B8 Personal Discovery 4 Lanes

- Grounded
- Pattern/Challenge
- Analogy
- Exploratory Jump
- No-Aha allowed

## P0-6.2 B9 Discovery Context Injection

Reuse A7/A8/A9; no Discovery bypass.

## P0-6.3 B10 Product Events / Denominators

Freeze event semantics.

## P0-6.4 B11 Founder technical Golden cases

Run deterministic technical gates.

### Checkpoint Slice B

B11 PASS is technical readiness only, not Product GO.

---

# Phase 7 — Passive Recall safety and Control Plane

## P0-7.1 R6 Passive Recall v0.2

Requires:
- C6 VERIFIED structured user event/passive injection capability;
- authentic single-use Trusted Intent Token;
- A7 per-candidate egress approval;
- PERSONAL-only silent external egress.

Run adversarial prompt-injection/token-forgery fixtures.

## P0-7.2 C5 Canonical Export

Implement Portable Canonical Archive and manifest/checksum verification.

## P0-7.3 R7 Thin Control Plane v0.2

Expose:
- health;
- connections/scopes/capabilities from C6;
- privacy;
- R5 recovery;
- C3 delete;
- C5 export.

### Checkpoint Founder UX Safety

- healthy system can be ignored;
- user can inspect/revoke permissions;
- export works;
- delete wording does not claim forensic secure erase;
- passive recall cannot be triggered by untrusted content.

---

# Phase 8 — Host expansion and Web Chat spike

## P0-8.1 R8 Codex/Cursor v0.2

Verify host capabilities at implementation time and publish C6 reports.

Not required for first Founder run if Claude path is proof-capable.

## P0-8.2 R9 Web Chat one-way v0.2

Validation spike only.
C6 report must remain capture-only unless future Contract proves more.

---

# Phase 9 — Founder Product Proof

## P0-9.1 R10 F0 internal Instrument Validation

May run before full R7 user-facing completion while engineering validates event correctness.

## P0-9.2 R10 F1 external Founder Product Proof

Entry gate:

- A10 PASS
- B11 PASS
- R5 recovery PASS
- R6 adversarial PASS for passive Host
- B10 instrumentation ready
- R3 corpus readiness
- minimal R7 Control Plane available

Freeze experiment manifest before first eligible F1 event.

## P0-9.3 R10 F2 Gate Calibration

After F1 data lock, define next-round GO/PIVOT/KILL numeric thresholds.

No retrospective denominator manipulation.

---

# 10. Critical dependency graph

```text
C0
 └─ A2
     └─ C1
         ├─ A3/A4
         ├─ B1/B5 canonical events
         └─ R1 SOURCE_VERSION

A5 <─ C2 <─ R1/R2
A6 -> C3 -> C4/B7/R5/R7
A7/A8/A9 -> C6 -> R6/R8/R9
C5 -> R7 -> R10 F1
C4 -> B2/B3/B5/B6/B7/B8
B10+B11+R5+R6+R7 -> R10 F1
```

---

# 11. Implementation decisions that must remain implementation-time

Do not stop coding to reopen Product Strategy for:

- exact Swift/Node/Rust/Python stack until repository is selected;
- exact file coordination API;
- fetch library;
- X route;
- Apple Notes adapter;
- iOS transport;
- Host current APIs;
- model/prompt thresholds.

Record such choices in ADRs once a repository exists.

---

# 12. Final documentation-to-code handoff condition

The documentation phase is complete when:

- Contract Index v2.1 is the sole current map;
- v1.2.2 precedence is recorded;
- C0-C6 exist;
- active R revisions are used;
- Cross-document Audit v2.0 passes;
- MANIFEST.sha256 verifies;
- ZIP integrity passes.

Then implementation begins at Phase 0 without further broad design decomposition.
