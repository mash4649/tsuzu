# TSUZU P0 Vertical Slice B7 — Promotion / Dependency Invalidation / Recompute Contract v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Parent Plan: P0 Vertical Slice B
- Depends on: A6 + B3-B6
- Status: Implementation Contract / Ready to implement
- Scope: B7 only. Promotion states, dependency graph, tombstone/correction invalidation and remaining-evidence recompute.
- Non-scope: Discovery generation itself, physical secure erase, self-learning policy changes.

## 0. Decision

Processing / Promotion / Deletionを別軸のまま実装する。

Promotion states:

```text
CANDIDATE
WORKING
PROMOTED
SUPERSEDED
REJECTED
```

Deletion:

```text
LIVE
TOMBSTONED
```

TOMBSTONED always wins.

## 1. Promotion invariants

- assistant-generated only → never PROMOTED
- user explicit → strong evidence but temporal/scope still apply
- observed behavior → supports revealed behavior, not internal belief
- jointly derived → strong only with user evidence
- pattern promotion requires multiple independent cases
- exact thresholds are Implementation Spike and versioned

## 2. Dependency graph

Minimum:

```text
Source / Conversation / Artifact
→ Episode
→ Candidate / Evidence
→ Decision Assessment / Experience Trace / Pattern
→ Discovery Candidate / Learning
→ Index / Context Bundle / Product Event references
```

B7 tracks identity dependencies, not body copies.

## 3. Invalidation triggers

- tombstone/deletion
- Canonical Correction Event
- source revision affecting sensitivity/scope/temporal validity
- assertion superseded/rejected
- evidence becomes unavailable/corrupt

## 4. Recompute semantics

After invalidation:

1. mark dependent Derived objects stale
2. remove invalid evidence refs from eligibility
3. recalculate confidence
4. reconsider promotion state
5. regenerate/reconcile where needed
6. rebuild derived index/view

Do not immediately delete a multi-evidence Derived object if valid support remains.

## 5. Remaining evidence rules

All support removed:
- reject/tombstone equivalent Derived object
- recall/discovery ineligible

Some support remains:
- re-evaluate confidence/state
- may degrade PROMOTED → WORKING

Pattern/Discovery must never count deleted evidence as historical support.

## 6. Promotion policy versioning

Every promotion decision carries:
- policy_version
- evidence_refs
- evaluated_at
- prior_state/new_state

Policy may not self-modify based solely on AI output.

## 7. Supersede semantics

SUPERSEDED is history, not deletion.

It may be used for Judgment Evolution but must not be presented as current fact unless explicitly framed historically/conditionally.

## 8. Failure behavior

- dependency store unavailable → fail closed for dependent discovery/promotion usage
- recompute fails → old derived object marked stale/ineligible for strong current use
- tombstone state unknown → deny downstream eligibility
- correction committed but invalidation queue fails → correction still authoritative; stale downstream blocked until recompute

## 9. Golden cases

1. assistant-only candidate remains CANDIDATE.
2. explicit user-confirmed candidate becomes eligible for stronger state per policy.
3. promoted object loses one of several evidence refs → confidence/state re-evaluated.
4. all support tombstoned → object ineligible.
5. correction rejects assertion → assessment/pattern/discovery invalidated.
6. SUPERSEDED principle remains historical but not current.
7. pattern support falls below heuristic → degrade WORKING/REJECTED according to policy.
8. dependency graph failure → discovery fail closed.
9. deleted evidence restored from stale backup → A6 deletion still wins.
10. promotion policy version change → re-evaluation audit trail preserved.

## 10. Implementation tasks

### B7.1 Promotion state machine
### B7.2 Dependency edge store/interface
### B7.3 Invalidation dispatcher
### B7.4 Recompute coordinator
### B7.5 Supersede/current eligibility resolver
### B7.6 Golden/fault tests

## 11. Acceptance criteria

1. three lifecycle axes remain separate.
2. assistant-only cannot PROMOTE.
3. tombstone overrides promotion.
4. correction/tombstone invalidates downstream objects.
5. partial evidence loss triggers re-evaluation, not blind delete.
6. all evidence loss makes object ineligible.
7. superseded knowledge cannot silently act as current fact.
8. promotion decisions are versioned/auditable.
9. B8 can request only currently eligible evidence/patterns.

## 12. Gate to B8

B8 may start only when stale/tombstoned/superseded eligibility can be resolved reliably and one correction propagation golden case passes.

## 13. One-line contract

> B7は、Knowledgeの利用強度と削除を別軸で管理し、訂正・削除・Evidence変化を下流へ伝播して、残った根拠だけで再評価する。
