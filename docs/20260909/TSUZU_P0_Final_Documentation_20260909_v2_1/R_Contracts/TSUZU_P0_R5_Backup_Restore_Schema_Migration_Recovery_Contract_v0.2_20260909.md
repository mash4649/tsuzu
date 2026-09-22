# TSUZU P0 R5 — Backup / Restore / Schema Migration / Recovery Contract v0.2

- Date: 2026-09-09
- Base:
  - TSUZU Canonical Product Architecture v1.1
  - TSUZU Canonical Addendum v1.2
  - TSUZU Canonical Closing Addendum v1.2.1
  - TSUZU Canonical Implementation Closure Addendum v1.2.2
- Depends on:
  - C0 Active Vault Locator / Root Boundary
  - C3 Generic Deletion Ledger / No-Resurrection
  - A1 Canonical Source Contract
  - A2 Atomic Vault Writer Contract
  - A4 Single Writer Worker Contract
  - A5 SQLite / FTS Derived Index + Rebuild Contract
  - A6 Minimal Tombstone / Deletion Ledger Contract
  - B7 Promotion / Dependency Invalidation / Recompute Contract where B objects exist
- Status: **Implementation Contract / Closed / Ready to implement**
- Scope: P0 backup snapshot, restore, schema compatibility/migration, recovery orchestration, C0 cutover, rollback, integrity/failure tests.
- Non-scope: cloud backup service, custom encryption engine, multi-device merge/conflict protocol, undelete, selective object restore UI, automatic 3-way merge, physical secure erase, credential migration, continuous version history, Time Machine replacement.

## v0.2 cross-cutting closure

- C0 is the sole Active Vault Locator authority; this Contract uses C0 rather than defining a second locator implementation.
- Every reference to Deletion Ledger in restore/backup semantics means the generic C3 ledger across `(object_type, object_id)`; A6 is the SOURCE specialization.
- R5 does not promise secure erase of historical backups. C3 owns best-effort active-store purge and the user-facing guarantee boundary.


---

# 0. Decision

R5は、TSUZUのRecoveryを次の原則で閉じる。

> **Canonicalを守り、Derivedは作り直し、Restoreはlive Vaultを直接上書きせず、Deletion Ledgerを最優先し、壊れた状態を検証前にcurrentへ昇格させない。**

P0のRecoveryは「何でも自動で救う」仕組みではない。

次を保証する最小Contractとする。

```text
Backup
  ↓ immutable snapshot
Verify
  ↓
Temporary Vault
  ↓
Deletion Ledger merge/reapply
  ↓
Schema compatibility / migration
  ↓
Canonical integrity validation
  ↓
Derived rebuild
  ↓
Smoke test
  ↓
Atomic active-vault cutover
```

以下は禁止する。

```text
backup -> blind overwrite live Vault
corrupt Canonical -> AI guess repair
old backup ledger -> overwrite current ledger
Derived DB -> restore authority
migration -> mutate current Vault in place
restore -> Last-write-wins merge
```

---

# 1. Canonical basis and responsibility boundary

R5は既存正本の以下を実装可能な形へ落とす。

## 1.1 Canonical requirements inherited

- Restoreはin-place overwriteしない。
- Temporary Vaultへ復元する。
- Integrity Checkを行う。
- Deletion Ledgerを再適用する。
- Schema compatibilityを確認する。
- Indexを再構築する。
- Smoke Test後に切り替える。
- SQLite破損はdiscard/rebuildする。
- Derived破損はCanonical parentからregenerateする。
- Canonical破損は重大障害としてBackupから復旧する。
- Schema Migration前にBackup必須。
- Readerは原則N-1 schemaを読める。
- CanonicalをAI推測で自動修復しない。
- Restore Test / Failure Injection TestをRelease/Founder Gateに含める。

## 1.2 Existing contract ownership

R5は既存責務を再定義しない。

```text
A2 = atomic file / metadata write primitives
A4 = single mutable writer execution boundary
A5 = disposable SQLite/FTS rebuild + atomic index swap
A6 = SOURCE deletion specialization; C3 = generic Deletion Ledger + no-resurrection precedence
B7 = downstream dependency invalidation/recompute
R5 = backup/restore/migration/recovery orchestration
```

R5のRecovery Coordinatorは上記を呼び出す。

---

# 2. Recovery invariants

R5 Hard Invariants:

