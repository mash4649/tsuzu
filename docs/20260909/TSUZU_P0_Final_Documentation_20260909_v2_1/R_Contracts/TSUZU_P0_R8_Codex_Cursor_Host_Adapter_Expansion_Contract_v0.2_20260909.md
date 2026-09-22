# TSUZU P0 R8 — Codex / Cursor Host Adapter Expansion Contract v0.2

- Date: 2026-09-09
- Status: **Implementation Contract / Closed / Ready for host-specific verification**
- Canonical basis: v1.2 Claude Code/Codex/Cursor target + v1.2.1 ONE Host first / shared Adapter / remaining Hosts after initial proof-capable slice + v1.2.2 cross-cutting closure where applicable
- Dependencies: C6 Capability Registry/Router, A7-A9 common host boundary, B1 Chronicle, B9 Injection, R6 Trusted Intent
- Scope: common adapter contract and parity gates for adding Codex and Cursor after Claude Code
- Non-scope: requiring all three hosts before first Founder test, cloud relay, mobile/web chat bidirectional integration

## v0.2 cross-cutting closure

R8 owns Host-specific verification/mapping. C6 owns the shared capability vocabulary, registry, invalidation and router. `CapabilityReporter` MUST publish into C6 and cannot be treated as an authorization grant.


---

# 0. Decision

R8 does not assume that Codex and Cursor expose identical hooks/APIs.

P0 fixes the **behavioral Host Adapter contract**, then each host publishes a truthful capability report based on implementation-time verified host features.

Missing host capability degrades that feature; it does not cause the adapter to fake observation/injection fidelity.

---

# 1. Common Host Adapter capabilities

```yaml
host_capabilities:
  explicit_recall:
  context_injection:
  conversation_chronicle:
  structured_user_event:
  artifact_observation:
  project_scope_identity:
  session_identity:
  source_trace_rendering:
  passive_recall_trusted_intent:
```

Each value:

```text
SUPPORTED | PARTIAL | UNSUPPORTED | DISABLED_BY_POLICY
```

---

# 2. Required P0 baseline per added Host

A Host may be considered `TSUZU_RECALL_CAPABLE` when it supports:

- explicit recall through the common retrieval/egress path;
- trustworthy destination identity;
- bounded context return;
- Source/Context Trace;
- scope that cannot silently widen beyond user grant.

Chronicle/Passive Recall may be added independently only when their own evidence requirements are met.

---

# 3. Host descriptor

```yaml
host_descriptor:
  host_id: CODEX | CURSOR
  adapter_id:
  adapter_version:
  host_version_observed:
  destination_class: TRUSTED_EXTERNAL
  verified_at:
  capability_report_ref:
  supported_version_range:
```

If version leaves verified range, high-risk capabilities such as passive trusted-intent may automatically downgrade until reverified.

---

# 4. Common adapter interfaces

Conceptual interfaces:

```text
HostIdentityResolver
HostScopeResolver
ExplicitRecallBridge
ChronicleCaptureBridge
StructuredUserEventBridge
ContextInjectionBridge
ArtifactObservationBridge
SourceTraceRenderer
CapabilityReporter
```

Core logic remains in TSUZU, not duplicated per Host.

---

# 5. Destination / sensitivity

Codex and Cursor are treated as `TRUSTED_EXTERNAL` only when registered/known under A7 policy.

That still means:

- PERSONAL may egress under allowed capability;
- SENSITIVE external default deny;
- RESTRICTED deny;
- unknown destination/version/integration identity fails closed for protected content.

Vendor-side privacy settings do not replace TSUZU authorization.

---

# 6. Scope mapping

Host adapter must derive a typed scope from trustworthy host metadata where possible:

```yaml
host_scope:
  scope_type: GLOBAL | PROJECT
  scope_id:
  evidence: STRUCTURED_HOST_METADATA | USER_BOUND_CONFIG
```

A repository path string found in conversation content cannot grant scope.

If host cannot provide trustworthy project identity:

```text
GLOBAL_ONLY or explicit user-bound scope
```

never silent broadening.

---

# 7. Conversation Chronicle mapping

Chronicle requires ordered actor/event capture with enough fidelity for B1/B2.

Adapter must identify:

- user vs assistant vs tool/system event;
- session/thread identity;
- timestamp/order;
- scope;
- capture completeness/coverage.

If only partial conversation access is available, mark `PARTIAL` and propagate evidence-coverage bias. Do not infer missing user acceptance.

---

# 8. Structured user event / R6

Passive Recall is enabled per Host only if adapter can independently prove a structured current user-originated event suitable for R6 token minting.

If not:

```text
explicit recall works
passive recall = EXPLICIT_APPROVAL_ONLY or DISABLED
```

Never parse arbitrary conversation text to fabricate `USER_PROMPT` origin.

---

# 9. Artifact observation

Artifact/file/project observations are allowed only when:

- user explicitly granted relevant watch/read scope;
- host exposes trustworthy artifact event/path identity;
- content is treated as untrusted data;
- observation does not imply write permission.

If host lacks reliable event support, do not emulate by scanning the entire filesystem by default.

---

# 10. Common Recall contract

Where host tool protocol permits, expose behavior equivalent to A9 `tsuzu_recall`:

```yaml
input:
  query:
  requested_scope_if_supported:

output:
  bounded_context:
  source_trace:
  no_result_reason:
```

