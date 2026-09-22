# TSUZU P0 Cross-cutting C0-C6 Contracts — Integrated v1.0

- Date: 2026-09-09
- Status: Convenience integrated view; standalone active Contracts + Contract Index v2.1 control precedence.


---

<!-- BEGIN TSUZU_P0_C0_Active_Vault_Locator_Root_Boundary_Contract_v0.1_20260909.md -->

# TSUZU P0 C0 — Active Vault Locator / Root Boundary Contract v0.1

- Date: 2026-09-09
- Status: **Cross-cutting Foundation Contract / Closed / Ready to implement**
- Canonical basis: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1
- Applies to: A2, A4, A5, A6, B1-B7 where persistent state is resolved, R1-R7, especially R5 cutover
- Scope: active Vault identity, root resolution, generation-safe handles, filesystem capability preflight, atomic locator cutover
- Non-scope: backup contents, schema migration semantics, multi-writer consensus, sync conflict merge, cloud discovery

---

# 0. Decision

P0では、各moduleがVault pathを個別設定・hard-code・自動探索してはならない。

すべてのpersistent/read-write componentは、**1つのlocal Active Vault Locator**を通じて現在のVaultを解決する。

```text
component
  -> C0 resolveActiveVault()
  -> vault_id + root + generation + capabilities
  -> operation
```

R5 Restore / MigrationによるVault切替は、directory内容をlive pathへ上書きするのではなく、検証済みcandidate Vaultへ**locatorをatomicに切り替える**。

---

# 1. Hard invariants

1. Active Vaultはpath文字列だけではなく`vault_id`で識別する。
2. LocatorはActive Vaultの内部に置かない。
3. Locatorがmissing/corrupt/ambiguousならfail closedし、近傍directoryを勝手に探索しない。
4. すべてのwriterは操作開始時にlocator generationを取得する。
5. long-running writeのcommit前にgenerationが変化していないことを確認する。
6. R5 cutoverはexpected generation付きCAS相当で行う。
7. old Vaultとnew Vaultを同時にmutable writerとして公開しない。
8. Vault rootはuser-controlled filenameやremote contentから決めない。
9. symlink/reparse/path traversalにより許可root外へ書かない。
10. filesystem capabilityが不明ならCanonical writeを開始しない。
11. Locator recordへcredential/body/contentを保存しない。
12. locator changeはbody-free audit/receiptを残す。

---

# 2. Locator record

概念Schema:

```yaml
locator_schema_version: "1.0.0"
locator_revision: 7

active:
  vault_id: uuid
  root_ref: platform_path_or_bookmark_reference
  root_fingerprint: sha256
  volume_identity: opaque_platform_identity
  generation: 12

capabilities:
  local_read: true
  local_write: true
  same_volume_staging: true
  atomic_rename: true
  no_clobber_publish: true
  coordinated_access: SUPPORTED | NOT_REQUIRED | UNSUPPORTED

updated_at:
updated_by_operation_id:
```

`root_ref`をHost Context / telemetry / external modelへ送らない。

---

# 3. Storage location

LocatorはVault外のTSUZU-managed local application stateに置く。

概念例:

```text
~/Library/Application Support/TSUZU/control/active-vault.json
```

実際のplatform pathは実装stackで確定してよいが、以下は必須。

- synced Canonical Vault内部ではない
- credential storeではない
- user content storageではない
- atomic replace可能
- OS account protection下

---

# 4. Public interface

```text
resolve_active_vault() -> VaultHandle
preflight_vault(root_ref) -> VaultCapabilityReport
compare_generation(handle) -> CURRENT | STALE
switch_active_vault(expected_generation, candidate_handle, operation_id) -> SwitchResult
inspect_locator() -> body-free LocatorHealth
```

### VaultHandle

```yaml
vault_id:
root_ref:
generation:
capability_report_hash:
resolved_at:
```

Handleはauthority tokenではない。write permissionはA2/C1 Single Writer Boundaryが別途判定する。

---

# 5. Filesystem capability preflight

最低限確認する。

- readable/writable
- stagingとCanonicalを同一volumeに置ける
- atomic rename/replace
- no-clobber create semantics
- directory/file fsync相当の利用可否
- symlink escape防止
- File Provider/iCloudの場合のcoordination strategy

