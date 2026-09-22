# TSUZU P0 Contract Index v2.0

- Date: 2026-09-09
- Status: **Current Implementation Documentation Index**
- Purpose: one entry point for all P0 implementation contracts. This index changes no Product Constitution.

---

# 1. Global precedence

Product / Architecture interpretation:

1. `TSUZU_Canonical_Closing_Addendum_v1.2.1_20260906`
2. `TSUZU_Canonical_Addendum_v1.2_20260906`
3. `TSUZU_Canonical_Product_Architecture_v1.1_20260906`
4. older savepoints / conversation notes

Scoped implementation interpretation:

1. the named implementation Contract for its owned responsibility;
2. its parent Slice/plan;
3. v1.2.1;
4. v1.2;
5. v1.1.

A lower-level Contract may close implementation ambiguity but **may not weaken Product Constitution, Security, User Ownership, Deletion or Recoverability invariants**.

---

# 2. Slice A — Grounded Recall Core

| ID | Contract | Owner responsibility | Status |
|---|---|---|---|
| A1 | Canonical Source | raw captured Source identity/schema/immutability | Closed / Ready to implement |
| A2 | Atomic Vault Writer | atomic Canonical publish/revision conflict | Closed / Ready to implement |
| A3 | Local Capture + Secret Guard | ingress/secret/sensitivity/durable capture job | Closed / Ready to implement |
| A4 | Single Writer Worker | one mutable writer/idempotent job reconciliation | Closed / Ready to implement |
| A5 | SQLite/FTS Derived Index | disposable derived index/rebuild | Closed / Ready to implement |
| A6 | Tombstone / Deletion Ledger | no-resurrection deletion truth | Closed / Ready to implement |
| A7 | Retrieval / Policy / Egress | candidate retrieval and authorization | Closed / Ready to implement |
| A8 | Context Bundle / Source Trace | bounded approved bundle and trace | Closed / Ready to implement |
| A9 | Claude Code Adapter | first Host explicit recall | Closed / Ready to implement |
| A10 | E2E Golden / Exit Gate | deterministic Slice A verification | Closed / Ready for TDD |

---

# 3. Slice B — Conversation to Personal Discovery

| ID | Contract | Owner responsibility | Status |
|---|---|---|---|
| B1 | Claude Conversation Chronicle | raw host conversation Chronicle | Closed / Ready to implement |
| B2 | Episode Segmentation | conversation grouping | Closed / Ready to implement |
| B3 | Experience Candidate / Provenance | candidate extraction/origin | Closed / Ready to implement |
| B4 | Decision Case / Assertion / Evidence | stated/revealed evidence model | Closed / Ready to implement |
| B5 | Reconciliation / Correction | later evidence reconciliation/correction | Closed / Ready to implement |
| B6 | Experience Trace / Outcome / Learning | outcome trace without causal overclaim | Closed / Ready to implement |
| B7 | Promotion / Dependency / Recompute | promotion and derived invalidation | Closed / Ready to implement |
| B8 | Personal Discovery 4 Lanes | grounded/challenge/analogy/jump | Closed / Ready to implement |
| B9 | Discovery Injection / Claude | discovery -> host bridge + security spike | Closed / Ready to implement |
| B10 | Product Proof Events / Denominators | event semantics/instrumentation | Closed / Ready to implement |
| B11 | Founder Golden Cases / Exit | Slice B technical verification | Closed / Ready for TDD |

---

# 4. R Contracts — Remaining P0 Closure