1. **Active VaultをRestore/Migration中に直接上書きしない。**
2. **Backup Snapshotは作成後immutable。**
3. **Deletion Ledgerは常にSource/Knowledge状態より優先する。**
4. **TSUZU-managed restoreでは current generic C3 ledger UNION backup generic C3 ledger を先に構築する。**
5. **Current ledgerを古いbackup ledgerで置換しない。**
6. **Backup/RestoreからSQLite/FTS/queue/cache/lockを正本として復元しない。**
7. **Derivedの破損をCanonicalへ逆流させない。**
8. **Migration前Backupが成功しない限りMigrationを開始しない。**
9. **Schema migrationはdeterministic codeのみ。AI/LLMを使用しない。**
10. **Unsupported/unknown schemaは推測変換しない。**
11. **Restore candidateが完全検証されるまでactive locatorを変更しない。**
12. **Restore/Migration失敗時、現在のactive Vaultはそのまま利用可能である。**
13. **RESTRICTED credential/session secretをBackupへ追加しない。**
14. **Telemetry/operation receiptへSource本文を保存しない。**
15. **Unknown deletion stateはfail closed。**

---

# 3. Backup protection classes

物理directory名だけで「Backup対象/非対象」を推測しない。

P0ではversioned static registryとしてProtection Classを定義する。

```text
PROTECTED
REBUILDABLE
RUNTIME
EXTERNAL_SECRET
```

## 3.1 PROTECTED

失うとCanonical truth / user-owned history / safety factが失われるもの。

最低限:

- Raw Source / User Input
- Canonical Conversation Chronicle
- User Explicit records
- Promoted Knowledge
- Decision Case / canonical assertions where applicable
- Correction Event
- Outcome / canonical Experience evidence
- Lifecycle Event required for authoritative state
- Tombstone / Deletion Ledger
- Canonical system records required for identity/revision/schema
- body-free B10 Product Proof events/denominator records required to preserve an in-progress Founder experiment
- body-free security/egress trace records explicitly classified durable by their owning Contract

**物理pathに関係なくPROTECTEDはBackup必須。**

## 3.2 REBUILDABLE

Canonicalから再生成できるもの。

最低限:

- SQLite / FTS index
- Embeddings
- Derived summaries that are explicitly rebuildable
- Recomputed ranking/cache views
- Dependency/materialized views that can be reconstructed from protected refs

P0 authoritative Backupからは原則除外する。B10 Product Proof events are not placed here merely because they are body-free: during an active Founder experiment they are durable evidence and belong to PROTECTED system records.

Optional copyを将来持ってもよいが、Restore時にauthorityとして採用してはならない。

## 3.3 RUNTIME

Backupしない。

- pending/processing/retry runtime queues
- worker lock
- cache
- WAL/SHM
- temporary telemetry state
- rebuild candidates
- staging files

Runtimeはactive machineのoperation stateであり、Vault Backupではない。

## 3.4 EXTERNAL_SECRET

Backupしない。

- API Key
- OAuth access/refresh token
- session cookie
- private key
- recovery code
- OS Keychain secrets

Restore後にconnector re-authenticationが必要になってよい。

## 3.5 Unknown class

新しいpersistent object_typeがProtection Registryに存在しない場合:

```text
BACKUP_CLASS_UNKNOWN
→ backup fail closed
```

Silent omissionは禁止する。

---

# 4. Backup snapshot format

P0 Backupは**immutable versioned snapshot**とする。

論理構造:

```text
<backup_root>/
  <backup_id>/
    backup.md
    protected/
      ... copied protected objects ...
    COMMITTED
```

`backup_id`はUUIDv4等の衝突困難なID。

File/Directory名をbackup identityにしない。

## 4.1 backup.md

最低限:

```yaml
backup_id:
backup_contract_version: "1.0.0"
created_at:
completed_at:

source:
  vault_instance_id:
  vault_locator_hash:

protection_registry_version:

schema_inventory:
  - object_type:
    schema_versions: []
    count:

content_manifest:
  algorithm: "SHA-256"
  entry_count:
  manifest_hash:

privacy_summary:
  contains_public:
  contains_personal:
  contains_sensitive:
  contains_restricted_knowledge: false

deletion_ledger:
  record_count:
  ledger_manifest_hash:

app_contract:
  canonical_contract_version:
  created_by_app_version:
```

### No body in manifest

`backup.md`へ以下を保存しない。

- Source body
- Conversation body
- full URL content
- secret
- free-text user note

`content_manifest`の個別entryは最低限:

```text
relative_path
protection_class
object_type where applicable
byte_length
sha256
```

## 4.2 COMMITTED marker

Snapshotは最後に`COMMITTED`をdurable publishする。

`COMMITTED`がないSnapshotは:

```text
INCOMPLETE_BACKUP
```

Restore候補にしない。

---

# 5. Backup destination contract

## 5.1 Destination restrictions

Backup destinationは以下を満たす。

- active Vault rootの内部ではない
- App Support index/runtime directoryの内部ではない
- staging/rebuild directoryの内部ではない
- writable
- required capacityを満たす

