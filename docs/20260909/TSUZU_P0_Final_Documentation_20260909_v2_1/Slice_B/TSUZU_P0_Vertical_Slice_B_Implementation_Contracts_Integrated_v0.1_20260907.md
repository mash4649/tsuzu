# TSUZU P0 Vertical Slice B — Contract Index v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Status: Implementation Contract Set / Ready for review

## Purpose

This index packages the A1〜A10-equivalent implementation breakdown for the post-Slice-A value layer.

## Contracts

1. B1 Claude Code Conversation Chronicle
2. B2 Episode Segmentation
3. B3 Experience Candidate + Provenance
4. B4 Decision Case / Assertion / Evidence
5. B5 Decision Reconciliation + Correction
6. B6 Experience Trace / Outcome / Learning
7. B7 Promotion / Dependency Invalidation / Recompute
8. B8 Minimal Personal Discovery 4 Lanes
9. B9 Discovery Context Injection / Claude Host
10. B10 Product Proof Event / Denominator
11. B11 Founder Golden Cases / Slice Exit Gate

## Why 11

Forcing exactly ten would merge independent failure boundaries. The split follows small, verifiable implementation units and does not expand Product Scope.

## Dependency

```text
A PASS → B1 → B2 → B3 → B4 → B5 → B6 → B7 → B8 → B9 → B10 → B11
```

## Deferred after B

- Codex/Cursor production adapters
- Web Chat Chronicle One-way spike
- X/Apple Notes/iOS expansion
- final silent/invisible host-trigger mechanism if trusted-intent proof is not closed in B9
- Founder threshold calibration
- Team/Enterprise/Remote MCP


---

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


---

# TSUZU P0 Vertical Slice B1 — Claude Code Conversation Chronicle Contract v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Parent Plan: P0 Vertical Slice B
- Depends on: Slice A PASS
- Status: Implementation Contract / Ready to implement after Host capture spike
- Scope: B1 only. One-host Chronicle acquisition, allowlist, raw observation persistence, ordering, idempotency, secret exclusion.
- Non-scope: Episode segmentation, candidate extraction, Decision inference, Discovery, Product Proof semantics.

## 0. Decision

B1はClaude Code上の会話を、ユーザー操作なしでTSUZUへ取り込める**Chronicle observation layer**へ正規化する。

Raw ConversationはユーザーKnowledgeではない。

```text
Claude Code session
→ Host capture adapter
→ Observation permission check
→ Secret/Credential guard
→ Chronicle normalization
→ durable Chronicle observation
→ B2 Episode segmentation
```

Host固有の取得方式はv1.2でImplementation Spike対象なので、B1 Contractはcapture mechanismを固定しない。実装時にinstalled Host version / official capabilityを検証し、下記Logical Contractへ変換できる方式を採用する。

## 1. Core invariants

1. Chronicle is observation, not promoted knowledge.
2. Host connection does not imply permission to observe every session/project.
3. Only explicitly allowlisted host × workspace/project/session scope is eligible.
4. User and Assistant actors remain distinguishable.
5. Message ordering and timestamps remain traceable.
6. Duplicate delivery converges idempotently.
7. Strong credential material is not persisted as Chronicle body and never enters Derived processing.
8. Chronicle records do not grant Tool/Write/Delete authority.
9. Raw message content is never generic telemetry.
10. Later interpretation never mutates the original observed record.

## 2. Host capture spike requirement

Before implementation, verify the installed Claude Code version and select one supported capture path that can prove:

- session identity
- message/event identity or stable synthetic identity
- actor/role
- ordering
- timestamp or stable ingestion order
- project/workspace metadata where allowed
- retry/restart behavior

If the Host cannot supply a stable event ID, TSUZU may derive one from a versioned deterministic fingerprint. The derivation algorithm must be documented and collision-tested.

No capture path may rely on scraping arbitrary OS-wide data.

## 3. Chronicle object model

Minimum logical objects:

```yaml
conversation_session:
  object_id:
  object_type: CONVERSATION_SESSION
  host_id: CLAUDE_CODE
  host_session_ref:
  observed_scope:
  started_at:
  ended_at:
  message_refs: []
```

