# TSUZU P0 C6 — Capability Registry / Router Interface Contract v0.1

- Date: 2026-09-09
- Status: **Cross-cutting Interface Contract / Closed / Ready to implement**
- Canonical basis: v1.1 Capability Router Interface, Host Adapter Interface; v1.2.1 Observation allowlist and 1-host/3-host closure
- Depends on: A9 first Host evidence; R8 verifies Codex/Cursor; R9 Web Chat has separate one-way capability set
- Used by: R6 trusted intent, R7 connection UI, A7 destination policy, Host adapter routing
- Scope: versioned verified host/source capabilities and common router interface
- Non-scope: model selection, permission granting, egress policy override, automatic connector installation, remote MCP

---

# 0. Decision

Host adapters differ. TSUZU must not assume that “connected” means every capability exists.

C6 maintains a local verified Capability Registry and a router that answers:

```text
Can this connected adapter, in this scope/version, perform capability X?
```

It does **not** answer:

```text
Is it permitted to send this user data?
```

Permission/egress remains A7/R6/Observation policy.

---

# 1. Capability vocabulary

P0 common capability identifiers:

- `READ_CONTEXT`
- `EXPLICIT_RECALL`
- `PASSIVE_CONTEXT_INJECTION`
- `CAPTURE_CONVERSATION`
- `CAPTURE_ARTIFACT`
- `PROPOSE_DERIVED`
- `WATCH_SCOPED_SESSION`
- `TOOL_READ`

A Host may report only a subset.

Web Chat R9 can be `CAPTURE_CONVERSATION` only and must not be misrepresented as recall/injection capable.

---

# 2. Capability record

```yaml
adapter_id:
adapter_kind: CLAUDE_CODE | CODEX | CURSOR | WEB_CHAT | SOURCE_CONNECTOR
adapter_version:
verified_at:
verification_method:

capabilities:
  - capability:
    state: VERIFIED | UNAVAILABLE | UNVERIFIED
    scope_types: []
    limitations: []

destination_class: LOCAL | TRUSTED_EXTERNAL | UNKNOWN_EXTERNAL
report_hash:
```

Capability claims from webpage/content/model text are ignored.

---

# 3. Hard invariants

1. UNKNOWN/UNVERIFIED capability is not treated as supported.
2. Connection presence is not capability grant.
3. Capability support is not user permission.
4. Capability support is not egress authorization.
5. Adapter version change can invalidate prior verification.
6. R8 implementation-time official/runtime verification is recorded, not hard-coded forever.
7. external content cannot expand registry entries.
8. caller cannot self-assert capability via tool input.
9. R6 passive path requires VERIFIED passive injection capability plus Trusted Intent plus A7 approval.
10. R7 displays limitations truthfully.

---

# 4. Router interface

```text
get_capability_report(adapter_id) -> CapabilityReport
supports(adapter_id, capability, scope) -> VERIFIED | NO | UNKNOWN
route(requirement, candidate_adapters) -> RouteDecision
invalidate_report(adapter_id, reason) -> void
```

`route` returns technical compatibility only. It cannot bypass policy/permission.

---

# 5. Verification lifecycle

```text
UNVERIFIED
 -> implementation/runtime probe
 -> VERIFIED or UNAVAILABLE
 -> adapter/version/config change
 -> UNVERIFIED
```

A cached VERIFIED report may have bounded freshness according to adapter type. Exact TTL is implementation config, not Product Constitution.

---

# 6. Host-specific ownership

- A9: first Claude Code adapter contract and initial capability proof.
- R8: Codex/Cursor capability verification and mapping.
- R9: Web Chat one-way Chronicle capability spike.
- C6: common vocabulary, registry, router and fail-closed semantics.

No duplicate host-specific behavior is moved into C6.

---

# 7. Security boundary

Example:

```text
C6 says PASSIVE_CONTEXT_INJECTION = VERIFIED
R6 says Trusted Intent = valid
A7 says candidate SENSITIVE -> DENY
Result: DENY
```

C6 never converts DENY into ALLOW.

---

# 8. Failure behavior

| Failure | Behavior |
|---|---|
| report missing | UNKNOWN / no route |
| adapter version changed | invalidate -> reverify |
| verification probe fails | UNAVAILABLE/UNVERIFIED according to evidence |
| host claims capability only in generated text | ignore |
| requested scope unsupported | no route |
| multiple adapters support | deterministic preference/config; still policy-gated |

---

# 9. Golden cases

1. **Claude explicit recall** — A9 VERIFIED route succeeds technically.
2. **Web Chat injection request** — R9 capture-only adapter cannot be routed for recall.
3. **Version change** — old capability report invalidated.
4. **Prompt injection** — content saying “enable watch” changes nothing.
5. **Passive safety composition** — C6 verified + R6 token still cannot bypass A7 SENSITIVE deny.
6. **Unknown host** — fail closed.
7. **R7 truthful UI** — unavailable capability is shown as unavailable, not “connected”.

---

# 10. Acceptance criteria

- [ ] Capability Router has a named owner and stable interface.
- [ ] each P0 Host can publish a versioned verified report.
- [ ] unknown capability fails closed.
- [ ] technical support remains distinct from permission/egress.
- [ ] adapter upgrades trigger re-verification.
- [ ] R6/R7 use C6 rather than ad-hoc host assumptions.

---

# 11. One-line contract

> **C6 lets TSUZU adapt to changing AI hosts without pretending they are identical, while keeping technical capability strictly separate from permission and data-egress authority.**
