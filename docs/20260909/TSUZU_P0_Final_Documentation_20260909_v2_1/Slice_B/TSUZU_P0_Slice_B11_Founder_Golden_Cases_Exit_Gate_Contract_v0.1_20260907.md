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