Symlink等によりactive Vault内部へ再帰するdestinationは拒否する。

## 5.2 Privacy risk

P0はcustom encryption engineを実装しない。

そのためBackupはCanonicalと同等以上にprivacy-sensitiveと扱う。

Backup EngineはUIに依存せず、最低限以下を返せること。

```yaml
privacy_risk:
  contains_personal:
  contains_sensitive:
  destination_type:
  encryption_guarantee: UNKNOWN | OS_MANAGED | USER_MANAGED
  warning_required:
```

`destination_type`は最低限:

```text
LOCAL_USER_STORAGE
USER_SYNCED_STORAGE
REMOVABLE_STORAGE
UNKNOWN
```

UNKNOWN destinationへSENSITIVEを含むBackupを作成する場合、Control Plane側でwarning/confirmationを要求可能にする。

R5自身はUIを作らない。

---

# 6. Backup creation consistency

P0では複雑なfilesystem snapshot engineを作らない。

Recoverabilityをperformanceより優先し、**coherent backup barrier**を使う。

## 6.1 Write barrier

Backup開始時:

```text
1. validate destination
2. acquire Recovery/Maintenance operation lock
3. wait for current A4 Canonical commit boundary
4. pause new Canonical mutation commits
5. new Capture requests may remain in durable runtime queue
6. enumerate/copy PROTECTED set
7. verify copy
8. commit backup manifest + COMMITTED
9. release mutation barrier
10. A4 resumes queued work
```

新しいCapture ingress自体を失敗させる必要はない。

ただしBackup中にCanonicalへcommitはしない。

## 6.2 Why pause writes in P0

P0 Founder corpusでは、backup中の短時間write pauseを受け入れる。

目的:

- cross-object revisionのsnapshot drift回避
- TombstoneとSourceの時間差を減らす
- distributed snapshot protocolを持ち込まない

将来copy-on-write/snapshot APIへ最適化可能だが、R5 v0.1の要件ではない。

---

# 7. Backup creation algorithm

```text
1. BACKUP_REQUEST accepted
2. preflight destination / capacity / permissions
3. acquire maintenance lock
4. freeze Canonical mutation commits at boundary
5. load Protection Registry
6. enumerate all PROTECTED objects deterministically
7. validate each protected object before copy
8. copy exact bytes into backup staging
9. hash copied bytes
10. separately validate Deletion Ledger completeness/readability
11. write backup.md to staging
12. verify manifest against copied snapshot
13. fsync/durability boundary as supported
14. publish snapshot directory
15. publish COMMITTED last
16. read-back verify committed snapshot
17. release maintenance lock
18. record body-free receipt
```

If any PROTECTED object is corrupt/unreadable:

```text
BACKUP_SOURCE_INTEGRITY_FAILED
```

Normal healthy Backupとしてcommitしない。

Partial backupをsuccess扱いしない。

---

# 8. Backup operation result

Logical interface:

```text
createBackup(request) -> BackupResult
```

Request:

```yaml
request_id:
idempotency_key:
destination:
reason: MANUAL | PRE_MIGRATION | PRE_RESTORE | RECOVERY
```

Result:

```yaml
backup_id:
status: COMMITTED | FAILED | ALREADY_COMMITTED
created_at:
completed_at:
protected_object_count:
protected_bytes:
privacy_summary:
error_code:
```

Same idempotency key + same semantic request:

```text
ALREADY_COMMITTED
```

Conflicting request under same idempotency key:

```text
BACKUP_IDEMPOTENCY_CONFLICT
```

---

# 9. Restore modes

P0は2 restore modeを区別する。

## 9.1 NORMAL_RESTORE

Current VaultのDeletion Ledgerがvalid/readableな通常復元。

```text
restore ledger = current generic C3 ledger UNION backup generic C3 ledger
```

これが標準。

## 9.2 DISASTER_RESTORE

新端末/全損等で、current Deletion Ledgerが存在しない場合。

A6で確定済みの通り、backup以降に削除された情報を知る方法はない。

したがって:

```text
current ledger unavailable
+
backup ledger valid
=
DELETION_HISTORY_INCOMPLETE risk
```

P0 behavior:

- Normal Restoreとしてsilentに続行しない。
- 明示的なDisaster Restore modeが必要。
- Restore後Healthを`RECOVERED_WITH_DELETION_HISTORY_LIMITATION`とする。
- 「backup作成後に削除された項目が再出現する可能性」を表示可能なstructured warningを返す。

**Deletion historyをAIで推測しない。**

Founder safety gateの標準Restore TestはNORMAL_RESTOREを対象とする。

---

# 10. Restore is snapshot cutover, not merge

P0 Restoreはautomatic merge engineではない。

```text
Selected Backup Snapshot
→ validated restored Vault
→ active Vault switch
```

