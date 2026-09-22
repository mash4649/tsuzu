# TSUZU P0 Vertical Slice B5 — Decision Reconciliation + Correction Contract v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Parent Plan: P0 Vertical Slice B
- Depends on: B4
- Status: Implementation Contract / Ready to implement
- Scope: B5 only. Derived assessment, reconciliation triggers, canonical user correction and invalidation signaling.
- Non-scope: Pattern/Discovery generation, final threshold tuning.

## 0. Decision

Decisionを会話終了時に確定させない。

後続Evidenceにより未確定Caseを再評価し、Derived `current_assessment`を作る。

Original Assertions / Evidence are immutable historical evidence except for their own lifecycle/deletion metadata; AI reconciliation never rewrites what happened.

## 1. Reconciliation triggers

- new Conversation Episode
- new/changed Generated Artifact
- observed Project Change / Action
- Outcome addition
- Background Batch
- Canonical Correction Event

## 2. Assessment schema

```yaml
decision_assessment:
  object_id:
  object_type: DECISION_ASSESSMENT
  decision_case_id:
  best_assertion_ref:
  supporting_assertion_refs: []
  contradicting_assertion_refs: []
  unresolved_alternative_refs: []
  confidence: LOW | MEDIUM | HIGH
  status: UNRESOLVED | ASSESSED
  evidence_refs: []
  reconciler_version:
  evaluated_at:
```

Assessment is Derived.

## 3. Reconciliation rules

- explicit later user statement can strongly revise current assessment
- repeated observed action may support REVEALED, not STATED
- contradictory evidence remains visible
- insufficient evidence → UNRESOLVED
- no single truth is forced where alternatives remain viable
- deleted/tombstoned evidence is excluded from current assessment
- superseded context is not treated as current without temporal fit

Exact scoring/threshold is Implementation Spike and versioned.

## 4. Correction Event

User correction is Canonical Event.

Minimum:

```yaml
correction_event:
  object_id:
  object_type: CORRECTION_EVENT
  target_refs: []
  correction_type: WRONG_ASSERTION | NOT_DECIDED | CHANGED_NOW | PATTERN_MISREAD | OTHER_EXPLICIT
  statement_ref:
  observed_at:
  actor: USER
```

Correction body should reference the explicit user statement/source rather than duplicating unnecessary sensitive text.

## 5. Correction effect

Depending on target:
- REJECTED
- REVISED
- SUPERSEDED

Then signal B7 dependency invalidation for:
- Decision Assessment
- Pattern
- Discovery Candidate
- Personal Strategy derived view
- Learning Candidate

Original evidence is not physically edited to pretend the wrong inference never occurred.

## 6. Idempotency / regeneration

Same input evidence set + same reconciler version should produce semantically equivalent assessment.

Assessment may be regenerated.

Use an input evidence fingerprint to detect stale assessments.

## 7. Failure behavior

- missing/corrupt evidence → no confident assessment
- reconciler unavailable → keep prior assessment marked stale or no new assessment; do not fabricate
- correction target unknown → preserve correction event and flag unresolved link, do not discard user correction
- correction processing fails after event commit → correction remains authoritative; downstream remains stale until recompute

## 8. Golden cases

1. 980/1480 unresolved conversation + later 980 artifact → REVEALED 980 supported.
2. STATED A + repeated B action → assessment may favor B while preserving A contradiction.
3. later explicit C → REVISED/SUPERSEDED path.
4. silence only → remains UNRESOLVED.
5. user says “その判断はしていない” → correction event + affected assertion rejected/revised.
6. correction commit then recompute crash → correction survives, stale derived output not trusted.
7. supporting evidence tombstoned → confidence drops/re-evaluates.
8. contradictory evidence equal strength → unresolved alternatives retained.
9. stale assessment fingerprint → recompute required.
10. assistant-only proposal → cannot become current user decision without evidence.

## 9. Implementation tasks

### B5.1 Assessment schema + codec
### B5.2 Reconciliation input builder
### B5.3 Versioned reconciler interface
### B5.4 Correction Event writer through Single Writer boundary
### B5.5 Invalidation signal integration
### B5.6 Golden/fault tests

## 10. Acceptance criteria

1. Assessment is Derived, evidence remains unchanged.
2. unresolved alternatives are retained.
3. STATED/REVEALED contradiction survives.
4. silence remains unresolved.
5. Correction is Canonical Event.
6. Correction cannot be lost because downstream recompute fails.
7. tombstoned evidence cannot support current assessment.
8. B6/B7 can consume assessment/evidence with stable refs.

## 11. Gate to B6

A reconciled Case and a correction-driven recompute fixture must both exist, with original evidence still traceable.

## 12. One-line contract

> B5は、後続Evidenceから判断を後追いで再評価するが、過去の発言・行動を改変せず、ユーザー訂正をCanonical Eventとして最優先で下流再計算へ伝播する。
