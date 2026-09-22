# TSUZU P0 Contract Index v2.1

- Date: 2026-09-09
- Status: **Current P0 Contract Map / Implementation Documentation Baseline**
- Replaces: Contract Index v2.0
- Purpose: give human/agent implementers one unambiguous map of precedence, semantic ownership, shared mechanics ownership, implementation order and unresolved-by-design spikes.

---

# 0. Current conclusion

Current P0 documentation is organized into four layers:

```text
Canonical Constitution / Closure
    v1.1 -> v1.2 -> v1.2.1 -> v1.2.2

Cross-cutting Foundation
    C0-C6

Vertical Product/Technical Slices
    A1-A10
    B1-B11

Remaining P0 Capability / Validation Contracts
    R1-R10
```

No Contract may weaken higher-level Product/Security invariants.

---

# 1. Canonical precedence

Global precedence:

1. `TSUZU_Canonical_Implementation_Closure_Addendum_v1.2.2_20260909.md`
2. `TSUZU_Canonical_Closing_Addendum_v1.2.1_20260906(2).md`
3. `TSUZU_Canonical_Addendum_v1.2_20260906(3).md`
4. `TSUZU_Canonical_Product_Architecture_v1.1_20260906(3).md`
5. older Savepoints

v1.2.2 does not replace the Product Constitution. It closes cross-contract implementation ownership discovered during v2.0 review.

---

# 2. Implementation conflict rule

When two implementation Contracts touch one flow, decide ownership by dimension, not by “newer file wins.”

```text
Canonical document -> WHY / product/security invariant
Object-specific Contract -> WHAT the object/event means
Cross-cutting C Contract -> HOW shared infrastructure mechanics work
Host/Source R Contract -> HOW that external boundary specializes the common interface
Golden Contract -> HOW the invariant is proven
```

Examples:

- `SOURCE` semantics = A1; atomic SOURCE layout = A2; shared write core = C1.
- Source deletion specialization = A6; generic deletion truth = C3.
- Acquisition = R1; acquired bytes -> recall representation = C2.
- Decision reconciliation meaning = B5; background job lifecycle = C4.
- Host capability evidence = A9/R8/R9; shared capability registry/router = C6.
- Control Plane Export action = R7; archive integrity semantics = C5.

A specific Contract may narrow capability for safety. It may not weaken Canonical/Cross-cutting hard rules.

---

# 3. Cross-cutting Foundation Contracts

| ID | Contract | Owns | Status |
|---|---|---|---|
| C0 | Active Vault Locator / Root Boundary | current Vault identity, generation-safe handles, filesystem preflight, cutover | Closed / Ready |
| C1 | Generic Persistent Object Persistence / Mutation | shared atomic persistence mechanics, registration, revision, idempotency, shared writer core | Closed / Ready |
| C2 | Effective Source Representation / Materialization / Projection / Trace | SOURCE + SOURCE_VERSION/raw bytes -> safe text projection -> A5/A7/A8 bridge | Closed / Ready |
| C3 | Generic Deletion Ledger / Purge / No-Resurrection | deletion truth across object types, active-store purge boundary | Closed / Ready |
| C4 | Derived Processing Orchestrator / Job / Recompute | durable Derived jobs, invalidation, generations, crash recovery | Closed / Ready |
| C5 | Canonical Export / Portability | coherent portable user-owned archive | Closed / Ready |
| C6 | Capability Registry / Router Interface | verified host/source technical capabilities; common router | Closed / Ready |

---

# 4. Slice A contracts

