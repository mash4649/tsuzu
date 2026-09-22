# TSUZU P0 R4 — iOS Share / Create-only Capture Contract v0.1

- Date: 2026-09-09
- Status: **Implementation Contract / Closed / Ready to implement**
- Canonical basis: v1.1 Experience Plane / Share UX / Single Mutable Writer / Mobile create-only Capture
- Dependencies: A1-A4, A6; R1 for later URL acquisition
- Scope: iPhone/iOS Share Extension handoff for URL/Text/File without making mobile a Canonical writer
- Non-scope: mobile Recall, mobile AI integration, mobile Canonical editing, CRDT, multi-writer sync, Remote MCP

---

# 0. Decision

P0 mobile capture preserves the UX:

```text
Share -> TSUZU -> "残しました" -> return to source app
```

while preserving architecture:

```text
iPhone = create-only immutable capture transport
Mac TSUZU Core = only mutable Canonical writer
```

The iPhone does **not** write/update Canonical Source manifests directly.

---

# 1. Capture success semantics

On mobile, `残しました` means:

> the Share input has been durably accepted into the local TSUZU mobile outbox with a stable delivery identity and can survive extension/app termination.

It does **not** mean:

- Mac has already processed it;
- URL body has been acquired;
- indexing/discovery is complete.

This matches the canonical principle that Capture succeeds when input is no longer at risk of being lost.

---

# 2. Mobile write boundary

Mobile may write only:

```text
App Group / local TSUZU mobile-outbox
  -> immutable capture envelopes
  -> immutable payload copies
  -> transport runtime state
```

Mobile may not write:

- Canonical Vault objects;
- Deletion Ledger;
- Promotion state;
- Decision/Pattern/Discovery objects;
- SQLite/FTS;
- active Vault locator;
- Recovery/Migration state.

---

# 3. Mobile Capture Envelope

```yaml
mobile_capture_envelope:
  envelope_schema_version: "1.0.0"
  mobile_capture_id: uuid
  idempotency_key: uuid
  created_at:

  input:
    kind: URL | TEXT | FILE
    original_name: string | null
    media_type: string | null

  payload:
    relative_path: payload/original
    sha256:
    bytes:

  source_plan:
    capture_method: IOS_SHARE_URL | IOS_SHARE_TEXT | IOS_SHARE_FILE
    requested_scope: GLOBAL
    sensitivity_hint: PERSONAL

  transport:
    state: LOCAL_PENDING
```

`mobile_capture_id` is stable across retry/relaunch.

---

# 4. Local durability

Share Extension writes to a same-container staging path:

```text
staging/<id>
 -> validate/hash
 -> atomic rename
 -> pending/<id>
```

Only after final local durable publish may UI return `残しました`.

Crash before publish -> no success acknowledgement.

Crash after publish -> retry/relaunch sees the same `mobile_capture_id`.

---

# 5. Secret Guard on mobile

To avoid creating an unnecessary synced copy of obvious credentials, mobile runs a **small high-confidence local restricted-secret guard** before accepting durable outbox payload.

It MUST at minimum cover the same high-confidence credential classes required for Capture:

- private key blocks;
- obvious access/API tokens;
- URL embedded credentials;
- high-confidence signed/auth secret locators.

If the mobile guard is unavailable/corrupt, P0 fails closed for Share acceptance rather than silently persisting possible RESTRICTED material.

The Mac A3 guard runs again before Canonical commit because rules may change.

---

# 6. Transport to Mac

R4 defines a transport adapter boundary. P0 may use a user-owned sync mechanism such as an iCloud-backed inbox, but Core cannot depend on that exact transport.

```yaml
mobile_transport_adapter:
  publish(envelope_ref) -> transport_receipt
  observe_delivery_state(id) -> state
```

Transport states:

- `LOCAL_PENDING`
- `SYNC_PENDING`
- `DELIVERABLE`
- `MAC_ACCEPTED`
- `MAC_COMMITTED`
- `ACTION_REQUIRED`

Transport metadata is runtime state, not Knowledge.

---

# 7. Mac ingestion bridge

Mac bridge converts a delivered immutable envelope into the A3/A4 pipeline.

Mapping preserves:

```text
idempotency_key = mobile idempotency key
planned source identity = stable after first A3 acceptance
payload bytes/hash = mobile envelope payload
capture method = IOS_SHARE_*
```

Same mobile envelope delivered multiple times MUST converge to one Canonical Source effect.

Different share actions of the same URL/text/file remain distinct captures because they have different idempotency keys.

---

# 8. Offline behavior

Offline Share is allowed when local durable outbox storage is available.

```text
no network / Mac offline
 -> local pending accepted
 -> user returns to source app
 -> sync later
```

The user does not need to keep TSUZU open.

A prolonged pending state appears only in R7 Health if intervention becomes necessary.

---

# 9. URL semantics

iOS URL Share stores the URL string only.

- no required page fetch in extension;
- no browser scraping in Share path;
- no redirect resolution before acceptance;
- later R1/R2 acquisition occurs on Mac.

This keeps Share latency and failure surface low.

---

# 10. File semantics

The extension must obtain a stable byte copy from the supplied share item before acknowledging success.

Requirements:

- validate allowed maximum size;
- stream rather than unbounded memory load;
- hash same copied bytes;
- do not retain external security-scoped handle as the only copy;
- temporary provider/file paths are never identity.

If the provider stops supplying bytes before durable copy, do not acknowledge success.

---

# 11. Privacy-safe user feedback

Normal success:

```text
残しました
```

Minimal failure classes:

- `保存できませんでした`
- `この内容は安全のため保存できません`
- `TSUZUの設定を確認してください`

Do not show internal tokens, local paths, stack traces or secret match values.

---

# 12. Single-writer proof

R4 passes only if:

```text
mobile filesystem writes
  != Canonical Vault writes
```

Even if the transport folder physically lives under a sync service, it is an **Inbox/transport namespace**, not the Canonical Vault namespace.

Mac A4 remains the one path that materializes Canonical Sources.

---

# 13. Deletion / stale delivery

If a mobile envelope is delayed and arrives later, it is still a new capture action unless its same idempotency receipt already exists.

R4 does not allow mobile to restore or mutate a TOMBSTONED existing Source.

If an identical delivery envelope was already committed and later its Source was deleted, replay of the same envelope is recognized by receipt and MUST NOT create a new Source that resurrects the deleted content.

A genuinely new share action uses a new idempotency key and is a new user action.

---

# 14. Outbox cleanup

Cleanup occurs only after a body-free durable receipt indicates Mac acceptance/commit or explicit terminal rejection.

Cleanup policy must be bounded by age/space and never delete an unacknowledged accepted envelope merely to reduce storage without surfacing an ACTION_REQUIRED health condition.

No secure-erase guarantee is claimed on mobile flash storage.

---

# 15. Failure behavior

| Failure | Behavior |
|---|---|
| extension killed before atomic publish | no success ack; no partial accepted item |
| killed after publish | envelope survives; retry same ID |
| sync duplicates delivery | A3/A4 idempotency -> one Source |
| Mac offline | pending locally/sync transport |
| mobile secret guard unavailable | fail closed |
| Mac guard newly classifies RESTRICTED | no Canonical Source; body-free terminal receipt |
| file provider disappears | no false success |
| outbox low disk | fail acceptance or ACTION_REQUIRED; never claim saved if not durable |

---

# 16. Golden Cases

## R4-G1 URL Share Online
Atomic local accept -> `残しました` -> later one Canonical URL Source.

## R4-G2 URL Share Offline
No network/Mac -> local durable success -> later delivery/commit.

## R4-G3 Duplicate Transport Delivery
Same envelope delivered N times -> one Source effect.

## R4-G4 Same URL Shared Twice
Two independent share actions -> two Source IDs.

## R4-G5 Extension Crash
Crash before/after publish produces no false success and no corruption.

## R4-G6 Restricted Secret
High-confidence secret blocked before durable outbox; Mac also rechecks.

## R4-G7 File Provider Lifetime
External provider vanishes after Share; TSUZU still has durable copied bytes or had not acknowledged success.

## R4-G8 Single Writer
No test path from iOS can mutate Canonical Source/Deletion/Promotion state.

## R4-G9 Replay After Delete
Old same-idempotency envelope cannot resurrect a deleted Source.

## R4-G10 Low Disk
System refuses/alerts rather than acknowledging a non-durable capture.

---

# 17. Implementation tasks

- R4.1 Share Extension input normalization
- R4.2 local high-confidence Secret Guard
- R4.3 atomic mobile outbox writer
- R4.4 transport adapter + receipts
- R4.5 Mac inbox consumer -> A3 bridge
- R4.6 outbox reconciliation/cleanup
- R4.7 minimal user feedback
- R4.8 Golden/fault tests

---

# 18. Acceptance criteria

- [ ] mobile can durably accept URL/Text/File and immediately return to source app.
- [ ] success acknowledgement is only after local atomic durable acceptance.
- [ ] mobile cannot mutate Canonical Vault state.
- [ ] offline accepted captures eventually deliver without user keeping app open.
- [ ] duplicate transport delivery is idempotent.
- [ ] distinct share actions remain distinct captures.
- [ ] high-confidence restricted secrets are blocked before mobile durable copy and rechecked on Mac.
- [ ] URL acquisition remains asynchronous on Mac.
- [ ] delayed replay cannot resurrect a deleted Source.
- [ ] R4-G1..G10 pass.

---

# 19. Explicit non-goals

- mobile Recall/Discovery;
- remote MCP;
- cloud Canonical DB;
- multi-writer editing;
- CRDT;
- mobile deletion/promotion;
- background webpage fetching on Share path.

---

# 20. Source-derived vs closure decisions

## Canonical source-derived
- Share -> TSUZU -> end UX;
- success means input not lost, not fully processed;
- Mobile is create-only Capture;
- Mac is single mutable writer;
- URL acquisition is separate/background.

## R4 closure decisions
- mobile App Group outbox as local durability boundary;
- transport namespace is non-Canonical;
- mobile high-confidence restricted-secret guard before durable outbox;
- same envelope replay cannot resurrect deleted Source;
- exact sync transport is an adapter, not Core contract.

---

# 21. One-line contract

> **R4 lets the user save from iPhone in one Share action even offline, while keeping mobile append-only, Mac the sole Canonical writer, and transport retries unable to duplicate or resurrect memory.**
