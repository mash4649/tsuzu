# TSUZU P0 Vertical Slice B8 — Minimal Personal Discovery 4-Lane Contract v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Parent Plan: P0 Vertical Slice B
- Depends on: A7-A8 + B4-B7
- Status: Implementation Contract / Ready to implement with model/retrieval spike parameters
- Scope: B8 only. Current Decision Structure, 4 discovery lanes, Pattern Challenger, evidence labeling, diversity and No-Aha.
- Non-scope: Host transport, Product Proof event storage, fixed vector/model/threshold choice.

## 0. Decision

TSUZUのP0固有価値はPersonalizationではなくPersonal Discovery。

Current questionをTopicだけで検索せず、Current Decision Structureへ分解して過去のExperience/Evidenceと接続する。

Output is 0–3 Discovery Candidates, not a mandatory single answer.

## 1. Current Decision Structure

Minimum fields:
- Problem
- Stage
- Desired Outcome
- Constraints
- Options
- Trade-offs
- Uncertainties

This structure is Derived runtime/working context, not user canonical fact unless explicitly stated.

## 2. Four lanes

### A — GROUNDED_CONNECTION
Directly relevant past Experience / Decision / Outcome.

### B — PATTERN_CHALLENGE
Repeated pattern, contradiction, exception, failure condition, stage mismatch.

### C — STRUCTURAL_ANALOGY
Different topic but similar problem structure / trade-off / failure mode.

### D — EXPLORATORY_JUMP
Combination, inversion, unexplored possibility; clearly hypothesis-labeled.

## 3. Discovery Candidate schema

```yaml
discovery:
  object_id:
  object_type: DISCOVERY_CANDIDATE
  lane:
  statement:
  evidence_refs: []
  evidence_confidence:
  discovery_distance:
  decision_utility:
  novelty:
  temporal_fit:
  status: GROUNDED | HYPOTHESIS
  pattern_refs: []
  current_decision_context_ref:
  generator_version:
```

Envelope applies.

## 4. Ranking axes stay separate

Never collapse into one opaque score:
- Evidence Confidence
- Discovery Distance
- Decision Utility
- Novelty
- Diversity
- Temporal/Stage Fit

Evidence Confidence and Discovery Distance are explicitly independent.

## 5. Pattern Candidate / Challenger

Pattern candidate heuristic:
- multiple independent Decision Cases
- initial guide ≈ 3+ cases
- preferably 2+ contexts

Pattern must include:
- supporting cases
- contradicting cases
- exceptions
- context conditions
- temporal trend

Threshold is P0-tunable, not permanent law.

Pattern Challenger checks:
- failure examples
- opposite choices
- recent trend changes
- stage mismatch
- success/failure conditions

## 6. Structural Analogy

May use abstract structure projections such as:
- Proxy Metric Problem
- Cold Start
- Exploration vs Exploitation
- Cost vs UX
- Speed vs Trust
- Product Proof before Expansion
- Reversibility
- Outcome Optimization

Exact retrieval technology (FTS/vector/model) remains implementation spike.

Every analogy must trace to concrete evidence refs.

## 7. Exploratory Jump

Allowed only as HYPOTHESIS.

Low evidence + long distance must never be phrased as personal fact/decision.

## 8. Diversity selection

Select 0–3 candidates.

Preferred mix when quality exists:
- one grounded
- zero to two from challenge/analogy/jump

Do not fill quota when quality is insufficient.

## 9. No-Aha contract

Valid result:

```text
NO_DISCOVERY_WORTH_SURFACING
```

Aha count is not a target. Hallucinated novelty is worse than silence.

## 10. Eligibility / policy

Candidate evidence must pass:
- deletion eligibility
- promotion/current-state eligibility
- scope
- sensitivity
- temporal fit

B8 generation does not grant egress. B9/A7/A8 still decide what can leave TSUZU.

## 11. False Personal Assertion guard

Discovery statement must not say:
- “you always...”
- “you decided...”
- “you dislike...”

unless evidence supports that exact claim and confidence/temporal context justify it.

Otherwise language must reflect:
- observed range
- possibility
- hypothesis
- historical/conditional context

## 12. Golden cases

1. direct past relevant case → Grounded.
2. repeated pattern + counterexample → Pattern/Challenge includes exception.
3. unrelated topic with same trade-off → Analogy, evidence traced.
4. creative combination → Jump/HYPOTHESIS.
5. no strong candidate → No-Aha.
6. superseded principle only → not presented as current.
7. tombstoned support → unavailable.
8. pattern with only one case → no strong repeated-pattern claim.
9. unobserved blind spot → phrased “within observed evidence”, not fact.
10. assistant-generated principle without user evidence → cannot support strong personal claim.
11. high distance + low confidence → hypothesis label.
12. three similar candidates → diversity reduces redundancy.

## 13. Implementation tasks

### B8.1 Current Decision Structure extractor
### B8.2 Evidence retrieval interface / spike
### B8.3 Pattern Candidate + Challenger
### B8.4 Four-lane generators
### B8.5 Multi-axis scorer/diversity selector
### B8.6 False Personal Assertion validator
### B8.7 Golden/adversarial tests

## 14. Acceptance criteria

1. four lanes remain distinguishable.
2. evidence confidence != discovery distance.
3. candidate has evidence refs.
4. Pattern contains contradictions/exceptions.
5. No-Aha works.
6. low-confidence jump is hypothesis-labeled.
7. tombstoned/superseded evidence is not misused.
8. output count <=3.
9. B9 can consume eligible Discovery Candidates without reinterpreting evidence.

## 15. Gate to B9

At least Grounded, Challenge, Analogy, Jump and No-Aha fixtures must pass with evidence trace and assertion safety.

## 16. One-line contract

> B8は、過去を正解として再生せず、根拠・例外・距離を分離した4種類の発見候補を0〜3件だけ生成し、価値ある接続がないときは何も出さない。
