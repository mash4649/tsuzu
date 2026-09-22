# TSUZU P0 R7 — Thin Settings / Health / Privacy / Data Management Control Plane Contract v0.1

- Date: 2026-09-09
- Status: **Implementation Contract / Closed / Ready to implement**
- Canonical basis: v1.1 Experience Plane/Control Plane + Settings/Health sections + v1.2 Control Plane restatement
- Dependencies: A/R/B health and policy projections; especially A3/A4/A5/A6/A7, R1, R5, R6
- Scope: the minimal TSUZU application/control surface for setup, permissions, privacy, data/recovery and health
- Non-scope: daily chat, memory browser as primary UX, task Inbox, Aha feed, Knowledge Graph UI, analytics dashboard

---

# 0. Decision

TSUZU's own UI is a **control plane, not the place where value is consumed**.

P0 top-level IA is limited to:

```text
Home / Health
Connections
Data Sources & Import
Privacy & Permissions
Storage / Backup / Recovery
Data Management
Advanced
```

No daily-use `Search`, `Chat`, `Aha`, `Tasks`, `Inbox` navigation is added.

---

# 1. Product invariants

1. Control Plane must not create a new organizational burden.
2. Routine healthy processing stays invisible.
3. User action is requested only when necessary.
4. Internal sensitivity taxonomy need not be fully exposed to ordinary users.
5. No UI control can weaken hard security invariants such as RESTRICTED external deny.
6. Health is system state, not a work queue.
7. Data ownership/export/delete/recovery are first-class controls.
8. Connector secrets are never rendered after entry except masked status.
9. Destructive/recovery operations are explicit and traceable.
10. Product Proof does not depend on app DAU/time-in-app.

---

# 2. Home / Health Summary

Default home shows a compact state such as:

```text
TSUZU

● 正常に動作しています
最終処理: 数分前

接続
データソース
プライバシー
保存とバックアップ
データ管理
詳細設定
```

Allowed summary content:

- overall Green/Yellow/Red;
- last successful processing time;
- whether user action is required;
- backup freshness summary;
- connection state summary.

Do not show raw queue counts as a productivity Inbox by default.

---

# 3. Health state model

Each subsystem reports normalized state:

```yaml
health_projection:
  subsystem_id:
  status: GREEN | YELLOW | RED
  action_required: boolean
  reason_code:
  last_success_at:
  observed_at:
  detail_ref: body_free_ref
```

### GREEN
Normal; no user action.

### YELLOW
Degraded/retrying/stale but safe; may not require action.

### RED
Safety/integrity/permission failure or durable processing blocked; likely action required.

A content item failing acquisition is not automatically global RED.

---

# 4. Health aggregation

Overall health is severity-aware, not a naive max:

- Canonical corruption / Deletion Ledger unavailable / Recovery failure -> RED;
- Secret Scanner unavailable for new persistence/egress -> RED or blocking RED;
- one external fetcher outage while capture remains durable -> YELLOW;
- one optional host disconnected -> YELLOW/ACTION_REQUIRED depending user intent;
- no pending work and healthy core -> GREEN.

Aggregation rules are deterministic and versioned.

---

# 5. Connections

Connections page displays:

- supported Host adapters;
- source/fetcher connectors;
- connection status;
- allowed scope/capabilities;
- last verified/last success;
- reconnect/revoke action.

Per connection:

```yaml
connection_view:
  connector_id:
  connector_type:
  status:
  granted_scopes: []
  granted_capabilities: []
  credential_present: boolean
  credential_value: NEVER_EXPOSED
  last_success_at:
```

`connected` does not imply global observation permission.

---

# 6. Data Sources & Import

Provides:

- Apple Notes/Markdown bootstrap entry (R3);
- future supported source connectors only when enabled;
- import scope/coverage summary;
- acquisition health summary;
- user-action-required failures.

No Folder/Tag reorganization UI is required.

---

# 7. Privacy mode contract

P0 exposes two understandable modes while preserving hard policy:

## STANDARD
- existing A7/R6 policy;
- PUBLIC/PERSONAL may go to trusted external host when authorized;
- passive PERSONAL allowed only under R6 trusted intent;
- SENSITIVE external default deny;
- RESTRICTED deny.

## STRICT
- hard rules remain;
- passive external PERSONAL recall is disabled or requires explicit approval;
- explicit external recall can require approval per host;
- local processing remains available.

No mode can allow silent SENSITIVE or any RESTRICTED external egress.

The internal four sensitivity levels remain implementation policy; UI may provide advanced detail separately.

---

# 8. Permission controls

At minimum expose:

```text
host x workspace/project/session scope x capability
```

Capabilities may include:

- read/recall;
- capture/chronicle;
- watch/observe;
- propose.

UI never implies `connected = all capabilities`.

Permission revocation must take effect before new observation/token issuance.

---

# 9. Storage / Backup / Recovery

R7 is UI/orchestration surface only; R5 owns mechanics.

Expose:

- active Vault location/reference;
- backup destination/status/freshness;
- create backup;
- restore preflight;
- recovery/maintenance state;
- schema compatibility/update-required status.

