# TSUZU P0 Vertical Slice B Implementation Plan v0.1

- Date: 2026-09-07
- Baseline: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Status: Implementation Contract Breakdown / Ready for review
- Slice: B — Conversation-to-Discovery / Decision Learning
- First Host: Claude Code
- Depends on: Slice A PASS for Capture-to-Explicit-Recall Core

## 0. Decision

Slice Bは、Slice Aで成立した安全・追跡可能・再構築可能なCoreの上に、TSUZU固有価値であるPersonal Discoveryを最小構成で載せる。

End-to-end path:

```text
Claude Code Conversation
→ Chronicle
→ Episode
→ Experience Candidate
→ Decision Assertion / Evidence
→ Reconciliation / Correction
→ Experience Trace / Outcome / Learning
→ Promotion / Dependency Recompute
→ Personal Discovery 4 Lanes
→ Policy-aware Context Injection
→ Product Proof Events
→ Founder Golden Cases
```

Slice Bの目的は、アルゴリズムを完成させることではない。

> 自分では今回持ち込まなかった過去の経験が、根拠と確度を保ったまま現在の思考へ接続され、CONNECTED以上の発見候補を生み、その利用・判断影響まで計測できることを証明する。

## 1. Why B is 11 contracts, not 10

A1〜A10相当の粒度を維持するため、BはB1〜B11へ分割する。

`Candidate Extraction`、`Discovery Context Injection`、`Product Proof Event Logging`は独立した故障境界であり、1 Contractへまとめると責務・Failure Mode・Acceptance Testが混ざるため分離する。

これはProduct Scope追加ではない。v1.2 / v1.2.1で既にP0 Required / Closedとなっている内容の実装分割である。

## 2. Slice B In Scope

- Claude Code Conversation Chronicle one-host path
- Observation allowlist / session scope enforcement
- Chronicle raw observationとKnowledgeの分離
- Episode Segmentation
- Experience Candidate extraction
- Origin / Provenance / Confidence / Promotion State
- Decision Case / Decision Assertion / Decision Evidence
- STATED / REVEALED coexistence
- Silence = UNKNOWN / UNRESOLVED
- Minimal Decision Reconciliation
- Canonical Correction Event
- Experience Trace / Outcome / Possible Explanation / Learning Candidate
- Promotion State lifecycle
- Dependency-aware invalidation / recompute for B objects
- Pattern Candidate / Pattern Challenger
- Minimal Personal Discovery 4 Lanes
- Evidence Confidence / Discovery Distance separation
- No Aha allowed
- Discovery Context Compiler integration
- Claude Code Host delivery under existing A7/A8/A9 security boundaries
- Context Usage / Discovery Level / Decision Impact / Reuse / WTP event logging
- False Personal Assertion / Unsupported Decision Claim hard-failure tests
- Founder Golden Cases

## 3. Explicitly Out of Scope

- Codex production adapter
- Cursor production adapter
- Web Chat full bidirectional integration
- Web Chat Chronicle One-way beyond separate validation spike
- Remote MCP / Cloud Relay
- Mobile AI integration
- OS-wide observation
- Full browser history / email observation
- Google Drive / Notion / Obsidian production connectors
- Team / Enterprise
- Automatic external action execution
- Automatic policy self-modification
- Fixed GO/PIVOT/KILL numeric thresholds before Founder evidence
- Fixed vector/embedding/model vendor choice
- Exact Promotion/Pattern/Ranking threshold tuning before P0 evidence

## 4. Hard Invariants

### Knowledge / Provenance
- Raw Chronicle is observation, not automatically user Knowledge.
- Assistant-generated content alone cannot become PROMOTED.
- STATED and REVEALED are never collapsed into one assertion.
- Silence is neither acceptance nor rejection.
- Reconciliation is Derived Assessment; canonical evidence is never rewritten by AI.
- Correction is Canonical Event and invalidates downstream Derived objects.

### Experience / Outcome
- Action is not synonymous with Decision.
- Outcome is observation, not causal proof.
- Possible Explanation remains hypothesis unless stronger evidence exists.
- Single Case learning never auto-promotes to general principle.

### Discovery
- Past is evidence, not authority.
- Grounded / Challenge / Analogy / Jump remain distinguishable.
- Evidence Confidence and Discovery Distance remain separate.
- Pattern must retain contradiction / exception information.
- No Aha is valid output.
- TOMBSTONED evidence cannot support Discovery.
- SUPERSEDED Knowledge cannot be presented as current fact without context.

### Security / Observation
- Observation remains allowlist-scoped.
- Content is data, never authority.
- Credentials are not Knowledge and never enter Derived Processing.
- SENSITIVE external egress remains default deny.
- RESTRICTED never egresses.
- Discovery novelty cannot bypass A7/A8 policy/trace gates.
- Telemetry contains IDs/metadata, not conversation/source bodies.

## 5. Task Breakdown

### B1. Claude Code Conversation Chronicle Contract
Capture allowlisted conversation observations into a stable, append-oriented Chronicle without treating assistant content as user knowledge.

### B2. Episode Segmentation Contract
Convert Chronicle messages into Derived Episodes representing one coherent decision/problem thread.

