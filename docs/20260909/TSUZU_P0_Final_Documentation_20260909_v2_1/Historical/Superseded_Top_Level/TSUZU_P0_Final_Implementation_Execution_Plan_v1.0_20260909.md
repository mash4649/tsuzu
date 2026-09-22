# TSUZU P0 Final Implementation Execution Plan v1.0

- Date: 2026-09-09
- Status: **Final documentation plan / Ready for code implementation**
- Input Contracts: Canonical v1.1/v1.2/v1.2.1 + A1-A10 + B1-B11 + R1-R10
- Objective: implement P0 in dependency order while proving security/recovery early and keeping optional expansion out of the critical path.

---

# 0. Guiding rule

Do not build horizontally by subsystem and connect everything at the end.

Build verifiable end-to-end checkpoints and keep the system runnable after each phase.

No code task may redefine a Contract silently. If implementation evidence forces a contract change, update the owning Contract first and record the reason.

---

# 1. Dependency graph

```text
A1 Canonical Source
 -> A2 Atomic Writer
 -> A3 Capture/Secret Guard
 -> A4 Single Writer
    -> R1 Generic Acquisition
    -> R3 Historical Bootstrap bridge
    -> R4 Mobile bridge (later)

A4 -> A5 Derived Index
A4 -> A6 Deletion Ledger
A5/A6 -> R5 Recovery
A5/A6 -> A7 Retrieval/Egress -> A8 Bundle/Trace -> A9 Claude -> A10 Slice A Gate

A9 -> B1 Chronicle -> B2 Episode -> B3 Candidate
B3 -> B4 Decision/Evidence -> B5 Reconciliation
B4/B5 -> B6 Experience/Outcome -> B7 Promotion/Invalidation
B7 -> B8 Discovery -> B9 Injection -> B10 Events
B9/A7/A8 -> R6 Trusted Intent Passive Recall
B10/R6 -> B11 technical Founder gate

R3 + R5 + R6 + B10/B11 -> R10 Founder Product Proof

R7 Control Plane integrates all core health/permission/recovery states
R2 X specializes R1
R8 Codex/Cursor expands A9/B1/R6
R9 Web Chat one-way feeds B1
```

---

# 2. Phase 1 — Canonical Capture Foundation

Implement in order:

1. A1 Canonical Source
2. A2 Atomic Writer
3. A3 Local Capture + Secret Guard
4. A4 Single Writer Worker

Checkpoint P1:

- TEXT/URL/FILE captured end-to-end;
- restricted secrets blocked;
- same retry idempotent;
- duplicate independent user actions distinct;
- crash cannot produce partial Canonical.

Do not proceed to higher-level memory behavior while Canonical write integrity is unstable.

---

# 3. Phase 2 — Acquisition / Derived / Deletion

5. R1 Generic Acquisition baseline
6. A5 SQLite/FTS Derived Index
7. A6 Deletion Ledger

Checkpoint P2:

- URL Capture succeeds offline/network-failing;
- successful public fetch produces immutable version;
- index is rebuildable;
- tombstoned data disappears from retrieval eligibility;
- no stale fetch/index can resurrect deleted data.

R2 X may begin route spikes in parallel after R1 interface stabilizes but is not required to block the next core checkpoint.

---

# 4. Phase 3 — Recovery Before Memory Intelligence

8. R5 Backup / Restore / Migration / Recovery

Checkpoint P3 mandatory safety cases:

- healthy backup/restore round trip;
- no tombstone resurrection;
- migration requires backup;
- migration rollback;
- index rebuild after restore;
- cutover health failure rollback.

Do not expose meaningful accumulated personal history without a tested recovery path.

---

# 5. Phase 4 — Explicit Grounded Recall

9. A7 Retrieval / Policy / Egress
10. A8 Context Bundle / Source Trace
11. A9 Claude Code first Host
12. A10 Slice A E2E

Checkpoint P4:

```text
Capture -> Canonical -> Index -> Explicit Recall in ONE Host -> Source Trace
```

Security matrix and A10 Golden Cases must pass before Discovery/passive behavior.

---

# 6. Phase 5 — Cold-start Corpus

13. R3 Historical Bootstrap

Checkpoint P5:

- bounded Apple Notes/Markdown import;
- no forced migration;
- import retry idempotency;
- coverage markers;
- enough real personal history for meaningful internal discovery tests.

Concrete Apple Notes bridge implementation can be swapped behind R3 Adapter.

---

# 7. Phase 6 — Conversation Learning

14. B1 Chronicle
15. B2 Episode
16. B3 Candidate / Provenance
17. B4 Decision / Assertion / Evidence
18. B5 Reconciliation / Correction
19. B6 Experience / Outcome / Learning
20. B7 Promotion / Dependency / Recompute