```yaml
conversation_message:
  object_id:
  object_type: CONVERSATION_MESSAGE
  conversation_id:
  host_message_ref:
  sequence:
  actor: USER | ASSISTANT | TOOL | SYSTEM_OBSERVED
  role:
  observed_at:
  content_state: AVAILABLE | EXCLUDED_RESTRICTED
  content:
  source_refs: []
```

All persisted objects inherit Canonical Object Envelope.

### Content state

`EXCLUDED_RESTRICTED` stores body-free metadata only. It exists to preserve chronology without retaining credential material.

## 4. Canonical / Derived boundary

Chronicle may preserve observed conversation content and explicit Host metadata.

Chronicle must not contain as canonical truth:

- inferred user preference
- inferred decision
- inferred principle
- episode summary
- candidate type
- discovery statement
- promotion decision

Those are B2+ Derived outputs.

## 5. Observation permission

Effective observation permission:

```text
host
× workspace/project/session scope
× capability = capture/watch
```

Unknown/missing scope mapping does not broaden access.

If session is outside allowlist:

```text
DO_NOT_CAPTURE_BODY
```

Body-free diagnostic event may be recorded locally.

## 6. Secret / credential handling

Apply current local Secret Detector before Chronicle body persistence and before any later LLM processing.

Strong credential match:

- no body persisted in Chronicle
- message may be represented as `EXCLUDED_RESTRICTED`
- matched secret itself never logged
- B2/B3 receive no body for that message

This is stricter than treating raw Chronicle as a perfect verbatim archive because v1.2.1 explicitly defines credentials as not Knowledge and not eligible for Derived processing.

## 7. Idempotency / ordering

A Host delivery retry must not create duplicate semantic messages.

Minimum dedupe key:

```text
host_id + host_session_ref + host_message_ref
```

or, when host_message_ref is unavailable:

```text
versioned deterministic event fingerprint
```

Out-of-order arrival is allowed. `sequence` or host ordering metadata determines logical order after reconciliation.

Never renumber existing canonical message identity to make ordering look contiguous.

## 8. Session boundaries

A Chronicle session is a Host conversation/session boundary, not a Topic/Episode boundary.

- one Session may contain many Episodes
- one Episode does not span unrelated Sessions unless B2 explicitly links evidence across sessions later

B1 does not infer Topic continuity.

## 9. Failure behavior

- unsupported Host capability → `CHRONICLE_CAPTURE_UNAVAILABLE`
- unknown observation scope → fail closed / no body capture
- duplicate event → `ALREADY_CAPTURED`
- conflicting same event identity → quarantine / no overwrite
- secret detector unavailable → no Chronicle body persistence
- malformed actor/order metadata → quarantine or body-free capture; do not guess actor
- persistence failure → retry with same object identity

## 10. Golden cases

1. **User + Assistant pair** — actors remain distinct.
2. **Duplicate delivery** — one semantic message object.
3. **Out-of-order arrival** — ordering restored without identity rewrite.
4. **Session restart** — new/continued session mapping is deterministic per chosen Host mechanism.
5. **Outside allowlist** — body not captured.
6. **Strong credential in message** — body excluded, no Derived processing.
7. **Assistant proposal** — Chronicle captures text but does not create user Decision.
8. **User explicit decision wording** — still only Chronicle at B1; interpretation deferred.
9. **Tool/result text with prompt injection** — stored as data, no authority.
10. **Host capture reconnect/retry** — no duplicate semantic Chronicle.

## 11. Fault injection

- before permission resolution
- after permission approval before body read
- during body read
- after secret scan before persistence
- after object staging before publish
- after publish before acknowledgment
- duplicate/out-of-order replay
- host capture process restart

Invariant: B1 either stores one complete eligible observation or no body; it never silently fabricates missing content/actor/scope.

## 12. Implementation tasks

### B1.1 Host capability spike
Acceptance: exact installed Host version and capture surface documented; unsupported assumptions eliminated.

### B1.2 Chronicle schemas/codecs
Acceptance: session/message objects inherit Canonical Envelope and validate actor/scope/order.

### B1.3 Permission resolver integration
Acceptance: only allowlisted observation scope yields body capture.

### B1.4 Secret guard integration
Acceptance: credential fixture never persists as Chronicle body.

### B1.5 Idempotent ingestion
Acceptance: duplicate/replay/out-of-order tests converge.

