# TSUZU P0 Vertical Slice B6 — Experience Trace / Outcome / Learning Contract v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Parent Plan: P0 Vertical Slice B
- Depends on: B4-B5
- Status: Implementation Contract / Ready to implement
- Scope: B6 only. Experience Trace, action/intervention, observed outcome, possible explanations and learning candidates.
- Non-scope: Task management, causal inference engine, Promotion policy, Discovery ranking.

## 0. Decision

Outcomes over Archivesを最小Schemaへ落とす。

TSUZUはTask Managerにならず、Experience Loopに必要な関係だけを保持する。

```text
Before / Problem
→ Decision refs
→ Action / Intervention
→ Observed After State / Outcome
→ Possible Explanations
→ Learning Candidates
```

## 1. Experience Trace schema

```yaml
experience_trace:
  object_id:
  object_type: EXPERIENCE_TRACE
  before_state:
  problem:
  decision_refs: []
  action_or_intervention:
  observed_after_state:
  outcome:
  possible_explanations: []
  learning_candidate_refs: []
  evidence_refs: []
  confidence:
```

Canonical Envelope supplies scope/provenance/sensitivity/temporal/deletion.

## 2. Action semantics

Action is observed activity/intervention, not Decision status.

It may support a REVEALED assertion in B4/B5.

Action source must come from:
- user explicit statement
- allowlisted observed artifact/project/action
- later conversation
- imported external state within permission

## 3. Outcome semantics

Outcome is an observed result/state change.

Do not infer:

```text
Intervention happened before Outcome
→ therefore Intervention caused Outcome
```

Temporal sequence alone is insufficient.

## 4. Possible Explanation

Possible Explanation is hypothesis.

Must preserve confounders/alternative explanations when known.

Example:
- CVR improved after ad change
- LP also changed
- therefore ad change may have contributed but is not isolated causal proof

## 5. Learning Candidate

Outcome-derived learning starts as:
- CANDIDATE
- or WORKING where evidence is stronger

Never auto-PROMOTE a general principle from one case.

Learning must point to Experience Trace / Evidence refs.

## 6. Missing outcome

Experience Trace may remain open/incomplete.

Absence of Outcome is not failure and must not be filled by inference.

## 7. Temporal / scope fit

Outcome and action must belong to compatible case/scope/time window.

Ambiguous links remain unresolved rather than force-connected.

## 8. Failure behavior

- no evidence for action → do not assert action occurred
- no evidence for outcome → open trace
- confounded outcome → explanation stays hypothesis
- learning without trace/evidence refs → invalid
- deleted evidence → B7 re-evaluate trace/learning
- correction invalidates action/decision → trace becomes stale and recomputes

## 9. Golden cases

1. explicit decision + observed action + observed result → full trace.
2. action observed, decision unresolved → trace allowed; action does not finalize inner decision by itself.
3. outcome improves with known simultaneous change → possible explanation includes confounder.
4. no outcome yet → open trace.
5. single successful case → learning CANDIDATE, not PROMOTED.
6. later contradictory outcome → learning confidence reduced/revised.
7. outcome source tombstoned → trace recompute.
8. action from unobserved scope → inadmissible.
9. user correction invalidates decision ref → trace marked stale/relinked.
10. assistant predicts outcome but no real evidence → no observed outcome.

## 10. Implementation tasks

### B6.1 Experience Trace schema
### B6.2 Action/Outcome evidence linker
### B6.3 Possible Explanation generator interface
### B6.4 Learning Candidate materializer
### B6.5 Open/stale trace handling
### B6.6 Golden/fault tests

## 11. Acceptance criteria

1. Before/Decision/Action/Outcome are separable.
2. Action does not equal Decision.
3. Outcome does not equal causality.
4. possible explanations are explicitly hypotheses.
5. single-case learning cannot auto-promote.
6. missing outcome remains missing.
7. source/evidence refs are required.
8. B7 can invalidate/recompute trace/learning.

## 12. Gate to B7

At least one complete and one incomplete/confounded Experience Trace must exist with correct evidence refs and non-causal semantics.

## 13. One-line contract

> B6は、何を考え何をして何が起きたかをつなぐが、行動を意思決定と同一視せず、結果の前後関係を因果へ自動昇格させない。
