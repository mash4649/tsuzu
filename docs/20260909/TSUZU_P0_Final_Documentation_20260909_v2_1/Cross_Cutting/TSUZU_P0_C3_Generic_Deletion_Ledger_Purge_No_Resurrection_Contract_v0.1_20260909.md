# TSUZU P0 C3 — Generic Deletion Ledger / Purge / No-Resurrection Contract v0.1

- Date: 2026-09-09
- Status: **Cross-cutting Foundation Contract / Closed / Ready to implement**
- Canonical basis: v1.2.1 Deletion State + Dependency-aware Delete/Invalidation/Recompute; v1.1 Forget/physical purge intent
- Depends on: A6 Source deletion specialization, C0, C1; integrates with C4 and R5
- Scope: deletion truth for every deletion-eligible persistent object, generic ledger, immediate ineligibility, best-effort active-Vault purge, anti-resurrection
- Non-scope: cryptographic/forensic secure erase guarantee on SSD/APFS/iCloud/backups, undelete, legal retention workflows, cloud tombstone service

---

# 0. Decision

A6 correctly closes Source-level logical deletion. v1.2.1 later requires TOMBSTONED semantics for Decision/Evidence/Conversation/Pattern-related persistent objects as well.

C3 generalizes the ledger target from `SOURCE` to:

```text
(target_object_type, target_object_id)
```

A6 remains the `SOURCE` specialization. C3 is the generic authority for all deletion-eligible object types.

---

# 1. Effective deletion

```text
effective_deleted(type, id)
=
valid generic Deletion Ledger Record exists
OR
valid object manifest explicitly says TOMBSTONED
```

When inconsistent:

```text
Ledger deleted + object LIVE -> DELETED
```

Ledger wins.

Deletion is monotonic in P0:

```text
LIVE -> TOMBSTONED
TOMBSTONED -/-> LIVE
```

No undelete.

---

# 2. Generic ledger layout

```text
<Vault>/system/deletion-ledger/
  <OBJECT_TYPE>/
    <object_id>.md
```

Path is lookup optimization only; record contents are validated.

Schema:

```yaml
record_type: DELETION_RECORD
ledger_schema_version: "2.0.0"
record_id: uuid

target:
  object_type:
  object_id:

deleted_at:
deleted_by:
  actor: USER | SYSTEM_ALLOWED
  method:

request:
  request_id:
  idempotency_key_hash:

snapshot:
  revision_at_delete: null | integer
  content_hash: null | sha256

reason_code:
```

No deleted body is copied into the record.

---

# 3. Hard invariants

1. Every deletion-eligible object type has a C3 resolver path.
2. Deletion record is Canonical factual state, not AI Derived.
3. AI cannot create a USER deletion request on its own.
4. Ledger record commit precedes availability removal/purge work.
5. Once ledger is durable, retrieval/context/discovery/promotion must treat target as deleted even if target file still says LIVE.
6. Deletion truth failure/unknown is fail closed for target eligibility.
7. C1 update cannot resurrect deleted target.
8. C4 recompute excludes deleted inputs.
9. R5 restore unions deletion facts by `(object_type, object_id)` across current + backup ledgers.
10. stale backup/sync copy cannot override a valid deletion record.
11. physical purge failure never rolls deletion truth back.
12. Deletion Ledger itself is PROTECTED in R5 backup.

---

# 4. Delete sequence

User-authorized delete:

```text
1. validate target/object type + user intent
2. generate stable delete request id/idempotency key
3. acquire shared writer boundary
4. append immutable C3 Deletion Record using the shared C1 atomic persistence primitives / writer lock
5. optionally reconcile target manifest -> TOMBSTONED with revision check
6. release immediate eligibility: DELETED
7. dispatch C4 dependency invalidation
8. remove A5/derived/cache eligibility/materializations
9. best-effort purge target body/files from active Vault where safe
10. emit body-free completion/partial-purge health state
```