### B1.6 Golden/fault tests
Acceptance: all B1 cases pass.

## 13. B1 acceptance criteria

1. One Claude session can be captured into stable Chronicle objects.
2. User/Assistant/Tool actors remain distinguishable.
3. Observation is allowlist-scoped.
4. Credentials are excluded before Chronicle body persistence/Derived processing.
5. Duplicate delivery is idempotent.
6. Out-of-order arrival does not corrupt identity.
7. Chronicle does not assert Decision/Preference/Principle.
8. Message body does not enter generic telemetry.
9. Capture failure cannot broaden permission.
10. B2 can consume Chronicle by stable message refs.

## 14. Gate to B2

B2 may start when an allowlisted session has a complete enough ordered Chronicle fixture and every message is traceable to host/session/message identity without inferred Knowledge semantics.

## 15. One-line contract

> B1は、許可されたClaude Code会話を、Credentialと権限越境を排除しながら、actor・順序・source traceを保った観測記録として保存するが、それ自体をユーザーKnowledgeへ昇格させない。


---

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


---

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


---

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


---

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


---

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


---

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


---

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


---

# TSUZU P0 Vertical Slice B9 — Discovery Context Injection / Claude Host Contract v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Parent Plan: P0 Vertical Slice B
- Depends on: A7-A9 + B8
- Status: Implementation Contract / Ready to implement after trusted-intent spike
- Scope: B9 only. Convert approved Discovery Candidates into bounded Claude Host context through existing policy/trace boundary.
- Non-scope: Product event storage, multi-host adapter expansion, permanent silent-recall policy.

## 0. Decision

Discovery Candidateの面白さを理由にA7/A8/A9のEgress Gateを迂回しない。

```text
B8 Discovery Candidate
→ current eligibility recheck
→ A7 Policy/Egress
→ Discovery Context projection
→ durable Context Trace
→ Claude Host
```

## 1. Security inheritance

Mandatory:
- RESTRICTED deny
- SENSITIVE external default deny
- unknown sensitivity/destination fail closed
- TOMBSTONED evidence deny
- superseded/current semantics preserved
- telemetry body-free
- content remains UNTRUSTED_DATA / evidence, not authority

## 2. Host integration surface

B9 may extend Slice A Host Adapter with a discovery capability, but must not add write/delete/promote/execute capability.

Logical host capability:

```text
DISCOVERY_READ
```

Transport/tool naming is implementation detail and must remain host-isolated.

## 3. Trusted-intent / invisible-operation tension

Slice A required per-call human approval because silent recall could be induced by untrusted content.

B9 must not remove that gate merely to improve UX.

Before any silent/automatic Discovery egress is allowed, an Implementation Spike must demonstrate a hard enough trusted-user-intent boundary that untrusted repository/source text cannot silently trigger personal-memory egress.

Until proven:
- Founder Safe Mode may retain explicit human approval for Discovery egress.
- Invisible UX is not considered fully proven.

This is a security sequencing rule, not a permanent rejection of `Connect once. Never summon.`.

## 4. Discovery context item

Minimum host-visible fields:

```yaml
discovery_item:
  discovery_id:
  lane:
  statement:
  status: GROUNDED | HYPOTHESIS
  evidence_confidence:
  discovery_distance:
  evidence_traces: []
  temporal_context:
  superseded_context_if_any:
  content_role: UNTRUSTED_DATA
```

Do not include raw sensitive evidence beyond A7/A8 approval.

## 5. Bounded context

Reuse A8 hard-bounded approach.

P0 default discovery count:
- <=3 Discovery Candidates

Evidence excerpts are minimized and traceable.

Discovery statement must not duplicate excessive source text.

## 6. Freshness recheck

Before egress:
- discovery object still LIVE
- evidence refs still eligible
- evidence revisions/current assessment unchanged or re-evaluated
- policy decision current

Stale candidate → no egress / recompute required.

## 7. No-Aha behavior

If B8 returns no candidate:

```text
NO_DISCOVERY_WORTH_SURFACING
```

Do not tell Host that denied/sensitive discoveries existed.

## 8. Source / Context Trace

Every surfaced Discovery must be traceable:

