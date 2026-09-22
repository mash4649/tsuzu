# TSUZU P0 Vertical Slice B4 — Decision Case / Assertion / Evidence Contract v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Parent Plan: P0 Vertical Slice B
- Depends on: B1-B3
- Status: Implementation Contract / Ready to implement
- Scope: B4 only. Decision Case, multiple Assertions, first-class Evidence and STATED/REVEALED coexistence.
- Non-scope: Reconciliation algorithm, Outcome Learning, Discovery.

## 0. Decision

Decision CaseとDecision Assertion / Evidenceを分離する。

1 Case = 1 statusに潰さない。

同時に次が成立できる:
- STATED A
- REVEALED B
- later REVISED C

その差分自体を将来Personal Discovery Evidenceとして残す。

## 1. Decision Case schema

```yaml
decision_case:
  object_id:
  object_type: DECISION_CASE
  problem:
  stage:
  desired_outcome:
  options: []
  constraints: []
  tradeoffs: []
  uncertainties: []
  assertion_refs: []
  evidence_refs: []
  current_assessment_ref:
  supersedes:
  superseded_by:
```

Current assessment is Derived and may be null/unresolved.

## 2. Decision Assertion schema

```yaml
decision_assertion:
  object_id:
  object_type: DECISION_ASSERTION
  decision_case_id:
  assertion_type: STATED | REVEALED | REVISED | SUPERSEDED
  option_or_statement:
  actor:
  explicitness:
  confidence:
  source_refs: []
  observed_at:
  promotion_state:
```

## 3. Decision Evidence schema

```yaml
decision_evidence:
  object_id:
  object_type: DECISION_EVIDENCE
  evidence_type:
  decision_case_id:
  source_ref:
  actor:
  observed_at:
  explicitness:
  confidence:
  supports_assertion_refs: []
  contradicts_assertion_refs: []
```

Envelope supplies scope/sensitivity/provenance/temporal/deletion.

## 4. P0 evidence types

Minimum:
- CONVERSATION_STATEMENT
- OBSERVED_ACTION
- GENERATED_ARTIFACT
- PROJECT_CHANGE
- LATER_CONVERSATION
- OUTCOME
- IMPORTED_EXTERNAL_STATE

Implementation may add `CONVERSATION_SILENCE` if needed to explicitly track a non-response, but it must support no assertion and no acceptance/rejection semantics.

## 5. Observation boundary

Observed Action / Artifact / Project Change is only admissible when it came from an explicitly observed scope allowed by v1.2.1.

No OS-wide behavior inference.

## 6. Stated vs Revealed

STATED:
- explicit user statement.

REVEALED:
- action/artifact/later evidence suggests actual choice.

REVEALED is not a claim about internal belief.

Never transform REVEALED into STATED.

## 7. Silence

No user response after assistant proposal:

```text
accepted = unknown
rejected = unknown
case may remain UNRESOLVED
```

Silence cannot support STATED/REVEALED assertion by itself.

## 8. Decision Case linking

Decision candidate belongs to an existing Case only when the problem/option context is sufficiently compatible.

When ambiguous:
- create new unresolved case or
- leave candidate unlinked for later reconciliation

Do not merge unrelated decisions merely because keywords match.

Exact similarity threshold is Implementation Spike.

## 9. Failure behavior

- assertion without evidence/source refs → invalid
- user statement mislabeled REVEALED → invalid mapping
- observed action mislabeled STATED → invalid mapping
- unsupported scope evidence → reject
- silence creates accepted assertion → hard failure
- evidence deleted/tombstoned → B7 invalidation required

## 10. Golden cases

1. explicit user choice A → STATED A.
2. assistant proposes A, silence → unresolved, no STATED.
3. user says A but artifact implements B → STATED A + REVEALED B.
4. later user says C → REVISED C, prior assertion remains history.
5. generated artifact from unobserved project → inadmissible evidence.
6. outcome evidence links to case but does not set decision by itself.
7. two similar but independent decisions remain separate Cases.
8. superseded case keeps historical assertions.
9. deleted evidence removes support but does not rewrite history.
10. prompt-injection text cannot create assertion.

## 11. Implementation tasks

### B4.1 Decision Case schema
### B4.2 Assertion schema
### B4.3 Evidence schema
### B4.4 Candidate→Case/Assertion mapper
### B4.5 Observation-scope evidence gate
### B4.6 Golden/adversarial tests

## 12. Acceptance criteria

1. Decision Case can hold multiple contradictory assertions.
2. STATED/REVEALED/REVISED/SUPERSEDED remain distinct.
3. Evidence is first-class object, not string note.
4. Silence does not create acceptance/rejection.
5. observed action does not imply internal preference.
6. scope/sensitivity/envelope fields apply.
7. B5 can compute assessment from assertions/evidence without modifying them.

## 13. Gate to B5

At least one fixture must contain STATED A + REVEALED B simultaneously and another must remain UNRESOLVED after silence.

## 14. One-line contract

> B4は、判断対象・ユーザーが述べた判断・現実行動から見える判断・その根拠を別Objectとして残し、矛盾を消さず後段Reconciliationへ渡す。