Current Vaultの新しいObjectをbackup snapshotへ自動3-way mergeしない。

例外は安全上必須の:

```text
Deletion Ledger = current UNION backup
```

のみ。

Restore開始前、current Vaultがhealthy enoughであれば、**PRE_RESTORE Backup**を作成する。

これによりbackup時点以降のcurrent dataを捨てる判断を可逆にする。

Current Vaultが破損して通常Backup不能の場合:

- PRE_RESTORE Backup failureを記録
- live Vaultを直接改変しない
- broken Vault pathをquarantine/retain
- Restore candidateを別pathで構築する

---

# 11. Temporary Vault restore layout

Restoreはlive rootへ展開しない。

例:

```text
<restore_workspace>/
  restore.<restore_id>/
    vault/
    restore-state.md
```

active Vaultと同じfilesystem semanticsが必要なcutoverを行う場合、最終candidateは同一volume上へ配置する。

ただしP0は「directory内容をliveへ上書き」より、**validated new Vault + active locator switch**を優先する。

---

# 12. Active Vault locator usage profile

C0がlocator contractの唯一のownerである。R5は以下のRecovery usage profileを要求する。

R5ではcurrent Vaultへの参照を中央resolver経由にする。

```text
C0.resolve_active_vault() -> generation-safe vault handle
```

A2/A4/A5/A6/B7等がhard-coded pathを独自保持してはいけない。

Cutover時:

```text
1. acquire maintenance lock
2. stop Canonical mutation commits
3. close Vault-bound readers/writers
4. atomically update local active-vault locator record
5. reopen against candidate Vault
6. run immediate health check
7. resume A4 queued mutations
```

Locator record自体はlocal Control Stateであり、Canonical user knowledgeではない。

Cutover後も旧Vaultを即時削除しない。

```text
old Vault -> recovery quarantine / retained rollback source
```

明示cleanupまでは保持可能とする。

---

# 13. Restore pipeline

NORMAL_RESTORE:

```text
1. RESTORE_REQUEST accepted
2. validate backup COMMITTED marker
3. verify backup manifest/hash inventory
4. verify backup schema inventory can be handled
5. if live Vault readable: create PRE_RESTORE Backup
6. acquire maintenance lock
7. pause Canonical commits; new Capture stays queued
8. materialize backup into Temporary Vault
9. validate all PROTECTED objects
10. load current Deletion Ledger
11. load backup Deletion Ledger
12. merge = current UNION backup
13. publish merged Ledger into Temporary Vault first
14. reapply effective deletion to restored objects
15. run schema compatibility/migration if needed
16. run Canonical integrity validation again after migration
17. discard all restored REBUILDABLE state if any exists
18. A5 full index rebuild from restored Canonical
19. B7 dependency invalidation/recompute bootstrap where implemented
20. run Restore Smoke Test
21. mark candidate READY
22. switch active-vault locator
23. reopen services
24. post-cutover health check
25. resume queued A4 mutations into new active Vault
26. retain old Vault/pre-restore backup for rollback
27. body-free restore receipt
```

Deletion Ledger merge must occur **before** any restored Source becomes retrieval-eligible.

---

# 14. Deletion Ledger merge contract

## 14.1 Set semantics

Deletion record identity (C3 generic):

```text
(object_type, object_id)
```

For same target:

### same valid deletion semantics

Use one effective record; preserve earliest valid deletion fact where semantically equivalent.

### conflicting valid records

Example:

```text
same target
but different payload fingerprint / impossible source identity
```

Result:

```text
DELETION_LEDGER_CONFLICT
→ restore fail closed
```

AIで解決しない。

## 14.2 Current wins only by union, not overwrite

「current wins」はLWWを意味しない。

意味は:

```text
if either valid ledger says deleted
→ deleted
```

削除単調性を守る。

---

# 15. Canonical integrity validation during restore

最低限:

- required directory/system state readable
- known protected object schema valid
- object_id/path consistency where contract requires
- revision valid
- payload exists where required
- payload byte length matches
- payload SHA-256 matches
- source immutable payload contract preserved
- Deletion Ledger records valid
- no deletion target/path mismatch
- no unknown PROTECTED object class
- no RESTRICTED credential material introduced as Knowledge through restore processing

Corrupt objectをskipしてRestore成功にはしない。

```text
RESTORE_CANONICAL_INTEGRITY_FAILED
```

---

# 16. Schema compatibility contract

Schema compatibilityはobject typeごとに判定する。

Current appを`N`としたP0 default:

```text
schema == N
→ READ_NATIVE

schema == N-1
→ READ_COMPATIBLE / MIGRATE_TO_N before cutover

schema > N
→ RESTORE_REQUIRES_NEWER_APP

schema < N-1
→ UNSUPPORTED_OLD_SCHEMA
   unless an explicitly registered and tested migration chain exists

unknown object_type/schema
→ SCHEMA_UNKNOWN_FAIL_CLOSED
```