| ID | Contract | Owner responsibility | Status |
|---|---|---|---|
| R1 | Acquisition / Fetcher Adapter | generic post-capture remote acquisition | **Closed / Ready to implement** |
| R2 | X Acquisition / Rescue Route | X route strategy/fidelity/cost/rescue | **Closed / Ready for route spikes** |
| R3 | Historical Bootstrap | bounded Apple Notes/Markdown import | **Closed / Ready to implement** |
| R4 | iOS Share Create-only Capture | mobile append-only outbox -> Mac writer | **Closed / Ready to implement** |
| R5 | Backup / Restore / Migration / Recovery | recoverability and schema migration | **Closed / Ready to implement** |
| R6 | Passive Recall / Trusted Intent | safe invisible recall authorization | **Closed / Ready to implement** |
| R7 | Thin Control Plane | settings/health/privacy/data/recovery UI | **Closed / Ready to implement** |
| R8 | Codex / Cursor Expansion | remaining Host adapter capability/parity | **Closed / Ready for host verification** |
| R9 | Web Chat Chronicle One-way | validation spike contract | **Closed / Ready to execute spike** |
| R10 | Founder Product Proof Experiment | real-human proof/gate calibration | **Closed / Ready after technical gates** |

---

# 5. Unique ownership rules

To prevent cross-contract ambiguity:

| Concern | Authoritative owner | Other contracts may only... |
|---|---|---|
| Source raw bytes / identity | A1 | create child/import references |
| Canonical atomic mutation | A2/A4 | request through writer |
| pre-persistence secret classification | A3 | run additional earlier guard, never weaken A3 |
| deletion truth / no resurrection | A6 | reapply/orchestrate, never override |
| index truth | A5 (derived only) | trigger rebuild |
| item egress authorization | A7 | request evaluation, never bypass |
| context body/trace | A8 | supply eligible content |
| first host explicit recall | A9 | extend host parity |
| Chronicle raw capture | B1 | adapt sources into B1 |
| decision evidence/reconciliation | B4/B5 | provide evidence only |
| promotion/invalidation | B7 | request recompute only |
| discovery semantics | B8 | select/inject only |
| product event semantics | B10 | emit versioned events only |
| generic acquisition | R1 | specialize through adapter |
| X route selection | R2 | return normalized R1 result |
| import identity/bootstrap | R3 | feed A3/A4 |
| mobile transport | R4 | feed A3/A4; no Canonical writes |
| recovery orchestration | R5 | call A5/A6; never redefine them |
| passive recall authorization | R6 | invoke A7/A8/B9; never authorize individual denied items |
| Control Plane | R7 | invoke owning contracts; no direct data mutation |
| additional host adaptation | R8 | preserve A7/R6/B1 semantics |
| web chat one-way capture | R9 | feed B1 only |
| experiment interpretation | R10 | read B10 events; no runtime behavior change |

---

# 6. Current documentation completion status

```text
Canonical Product / Architecture       COMPLETE
Slice A standalone implementation     COMPLETE (A1-A10)
Slice B standalone implementation     COMPLETE (B1-B11)
Remaining P0 standalone contracts     COMPLETE (R1-R10)
Cross-contract ownership map          COMPLETE
Final implementation plan             COMPLETE
Final cross-document audit            COMPLETE
Code implementation                   NOT STARTED / NOT CLAIMED
Golden Case execution                 NOT PASSED / NOT CLAIMED
Founder Product Proof                 NOT EXECUTED / NOT CLAIMED
```

There is **no known un-decomposed P0 responsibility** in the current canonical scope.

---

# 7. Intentionally unresolved at documentation completion

These are not specification gaps. Their resolution mechanism is defined by Contract:

- exact network size/time defaults -> implementation configuration + tests;
- concrete generic fetcher library -> implementation choice;
- currently usable X API/browser/Grok route -> R2 implementation-time route verification;
- Apple Notes bridge API/mechanism -> R3 implementation-time adapter verification;
- iOS transport technology -> R4 transport adapter implementation choice;
- Discovery model/prompt/ranking thresholds -> B8/B9 Founder tuning;
- Codex/Cursor current hooks/interfaces -> R8 host source verification;
- Web Chat provider capture method -> R9 spike;
- GO/PIVOT/KILL numeric thresholds -> R10 F2 calibration after F1 evidence.

Do not convert these into Product Constitution without evidence.

---

# 8. Resume point

Implementation begins from the final execution plan, not from further product ideation.

Earliest code dependency root:

```text
A1 -> A2 -> A3 -> A4
```

The name discussion `TSUZU vs AHA` remains explicitly deferred and has no implementation effect.
