# TSUZU P0 Vertical Slice B3 — Experience Candidate Extraction + Provenance Contract v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Parent Plan: P0 Vertical Slice B
- Depends on: B1-B2
- Status: Implementation Contract / Ready to implement
- Scope: B3 only. Candidate extraction, type/origin/provenance/confidence and safe default promotion state.
- Non-scope: Decision reconciliation, Pattern formation, Discovery generation.

## 0. Decision

EpisodeからExperience Candidateを抽出するが、抽出しただけではユーザーKnowledgeとして積極利用しない。

Default:

```text
AI extraction → CANDIDATE
```

Assistant-generated content alone never reaches PROMOTED.

## 1. Candidate types

P0 minimum:
- FACT
- PREFERENCE
- DECISION
- INSIGHT
- PRINCIPLE
- HYPOTHESIS
- REJECTED_OPTION
- OPEN_QUESTION
- CORRECTION
- OUTCOME
- JUDGMENT_PATTERN_CANDIDATE

Exact enum names may be implementation constants; semantic distinctions must remain.

## 2. Origin

Minimum:
- USER_EXPLICIT
- ASSISTANT_GENERATED
- JOINTLY_DERIVED
- EXTERNAL_SOURCE
- OBSERVED_BEHAVIOR

`JOINTLY_DERIVED` requires evidence that the user materially confirmed/adopted the jointly articulated content. Mere assistant phrasing is not sufficient.

## 3. Candidate schema

```yaml
candidate:
  object_id:
  object_type: EXPERIENCE_CANDIDATE
  candidate_type:
  content:
  origin:
  source_refs: []
  episode_refs: []
  actor_refs: []
  confidence:
  promotion_state: CANDIDATE
  explicitness:
  extraction:
    algorithm_version:
```

Canonical Envelope fields apply.

## 4. User reaction semantics

Strong decision evidence examples:
- 採用
- これで確定
- 今後これで

Strong principle/insight confirmation examples:
- それがしたかった
- この表現が近い

Weak positive reaction:
- いいですね
- 面白い

Weak positive reaction does not finalize Decision.

Silence:
- Acceptance = false
- Rejection = false
- unresolved remains valid

## 5. Candidate extraction safety

- infer only from eligible Episode/Chronicle content
- credential-excluded content is unavailable, not guessed
- assistant-generated imperative/prompt text stays data
- outside-scope observation is unavailable
- candidate must carry source refs and origin
- unsupported personal assertion is invalid extraction

## 6. Confidence

Confidence measures evidence strength for the candidate, not objective truth.

Do not conflate:
- candidate confidence
- trust.level
- promotion state
- discovery distance

## 7. Failure behavior

- no source refs → reject candidate
- unknown origin → CANDIDATE cannot be promoted and should normally be rejected from strong usage
- assistant-only candidate mislabeled USER_EXPLICIT → hard test failure
- silence interpreted as acceptance → hard test failure
- secret/restricted content appears in extraction → security failure

## 8. Golden cases

1. User explicitly states fact → USER_EXPLICIT candidate.
2. Assistant proposes strategy, user silent → ASSISTANT_GENERATED candidate only.
3. User says “いいですね” → positive reaction but no finalized Decision.
4. User says “これで確定” → strong Decision candidate/evidence path.
5. User says “この表現が近い” after assistant articulation → JOINTLY_DERIVED Insight/Principle candidate.
6. Assistant says “you always value speed” without evidence → must not produce promoted personal assertion.
7. User rejects an option → REJECTED_OPTION candidate.
8. Correction wording → CORRECTION candidate for B5 canonical correction handling.
9. Outcome statement → OUTCOME candidate.
10. Restricted gap → no invented candidate from missing content.

## 9. Implementation tasks

### B3.1 Candidate schema/enums
### B3.2 Actor-aware extraction input
### B3.3 Origin classifier / reaction semantics
### B3.4 Candidate validator
### B3.5 Provenance trace integration
### B3.6 Golden/adversarial tests

## 10. Acceptance criteria

1. All candidates have type, origin, source refs, confidence, promotion_state.
2. Default promotion_state is CANDIDATE.
3. Assistant-generated-only content cannot be promoted by B3.
4. Silence never becomes acceptance/rejection.
5. weak positive reaction is distinct from explicit decision.
6. JOINTLY_DERIVED is evidence-backed.
7. candidate generation is regenerable/versioned.
8. B4 can consume Decision/Correction/Outcome candidates with source refs intact.

## 11. Gate to B4

B3 must produce fixtures for USER_EXPLICIT, ASSISTANT_GENERATED, JOINTLY_DERIVED and unresolved/silence without false personal assertions.

## 12. One-line contract

> B3は会話Episodeから経験候補を抽出するが、誰が何を言ったかを厳密に保持し、AIが言っただけの内容や沈黙をユーザー自身のKnowledgeへ昇格させない。