安全なCanonical atomicityを実現できないfilesystemはP0 Vaultとしてunsupported。

Network share / arbitrary SMB/NFSをP0 supported rootとしない。

---

# 6. Generation binding

以下のraceを禁止する。

```text
worker resolves old Vault A
R5 switches to Vault B
worker commits into old Vault A
```

write operationは:

```text
resolve generation G
  -> compute/stage
  -> before publish verify locator generation == G
  -> if changed: abort/requeue against new Vault
```

R5 maintenance barrier中はnew Canonical mutationをboundedに停止/queueできる。

---

# 7. R5 cutover

R5 candidateがREADYになった後のみ:

```text
1. verify maintenance lock
2. expected_generation = current G
3. verify candidate vault_id != current vault_id
4. atomic locator replace G -> G+1
5. read-back locator
6. health smoke test through newly resolved handle
7. if failure before maintenance release:
     rollback locator G+1 -> G+2 pointing old Vault
8. release maintenance lock
```

Rollbackでもgenerationは単調増加させる。古いhandleの再利用を防ぐため。

---

# 8. Failure behavior

| Failure | Required behavior |
|---|---|
| locator missing | RED / fail closed; no arbitrary directory scan |
| locator corrupt | RED / recovery action required |
| root unavailable | read/write denied; health degraded |
| generation changes mid-write | abort publish / retry against current Vault |
| candidate cutover CAS mismatch | do not switch; re-evaluate |
| filesystem lacks no-clobber | unsupported as mutable Canonical Vault |
| path resolves outside approved root | deny |
| old Vault still mounted | not an authority; locator decides current Vault |

---

# 9. Golden cases

1. **Single resolution** — A2/A5/R1 resolve identical active vault_id/generation.
2. **Mid-write cutover** — staged write against old generation cannot publish after R5 switch.
3. **Corrupt locator** — system fails closed rather than choosing newest-looking directory.
4. **Cutover rollback** — post-switch health failure restores old Vault through a new generation.
5. **Symlink escape** — Canonical write outside root is denied.
6. **Unsupported filesystem** — preflight blocks initialization before first Canonical write.
7. **Old handle reuse** — stale handle is rejected after generation advance.

---

# 10. Implementation tasks

- C0.1 locator schema + codec
- C0.2 platform root reference abstraction
- C0.3 filesystem capability preflight
- C0.4 generation-aware VaultHandle
- C0.5 atomic CAS cutover + rollback
- C0.6 health projection + body-free receipt
- C0.7 Golden/fault tests

---

# 11. Acceptance criteria

- [ ] every persistent subsystem can resolve Vault only through C0.
- [ ] no writer hard-codes a live Vault root.
- [ ] locator corruption fails closed.
- [ ] generation change prevents stale commits.
- [ ] R5 can switch and rollback without mutating two active Vaults concurrently.
- [ ] capability preflight blocks unsupported storage.
- [ ] locator telemetry contains no user content/credential.

---

# 12. One-line contract

> **C0 makes “which Vault is current” a single generation-safe local authority so restore/migration can switch state without stale writers continuing to mutate the wrong Vault.**

<!-- END TSUZU_P0_C0_Active_Vault_Locator_Root_Boundary_Contract_v0.1_20260909.md -->

---

<!-- BEGIN TSUZU_P0_C1_Generic_Persistent_Object_Persistence_Canonical_Mutation_Contract_v0.1_20260909.md -->

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

<!-- END TSUZU_P0_C1_Generic_Persistent_Object_Persistence_Canonical_Mutation_Contract_v0.1_20260909.md -->

---

<!-- BEGIN TSUZU_P0_C2_Effective_Source_Representation_Materialization_Projection_Trace_Contract_v0.1_20260909.md -->

# TSUZU P0 C2 — Effective Source Representation / Materialization / Projection / Trace Contract v0.1