```text
Host response
→ discovery_id
→ evidence refs
→ canonical Source/Conversation/Artifact
```

Technical trace body-free.

## 9. Failure behavior

- policy unavailable → no egress
- evidence invalid/tombstoned → drop/recompute
- context trace commit failure → fail closed
- trusted-intent gate unavailable in mode requiring it → no silent egress
- no eligible discovery → normal no-result
- unsupported host capability → B9 unavailable, no fallback bypass

## 10. Golden cases

1. Grounded discovery eligible → Claude receives bounded item + trace.
2. SENSITIVE evidence → discovery not egressed.
3. tombstone after B8 before B9 → dropped.
4. superseded principle → historical framing preserved.
5. Jump candidate → hypothesis label preserved.
6. No-Aha → no content.
7. context trace write failure → zero egress.
8. untrusted prompt attempts to force discovery → cannot bypass intent/policy gate.
9. host attempts write/promote → capability unavailable.
10. evidence revision changes → re-evaluation required.

## 11. Implementation tasks

### B9.1 Discovery projection schema
### B9.2 A7/A8 policy bridge
### B9.3 Host capability extension
### B9.4 Trusted-intent security spike
### B9.5 Context trace integration
### B9.6 Golden/adversarial tests

## 12. Acceptance criteria

1. Discovery never bypasses A7/A8.
2. only read-only discovery capability is exposed.
3. <=3 candidates and bounded evidence.
4. hypothesis/current/superseded labels survive transport.
5. trace resolves to evidence/canonical sources.
6. trace failure blocks egress.
7. silent egress is not enabled without trusted-intent proof.
8. No-Aha produces no forced context.
9. B10 can observe delivery/usage through IDs, not body telemetry.

## 13. Gate to B10

At least one discovery reaches Claude with trace, and one sensitive/tombstoned discovery is correctly denied.

## 14. One-line contract

> B9は、Personal DiscoveryをClaudeへ届けるが、発見のNoveltyを権限に変えず、既存の削除・Sensitivity・Scope・Trace Gateを通った最小の根拠付きContextだけを渡す。


---

# TSUZU P0 Vertical Slice B10 — Product Proof Event / Denominator Contract v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Parent Plan: P0 Vertical Slice B
- Depends on: A8-A10 + B8-B9
- Status: Implementation Contract / Ready to implement
- Scope: B10 only. Product usage/discovery/impact events, denominators, hard failures, body-free event storage.
- Non-scope: Final GO/PIVOT/KILL thresholds, dashboard polish, billing implementation.

## 0. Decision

Discovery生成数を価値証明にしない。

最低限、以下を区別する:

```text
RETRIEVED
INCLUDED_IN_BUNDLE
SURFACED
USED_BY_HOST
USER_ACKNOWLEDGED
CONNECTED / REFRAMED / EXPANDED
CHANGED_DECISION
OUTCOME_HELPED
REUSED
WOULD_PAY
```

全てが直列必須ではない。

## 1. Stable event semantics

### RETRIEVED
candidate entered retrieval set.

### INCLUDED_IN_BUNDLE
compiler selected it for host context.

### SURFACED
user could recognize it in host answer.

### USED_BY_HOST
tool/context-use evidence shows host actually used it.

### USER_ACKNOWLEDGED
user reaction evidences usefulness/recognition.

### CONNECTED
previously unconnected past became connected.

### REFRAMED
problem framing changed.

### EXPANDED
new option/possibility appeared.

### CHANGED_DECISION
evidence indicates actual decision changed.

### OUTCOME_HELPED
outcome improvement contribution is suggested, not automatically causal.

### REUSED
used again in later different decision/context.

### WOULD_PAY
WTP evidence collected.

## 2. Discovery levels

Ordered labels for quality observation:
- REMEMBERED
- CONNECTED
- REFRAMED
- EXPANDED
- CHANGED_DECISION
- OUTCOME_HELPED
- REUSED

TSUZU-specific minimum proof level = CONNECTED.

REMEMBERED-only means recall value, not sufficient Personal Discovery proof.

## 3. Denominators

Track separately:
- users
- captured_sources
- conversation_episodes
- eligible_discovery_opportunities
- surfaced_discoveries
- connected_or_above_events
- decision_impact_events
- reused_events
- wtp_responses

