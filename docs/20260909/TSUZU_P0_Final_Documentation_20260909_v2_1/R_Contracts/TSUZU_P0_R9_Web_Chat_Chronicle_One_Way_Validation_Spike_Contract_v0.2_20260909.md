# TSUZU P0 R9 — Web Chat Chronicle One-way Validation Spike Contract v0.2

- Date: 2026-09-09
- Status: **Validation Spike Contract / Closed / Ready to execute**
- Canonical basis: v1.2/v1.2.1 Web Chat Chronicle One-way = P0 Validation Spike; full bidirectional Web/Mobile AI = post-proof + v1.2.2 cross-cutting closure where applicable
- Dependencies: C6 Capability Registry, B1 Chronicle, B2 Episode, B3 Provenance, A3 Secret Guard, Observation Permission
- Scope: determine whether selected web AI conversations can be safely captured one-way with enough actor/order/scope fidelity to become Chronicle evidence
- Non-scope: web chat Recall/injection, session hijacking, credential/cookie extraction, automation that bypasses provider access controls, Remote MCP

## v0.2 cross-cutting closure

A successful provider/method spike MUST publish a C6 Capability Report. R9 Web Chat remains capture-only unless another future Contract separately verifies recall/injection; C6 must therefore route it as Chronicle capability only.


---

# 0. Decision

R9 is a **Spike**, not a promise that every web AI is supported.

Success criterion is not "we scraped the page." It is:

> a legitimate user-authorized method can capture a bounded conversation with actor/order/session provenance, without storing credentials or claiming completeness it cannot prove.

If that cannot be demonstrated for a provider/method, the provider remains unsupported/partial.

---

# 1. One-way boundary

Allowed direction:

```text
Web AI conversation -> local TSUZU Chronicle
```

Forbidden in R9:

```text
TSUZU memory -> Web AI context
TSUZU -> post/send/edit/delete in Web AI
```

This separation contains security and provider fragility.

---

# 2. Candidate acquisition method classes

R9 may evaluate, in order of legitimacy/fidelity:

- `USER_EXPORT_IMPORT`
- `EXPLICIT_SHARE_COPY`
- `BROWSER_EXTENSION_READ_ONLY_CAPTURE`
- `OTHER_PROVIDER_SUPPORTED_EXPORT`

Exact provider method is implementation-time verified.

R9 does not store login cookies/session tokens as a shortcut.

---

# 3. Observation permission

Web Chronicle capture requires explicit configuration:

```text
provider/domain
x account/profile if resolvable without storing credentials
x conversation/session scope
x capability = capture/chronicle
```

Connection to a browser does not authorize all browser history/tabs.

---

# 4. Chronicle event schema mapping

For each captured message/event, R9 must produce enough information for B1:

```yaml
web_chat_event:
  provider_id:
  conversation_external_key_hash:
  session_observed_at:
  event_order:
  actor: USER | ASSISTANT | TOOL | SYSTEM | UNKNOWN
  timestamp_observed: timestamp | null
  content_stream_ref:
  capture_method:
  fidelity:
  completeness:
```

`UNKNOWN` actor is retained as unknown; never guessed into user acceptance.

---

# 5. Fidelity classes

- `EXPORT_STRUCTURED`: provider/export gives structured actor/order data.
- `DOM_OBSERVED`: local extension observed rendered page structure.
- `USER_COPIED`: explicit user-shared representation.
- `UNKNOWN_RECONSTRUCTION`: insufficient for Chronicle Knowledge extraction by default.

Actor/order confidence is separate from content plausibility.

---

# 6. Completeness / coverage

Each captured conversation records:

```yaml
chronicle_coverage:
  state: COMPLETE_AS_OBSERVED | PARTIAL | UNKNOWN
  first_event_observed:
  last_event_observed:
  missing_history_possible: boolean
  reason_codes: []
```

DOM viewport capture does not claim full conversation history unless independently verified.

B5/B8 downstream must preserve coverage bias.

---

# 7. Secret handling

Conversation content may contain credentials.

Before Canonical Chronicle persistence:

- local high-confidence Secret Guard runs;
- RESTRICTED segments are not stored as body;
- body-free omission marker preserves event ordering/coverage;
- surrounding conversation is not automatically discarded if safe to retain;
- SENSITIVE follows local storage/external egress policy.

R9 never stores browser auth cookies/tokens as Knowledge or telemetry.

---

# 8. DOM / browser content trust

If browser extension capture is tested:

- page DOM is untrusted data;
- embedded instructions cannot grant TSUZU permissions;
- extension runs read-only for the allowed page/domain;
- no arbitrary script from page is executed with TSUZU privileges;
- only required conversation fields are extracted;
- permission remains domain/scope bounded.

---