- Date: 2026-09-09
- Status: **Cross-cutting Integration Contract / Closed / Ready to implement**
- Canonical basis: Capture/Acquisition separation, immutable Source Versions, Source Trace, Canonical/Derived separation
- Depends on: A1, A5, A6, A7, A8, C1, C3, R1; R2 specializes acquired fidelity
- Scope: deterministic selection of raw content representation, safe rebuildable text projection for index/context, and trace linkage back to user capture
- Non-scope: network fetching, semantic extraction algorithm, Discovery ranking, remote refresh policy

---

# 0. Problem closed by C2

A1 URL Source preserves the **user capture action and locator**. R1 stores fetched remote bytes as immutable `SOURCE_VERSION`.

Without C2, A5/A7 can keep indexing only the URL locator while the acquired page body exists but is never recallable.

C2 defines one explicit bridge:

```text
Root SOURCE (user action)
    + eligible SOURCE_VERSION (content evidence)
        -> Effective Source Representation
        -> A5 projection
        -> A7 revalidation
        -> A8 body + Source Trace
```

Root Source identity is never replaced by a fetched version.

---

# 1. Concepts

## Root Source

A1 `SOURCE`. Represents what the user captured/saved.

## Representation

Bytes/text eligible to represent that Source for a purpose.

- direct TEXT/FILE payload from Root Source
- acquired remote `SOURCE_VERSION` from R1/R2
- locator-only metadata when body is unavailable

## Effective Representation

The deterministic representation selected at query/index time under current deletion/sensitivity/scope/integrity state.

---

# 2. Hard invariants

1. `source_id` remains the primary user-action identity.
2. SOURCE_VERSION never overwrites Root Source payload.
3. A5 must not assume Root Source payload is always the best content body.
4. A7/A8 must re-resolve/revalidate representation from persistent truth; FTS snippet is not authority.
5. C3 deletion of Root Source makes every child representation ineligible.
6. C3 deletion of one Source Version removes only that version; root may remain locator-only or use another eligible version.
7. effective sensitivity can only stay equal or become stricter than the Root Source.
8. child representation cannot widen Root Source scope.
9. unknown/corrupt representation fails closed for body usage.
10. Source Trace records both user capture root and actual representation used.
11. External content remains `UNTRUSTED_DATA` regardless of fidelity.
12. No summary/extraction is promoted to Canonical remote bytes.

---

# 3. Resolver interface

```text
resolve_effective_representation(source_id, purpose, as_of?)
  -> EffectiveRepresentation
```

P0 purposes:

- `INDEX_CURRENT`
- `RETRIEVAL_CURRENT`
- `CONTEXT_CURRENT`
- `TRACE_ONLY`

Historical time-travel UI is not P0, but immutable versions must not block future `as_of` support.

---

# 4. Selection rules

## TEXT / direct note

```text
valid LIVE Root Source payload
-> representation = ROOT_PAYLOAD
```

## FILE

If supported textual payload is directly indexable:

```text
ROOT_PAYLOAD
```

Otherwise metadata-only until a separate extractor Contract produces Derived text. C2 does not invent OCR/parser semantics.

## URL

Candidate Source Versions must satisfy:

- parent_source_id == source_id
- integrity valid
- effective deletion == LIVE
- acquisition status success
- sensitivity known
- representation version supported

For P0 `CURRENT` purpose, select deterministic newest eligible acquired version by:

```text
acquired_at DESC
then object_id deterministic tie-break
```

If none exists:

```text
LOCATOR_ONLY
```

Because R1 does not auto-refresh in P0, most URL Sources have zero or one acquired version initially.

---

# 5. Effective policy fields

### Sensitivity

```text
effective_sensitivity = stricter(root.sensitivity, representation.sensitivity)
```

If either side is unknown -> UNKNOWN -> external fail closed.

### Scope

Representation may narrow but never widen Root scope.

```text
effective_scope = intersection(root_scope, representation_scope_constraints)
```

If no valid intersection -> ineligible.

### Temporal

Expired/current-fact rules from Canonical apply to both root and child.

---

# 6. EffectiveRepresentation schema

Runtime/Derived projection descriptor:

```yaml
root_source_id:
representation_kind: ROOT_PAYLOAD | SOURCE_VERSION | LOCATOR_ONLY
representation_ref:
  object_type: SOURCE | SOURCE_VERSION
  object_id:
content_sha256: null | sha256
content_bytes: null | integer
media_type:
fidelity: DIRECT_USER | ORIGIN_RESPONSE | RESCUE_VERBATIM | RESCUE_RECONSTRUCTED | LOCATOR_ONLY

effective_scope:
effective_sensitivity:
resolved_at:
resolver_version:
```

This descriptor is not a new Canonical truth.

---

# 7. Indexable text projection

Raw Canonical bytes are not automatically indexable text. C2 therefore owns the semantic boundary of a **rebuildable text projection**. Execution/retry may use C4.

```text
Canonical raw representation
 -> media-type-specific local deterministic extractor
 -> Derived Text Projection
 -> A5 FTS / A8 excerpt
```

P0 rules:

- `text/plain` / Markdown-like text: bounded charset decode/normalization.
- HTML: no script execution; deterministic local parsing/sanitization/visible-text extraction.
- PDF: local deterministic text extractor adapter when supported; if extraction cannot be performed safely, record `EXTRACTION_UNAVAILABLE` and remain metadata-only rather than inventing text.
- Binary/unsupported media: metadata-only unless a separately registered safe extractor exists.
- No LLM summary is a substitute for raw-text extraction.
- extractor output is Derived/rebuildable and never overwrites raw SOURCE/SOURCE_VERSION bytes.

Conceptual projection descriptor:

```yaml
text_projection:
  projection_id:
  root_source_id:
  raw_representation_ref:
  raw_sha256:
  extractor_id:
  extractor_version:
  status: READY | METADATA_ONLY | EXTRACTION_UNAVAILABLE | FAILED
  text_sha256: null | sha256
  text_bytes: null | integer
  generated_at:
```

A5 indexes only a `READY` text projection or direct safe text representation. A8 may excerpt the same validated projection, and Source Trace includes raw representation + extractor version.

---

# 8. A5 index projection integration

A5 `source_index`/FTS projection must carry enough identity to prove what body was indexed.

Conceptual columns:

```text
root_source_id
representation_object_type
representation_object_id
representation_sha256
resolver_version
projection_version
scope/sensitivity snapshot
```

FTS body comes from the C2 validated text projection (or direct safe text representation), never automatically from raw binary/HTML bytes or `SOURCE.payload/original` alone.

Rebuild:

```text
Canonical Root Sources
+ eligible SOURCE_VERSION objects
+ C3 deletion truth
-> C2 resolve
-> A5 deterministic projection
```

A rebuilt index must select the same representation under identical inputs/policy versions.

---

# 9. A7 retrieval revalidation

An index hit is only a candidate.

A7 must:

1. re-read Root Source;
2. ask C3 effective deletion;
3. re-resolve C2 representation;
4. compare indexed representation identity/hash where needed;
5. re-evaluate current sensitivity/scope/destination policy;
6. drop stale index candidate if resolver result changed.

A stale index can never force use of a deleted/older representation.

---

# 10. A8 Context / Source Trace

A8 revalidates the selected raw representation after A7 approval, then uses the matching READY C2 text projection for excerpting when projection is required. It does not treat a stale FTS snippet as body authority.

Trace must distinguish:

```yaml
source_trace:
  root_source_id:
  representation:
    object_type:
    object_id:
    sha256:
    fidelity:
  text_projection:
    projection_id: optional
    extractor_id: optional
    extractor_version: optional
    text_sha256: optional
  acquisition_receipt_ref: optional
  excerpt_range_or_method:
```

User-facing trace can link to the original capture while diagnostic trace proves which version supplied the content.

---

# 11. Deletion and reacquisition

### Root deleted

All versions become ineligible immediately through C3, even if version files remain pending purge.

### Version deleted

Resolver selects next eligible version or LOCATOR_ONLY. It never resurrects the deleted version.

### New explicit reacquisition

New immutable Source Version may become `CURRENT` representation without overwriting history.

Index invalidation/reprojection is dispatched through C4/A5.

---

# 12. Failure behavior

| Failure | Behavior |
|---|---|
| root missing/corrupt | no representation / health error |
| selected version corrupt | exclude; fall back only to another independently valid eligible representation |
| deletion truth unavailable | fail closed |
| sensitivity unknown | external deny; index policy follows configured safe rule |
| stale FTS version ref | candidate discarded/reprojected |
| body unavailable | locator/metadata-only, not fabricated body |
| version-parent mismatch | quarantine version |