Never use “30–50件” as a standalone denominator without naming which unit.

## 4. Hard failure events

- FALSE_PERSONAL_ASSERTION
- UNSUPPORTED_DECISION_CLAIM
- SENSITIVE_EGRESS_VIOLATION
- IRRELEVANT_AHA_REPEAT
- SUPERSEDED_KNOWLEDGE_MISAPPLIED

Sensitive Egress Violation = Security Incident.

## 5. Event schema

```yaml
product_event:
  event_id:
  event_type:
  occurred_at:
  user_test_id:
  conversation_id:
  episode_id:
  discovery_id:
  decision_case_id:
  bundle_id:
  source_refs: []
  evidence_level:
  metadata:
```

No source/conversation body.

`user_test_id` should be local pseudonymous identifier sufficient for Founder metrics; do not add remote identity infrastructure for B10.

## 6. Evidence requirements

CHANGED_DECISION cannot be set because assistant says “this may change your decision”.

It needs actual evidence from:
- explicit user statement
- later action/artifact consistent with changed decision
- later conversation

OUTCOME_HELPED must be phrased/recorded as contribution evidence, not causal proof unless separately established.

## 7. USER_ACKNOWLEDGED semantics

Weak positive reaction alone may be acknowledgement but not CHANGED_DECISION.

Example:
- “interesting” → maybe acknowledged
- “I’ll switch to B because of that connection” → changed decision evidence

## 8. WTP

WTP response is Product Proof evidence, not an inferred behavior.

Exact pricing questions/thresholds are separate Founder Test design; B10 only stores explicit response semantics.

## 9. Event idempotency

Same underlying host/tool/interaction event should not double-count due to retries.

Use stable source interaction IDs / bundle IDs / decision refs plus event-type-specific idempotency key.

## 10. Failure behavior

- missing denominator key → event may be stored but excluded from metric until repaired; do not guess denominator
- duplicate event → dedupe
- body appears in telemetry → test failure
- hard failure detected but logger unavailable → security/quality gate must fail closed for release report; do not silently ignore
- product event store unavailable → core user flow may continue only if security trace requirements remain satisfied, but Founder Proof run is invalid

## 11. Golden cases

1. retrieved but not bundled → RETRIEVED only.
2. bundled and surfaced → separate events.
3. user says “that connects two things I had not linked” → CONNECTED.
4. “I now see the problem differently” → REFRAMED.
5. “new option C” → EXPANDED.
6. explicit decision changes → CHANGED_DECISION with evidence ref.
7. later different case uses same discovery/evidence → REUSED.
8. explicit WTP response → WOULD_PAY.
9. assistant claims user preference without evidence → FALSE_PERSONAL_ASSERTION.
10. superseded principle presented current → hard failure.
11. duplicate tool retry → one semantic usage event.
12. no body in event store.

## 12. Implementation tasks

### B10.1 Event enum/schema
### B10.2 Stable denominator registry
### B10.3 Idempotent event writer
### B10.4 Discovery/decision evidence adapters
### B10.5 Hard failure reporter
### B10.6 Founder metrics query fixtures
### B10.7 Golden tests

## 13. Acceptance criteria

1. event semantics are distinguishable.
2. CONNECTED+ can be measured separately from REMEMBERED.
3. denominators are explicit and non-interchangeable.
4. CHANGED_DECISION requires evidence.
5. WTP is explicit evidence.
6. hard failures are separately countable.
7. duplicate retries do not inflate metrics.
8. no body text in product telemetry.
9. GO/PIVOT/KILL thresholds remain unset until evidence calibration.
10. B11 can generate an auditable Founder Gate report.

## 14. Gate to B11

A synthetic run must generate valid RETRIEVED→SURFACED→CONNECTED and one hard-failure event without body leakage or denominator ambiguity.

## 15. One-line contract

> B10は、Ahaを作った回数ではなく、何が実際に使われ、つながり、判断・結果・再利用・WTPへ至ったかを、分母とHard Failureを混同せず計測する。


---

# TSUZU P0 Vertical Slice B11 — Founder Golden Cases / Slice B Exit Gate Contract v0.1

