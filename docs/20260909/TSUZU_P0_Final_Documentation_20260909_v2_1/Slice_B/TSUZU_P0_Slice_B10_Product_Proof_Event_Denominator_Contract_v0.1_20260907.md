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