---

# 13. Golden cases

1. **URL body recall** — captured URL + R1 version indexes page body and A8 traces both IDs.
2. **No acquisition** — URL remains locator-only; system does not hallucinate page content.
3. **Reacquisition** — newer valid version becomes current; older remains historical.
4. **Version delete** — deleted current version is not used; next eligible/locator fallback.
5. **Root delete** — all child content disappears from retrieval despite stale FTS rows.
6. **Sensitive upgrade** — child SENSITIVE makes effective representation SENSITIVE.
7. **Stale index** — A7 detects mismatch and drops old representation.
8. **R2 reconstructed rescue** — fidelity stays reconstructed in trace and is never labeled origin response.
9. **HTML projection** — scripts are not executed; visible text projection rebuilds deterministically.
10. **PDF unavailable extractor** — metadata-only status, no fabricated text.

---

# 14. Acceptance criteria

- [ ] acquired Web/X body can reach A5/A7/A8 without mutating Root Source.
- [ ] every indexed body has a representation identity/hash.
- [ ] stale/deleted representation cannot survive Canonical revalidation.
- [ ] effective sensitivity/scope never weakens root restrictions.
- [ ] Source Trace names both capture root and content representation.
- [ ] rebuild produces equivalent representation selection.
- [ ] HTML/PDF/raw binary never becomes index text without a registered safe projection path.
- [ ] A8 trace can identify extractor/version for projected text.

---

# 15. One-line contract

> **C2 makes captured identity and acquired content coexist: TSUZU remembers what the user saved, indexes the best eligible immutable representation, and can always prove exactly which bytes informed recall.**

<!-- END TSUZU_P0_C2_Effective_Source_Representation_Materialization_Projection_Trace_Contract_v0.1_20260909.md -->

---

<!-- BEGIN TSUZU_P0_C3_Generic_Deletion_Ledger_Purge_No_Resurrection_Contract_v0.1_20260909.md -->

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

<!-- END TSUZU_P0_C3_Generic_Deletion_Ledger_Purge_No_Resurrection_Contract_v0.1_20260909.md -->

---

<!-- BEGIN TSUZU_P0_C4_Derived_Processing_Orchestrator_Job_Recompute_Contract_v0.1_20260909.md -->

# TSUZU P0 C4 — Derived Processing Orchestrator / Job / Recompute Contract v0.1

- Date: 2026-09-09
- Status: **Cross-cutting Foundation Contract / Closed / Ready to implement**
- Canonical basis: v1.2 Realtime/Batch Processing + v1.2.1 dependency invalidation/recompute
- Depends on: C0, C1, C3, A3 Secret Guard, A7 policy library where external model egress is used
- Applies to: B2 Episode, B3 Candidate, B5 Reconciliation, B6 Learning, B7 invalidation/recompute, B8 precompute; acquisition-specific network jobs remain R1-owned
- Scope: durable local derived job scheduling, idempotency, input fingerprinting, stale generation, crash recovery, recompute/invalidation priority
- Non-scope: object-specific AI prompts, promotion policy, Acquisition network retry, Canonical user event invention, host recall transport

---

# 0. Decision

B contracts define what Derived processing means but not who owns the durable batch/job lifecycle.

C4 provides one orchestrator for derived work:

```text
Canonical event/change
  -> dependency trigger
  -> C4 job
  -> safe input snapshot/fingerprint
  -> model/algorithm
  -> validate output
  -> Derived materialization
  -> dependency edges/generation
```

At-least-once execution is allowed. Observable Derived effect must be idempotent/equivalent.

---

# 1. Job classes

Initial registered job types may include:

- `EPISODE_SEGMENT`
- `CANDIDATE_EXTRACT`
- `DECISION_RECONCILE`
- `EXPERIENCE_TRACE_RECOMPUTE`
- `DEPENDENCY_INVALIDATE`
- `PATTERN_RECOMPUTE`
- `DISCOVERY_PRECOMPUTE`
- `DERIVED_INDEX_REPROJECT`