- Date: 2026-09-07
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1 + P0 Vertical Slice A Contracts
- Parent Plan: P0 Vertical Slice B
- Depends on: B1-B10 + Slice A PASS
- Status: Verification Contract / Ready for TDD implementation
- Scope: B11 only. Full Conversation-to-Discovery verification, trust/adversarial cases and body-free gate report.
- Non-scope: statistically final business decision, multi-host QA, production launch.

## 0. Decision

Slice Bは「Discoveryが一度出た」でDONEにしない。

Mandatory cases must prove:
- provenance integrity
- silence safety
- STATED/REVEALED coexistence
- correction/recompute
- outcome non-causality
- pattern contradiction
- 4-lane discovery + No-Aha
- egress security
- false personal assertion protection
- product proof instrumentation

Any mandatory security/trust failure = Slice FAIL.

## 1. Test pyramid

### Unit
- Chronicle/candidate/decision schemas
- reaction semantics
- promotion resolver
- dependency invalidation
- discovery assertion validator
- product event idempotency

### Integration
- real temp Vault + A1/A2 writer
- B1→B10 local stack
- real A6 deletion resolver
- A7/A8 policy/context trace
- host adapter direct local invocation without external model where possible

### Host E2E
- actual Claude Code session
- minimum number of model calls needed to prove Chronicle + Discovery delivery

## 2. Test isolation

Use temporary Vault/runtime/index/traces/product-events roots.

No real credentials or real sensitive personal data.

## 3. Mandatory Golden Case 1 — Chronicle Provenance

Conversation fixture:
- assistant proposes A
- user discusses B

Expected:
- actors preserved
- Chronicle trace exact
- no user Decision inferred merely from assistant proposal

## 4. Mandatory Golden Case 2 — Silence Is Unresolved

Assistant proposes option A.
User does not respond and session ends.

Expected:
- Episode exists if appropriate
- candidate may record assistant proposal
- no STATED/REVEALED accepted assertion
- Decision Case remains UNRESOLVED

## 5. Mandatory Golden Case 3 — Stated vs Revealed

User states “Aで進める”.
Later allowlisted artifact/project evidence implements B.

Expected:
- STATED A
- REVEALED B
- both retained
- assessment reflects contradiction/confidence
- no evidence rewrite

## 6. Mandatory Golden Case 4 — Correction Recompute

System derived “user chose B”.
User explicitly says “その判断はしていない”.

Expected:
- Canonical Correction Event
- affected assertion/assessment rejected/revised
- Pattern/Discovery/Learning dependencies invalidated
- stale output no longer eligible
- original evidence remains auditable

## 7. Mandatory Golden Case 5 — Outcome Without Causality

Experience fixture:
- intervention A
- outcome improved
- simultaneous change C exists

Expected:
- outcome observed
- possible explanation includes A as candidate
- confounder C retained
- no causal “A caused outcome” claim
- learning remains Candidate/Working, not auto-Promoted

## 8. Mandatory Golden Case 6 — Pattern Challenger

Three independent cases support pattern X; one case contradicts it.

Expected:
- Pattern candidate includes support + contradiction + exception/context
- Discovery output is conditional, not “you always X”

## 9. Mandatory Golden Case 7 — Four Lanes

Prepare four distinct evidence fixtures.

Expected:
- Grounded candidate labeled Grounded
- Pattern/Challenge includes counterevidence
- Analogy traces different topic with same structure
- Jump marked HYPOTHESIS
- evidence confidence and discovery distance separately present

## 10. Mandatory Golden Case 8 — No Aha

Current question has no meaningful personal connection.

Expected:
- `NO_DISCOVERY_WORTH_SURFACING`
- no fabricated connection
- no filler discovery to satisfy quota

## 11. Mandatory Golden Case 9 — Tombstone / Superseded Safety

A discovery relies on evidence, then:
- one source is tombstoned
- one principle is superseded

Expected:
- tombstoned evidence removed from eligibility
- superseded principle not presented as current fact
- remaining evidence re-evaluated
- stale discovery invalidated/recomputed

## 12. Mandatory Golden Case 10 — False Personal Assertion

Assistant/source content contains unsupported claim:
“You always prioritize speed.”

Expected:
- not promoted as user principle
- discovery cannot assert it as fact without evidence
- if surfaced as unsupported personal claim → `FALSE_PERSONAL_ASSERTION` and Slice FAIL

