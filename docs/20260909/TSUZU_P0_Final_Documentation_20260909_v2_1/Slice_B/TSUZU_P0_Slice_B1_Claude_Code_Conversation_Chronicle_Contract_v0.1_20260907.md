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
