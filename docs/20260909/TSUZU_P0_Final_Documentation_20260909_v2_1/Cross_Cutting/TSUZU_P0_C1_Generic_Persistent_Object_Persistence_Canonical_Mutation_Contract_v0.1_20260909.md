# TSUZU P0 C1 — Generic Persistent Object Persistence / Canonical Mutation Contract v0.1

- Date: 2026-09-09
- Status: **Cross-cutting Foundation Contract / Closed / Ready to implement**
- Canonical basis: v1.2.1 Canonical Object Envelope, Lifecycle/Correction/Decision contracts
- Depends on: C0 Active Vault Locator; A2 Source Atomic Writer as the first specialization
- Applies to: every tracked persistent object. Canonical records/events use C1 mutation authority; Derived generations use C4 semantics while reusing C1 atomic persistence primitives.
- Scope: generic persistent-object atomicity, object registry, Canonical create/update/event mutation, Derived physical commit primitives, revision checks, idempotency, single-writer mutation
- Non-scope: object meaning, promotion policy, Derived computation, deletion semantics, index projection, user-facing UI

---

# 0. Decision

A2は`SOURCE`に対する正しいAtomic Writerだが、v1.2/v1.2.1で増えたCanonical Object全体のwriter contractではない。

P0はA2の安全原則を一般化した**1つのPersistent Write Core**を持つ。Canonical authorityとDerived semanticsは分離するが、危険な独自writer実装を増やさない。

```text
Object-specific Contract
  -> schema/meaning
C1
  -> persistence/revision/atomicity/idempotency
C0
  -> active Vault
```

A2は削除しない。`SOURCE`向けのspecialized adapterとしてC1 Coreを使う形に収束させる。

---

# 1. Persistent object classification

各object_typeのowner Contractは、少なくとも以下を宣言する。

```yaml
object_registration:
  object_type:
  storage_class: CANONICAL | DERIVED | RUNTIME_ONLY
  mutability: IMMUTABLE | REVISIONED
  body_mode: NONE | INLINE | PAYLOAD
  schema_owner:
  deletion_eligible: true | false
```

### Rules

- `CANONICAL` mutation -> C1 mandatory.
- `DERIVED` lifecycle/generation -> C4 owns semantics; physical commit MUST reuse C1 atomic persistence primitives under a Derived namespace so no second unsafe writer core is invented. Envelope inheritance remains mandatory where persisted.
- `RUNTIME_ONLY` -> C1へ保存しない。
- unknown object_type/storage_class -> fail closed.

AI output alone cannot self-register a new object type.

---

# 2. C1 hard invariants

1. All Canonical persistent objects inherit the v1.2.1 Canonical Object Envelope.
2. Canonical mutation is allowed only while the shared Single Writer lock is held.
3. C1 and A2 MUST use the same writer-lock authority; there is no second mutable writer.
4. object_id is stable identity; filename/path is not identity.
5. create uses no-clobber atomic publish.
6. revisioned update requires `expected_revision`.
7. Last-write-wins is forbidden.
8. immutable fields cannot be patched.
9. Canonical payload/body is never rewritten by AI “repair”.
10. caller-provided hash/size for stored payload is re-computed at boundary.
11. C0 generation is verified immediately before publish.
12. retry with same idempotency identity converges to one effect.
13. different legitimate user events remain different objects even if body hashes match.
14. Secret/RESTRICTED hard rules of owning boundary are revalidated before commit where required.
15. Deletion record truth is owned by C3; C1 cannot turn a C3-deleted object LIVE.

---

# 3. Generic physical layout

P0 does not force legacy `SOURCE` layout to migrate.

Default for new generic objects:

```text
<Vault>/
  canonical/
    objects/
      <object_type>/
        <object_id>/
          object.md
          payload/
            original      # only when body_mode=PAYLOAD
```

Object Storage Registry may map an established type to a specialized layout:

```text
SOURCE -> A1 canonical/sources/<source_id>/
```

A path mapping is implementation detail and cannot change identity/semantics.

---

# 4. Generic interfaces

```text
create_canonical(CreateCanonicalIntent) -> CommitResult
update_canonical(UpdateCanonicalIntent) -> CommitResult
append_canonical_event(AppendEventIntent) -> CommitResult
inspect_canonical(object_type, object_id) -> IntegrityResult
```

### CreateCanonicalIntent

```yaml
object_type:
object_id:
schema_version:
created_at:
idempotency_key:
manifest_fields:
payload_ref: null | runtime_stream_ref
```

