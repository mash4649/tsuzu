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