Exact MCP/tool/function mechanism may differ, but semantics and A7/A8 gates do not.

---

# 11. Context injection

Host-specific injection must preserve:

- content role = untrusted/user-memory data, not authority;
- bounded context;
- source IDs/traces;
- current policy revalidation;
- B8 lane/confidence semantics for discovery;
- R6 trusted-intent requirement for passive mode.

---

# 12. Capability Report

Implementation generates a body-free report:

```yaml
host_capability_report:
  host_id:
  host_version:
  adapter_version:
  verified_at:
  official_or_primary_docs_checked: []
  capabilities:
    explicit_recall: SUPPORTED
    conversation_chronicle: ...
    structured_user_event: ...
    passive_recall_trusted_intent: ...
  limitations: []
  regression_fixture_version:
```

This report is the truth; marketing/UI cannot claim unsupported capability.

---

# 13. Reconnect / failure behavior

- connector unavailable -> local TSUZU data remains safe;
- host version incompatible -> disable affected capability, not entire Vault;
- hook/event missed -> mark Chronicle coverage incomplete;
- malformed host event -> discard/fail closed, not reclassify by text guess;
- source trace rendering unavailable -> explicit recall may return structured trace data but capability is PARTIAL;
- tool protocol error -> distinguish no-result from system failure.

---

# 14. Host parity matrix

Required comparison against Claude Code baseline:

| Capability | Claude baseline | Codex | Cursor |
|---|---|---|---|
| Explicit recall | reference | verify | verify |
| A7/A8 policy/trace | reference | mandatory | mandatory |
| Chronicle | B1 reference | verify | verify |
| User-event provenance | R6 reference | verify | verify |
| Passive recall | conditional | conditional | conditional |
| Artifact observation | conditional | verify | verify |
| Project scope | constrained | verify | verify |

`verify` is not permission to assume support.

---

# 15. Golden Cases per Host

## R8-G1 Explicit Recall Parity
Same canonical fixture/query -> same eligible Source set before host formatting.

## R8-G2 SENSITIVE Deny Parity
No host adapter bypasses A7.

## R8-G3 Tombstone Parity
Deleted Source never appears.

## R8-G4 Scope Broadening Attempt
Host metadata/content cannot widen user grant.

## R8-G5 Chronicle Actor Fidelity
Captured events preserve user/assistant/tool roles or mark unsupported/partial.

## R8-G6 Missing User-event Provenance
Passive Recall remains disabled/approval-only.

## R8-G7 Host Upgrade
Unverified incompatible version downgrades risky capabilities until verification.

## R8-G8 Prompt Injection
Repository/tool content cannot mint R6 intent or alter adapter policy.

## R8-G9 Trace Parity
Every egress has Context Trace/host destination identity.

## R8-G10 Capability Honesty
Unsupported feature is reported as unsupported, never silently emulated with broader observation.

---

# 16. Implementation-time source verification

For each Host, before implementation/enabling a capability:

1. check current primary/official documentation;
2. record host/version and supported interface;
3. create minimal spike fixture;
4. verify scope/event ordering/failure behavior;
5. update Capability Report;
6. run parity/security tests.

Host-specific details belong in implementation notes/ADR, not in this stable behavioral Contract.

---

# 17. Implementation tasks

- R8.1 common HostAdapter type/capability model
- R8.2 Codex source verification/spike
- R8.3 Codex adapter + parity tests
- R8.4 Cursor source verification/spike
- R8.5 Cursor adapter + parity tests
- R8.6 capability/version downgrade logic
- R8.7 R6 trusted-intent integration per host
- R8.8 capability reports + UI projection

---

# 18. Acceptance criteria

- [ ] Codex/Cursor share a common behavioral adapter contract with Claude Code.
- [ ] host-specific APIs/hooks do not leak into TSUZU Core contracts.
- [ ] every enabled capability has implementation-time verification evidence.
- [ ] missing capabilities are truthfully downgraded, not guessed.
- [ ] all hosts preserve A7/A8 deletion/sensitivity/trace invariants.
- [ ] R6 passive mode is enabled only with trustworthy user-event provenance.
- [ ] project scope cannot be inferred from untrusted content.
- [ ] capability report is versioned and visible to R7.
- [ ] R8-G1..G10 pass per enabled Host.

---

# 19. Explicit non-goals

- making three-host QA a first-Founder-test blocker;
- requiring feature-perfect host parity;
- remote/cloud relay;
- host write/action permissions;
- filesystem-wide observation to compensate for missing hooks.

---

# 20. Source-derived vs closure decisions

## Canonical source-derived
- Claude Code/Codex/Cursor share adapter architecture;
- one Host first;
- remaining two added after first proof-capable operation;
- three-host formal QA not Founder entry gate;
- observation is allowlisted;
- host-specific hook methods are spike concerns.

## R8 closure decisions
- truthful per-host Capability Report;
- unsupported features degrade independently;
- host/version compatibility can downgrade risky capabilities;
- R6 passive support requires structured user-event provenance per Host;
- parity defined at policy/result semantics, not identical API mechanics.

---

# 21. One-line contract

> **R8 lets TSUZU follow the user from Claude Code to Codex and Cursor without pretending the hosts are identical: the Core contract stays stable, each adapter proves only the capabilities its current host version can actually support, and safety semantics remain identical.**