Exact implementation can add internal job types only through a versioned registry. External content cannot register jobs.

---

# 2. Runtime job schema

Runtime durable state, not Canonical Knowledge:

```yaml
job_id:
job_type:
job_key_hash:
trigger_ref:
input_refs: []
input_fingerprint:
algorithm_version:
policy_version:
created_at:
attempt_count:
state: PENDING | RUNNING | RETRY_WAIT | SUCCEEDED | PERMANENT_FAILURE | BLOCKED_STALE | CANCELLED
next_attempt_at:
output_refs: []
last_failure_code:
```

Queue/body cache belongs outside synced Canonical truth and is excluded from R5 PROTECTED backup.

---

# 3. Idempotency identity

```text
job_key = H(
  job_type
  + normalized input object ids/revisions/content hashes
  + algorithm_version
  + policy_version
  + relevant scope
)
```

Same key:

- duplicate delivery -> one equivalent Derived generation;
- crash/retry -> no duplicate semantic outputs;
- algorithm/input revision change -> new key/generation.

---

# 4. Input safety gate

Before model/algorithm invocation:

1. resolve current C0 Vault;
2. re-read referenced persistent objects;
3. apply C3 deletion eligibility;
4. reject corrupt/unknown schema;
5. apply A3/current Secret Guard where body is processed;
6. enforce sensitivity/scope;
7. if external model is used, invoke the shared destination-aware **A7 Policy/Egress Decision Core** factored from A7 hard rules; C4 is only a caller and cannot define a weaker policy. SENSITIVE external default-deny remains;
8. mark all content as untrusted data.

A queued job created before deletion/sensitivity change must not process stale unsafe input later.

---

# 5. Canonical authority boundary

C4 cannot turn model output into Canonical fact by itself.

### Allowed

- persist Derived Episode/Candidate/Assessment/Pattern/Discovery generations;
- update Derived dependency metadata;
- request C1 persistence only for a Canonical event already authorized/defined by its owner Contract and produced from a trusted non-AI authority path.

### Forbidden

```text
assistant/model says user decided X
-> C4 writes USER_EXPLICIT Decision Assertion
```

User Correction Event must be committed through B5+C1 before C4 recompute.

---

# 6. Derived storage/generation

Persistent Derived objects inherit Canonical Object Envelope fields required by v1.2.1 for traceability, but remain explicitly `DERIVED`.

Conceptual identity:

```yaml
object_id:
object_type:
storage_class: DERIVED
derivation:
  generation_id:
  input_fingerprint:
  algorithm_version:
  created_at:
  stale: false
```

New recompute does not rewrite the historical inputs.

Current eligibility resolves to the newest valid non-stale generation under owner policy.

---

# 7. Invalidation priority

Deletion/Correction/Sensitivity invalidation has higher priority than quality/enrichment work.

On C3 deletion or B5 Correction:

```text
1. synchronously mark known dependent current views ineligible/stale where possible
2. enqueue dependency invalidation/recompute
3. A7/B8 eligibility checks must also revalidate persistent truth and not rely solely on queue completion
```

Queue outage cannot make stale Derived knowledge authoritative.

---

# 8. Concurrency

Compute can run concurrently where safe, but:

- Canonical mutation still serializes through C1 shared writer.
- output commit uses deterministic/idempotent generation identity.
- two workers claiming same job use atomic claim/lease.
- lease expiration supports crash recovery.
- no unbounded worker spawning.

P0 may begin with one derived worker process for simplicity.

---

# 9. Retry classes

### Retryable

- temporary model/adapter outage
- transient I/O
- worker crash/lease expiration
- bounded rate limit

### Permanent/input-blocked

- invalid schema
- deleted input
- policy-denied external egress where no local path exists
- unsupported object version
- deterministic invalid model output after bounded retry

`PERMANENT_FAILURE` never changes Canonical evidence.

---

# 10. Failure behavior

| Failure | Behavior |
|---|---|
| crash after claim | lease expires/retry |
| crash after output temp write | no half published Derived object |
| input changed mid-compute | output fingerprint stale -> discard/requeue |
| input deleted mid-compute | no eligible output commit |
| invalidation queue unavailable | current dependent marked stale/ineligible; health degraded |
| external model denied by policy | no egress; retry only if policy/path changes |
| model output violates schema | reject; never coerce to Canonical |