「だいたい読めそう」で続行しない。

---

# 17. Canonical migration contract

Canonical migrationはlive Vaultへ直接行わない。

```text
Current Vault
  ↓ mandatory pre-migration Backup
Temporary Migration Vault
  ↓ deterministic migration
Validate
  ↓ rebuild Derived
Smoke
  ↓ active locator cutover
```

## 17.1 Migration properties

Migration functionは:

- deterministic
- versioned
- test fixtureあり
- idempotent where practical
- body meaningを勝手に変更しない
- AI/LLM不使用
- Source raw payloadを変更しない
- object_idを維持
- schema_versionを明示更新
- required revision/update semanticsを守る

## 17.2 Migration registry

Logical interface:

```text
migrate(object_type, from_version, to_version, object)
```

Unregistered migration:

```text
MIGRATION_PATH_MISSING
```

## 17.3 Migration receipt

Body-free system record:

```yaml
migration_id:
started_at:
completed_at:
from_schema_inventory_hash:
to_schema_inventory_hash:
migration_contract_version:
object_counts:
failure_counts:
pre_migration_backup_id:
status:
```

Source本文を保存しない。

---

# 18. Pre-migration backup gate

Migration開始条件:

```text
pre_migration_backup.status == COMMITTED
AND backup read-back verification passed
```

Backup失敗時:

```text
MIGRATION_BLOCKED_NO_BACKUP
```

Migrationを開始しない。

これはwarningではなくHard Gate。

---

# 19. Migration rollback

Migration failure before cutover:

```text
active Vault untouched
candidate quarantined/discardable
pre-migration backup retained
```

Migration failure after locator cutover but immediate health check before release:

```text
reacquire/retain maintenance lock
switch locator back to old Vault
mark migration failed
keep candidate for diagnosis without body telemetry export
```

A4 queued mutationsはrollback完了後にold active Vaultへ再開する。

---

# 20. Recovery class behavior

## 20.1 SQLite / FTS corrupt

Ownership: A5.

```text
detect
→ close
→ discard derived DB/sidecars
→ rebuild from active Canonical
```

R5はCanonical Restoreを起動しない。

## 20.2 Rebuildable Derived corrupt

```text
mark stale/ineligible
→ regenerate from protected parent/evidence
```

必要に応じてB7を使う。

CanonicalへDerived内容を戻さない。

## 20.3 Canonical object corrupt

```text
stop strong use of affected object
health = CANONICAL_INTEGRITY_FAILURE
→ recover from valid Backup
```

AI inferenceで修復しない。

## 20.4 Deletion Ledger unavailable/corrupt

Ownership: A6 safety rule。

```text
UNKNOWN_FAIL_CLOSED
→ recall/rebuild eligibility deny
→ restore/recovery required
```

可用性よりanti-resurrectionを優先する。

## 20.5 Runtime queue corrupt

Runtime stateはBackup source of truthではない。

Recoverable jobのみquarantine/retry policyへ。

Canonical committed receiptがあるものを二重commitしない。

R5はA4 idempotency contractを利用する。

---

# 21. Restore Smoke Test

Restore candidateをREADYにする最低条件:

1. Canonical protected-object full validation PASS
2. Deletion Ledger full validation PASS
3. effective deletion resolver PASS
4. A5 `integrity_check` PASS on rebuilt index
5. eligible source set is consistent with Canonical + Ledger
6. fixed bounded exact-ID/read fixtures PASS
7. TOMBSTONED fixture is not retrievable
8. current active Hostを使わないlocal retrieval smoke PASS
9. no external AI egress required
10. body-free Health state = RESTORE_CANDIDATE_HEALTHY

Personal Discovery品質そのものをRestore Gateにしない。

B-derived rebuildが未完了の場合:

```text
Canonical healthy
Index healthy
Discovery derived rebuilding
→ candidate may cut over with Health YELLOW
```

ただしstale B-derived objectをstrong current useしてはならない。

---

# 22. Health states exposed by R5

R7 Control Planeが利用できるstructured health onlyを定義する。

```text
HEALTHY
BACKUP_IN_PROGRESS
BACKUP_FAILED
RESTORE_IN_PROGRESS
RESTORE_CANDIDATE_INVALID
RESTORE_READY
RECOVERED_WITH_DELETION_HISTORY_LIMITATION
MIGRATION_IN_PROGRESS
MIGRATION_BLOCKED_NO_BACKUP
MIGRATION_FAILED
CANONICAL_INTEGRITY_FAILURE
DELETION_LEDGER_UNAVAILABLE
DERIVED_REBUILDING
```