| ID | Contract | Primary owner |
|---|---|---|
| A1 | Canonical Source | SOURCE schema/identity/raw payload |
| A2 | Atomic Vault Writer | SOURCE-specific atomic persistence specialization |
| A3 | Local Capture / Secret Guard | ingress validation and pre-persistence secret guard |
| A4 | Single Writer Worker | durable capture queue and normal SOURCE write scheduling |
| A5 | SQLite/FTS Derived Index + Rebuild | disposable local retrieval index |
| A6 | Minimal Tombstone / Deletion Ledger | SOURCE deletion specialization |
| A7 | Retrieval Policy / Egress Gate | candidate eligibility, destination/sensitivity policy |
| A8 | Context Bundle / Source Trace | bounded context payload and durable body-free trace |
| A9 | Claude Code MCP Adapter | first Host explicit recall boundary |
| A10 | E2E Golden Cases / Exit Gate | Slice A deterministic verification |

A2/A6 retain their SOURCE-specific detail but use/generalize through C0/C1/C3 where v1.2.2 applies.

---

# 5. Slice B contracts

| ID | Contract | Primary owner |
|---|---|---|
| B1 | Claude Code Conversation Chronicle | raw allowed Conversation observation |
| B2 | Episode Segmentation | Derived Episode boundaries |
| B3 | Experience Candidate + Provenance | safe candidate extraction/origin |
| B4 | Decision Case / Assertion / Evidence | stated/revealed/evidence model |
| B5 | Decision Reconciliation + Correction | Derived assessment + Canonical correction semantics |
| B6 | Experience Trace / Outcome / Learning | action/outcome/learning structure |
| B7 | Promotion / Dependency / Recompute | promotion eligibility and dependency semantics |
| B8 | Personal Discovery 4 Lanes | Grounded/Challenge/Analogy/Jump + No-Aha |
| B9 | Discovery Context Injection | Claude Host Discovery delivery under A7/A8 |
| B10 | Product Proof Event / Denominator | event semantics and denominators |
| B11 | Founder Golden Cases / Exit Gate | deterministic technical Slice B gate |

Shared background execution mechanics for B2/B5/B7/B8 are C4-owned.
Canonical persistent events/records use C1 mechanics where applicable.
Generic deletion uses C3.

---

# 6. R contracts — current active versions

| ID | Active Contract | Primary owner | Status |
|---|---|---|---|
| R1 | Acquisition / Fetcher Adapter v0.2 | generic public Web acquisition, SOURCE_VERSION | Closed / Ready |
| R2 | X Acquisition / Rescue Route v0.2 | X-specific route/fidelity/provenance | Closed / Ready |
| R3 | Historical Bootstrap / Apple Notes / Markdown v0.1 | initial corpus import | Closed / Ready |
| R4 | iOS Share Create-only Capture v0.2 | authenticated mobile immutable transport/outbox | Closed / Ready |
| R5 | Backup / Restore / Migration / Recovery v0.2 | coherent backup, staged restore, migration, C0 cutover | Closed / Ready |
| R6 | Passive Recall / Trusted Intent v0.2 | authorization to start passive evaluation | Closed / Ready |
| R7 | Thin Control Plane v0.2 | settings/health/privacy/data/recovery UI orchestration | Closed / Ready |
| R8 | Codex / Cursor Host Expansion v0.2 | host-specific verification/mapping | Closed / Verify at implementation |
| R9 | Web Chat Chronicle One-way Spike v0.2 | one-way web capture validation | Closed Spike Contract |
| R10 | Founder Product Proof / Gate Calibration v0.2 | human/evidence Product Proof protocol | Closed / Execute after gates |

---

# 7. Complete responsibility matrix