# 9. Duplicate / update semantics

Same observed conversation captured multiple times:

- same stable event fingerprint -> no duplicate Chronicle event;
- new later messages -> append new immutable Chronicle events;
- changed rendered text with same provider event identity -> preserve a new observed version or conflict marker, never silent overwrite;
- missing earlier events on a later capture do not imply deletion.

---

# 10. Provider/account identity

Do not infer personal identity from display names alone.

Provider/account binding is user-configured or based on trustworthy local browser/profile context where available. If ambiguous, capture may remain provider/session scoped without asserting person identity.

---

# 11. Spike output

For each provider/method tested, write body-free Capability Evidence:

```yaml
web_chronicle_spike_result:
  provider_id:
  method:
  verified_at:
  status: PASS | PARTIAL | FAIL
  actor_fidelity:
  ordering_fidelity:
  session_identity_fidelity:
  completeness_fidelity:
  credential_risk:
  maintenance_risk:
  limitations: []
  recommendation: ENABLE | EXPERIMENTAL | DO_NOT_ENABLE
```

No provider support is Canonical until its spike PASS/PARTIAL decision is recorded.

---

# 12. Failure behavior

- provider UI changes -> adapter PARTIAL/disabled, not guessed;
- actor marker unavailable -> UNKNOWN;
- conversation history lazy/unloaded -> PARTIAL;
- login/session unavailable -> ACTION_REQUIRED; do not extract credential;
- extension permission revoked -> stop capture immediately;
- content secret detected -> omit blocked body, preserve coverage marker;
- duplicate capture -> idempotent event mapping.

---

# 13. Golden / spike cases

## R9-G1 Structured Export
Actor/order/session preserved -> PASS-capable Chronicle.

## R9-G2 DOM Partial View
Only visible subset captured -> PARTIAL, never complete.

## R9-G3 Assistant Suggestion Not User Decision
Roles preserved so B3 cannot promote assistant output as user Knowledge.

## R9-G4 Restricted Segment
Secret-containing message omitted/body-blocked without losing event-order marker.

## R9-G5 Duplicate Capture
Re-capture same thread -> no duplicate same event.

## R9-G6 UI Change
Selector/structure fails -> adapter disables/partial; no text-guess actor mapping.

## R9-G7 Prompt Injection in Chat
Conversation content cannot change extension/TSUZU permissions.

## R9-G8 No Cookie Storage
Capture works or fails without persisting auth cookie/session token.

## R9-G9 Missing Old History
Coverage marker prevents downstream statement that unobserved history never occurred.

## R9-G10 One-way Enforcement
No available R9 code path injects TSUZU memory or sends messages to provider.

---

# 14. Implementation tasks

- R9.1 WebChronicle adapter interface
- R9.2 structured export/import spike
- R9.3 read-only browser-extension spike where appropriate
- R9.4 actor/order/session mapper
- R9.5 Secret Guard + omission markers
- R9.6 duplicate/coverage reconciliation
- R9.7 provider capability evidence report
- R9.8 Golden/security cases

---

# 15. Acceptance criteria

R9 Contract is execution-complete when at least one tested method has a documented PASS/PARTIAL/FAIL result and:

- [ ] no web credentials/cookies are stored as Knowledge/telemetry.
- [ ] actor/order/session fidelity is measured, not assumed.
- [ ] partial history is explicitly marked partial.
- [ ] assistant/user roles remain distinct.
- [ ] Secret Guard prevents RESTRICTED Chronicle body persistence.
- [ ] capture permissions are provider/domain/scope bounded.
- [ ] page/chat content cannot alter permissions.
- [ ] capture is idempotent for repeated observations.
- [ ] R9 remains one-way only.
- [ ] R9-G1..G10 pass for each method claimed enabled.

---

# 16. Explicit non-goals

- full bidirectional ChatGPT/Claude/Gemini integration;
- remote MCP;
- browser credential extraction;
- provider auth automation;
- cross-account monitoring;
- universal support guarantee.

---

# 17. Source-derived vs closure decisions

## Canonical source-derived
- Web Chat Chronicle One-way is a P0 Validation Spike;
- full bidirectional Web/Mobile AI is post-proof;
- Chronicle requires user/assistant separation and provenance;
- observation is allowlisted;
- secret/prompt-injection rules apply.

## R9 closure decisions
- one-way capability evaluated by fidelity, not scraping success;
- explicit method classes;
- coverage/partial markers mandatory;
- no credential/cookie persistence;
- provider/method capability evidence report determines enablement.

---

# 18. One-line contract

> **R9 tests whether web AI conversations can become trustworthy one-way Chronicle evidence without pretending partial DOM access is complete, confusing assistant text with user decisions, or turning browser credentials into TSUZU data.**