R5は日常Dashboardを作らない。

---

# 23. Failure behavior

| Failure | Required behavior |
|---|---|
| Backup interrupted before COMMITTED | incomplete; never selectable as valid restore |
| Backup destination full | fail backup; live Vault untouched |
| Source corrupt during backup | fail healthy backup; do not silently skip |
| Manifest/hash mismatch | backup invalid; restore denied |
| Unknown protected object class | fail closed |
| Restore interrupted before cutover | live Vault unchanged |
| Current Ledger valid, backup Ledger stale | union; current deletion remains effective |
| Ledger record conflict | restore fail closed |
| Current Ledger unavailable in normal restore | normal restore denied; explicit Disaster Restore only |
| Backup schema newer than app | require newer app; no downgrade guess |
| Backup schema N-1 | migrate in Temporary Vault |
| Migration path missing | fail before cutover |
| Pre-migration backup fails | migration not started |
| Migration crashes | old live Vault remains/switches back |
| Index rebuild fails | candidate not READY for normal Founder restore |
| B-derived recompute fails | mark stale/ineligible; Canonical may remain recoverable |
| Active locator cutover health check fails | rollback locator before releasing maintenance lock |

---

# 24. Concurrency and maintenance lock

R5 operation lockはA4 Single Writer process boundaryと協調する。

P0では同時に許可しない:

```text
Backup commit snapshot
Restore cutover
Canonical schema migration
```

Operation ordering:

```text
one Recovery/Maintenance operation at a time
```

Capture ingressは可能ならdurable queueへ受け入れてよいが、Canonical commitはbarrier解除まで待つ。

Delete mutationも同様にqueueされる。

**Restore中にDeletion mutationを別Vaultへcommitさせない。**

---

# 25. Backup retention and cleanup

R5 v0.1はretention policyを自動最適化しない。

P0 minimum:

- committed Backupを自動上書きしない
- pre-migration Backupはmigration success直後に自動削除しない
- pre-restore Backupはrestore success直後に自動削除しない
- incomplete stagingはrecovery scanでcleanup可能
- deletion of old backups is explicit Control Plane operation in R7 scope

Backup削除はCanonical Source deletionとは別操作。

---

# 26. Security boundaries

## 26.1 Backup content is data

Backup内のWeb/X/PDF/Conversation本文はuntrusted data。

Restore中に:

- promptとして実行しない
- Tool命令として解釈しない
- migration instructionとして解釈しない
- external AIへ送らない

## 26.2 No credentials

OS Credential StoreはBackup対象外。

Restoreによってconnector secret/sessionを復元しない。

## 26.3 Filesystem safety

Restore enumeration時:

- path traversal拒否
- unexpected symlink拒否/明示扱い
- manifest外fileをauthorityとして自動読込しない
- expected regular-file/directory structureを検証

## 26.4 Telemetry

Allowed:

- backup_id / restore_id / migration_id
- counts / bytes
- durations
- error codes
- hash/fingerprint where not secret-derived leakage risk
- schema versions
- health states

Not allowed:

- Source body
- Conversation body
- FTS body
- full URLs
- credentials
- backup archive/file itself

---

# 27. Recovery operation receipts

Body-free local receiptsを残す。

## Backup Receipt

```yaml
operation: BACKUP
request_id:
backup_id:
status:
started_at:
completed_at:
protected_object_count:
manifest_hash:
error_code:
```

## Restore Receipt

```yaml
operation: RESTORE
restore_id:
backup_id:
mode: NORMAL_RESTORE | DISASTER_RESTORE
status:
started_at:
completed_at:
pre_restore_backup_id:
merged_deletion_record_count:
from_schema_inventory_hash:
to_schema_inventory_hash:
old_vault_locator_hash:
new_vault_locator_hash:
error_code:
```

## Migration Receipt

Section 17.3を使用。

Receiptsに本文を保存しない。

---

# 28. Golden Cases

R5 Mandatory Golden Cases:

## R5-G1 — Healthy Backup / Restore Round Trip

Given:
- valid active Vault
- LIVE Sources
- valid Deletion Ledger

When:
- backup
- restore into Temporary Vault
- rebuild A5
- smoke
- cutover

Then:
- protected Canonical identity/revision/hash set preserved
- live eligible Source set equivalent
- no body copied into telemetry

## R5-G2 — Interrupted Backup

Inject crash after file copy but before COMMITTED.

Expected:
- snapshot not valid
- live Vault unchanged
- retry creates/finishes one valid snapshot by idempotency policy

## R5-G3 — Corrupt Backup Payload

Modify one backed-up payload byte.

Expected:
- hash validation fails
- restore denied before cutover

## R5-G4 — Tombstone No Resurrection