---

# 11. Golden cases

1. **B2 crash retry** — one Episode generation after worker crash.
2. **Correction first** — Correction event persists; reconciliation crash cannot lose it.
3. **Deletion during compute** — output does not become eligible.
4. **Algorithm version bump** — new generation created; old inputs unchanged.
5. **Queue duplicate** — same job key converges.
6. **Invalidation queue failure** — stale Decision/Pattern is blocked before recompute finishes.
7. **Sensitive external processing** — default deny prevents body egress.
8. **Model hallucinated decision** — remains Derived Candidate, cannot become USER_EXPLICIT.

---

# 12. Implementation tasks

- C4.1 job type registry/schema
- C4.2 durable local queue + atomic claim/lease
- C4.3 input fingerprint builder
- C4.4 privacy/deletion preflight
- C4.5 Derived generation materializer
- C4.6 invalidation priority dispatcher
- C4.7 retry/health/receipts
- C4.8 Golden/fault tests

---

# 13. Acceptance criteria

- [ ] B2/B5/B7 background work has a single explicit lifecycle owner.
- [ ] job retries are idempotent.
- [ ] deletion/correction cannot be delayed into unsafe eligibility by queue outage.
- [ ] external model processing uses the shared **A7 Policy/Egress Decision Core** and observes Secret/Sensitivity policy; C4 has no independent allow path.
- [ ] model output cannot self-promote to Canonical user truth.
- [ ] input/algorithm change produces a new traceable generation.
- [ ] runtime queue is rebuildable/non-authoritative.

---

# 14. One-line contract

> **C4 owns the messy reality between “a Canonical event happened” and “Derived knowledge is safely recomputed,” making background AI work retryable, traceable and incapable of outranking Canonical truth.**

<!-- END TSUZU_P0_C4_Derived_Processing_Orchestrator_Job_Recompute_Contract_v0.1_20260909.md -->

---

<!-- BEGIN TSUZU_P0_C5_Canonical_Export_Portability_Contract_v0.1_20260909.md -->

# TSUZU P0 C5 — Canonical Export / Portability Contract v0.1

- Date: 2026-09-09
- Status: **Cross-cutting User Ownership Contract / Closed / Ready to implement**
- Canonical basis: v1.1 User Ownership, Data Management, Export; Vault-first / portability principle
- Depends on: C0, C1, C3, R5 integrity classification; invoked by R7 Control Plane
- Scope: user-triggered portable export of authoritative TSUZU state with checksums/schema inventory and deletion history protection
- Non-scope: cloud sync, automatic import/reimport, custom encrypted archive format, team sharing, public API/SDK

---

# 0. Decision

“User-owned” must be operational, not branding.

P0 provides one deterministic **Portable Canonical Archive** export that can be inspected/copied by the user and does not depend on TSUZU's disposable index/runtime state.

```text
R7 explicit Export
 -> C5 coherent read snapshot
 -> Portable Archive staging
 -> validate/checksum
 -> atomic finalization
```

---

# 1. Included by default

- LIVE Canonical Sources and payloads
- immutable eligible Source Versions
- Canonical Conversation records in supported scope
- Canonical Decision Assertions/Evidence/Correction Events/Experience records as defined by owner Contracts
- superseded but still LIVE history required to preserve Judgment Evolution
- generic C3 Deletion Ledger records (body-free)
- schema inventory and object registry version
- export manifest/checksums

The archive preserves provenance/history but does not revive tombstoned bodies.

---

# 2. Excluded by default

- SQLite/FTS/embeddings/indexes
- runtime queues/leases/cache
- temporary staging
- telemetry bodies (none should exist)
- OS Keychain credentials/tokens/cookies/private keys
- transient model prompts/responses not otherwise part of a defined persistent object
- tombstoned payload bytes

Derived objects are excluded from the required P0 portable archive because they are rebuildable and not authority. A future optional Derived export may be additive.

---

# 3. Restricted/secret anomaly behavior

Credential material must not be Canonical Knowledge. If export preflight detects high-confidence RESTRICTED material in a location that should be exported:

```text
EXPORT_BLOCKED_RESTRICTED
```

Do not silently omit a Canonical object and claim complete export.
Do not automatically include the secret.
Surface remediation through R7.

---

# 4. Export manifest

```yaml
export_format: TSUZU_PORTABLE_CANONICAL_ARCHIVE
export_format_version: "1.0.0"
export_id:
created_at:
source_vault_id:
source_locator_generation:

schema_inventory:
object_counts_by_type:
ledger_record_count:

files_manifest:
  - relative_path:
    sha256:
    bytes:

excluded_classes:
  - DERIVED_REBUILDABLE
  - RUNTIME
  - CREDENTIAL
```

Manifest itself contains no user content body.

---

# 5. Coherent snapshot boundary

P0 favors correctness over zero-pause export.

Options allowed:

- reuse R5 coherent maintenance/read barrier; or
- create a validated immutable temporary snapshot through a filesystem-safe mechanism.

Required property:

> Export must not combine half of object revision N and half of revision N+1.

Capture can queue during a short barrier according to existing durable capture semantics.

---

# 6. Deletion semantics

Before archive finalization:

- C3 generic ledger is read/validated.
- tombstoned object payload is excluded.
- deletion records are included so another TSUZU-aware future importer cannot naïvely resurrect stale material from mixed archives.

C5 is not a backup replacement: R5 remains the supported recovery Contract.

---

# 7. Privacy / UX

R7 must warn that the archive can contain PERSONAL/SENSITIVE user content.

P0 does not implement a proprietary encryption engine. User can choose a protected destination using OS/filesystem tools.

Export operation requires explicit user action and destination choice.

No automatic external upload.

---

# 8. Atomic finalization

```text
1. preflight destination capacity/write permission
2. resolve C0 generation
3. coherent snapshot/barrier
4. export to unique staging directory/file
5. calculate checksums
6. verify manifest/object coverage
7. recheck source generation/revision boundary as required
8. mark archive COMPLETE
9. atomic move/rename to chosen final destination where supported
10. body-free export receipt
```

Partial staging is never presented as a valid complete archive.

---

# 9. Failure behavior

| Failure | Behavior |
|---|---|
| destination full | fail; no valid final archive |
| Canonical corruption | fail complete export; surface recovery |
| C3 ledger unavailable | fail closed |
| RESTRICTED anomaly | block export pending remediation |
| file changes outside coherent snapshot | retry/new snapshot |
| checksum mismatch | archive invalid; do not mark complete |
| destination is external sync service | user-controlled destination only; TSUZU does not grant connector authority |

---

# 10. Golden cases

1. **Portable core** — export contains Canonical content and no SQLite/queue.
2. **Credential exclusion** — OS Keychain secret absent.
3. **Tombstone** — deleted body absent, deletion record present.
4. **Sensitive data** — exported locally with explicit privacy warning, not auto-uploaded.
5. **Interrupted export** — no COMPLETE archive.
6. **Corrupt source** — fail rather than silently skip.
7. **Superseded history** — retained when LIVE.
8. **Manifest verification** — every exported file checksum matches.

---

# 11. Acceptance criteria

- [ ] R7 Export invokes C5 rather than ad-hoc file copy.
- [ ] archive is complete/validated or clearly failed.
- [ ] Canonical history is portable without Derived/runtime dependencies.
- [ ] credentials and tombstoned bodies are absent.
- [ ] deletion ledger is preserved body-free.
- [ ] no automatic external upload occurs.
- [ ] export does not claim to be R5 recovery backup.

---

# 12. One-line contract

> **C5 turns user ownership into a testable feature: the authoritative record can leave TSUZU in a coherent, checksummed, credential-free archive without dragging along disposable indexes or deleted bodies.**

<!-- END TSUZU_P0_C5_Canonical_Export_Portability_Contract_v0.1_20260909.md -->

---

<!-- BEGIN TSUZU_P0_C6_Capability_Registry_Router_Interface_Contract_v0.1_20260909.md -->

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

<!-- END TSUZU_P0_C6_Capability_Registry_Router_Interface_Contract_v0.1_20260909.md -->