Checkpoints every 2–3 contracts:

- actor/provenance preservation;
- assistant-generated cannot become user truth;
- silence remains unresolved;
- corrections invalidate/recompute derived objects;
- outcome does not imply causality;
- deletion removes evidence from downstream models.

---

# 8. Phase 7 — Personal Discovery + Measurement

21. B8 Personal Discovery 4 Lanes
22. B9 Claude Discovery Injection
23. B10 Product Proof Events / Denominators

Checkpoint P7:

- 4 lanes distinguishable;
- Confidence and Discovery Distance separate;
- No Aha works;
- false personal assertion fixtures fail safely;
- CONNECTED/REFRAMED/EXPANDED can be recorded with stable denominators.

---

# 9. Phase 8 — Invisible UX Security Gate

24. R6 Passive Recall / Trusted Intent

Run full origin x injection x sensitivity x token adversarial matrix.

Only after per-host R6 PASS may Claude move from A9 per-call approval safe mode to passive trusted-intent mode.

Checkpoint P8:

- file/web/tool/assistant cannot trigger personal-memory egress;
- current structured user event can;
- SENSITIVE/RESTRICTED remain denied;
- no-result/no-Aha remains silent.

---

# 10. Phase 9 — Technical Founder Gate / Control Plane

25. B11 Founder Golden technical gate
26. R7 Thin Control Plane

R7 can be developed partly in parallel once health schemas stabilize, but external Founder onboarding should use the final minimal permission/recovery controls.

Checkpoint P9:

- core technical Golden Cases pass;
- connections/permissions/recovery visible;
- healthy user does not need a daily TSUZU workflow;
- Strict/Standard privacy cannot weaken security.

---

# 11. Phase 10 — Founder Product Proof

27. R10 F0 Instrument Validation
28. R10 F1 Founder Product Proof
29. R10 F2 Gate Calibration

Before F1:

- freeze experiment manifest/denominators;
- verify cohort/corpus readiness;
- confirm no unresolved security incident.

After F1:

- lock data;
- report Pain / Invisible / Discovery / WTP separately;
- preserve hard failures;
- create GO/PIVOT/KILL recommendation;
- calibrate numeric thresholds only for the next run.

---

# 12. Phase 11 — P0 Source / Host Expansion

These can run partly in parallel after the core is stable and need not block the first safe Founder learning loop:

30. R2 X route implementation/spikes
31. R4 iOS Share Create-only Capture
32. R8 Codex adapter
33. R8 Cursor adapter
34. R9 Web Chat Chronicle one-way spike

P0 completeness is not a reason to postpone Founder evidence indefinitely; equally, early Founder evidence is not permission to call deferred P0 responsibilities "done".

---

# 13. Verification cadence

After each implementation task:

- unit/contract tests for changed boundary;
- regression fixtures for inherited invariants;
- build/lint/type checks once repository commands exist;
- body-free test receipt.

After each phase:

- cross-contract integration test;
- failure injection for stateful/data/security changes;
- update Resume Point.

No flaky pass accepted for deletion/recovery/security Golden Cases.

---

# 14. Parallelization

Safe parallel tracks after shared interfaces are frozen:

- R2 route spikes parallel with A5/A6 after R1 interface;
- R7 UI shell parallel with core after normalized Health interfaces;
- R4 mobile transport parallel after A3 input contract stable;
- R8 Host verification parallel after common HostAdapter/R6 interfaces stable;
- R9 spike parallel after B1 Chronicle schema stable.

Must remain sequential:

- A1->A4;
- A6 before anti-resurrection restore proof;
- A7->A8->Host egress;
- B1->B3 provenance extraction;
- B4/B5 before Pattern/Discovery reliance;
- R6 before passive approval removal;
- R10 F2 after F1 data lock.

---

# 15. Stop / rollback rules

Stop the affected phase if:

- Canonical integrity cannot be proven;
- Deletion Ledger unavailable and code would continue recall/restore;
- secret scanner bypass is observed;
- SENSITIVE/RESTRICTED egress violation occurs;
- migration/restore cannot roll back;
- false personal assertion stems from missing provenance boundary;
- implementation requires expanding observation scope beyond canonical allowlist.

Fix owning Contract/implementation before progressing.

---

# 16. Implementation completion definition

P0 implementation is not complete merely because features exist.

Required:

```text
All mandatory A/B/R code paths implemented
+ mandatory Golden Cases PASS
+ recovery/security failure injection PASS
+ body-free reports reproducible
+ no unowned contract deviation
```

Product/business GO is still separate and requires R10 Founder evidence.

---

# 17. Current resume point

**Documentation is complete. Code resume point: A1.**

When a repository is created/provided, begin with a repo-level specification for actual tech stack, commands, project structure and test tooling, then implement this Contract graph without reopening Product Scope.