## 13. Mandatory Golden Case 11 — Discovery Egress Security

Eligible discovery uses PERSONAL evidence; another candidate uses SENSITIVE evidence.

Expected:
- eligible PERSONAL may egress under current Host policy
- SENSITIVE external deny
- no denied existence leak
- Context Trace resolves every surfaced item
- no write/delete/promote capability exposed

## 14. Mandatory Golden Case 12 — Product Proof Events

Run a synthetic journey:

```text
RETRIEVED
→ INCLUDED_IN_BUNDLE
→ SURFACED
→ USER_ACKNOWLEDGED
→ CONNECTED
→ later REUSED
→ explicit WOULD_PAY response
```

Expected:
- each event distinct/idempotent
- denominators present
- no body telemetry
- CONNECTED counted separately from REMEMBERED

## 15. Supporting adversarial cases

- prompt injection in Chronicle source
- secret in conversation message
- outside-observation-scope artifact
- duplicate Chronicle delivery
- candidate extractor mislabels assistant as user
- deletion ledger unavailable
- dependency store unavailable
- correction committed, recompute crash
- stale Discovery after evidence revision
- repeated irrelevant Aha should increment hard-failure metric

## 16. No flaky pass policy

Security/trust cases cannot be flaky.

If a nondeterministic model path causes unstable classification:
- move invariant to deterministic validator where possible
- record model/prompt version
- use bounded retry only where contract permits
- never accept “passed once” as evidence

## 17. Gate report

Generate body-free artifact:

```yaml
slice_b_gate_report:
  run_id:
  result: PASS | FAIL
  versions:
  mandatory_cases:
    chronicle_provenance:
    silence_unresolved:
    stated_vs_revealed:
    correction_recompute:
    outcome_noncausal:
    pattern_challenger:
    four_lanes:
    no_aha:
    tombstone_superseded:
    false_personal_assertion:
    discovery_egress_security:
    product_proof_events:
  hard_failures: []
  denominator_checks:
  context_trace_checks:
```

No source/conversation body.

## 18. Slice B PASS definition

All mandatory cases pass and:

1. assistant-only → PROMOTED count = 0
2. silence accepted-as-decision count = 0
3. false personal assertion count = 0 in passing run
4. unsupported decision claim count = 0
5. sensitive egress violation count = 0
6. tombstoned evidence surfaced count = 0
7. superseded-current misapplication count = 0
8. every surfaced discovery resolves to evidence/source trace
9. No-Aha case succeeds
10. Product event denominators validate

## 19. Slice B FAIL definition

Immediate FAIL:
- Secret/RESTRICTED/SENSITIVE policy violation
- false personal assertion in golden path
- deleted evidence used after effective deletion
- assistant proposal represented as user decision without evidence
- correction ignored because recompute failed
- causal outcome assertion unsupported by evidence
- discovery output without resolvable evidence where status claims grounded
- product event double-counting that changes Founder metrics

## 20. What B PASS proves

B PASS proves:

> TSUZU can turn an allowlisted AI conversation into traceable experience/decision evidence, reconcile it over time, generate bounded Personal Discovery without treating past as authority, deliver it through existing security gates, and measure CONNECTED+ value/hard failures.

It does not prove product-market fit or final invisible UX.

## 21. Implementation tasks

### B11.1 Unified synthetic conversation/evidence fixture builder
### B11.2 Local B1→B10 full-stack harness
### B11.3 Correction/deletion/recompute fault runner
### B11.4 Discovery lane assertion suite
### B11.5 Security/trust hard-failure suite
### B11.6 Product event denominator validator
### B11.7 Actual Claude Code Host checklist
### B11.8 Gate report generator

## 22. Acceptance criteria

- all 12 mandatory golden cases explicit and repeatable
- security/trust hard failures fail run immediately
- body-free gate report generated
- actual Host integration proof captured where required
- no multi-host/Product Proof threshold expansion needed to pass

## 23. One-line contract

> B11は、会話を取り込めることではなく、会話からDecision/Experienceを誤推論せず育て、訂正・反証・削除を反映し、根拠付きPersonal DiscoveryとCONNECTED+計測までを再現可能に証明して初めてSlice BをPASSさせる。