Given:
- old backup contains Source as LIVE
- current Ledger says Source deleted

Restore.

Expected:
- current UNION backup ledger contains deletion
- restored Source remains ineligible
- A5 rebuild excludes it

## R5-G5 — Restore Crash Before Cutover

Crash after Temporary Vault build but before active locator update.

Expected:
- old active Vault still active
- candidate remains non-authoritative
- restart can discard/resume safely

## R5-G6 — N-1 Schema Migration

Backup contains supported N-1 object schema.

Expected:
- migration runs only in Temporary Vault
- raw payload unchanged
- object identity preserved
- post-migration validation passes
- original backup remains unchanged

## R5-G7 — Newer Schema Reject

Backup contains N+1 schema.

Expected:
- `RESTORE_REQUIRES_NEWER_APP`
- no mutation to live Vault

## R5-G8 — Migration Requires Backup

Force pre-migration backup failure.

Expected:
- migration never starts
- live schema unchanged

## R5-G9 — Migration Failure Rollback

Inject deterministic migrator failure.

Expected:
- live locator unchanged before cutover OR rolled back before maintenance release
- pre-migration backup retained

## R5-G10 — Missing/Corrupt SQLite

Backup has no SQLite or restored derived state is discarded.

Expected:
- A5 rebuild from Canonical succeeds
- recall eligibility equivalent after rebuild

## R5-G11 — Current Ledger Missing

NORMAL_RESTORE with no valid current ledger.

Expected:
- normal restore fails closed
- explicit Disaster Restore path required
- limitation health/warning emitted

## R5-G12 — Unknown Protection Class

Introduce persistent unknown object type.

Expected:
- Backup fails rather than silently omitting it

## R5-G13 — Cutover Health Failure

Inject failure immediately after locator switch but before maintenance release.

Expected:
- locator restored to old Vault
- queued mutations not written to failed candidate

## R5-G14 — Post-backup Capture Queue

Capture arrives while Backup/Restore maintenance barrier is held.

Expected:
- ingress accepted durably where A3/A4 permits
- not committed into frozen/candidate Vault prematurely
- processed once after active Vault resumes

---

# 29. Failure Injection Matrix

Minimum fault points:

1. after backup staging created
2. mid protected-file copy
3. after manifest write / before COMMITTED
4. after COMMITTED / before read-back receipt
5. mid Temporary Vault materialization
6. before Deletion Ledger merge
7. after Ledger merge / before migration
8. mid migration
9. after migration / before integrity validation
10. mid A5 rebuild
11. after candidate READY / before locator switch
12. immediately after locator switch
13. before queued A4 work resumes
14. old Vault cleanup attempt

Each fault must prove one of:

```text
old active remains authoritative
OR
new candidate is fully validated before authority
```

中間状態が「どちらが正本かわからない」状態になってはならない。

---

# 30. Implementation tasks

## R5.1 — Protection Registry + Backup Manifest

Acceptance:
- all persistent object types classify into PROTECTED/REBUILDABLE/RUNTIME/EXTERNAL_SECRET
- unknown class fails closed
- manifest is body-free and hash-verifiable

## R5.2 — Coherent Backup Coordinator

Acceptance:
- maintenance barrier produces one coherent protected snapshot
- incomplete backup cannot be restored
- idempotent retry semantics exist

## R5.3 — Backup Privacy / Destination Preflight

Acceptance:
- active Vault recursion prevented
- destination capacity/permission checked
- sensitivity/privacy summary exposed without content

## R5.4 — Restore Materializer + Validator

Acceptance:
- restore never writes into live Vault
- full protected integrity validation required
- corrupt snapshot rejected

## R5.5 — Ledger Merge / Anti-resurrection Restore

Acceptance:
- current UNION backup ledger semantics
- unknown/corrupt ledger fails closed
- stale backup cannot resurrect tombstoned Source

## R5.6 — Schema Compatibility + Migration Registry

Acceptance:
- N and N-1 handling explicit
- N+1 rejected
- migration deterministic/no LLM
- raw Source payload immutable

## R5.7 — Pre-migration Backup + Rollback

Acceptance:
- migration cannot start without committed backup
- failure leaves old active Vault usable

## R5.8 — Derived Rebuild Orchestration

Acceptance:
- restored SQLite/FTS is discarded/rebuilt via A5
- B7 stale/invalidation semantics honored where present
- Derived failure never repairs Canonical

## R5.9 — Active Locator Cutover

Acceptance:
- all writers resolve one active locator
- cutover occurs under maintenance lock
- immediate health failure rolls back before release

## R5.10 — Golden / Fault Tests

Acceptance:
- G1–G14 pass deterministically
- fault points 1–14 have assertions
- no flaky pass accepted for deletion/integrity/migration cases