Restore flow must clearly state that active data is switched only after validation and that R5 creates a pre-restore backup where applicable.

Never offer a blind `overwrite current vault` button.

---

# 10. Data Management

P0 includes:

- export user-owned Canonical data;
- delete/forget selected data where supported;
- full delete/reset workflow if implemented by deletion contract;
- show deletion/recovery consequences;
- no hidden AI-generated repair of Canonical.

Deletion action must use A6/R5 semantics, not direct filesystem removal from UI.

---

# 11. Destructive-operation confirmation

For delete/restore/reset/revoke-with-data-impact:

- identify operation and affected scope;
- explain reversible vs logically irreversible state;
- require explicit user confirmation;
- perform preflight;
- produce body-free receipt/result.

Do not require repetitive confirmations for routine non-destructive background processing.

---

# 12. Advanced

Advanced may contain:

- version/build info;
- policy/compiler/index versions;
- diagnostic export with body-free logs;
- adapter capability reports;
- experimental spike toggles;
- developer/test controls gated from ordinary users.

Advanced must not become a hidden path to bypass hard security policies.

---

# 13. Error disclosure

User-facing errors show actionable reason, not internal bodies/paths/secrets.

Diagnostic detail may contain IDs/hashes/version/reason codes but:

- no raw memory body;
- no credential;
- no Authorization/Cookie values;
- no full sensitive query strings;
- no stack trace in normal UI.

---

# 14. Notification philosophy

Default:

- silent healthy success;
- no notification for transient retry;
- surface only persistent action-required or safety/integrity issues;
- no engagement Push strategy in P0.

Control Plane does not optimize for opens.

---

# 15. Accessibility / resilience baseline

P0 controls for critical operations must remain usable with:

- keyboard navigation where desktop technology supports it;
- readable text labels, not color alone for Green/Yellow/Red;
- progress/error states that survive app restart through underlying receipts;
- destructive confirmation that does not depend on animation/transient toast only.

---

# 16. Golden Cases

## R7-G1 Healthy Idle
Home is simple Green; no Inbox/queue burden.

## R7-G2 Fetcher Degraded
R1 adapter outage -> Yellow; durable capture still healthy; no global corruption message.

## R7-G3 Deletion Ledger Failure
A6 critical state -> Red and relevant operations fail closed.

## R7-G4 Standard Privacy
PERSONAL trusted external behavior matches A7/R6; SENSITIVE/RESTRICTED remain blocked.

## R7-G5 Strict Privacy
Passive external PERSONAL is disabled/approval-only without deleting memory.

## R7-G6 Revoke Host
Revocation prevents subsequent observation/trusted-intent tokens.

## R7-G7 Restore
UI invokes R5 preflight/validated restore; no direct overwrite path.

## R7-G8 Delete
UI invokes A6 tombstone/ledger path, not raw file removal.

## R7-G9 Credential Display
Connection page confirms credential presence but never reveals stored token.

## R7-G10 No Daily-use Feature Creep
Navigation contains no chat/Aha feed/task Inbox/search-as-primary surface.

---

# 17. Implementation tasks

- R7.1 normalized health projection/aggregator
- R7.2 Home/Health screen
- R7.3 Connections/permissions screen
- R7.4 Data Sources/Import screen
- R7.5 Privacy modes + R6 controls
- R7.6 Storage/Backup/Recovery surface
- R7.7 Data Management destructive workflows
- R7.8 Advanced/diagnostic body-free export
- R7.9 Golden/UI integration tests

---

# 18. Acceptance criteria

- [ ] TSUZU UI remains a thin Control Plane.
- [ ] healthy users can ignore it.
- [ ] Green/Yellow/Red are deterministic and not raw queue counts.
- [ ] connector scopes/capabilities are visible and revocable.
- [ ] Standard/Strict modes cannot weaken hard sensitivity rules.
- [ ] R5 backup/restore and A6 delete are invoked through their contracts.
- [ ] credential values/content bodies are not exposed in health telemetry/UI diagnostics.
- [ ] routine retry does not create user task burden.
- [ ] destructive actions are explicit and auditable.
- [ ] R7-G1..G10 pass.

---

# 19. Explicit non-goals

- chat client;
- memory exploration feed;
- graph UI;
- tag/folder manager;
- acquisition Inbox Zero;
- admin analytics product;
- engagement notifications;
- team management.

---

# 20. Source-derived vs closure decisions

## Canonical source-derived
- TSUZU app is Control Plane;
- Connection/Data Sources/Privacy/Storage/Delete/Health/Advanced only;
- simple Health Summary;
- no daily operations dashboard;
- internal sensitivity need not be exposed directly;
- no Inbox burden.

## R7 closure decisions
- deterministic normalized Health projection;
- top-level IA fixed for P0;
- `STANDARD` and `STRICT` privacy modes;
- Strict downgrades passive external PERSONAL without weakening other hard rules;
- destructive workflows must route through owning contracts.

---

# 21. One-line contract

> **R7 gives users one small place to connect, protect, recover and own TSUZU without turning TSUZU itself into another app they must organize, check or spend time inside.**
