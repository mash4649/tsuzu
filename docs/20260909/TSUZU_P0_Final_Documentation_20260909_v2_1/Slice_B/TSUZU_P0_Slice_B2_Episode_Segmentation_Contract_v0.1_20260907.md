# TSUZU P0 Vertical Slice B2 — Episode Segmentation Contract v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Parent Plan: P0 Vertical Slice B
- Depends on: B1
- Status: Implementation Contract / Ready to implement
- Scope: B2 only. Derived Episode boundaries and traceability from Chronicle.
- Non-scope: Candidate extraction, Decision assertion, Promotion, Discovery.

## 0. Decision

1 Message = 1 Memoryを禁止し、同一論点の提案・比較・反論・修正・結論を1つのDerived Episodeとしてまとめる。

EpisodeはAI解釈を含むDerived Objectであり、Raw Chronicleを変更しない。

## 1. Core invariants

- Episode is DERIVED.
- Every Episode resolves to one or more Chronicle message refs.
- Episode boundary confidence is separate from message truth.
- Segmentation never converts assistant text into user fact/decision.
- Re-segmentation creates a new revision/generation; Chronicle remains unchanged.
- Tombstoned/unavailable Chronicle refs cannot remain silently active evidence.

## 2. Episode schema

```yaml
episode:
  object_id:
  object_type: EPISODE
  processing_state: DERIVED
  conversation_refs: []
  message_refs: []
  start_observed_at:
  end_observed_at:
  topic_label:
  working_summary:
  segmentation:
    algorithm_version:
    confidence:
  evidence_coverage:
    included_message_count:
    excluded_restricted_count:
```

All persistent Episode objects inherit Canonical Object Envelope.

`topic_label` / `working_summary` are Derived, not user-authored truth.

## 3. Segmentation semantics

Episode should capture a coherent decision/problem thread, not merely temporal adjacency.

Signals may include:
- stable problem/question
- same option comparison
- user correction/refinement
- explicit transition to a new problem
- session boundary as weak separator, not semantic proof

Exact model/prompt/threshold is Implementation Spike and must be versioned.

## 4. Restricted gaps

If one or more Chronicle messages are `EXCLUDED_RESTRICTED`:

- Episode may preserve that a gap exists
- must not infer the missing secret content
- evidence_coverage reflects excluded messages
- downstream confidence may be reduced

## 5. Determinism and regeneration

Same Chronicle input + same segmentation version should be reproducible enough to audit.

If model nondeterminism is used:
- persist algorithm/model/prompt version
- preserve source refs
- allow full regeneration from Chronicle
- never treat Episode text as Canonical truth

## 6. Deletion / correction interaction

Chronicle deletion or tombstone triggers Episode invalidation through B7 dependency tracking.

B2 does not physically cascade delete raw Chronicle.

## 7. Failure behavior

- missing message ref → Episode invalid / no downstream use
- actor unknown → no confident Episode interpretation
- all body unavailable → no semantic Episode generation
- segmentation model unavailable → queue for retry; Chronicle remains intact
- invalid output schema → reject Derived Episode, do not coerce

## 8. Golden cases

1. one coherent topic across 6 messages → one Episode.
2. two clearly different topics → two Episodes.
3. user rejects assistant proposal within same topic → same Episode.
4. user changes topic explicitly → boundary.
5. assistant monologue followed by no user response → Episode exists but no accepted Decision.
6. restricted message gap → coverage gap retained.
7. resegmentation version change → new Derived revision/generation, same Chronicle refs.
8. deleted Chronicle message → Episode invalidated/recomputed.
9. same topic across separate host sessions → not automatically merged in B2.
10. prompt-injection-like content → segmentation treats as data.

## 9. Implementation tasks

### B2.1 Episode schema + validator
### B2.2 Segmentation input builder
### B2.3 Versioned segmentation engine interface
### B2.4 Coverage / trace resolver
### B2.5 Regeneration / invalidation hook
### B2.6 Golden/fault tests

## 10. Acceptance criteria

1. Episode is traceable to Chronicle refs.
2. 1-message=1-memory assumption is absent.
3. Episode summary is explicitly Derived.
4. Assistant text does not become user truth.
5. restricted gaps are not hallucinated.
6. segmentation version is recorded.
7. invalid/missing source refs prevent downstream use.
8. B3 can consume Episode refs and actor-aware Chronicle evidence.

## 11. Gate to B3

At least one multi-message Episode fixture must exist with correct actor/message trace and one fixture where silence remains unresolved.

## 12. One-line contract

> B2は、会話を1メッセージ単位の記憶へ砕かず、同一の問題・判断文脈をEpisodeとしてDerived化するが、境界や要約をCanonical truthにはしない。