Step 4 is the point at which “forget” becomes logically effective.

---

# 5. Best-effort physical purge boundary

v1.1's physical purge intention is retained, but the guarantee is stated precisely.

## P0 MUST

After logical deletion becomes durable, TSUZU-managed active storage SHOULD/MUST attempt normal filesystem removal of target body/material files that are no longer needed for valid retained history.

Examples:

- deleted Source payload
- deleted Source Version payload
- deleted Conversation body when object itself is deleted
- Derived/cache/index copies

## P0 MUST NOT claim

- cryptographic secure erase of SSD blocks;
- purge from APFS snapshots/Time Machine not controlled by TSUZU;
- immediate deletion from already-created external backup copies;
- deletion from iCloud provider internal retention guarantees;
- forensic unrecoverability.

User-facing wording in R7 must distinguish **removed from TSUZU active use/storage** from **forensic secure erase**.

---

# 6. Dependency behavior

Deleting a parent does not require a deletion ledger record for every derived child to make them ineligible.

```text
parent deletion
-> dependency invalidation
-> child Derived eligibility false
```

But a persistent Canonical child with independent meaning may receive its own deletion record according to owner policy.

### Root Source + SOURCE_VERSION

- root Source deleted -> all child versions ineligible through C2/C3 dependency.
- Source Version alone deleted -> root remains.

---

# 7. Correction vs deletion

Correction is not deletion.

- B5 Correction can mark assertion wrong/revised while history remains.
- C3 deletion removes target from eligible use.
- `SUPERSEDED` is not deleted.
- `REJECTED` is not necessarily physically deleted.

Do not use delete to implement semantic disagreement.

---

# 8. Restore / backup

R5 NORMAL_RESTORE:

```text
merged_ledger = current generic ledger UNION backup generic ledger
```

Union key includes object type.

Any conflict in immutable deletion fact -> fail closed/recovery review.

DISASTER_RESTORE limitation remains: without a newer/current ledger, deletions after backup cannot be inferred.

---

# 9. Failure behavior

| Failure | Required behavior |
|---|---|
| target missing but delete requested | idempotent deletion record may still be valid if identity known |
| ledger commit fails | delete not acknowledged complete |
| manifest tombstone fails after ledger commit | target still DELETED; reconcile later |
| invalidation queue fails | C4 marks dependent state stale/ineligible until recompute |
| active-file purge fails | logical deletion remains; health/action report |
| ledger corrupt/unreadable | fail closed for affected eligibility; recovery required |
| stale object returns from sync | ledger suppresses |

---

# 10. Golden cases

1. **Decision Evidence delete** — generic ledger suppresses evidence and B5/B7 recompute.
2. **Conversation delete** — Episode/Candidate dependents become stale/ineligible.
3. **Source delete** — behavior remains equivalent to A6.
4. **Source Version delete** — C2 no longer selects it.
5. **Purge failure** — object remains logically deleted; no resurrection.
6. **Old backup restore** — current generic ledger suppresses object across types.
7. **SUPERSEDED not delete** — history remains usable for Judgment Evolution under policy.
8. **Correction not delete** — corrected assertion history remains unless separately deleted.
9. **Ledger corrupt** — affected retrieval fails closed.

---

# 11. Acceptance criteria

- [ ] A6 SOURCE behavior remains valid as specialization.
- [ ] every persistent deletion-eligible object can be targeted by type+id.
- [ ] logical deletion takes effect before asynchronous purge.
- [ ] deleted B objects cannot remain Discovery/Decision evidence.
- [ ] R5 unions generic ledger records across object types.
- [ ] best-effort active-store purge exists without false secure-erase claims.
- [ ] deletion cannot be implemented as semantic correction/supersede.

---

# 12. One-line contract

> **C3 makes deletion a generic monotonic fact across TSUZU, immediately removes deleted evidence from all future reasoning, and pursues practical file purge without promising impossible forensic erasure.**