---

# 31. Acceptance criteria

R5 DONE条件:

1. Backup対象がProtection Classで明示され、unknown persistent objectをsilent omitしない。
2. PROTECTED objectとDeletion LedgerがBackupされる。
3. SQLite/FTS/runtime/credentialをauthorityとしてBackup/Restoreしない。
4. Backupはimmutable snapshotで、COMMITTED前は無効。
5. Backup中のCanonical snapshot consistencyが保証される。
6. RestoreはTemporary Vaultへ行い、liveをblind overwriteしない。
7. NORMAL_RESTOREでcurrent generic C3 ledger UNION backup generic C3 ledgerが必ず適用される。
8. stale backupからTOMBSTONED objectがRecall可能に戻らない。
9. Current ledger不在をsilent normal restoreしない。
10. Canonical full integrity validation失敗時にcutoverしない。
11. Current/N-1/newer/unknown schemaの扱いが決定的。
12. Migration前BackupがHard Gate。
13. MigrationはdeterministicでAI/LLMを使わない。
14. Migration失敗時にold active Vaultへ戻れる。
15. Raw Source payloadをmigrationで変更しない。
16. A5 IndexをCanonicalから再構築できる。
17. Derived/B7再計算失敗がCanonicalへ逆流しない。
18. active-vault cutoverが単一のauthority boundaryを持つ。
19. Cutover直後Health失敗でrollbackできる。
20. Restore Smoke Testが外部AI egressなしで実行できる。
21. Backup destination privacy summaryをR7へ返せる。
22. Recovery telemetry/receiptsに本文・Secretを保存しない。
23. G1–G14がPASSする。
24. Restore Test / Failure Injection TestをFounder safety gateの証跡として残せる。

---

# 32. Explicit non-goals

- encrypted proprietary backup archive
- TSUZU cloud backup
- Dropbox/Drive等へのbackup connector
- automatic backup retention optimizer
- minute-by-minute version history
- multi-device restore conflict merge
- selective object restore UI
- semantic conflict resolution
- CRDT
- undelete
- forensic secure erase guarantee
- OS Keychain secret transfer
- automatic credential re-authentication
- AI-assisted schema migration
- AI-assisted corrupt Canonical repair
- restoring SQLite as source of truth
- guaranteed recovery from deletion history that no longer exists anywhere

---

# 33. Gate to R6 / Founder Product Proof

R5をFounder Safety Gateとして閉じる条件:

```text
R5-G1 Healthy Round Trip PASS
R5-G4 Tombstone No Resurrection PASS
R5-G6 N-1 Migration PASS
R5-G8 Migration Requires Backup PASS
R5-G9 Migration Failure Rollback PASS
R5-G13 Cutover Health Failure PASS
```

加えて:

- A5 rebuild equivalence PASS
- A6 Deletion Ledger availability/anti-resurrection PASS
- body-free recovery report生成

これを満たせば、Canonical/Recovery観点でR6 Passive Recall / Trusted Intentを次の主要Blockerとして扱える。

---

# 34. Source-derived vs implementation closure decisions

## Canonical source-derived requirements

以下はv1.1/v1.2.1およびA5/A6/B7から継承した要求:

- Temporary Vault restore
- no in-place overwrite
- Integrity Check
- Deletion Ledger reapplication
- current UNION backup ledger anti-resurrection semantics
- schema compatibility and N-1 reader expectation
- backup before schema migration
- index discard/rebuild
- Canonical corruption requires backup recovery
- no AI repair of Canonical
- Restore/Failure Injection Gate

## R5 v0.1 implementation closure decisions

既存Canonicalが方法を固定していなかったため、R5でP0用に確定したもの:

- Protection Class Registryでbackup inclusionを決める
- committed immutable backup snapshot + final COMMITTED marker
- coherent maintenance barrier during backup
- NORMAL_RESTORE / DISASTER_RESTORE分離
- P0 Restoreはsnapshot cutoverでありautomatic 3-way mergeではない
- validated new Vault + active locator switchを優先
- live migrationを禁止しTemporary Migration Vaultで行う
- Nより古いschemaは明示migration chainがなければfail closed
- cutover直後health failureはmaintenance release前にlocator rollback
- R5-G1〜G14をmandatory Golden Casesとする

これらはProduct Scope追加ではなく、既存Recovery ConstitutionをP0実装可能にするためのambiguity closureである。

---

# 35. One-line contract

> **R5は、TSUZUのユーザー所有Canonicalをimmutable Backupとして保護し、削除履歴を失わせず、壊れたDerivedは作り直し、Schema変更や復元を必ず検証済みTemporary Vault上で行ってから単一のactive Vaultへ切り替えることで、「壊しても戻せる」をP0 Founder Test前に証明する。**