### B3. Experience Candidate Extraction + Provenance Contract
Extract typed candidates with strict origin, evidence refs, confidence and CANDIDATE default state.

### B4. Decision Case / Assertion / Evidence Contract
Materialize Decision Case, multiple Assertions and first-class Evidence objects without collapsing STATED/REVEALED.

### B5. Decision Reconciliation + Correction Contract
Re-evaluate unresolved decisions from later evidence and apply canonical user corrections without rewriting source evidence.

### B6. Experience Trace / Outcome / Learning Contract
Connect before state, decisions, actions, observed outcomes, possible explanations and learning candidates without causal overclaim.

### B7. Promotion / Dependency Invalidation / Recompute Contract
Apply Promotion State rules and maintain dependency-aware invalidation/recompute across Candidate/Decision/Pattern/Discovery/Learning.

### B8. Minimal Personal Discovery 4-Lane Contract
Generate 0–3 grounded discovery candidates across Grounded / Challenge / Analogy / Jump with Pattern Challenger and No-Aha behavior.

### B9. Discovery Context Injection / Claude Host Contract
Transform policy-eligible Discovery Candidates into bounded Host context while preserving evidence labels, source trace and current/superseded semantics.

### B10. Product Proof Event / Denominator Contract
Record Context Usage, Discovery Level, Decision Impact, Reuse, WTP and hard failures with non-overlapping denominators.

### B11. Founder Golden Cases / Slice B Exit Gate
Prove the full Conversation-to-Discovery path, trust properties, correction/recompute and Product Proof instrumentation.

## 6. Dependency Graph

```text
Slice A PASS
   ↓
B1 Chronicle
   ↓
B2 Episode
   ↓
B3 Candidate / Provenance
   ↓
B4 Decision / Evidence
   ↓
B5 Reconciliation / Correction
   ↓
B6 Experience / Outcome / Learning
   ↓
B7 Promotion / Dependency
   ↓
B8 Personal Discovery
   ↓
B9 Host Injection
   ↓
B10 Product Proof Events
   ↓
B11 Founder Golden Cases
```

B8 may consume B4–B7 outputs but may not bypass them by reading raw assistant prose as user truth.

## 7. Checkpoints

### Checkpoint B1 — Conversation Foundation (B1–B3)
- Chronicle capture is allowlist-scoped and idempotent.
- Secret/credential material does not enter Derived processing.
- Episode boundaries are traceable to Chronicle messages.
- Assistant-only proposals remain CANDIDATE with assistant origin.
- Silence does not create accepted Decision.

### Checkpoint B2 — Decision Learning (B4–B7)
- STATED / REVEALED coexist.
- Reconciliation never rewrites canonical evidence.
- Correction invalidates and recomputes downstream Derived objects.
- Outcome does not imply causality.
- Assistant-generated-only candidate cannot PROMOTE.
- Tombstone/correction propagation prevents stale reuse.

### Checkpoint B3 — Discovery / Product Proof (B8–B11)
- 4 lanes are distinguishable.
- Evidence Confidence and Discovery Distance are separate.
- No-Aha path works.
- Superseded/tombstoned evidence is not misapplied.
- Discovery reaches Claude through existing policy/trace boundary.
- CONNECTED+ and hard failures are measurable with stable denominators.
- Founder Golden Cases pass.

## 8. Slice B Exit Criteria

Slice B is DONE only when:

1. One allowlisted Claude Code conversation is captured without manual save.
2. Chronicle → Episode → Candidate is traceable end-to-end.
3. Assistant proposal alone never becomes user Decision/Preference/Principle.
4. STATED and REVEALED can coexist and contradict.
5. Later evidence can reconcile an UNRESOLVED decision without altering original evidence.
6. User correction invalidates/recomputes affected Derived objects.
7. Outcome/Learning is recorded without automatic causal assertion.
8. Discovery produces grounded candidates in distinguishable lanes, including No-Aha when appropriate.
9. Discovery context cannot bypass sensitivity/deletion/scope/egress gates.
10. False Personal Assertion and Unsupported Decision Claim are testable hard failures.
11. CONNECTED / REFRAMED / EXPANDED / CHANGED_DECISION / OUTCOME_HELPED / REUSED / WOULD_PAY events have stable event semantics and denominators.
12. B11 mandatory Founder Golden Cases all pass.

## 9. What Slice B does NOT prove

Even if B passes, the following remain unproven:

- multi-host portability quality
- Web Chat capture reliability
- X/iOS capture UX
- final Invisible UX without temporary security approvals
- statistically stable GO/PIVOT/KILL threshold
- paid retention at scale
- Team/Enterprise value

## 10. Next after B

After B PASS, keep P0 scope disciplined.

Priority options are:

1. Founder Product Proof with real accumulated data and threshold calibration.
2. Codex / Cursor adapter expansion behind the same Host interface.
3. Web Chat Chronicle One-way Validation Spike.
4. X / Apple Notes / iOS capture expansion only where Core remains stable.

Do not interpret B PASS as permission to add Team / Cloud / Remote MCP.