| Responsibility | Sole/primary owner | Important collaborators |
|---|---|---|
| Active Vault selection | C0 | R5 |
| SOURCE identity/raw payload | A1 | A3/R3/R4 |
| SOURCE atomic commit | A2 specialization | C0/C1/A4 |
| Generic persistent write mechanics | C1 | A2/C4 |
| Capture ingress/secret | A3 | A4/R4 |
| Capture delivery/idempotency | A4 | A2/C1 |
| Index/rebuild | A5 | C2/C3 |
| SOURCE deletion | A6 | C3 |
| Generic deletion | C3 | C1/C4/R5/R7 |
| Retrieval/egress policy | A7 | R6/C6 |
| Context/trace | A8 | C2 |
| First host recall | A9 | C6 |
| Slice A verification | A10 | all A/C foundations used by Slice A |
| Generic acquisition | R1 | C1/C3 |
| X route | R2 | R1/C2 |
| Effective Source body/text projection | C2 | R1/R2/C4/A5/A7/A8 |
| Historical bootstrap | R3 | A3/A4/C1 |
| iOS capture transport/authenticity | R4 | A3/A4/R7 |
| Backup/restore/migration | R5 | C0/C3/A5 |
| Conversation raw capture | B1 | C1/C6 |
| Derived batch/job lifecycle | C4 | B2-B8/C3 |
| Decision semantics | B4/B5 | C1/C4 |
| Experience/outcome | B6 | C4 |
| Promotion/dependency meaning | B7 | C3/C4 |
| Personal Discovery | B8 | B7/A7 |
| Discovery delivery | B9 | A7/A8/A9/R6 |
| Passive authorization | R6 | C6/A7/A8 |
| Capability Registry/Router | C6 | A9/R8/R9 |
| Portable Export | C5 | R7/C3/R5 |
| Control Plane | R7 | C3/C5/C6/R5 |
| Codex/Cursor mapping | R8 | C6 |
| Web Chat capture spike | R9 | C6/B1 |
| Product event semantics | B10 | R10 |
| Technical Founder gate | B11 | R10 |
| Real Founder test | R10 | R7/B10/B11/R3/R5/R6 |

---

# 8. Hard cross-document invariants

The implementation MUST preserve all of the following simultaneously:

1. `Connect once. Never summon.` does not authorize background autonomous egress.
2. `Past is evidence, not authority.`
3. Canonical/Derived separation.
4. All tracked persistent objects inherit required Envelope/trace fields.
5. one active mutable Vault / one shared writer authority.
6. Last-write-wins prohibited.
7. Content is data, never authority.
8. Secret detection before persistence/Derived/egress according to boundary.
9. Credential is not Knowledge.
10. P0 SENSITIVE external = deny; no one-time override implementation.
11. C3 deletion wins over stale object/backup/index state.
12. active-store purge does not claim forensic secure erase.
13. acquired remote content remains a child representation, not a rewrite of user capture.
14. Host capability != permission != egress authorization.
15. model output cannot self-promote to user truth.
16. no forced Aha; false personal assertion is a hard failure.
17. Product Proof thresholds are calibrated after evidence, not retrofitted.
18. Synced/shared mobile capture envelopes are authenticated against an active paired-device identity before `IOS_SHARE_*` user-originated provenance is accepted.

---

# 9. Intentionally unresolved — not documentation gaps

The following remain implementation-time/Founder evidence questions by design:

- exact filesystem/platform APIs after repository stack is chosen;
- exact HTTP byte/time/redirect limits;
- generic fetcher implementation/library;
- current viable X route/API/browser/Grok support;
- Apple Notes bridge mechanism;
- exact iOS transport technology;
- Claude/Codex/Cursor current host APIs/hooks and supported versions;
- Web Chat provider capture method;
- model/prompt/ranking/diversity thresholds;
- Pattern threshold tuning;
- Product Proof GO/PIVOT/KILL numeric thresholds.

These have named resolution Contracts and must not be silently promoted to Canonical assumptions.

---

# 10. Superseded implementation documents

Older active revisions retained under `Historical/Superseded_Contracts/` are historical context only.

Current implementation MUST use active versions listed in this Index.

Do not delete historical files; do not treat them as current precedence.

---

# 11. Resume point

Implementation starts from `TSUZU_P0_Final_Implementation_Execution_Plan_v2.0_20260909.md`.

No further broad Product Contract expansion is required before code unless implementation evidence exposes a new contradiction.