C1 computes/forces:

- `revision = 1`
- `updated_at = created_at`
- object path mapping
- payload digest/bytes when applicable
- registered immutable envelope fields

### UpdateCanonicalIntent

```yaml
object_type:
object_id:
expected_revision:
idempotency_key:
patch:
```

Object owner defines the patch allowlist. C1 rejects fields not explicitly allowed.

---

# 5. Immutable event pattern

User correction, observation evidence and similar historical facts should prefer append-only Canonical Events when owner Contract requires history preservation.

```text
CORRECTION_EVENT
OBSERVATION_EVENT
DELETION_RECORD (written under C3 semantics)
```

C1 persists the event but does not interpret its meaning.

Derived generation materialization may reuse the same atomic storage primitives through C4, but `storage_class=DERIVED` is preserved and never gains Canonical authority merely because the bytes were written safely.

---

# 6. Atomic transaction

For create:

```text
1. resolve C0 VaultHandle generation G
2. acquire shared writer lock
3. validate object registration/schema
4. build isolated same-volume staging object
5. calculate integrity metadata
6. validate full staged object
7. verify C0 generation still G
8. no-clobber atomic publish
9. sync parent as supported
10. read-back identity/revision
11. durable body-free receipt
12. release lock
```

For update:

```text
read current
-> validate expected_revision
-> render full replacement manifest
-> stage
-> verify generation
-> atomic replace
-> read-back revision N+1
```

No in-place partial YAML/Markdown mutation.

---

# 7. Idempotency

Receipt identity:

```text
(object_type, object_id, operation_kind, idempotency_key_hash)
```

Same operation replay:

- already committed and same fingerprint -> `ALREADY_COMMITTED`
- same idempotency key but conflicting fingerprint -> hard conflict/quarantine
- destination exists with unrelated object -> hard collision

Receipts contain no object body.

---

# 8. Canonical / Derived boundary

C1 must never allow this flow:

```text
LLM output
-> "looks plausible"
-> direct Canonical overwrite
```

Allowed:

```text
LLM -> Derived Candidate (C4/B3)
user explicit event / observed allowed evidence -> owner Contract decides Canonical event
-> C1 persists
```

Promotion remains B7/owner policy, not C1.

---

# 9. Failure behavior

| Failure | Required behavior |
|---|---|
| unknown object_type | reject |
| schema invalid | reject before publish |
| revision mismatch | conflict; no overwrite |
| stale C0 generation | abort/retry on current Vault |
| shared writer lock unavailable | bounded `WRITER_BUSY` |
| staging crash | recover/quarantine staging; no half Canonical |
| idempotency fingerprint conflict | hard failure/quarantine |
| C3 says deleted | mutation cannot make object eligible/live |
| object corrupt | quarantine/health; never AI-repair |

---

# 10. Golden cases

1. **B1 Chronicle create** — Conversation Message commits atomically under generic path.
2. **B5 Correction event** — crash after event publish preserves exactly one correction.
3. **Revision conflict** — two updates from revision 3; only expected revision path succeeds.
4. **Same retry** — same event/idempotency produces one Canonical effect.
5. **Same body, new user event** — distinct object IDs both persist.
6. **Vault cutover race** — old-generation generic write cannot publish.
7. **Deleted target mutation** — metadata update cannot resurrect C3-deleted object.
8. **Unknown object registration** — rejected before staging publish.

---

# 11. Implementation tasks

- C1.1 object registration registry
- C1.2 shared writer core extraction/reuse from A2
- C1.3 generic staging/layout adapter
- C1.4 create/update/event APIs
- C1.5 revision/idempotency receipt store
- C1.6 C0 generation integration
- C1.7 Golden/fault tests

---

# 12. Acceptance criteria

- [ ] every Canonical object type has an explicit registered owner/storage class.
- [ ] B1/B4/B5/R1 can persist Canonical objects without inventing private writer logic.
- [ ] SOURCE continues to satisfy A1/A2 layout/invariants.
- [ ] all Canonical mutations share one lock/one C0 active Vault.
- [ ] revision mismatch never falls back to Last-write-wins.
- [ ] retry is idempotent and conflicting replay fails.
- [ ] AI output cannot directly overwrite Canonical truth.

---

# 13. One-line contract

> **C1 generalizes A2’s crash-safe single-writer semantics to every Canonical object TSUZU tracks, without changing the object-specific meaning owned by A/B/R contracts.**
