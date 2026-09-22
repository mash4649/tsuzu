# TSUZU P0 Vertical Slice A6 — Minimal Tombstone / Deletion Ledger Contract v0.1

- Date: 2026-09-06
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1
- Parent Plan: P0 Vertical Slice A
- Depends on:
  - A1 Canonical Source Contract v0.1
  - A2 Atomic Vault Writer Contract v0.1
  - A4 Single Writer Worker Contract v0.1
  - A5 SQLite / FTS Derived Index + Rebuild Contract v0.1
- Status: Implementation Contract / Ready to implement
- Scope: A6 only. Source-level logical deletion, immutable Deletion Ledger, anti-resurrection precedence, source-manifest reconciliation, index invalidation, stale restore handling.
- Non-scope: physical secure erase, undelete UI, deletion of future Decision/Pattern/Discovery objects, cloud tombstone service, multi-device conflict protocol.

## 0. Decision

P0の削除は、`Source.source.md` の `deletion.state=TOMBSTONED` だけでは成立しない。

削除事実をSourceから独立した **Deletion Ledger Record** として永続化する。

Effective deletionは以下で決める。

```text
effective_deleted(source_id)
=
Deletion Ledger contains source_id
OR
valid Source manifest says TOMBSTONED
```

ただしSource manifestが`LIVE`でもLedgerにrecordがあれば **Ledgerが必ず勝つ**。

```text
Ledger = deleted
Source = LIVE
→ DELETED
```

Index / Retrieval / Context / Rebuild / RestoreはこのResolverを共通利用する。

## 1. Why a separate ledger is required

Source manifestだけにTOMBSTONEを持つと、以下で旧`LIVE`状態が戻り得る。

```text
old backup restore
iCloud/File Provider conflict
manual stale copy
sync rollback/conflict
old Source directory reappearance
```

そのため、

```text
Source state
```

と

```text
Deletion fact
```

を別の永続物として持つ。

削除はP0では単調増加(monotonic)とする。

```text
not deleted
→ deleted

deleted
↛ live again
```

P0にundeleteはない。

## 2. Guarantee boundary

### P0で保証する

**現在または復元処理に持ち込めるDeletion Ledgerが存在する限り**、

- stale Source
- stale Index
- stale backup content
- iCloud/File Providerで再出現した旧Source

が戻っても自動的にRecall可能状態へ復活しない。

### P0で保証できない

完全に新しい端末で、

```text
Deletion Ledgerなし
+
削除前の古いBackupだけ
```

しか存在しない場合、そのSourceが過去に削除されたことを知る情報がない。

Local-first / no-cloud P0ではこれは原理的に判定不能。

したがって「Deletion Ledgerが失われても、pre-delete backupから削除履歴を推論する」ことは契約にしない。

### TSUZU-managed restore

TSUZUがRestoreを管理する場合は、

```text
current ledger
UNION
backup ledger
```

を必ず先に作り、復元Sourceへ再適用する。

current ledgerを古いbackup ledgerで上書きしてはならない。

## 3. Canonical storage layout

Deletion LedgerはVault内のCanonical system stateとする。

```text
<Vault>/
  canonical/
    sources/
      <source_id>/
        source.md
        payload/original

  system/
    deletion-ledger/
      SOURCE/
        <source_id>.md
```

P0では1 object_idにつき最大1 immutable deletion record。

File pathはlookup optimizationであり、record内のtarget object_idと一致検証する。

削除record自体はAI Derivedではない。
ユーザー/システムが行った削除操作のCanonical Event/Factual state。

## 4. Deletion Ledger Record schema

```yaml
---
record_type: "DELETION_RECORD"
ledger_schema_version: "1.0.0"

record_id: "uuid-v4"

target:
  object_type: "SOURCE"
  object_id: "<source_id>"

deleted_at: "2026-09-06T09:00:00.000Z"
deleted_by:
  actor: "USER"
  method: "LOCAL_DELETE"

source_snapshot:
  revision_at_delete: 3
  payload_sha256: "<sha256>"
  schema_version: "1.0.0"

request:
  request_id: "<uuid>"
  idempotency_key_hash: "<sha256>"

reason_code: "USER_REQUEST"
---
```

### No body

Deletion record本文にはSource bodyを入れない。

### Optional user reason

自由記述reasonはP0では保存しない。
必要なら将来別fieldを追加する。

### source_snapshot

削除対象の内容を復元するためではなく、

- ID collision診断
- stale source再出現診断
- deletion対象確認

のためのfingerprint metadata。

Payload本文は複製しない。

## 5. Deletion request

P0 Core interface:

```yaml
delete_request:
  request_id:
  idempotency_key:
  requested_at:

  target:
    object_type: SOURCE
    object_id:

  expected_revision:
```

`expected_revision`は必須。

理由:

- A1/A2のRevision Contractを維持
- Last-write-winsをしない
- userが見ていたSourceと現在Sourceの競合をdetectする

CLI adapterはcurrent Source revisionを読み、内部的にrequestへ付与できる。

## 6. Delete surface for Slice A

Final UIは作らない。

P0 test surface:

```text
tsuzu delete source <source_id>
```

ただしCLIが直接Vaultを書かない。

```text
CLI
↓
Deletion Mutation Request
↓
Single Writer boundary
↓
A6 deletion transaction
```

Canonical write主体を増やさない。

## 7. Single Writer integration

A4のSingle Writer processがCapture createだけでなく、Canonical mutationの唯一のexecutorである原則を維持する。

A6ではlogical mutation kindとして:

```text
DELETE_SOURCE
```

を追加する。

A4のCapture Job schemaそのものへDELETEを混ぜず、runtime mutation queueを分けてよい。

推奨:

```text
~/Library/Application Support/TSUZU/runtime/
  mutation-queue/
    pending/
    processing/
    retry/
    quarantine/
```

同一worker process lockの下で処理する。

## 8. Delete transaction ordering

安全側の順序を固定する。

```text
1. acquire Single Writer execution
2. load A1 Source
3. load/validate Deletion Ledger state
4. if already deleted → ALREADY_DELETED
5. validate Source + expected_revision
6. materialize immutable Deletion Record
7. durable atomic commit Deletion Record
8. read-back validate Deletion Record
9. deletion becomes EFFECTIVE
10. update Source manifest to TOMBSTONED (revision + 1)
11. request A5 index invalidation/reconcile
12. durable mutation receipt / telemetry
13. cleanup runtime mutation job
```

### Critical boundary

**Step 8完了時点で削除は論理的に成立する。**

Step 10のSource manifest更新やStep 11のIndex削除が遅れても、

```text
DeletionResolver
```

がLedgerを参照するためRecallしてはならない。

## 9. Why ledger first

逆に、

```text
Source manifest TOMBSTONED
↓
Ledger
```

の順にすると、

manifest更新後Ledger前にcrashし、その後古いbackupでmanifestがLIVEへ戻った場合に削除事実を失いやすい。

したがってP0は:

```text
Deletion Ledger first
→ manifest convergence second
```

とする。

## 10. Deletion record atomicity

Deletion recordは1 immutable fileなのでA2のatomic file primitiveを利用できる。

```text
stage
→ schema validate
→ fsync
→ exclusive atomic publish
→ parent durability
→ read-back
```

既存`<source_id>.md`がある場合:

### same valid deletion record semantics

```text
ALREADY_DELETED
```

### same target path but conflicting record identity/content

```text
DELETION_LEDGER_CONFLICT
```

自動overwriteしない。

ただし同一source_idへ複数削除を作る必要はP0ではない。

## 11. Effective Deletion Resolver

A6で共通Read APIを定義する。

```text
getDeletionState(object_type, object_id)
→
NOT_DELETED
DELETED
UNKNOWN_FAIL_CLOSED
```

### DELETED

- valid ledger record exists
- OR valid Source manifest TOMBSTONED

### NOT_DELETED

- ledger lookup succeeds with no record
- Source manifest valid and LIVE

### UNKNOWN_FAIL_CLOSED

例:

- ledger directory unavailable
- target ledger record corrupt
- ledger record target mismatch
- filesystem permission error
- Source deletion state invalid

UNKNOWNをLIVE扱いしてはいけない。

## 12. Ledger availability is a safety dependency

Retrieval/Rebuild時にDeletion Ledger root自体が読めない場合:

```text
do not assume nothing is deleted
```

P0 behavior:

```text
Deletion state UNKNOWN
→ fail closed for recall/rebuild eligibility
```

Healthへ:

```text
DELETION_LEDGER_UNAVAILABLE
```

を出す。

Indexの可用性よりanti-resurrectionを優先する。

## 13. Source manifest reconciliation

Ledger commit後、Source manifest:

```yaml
deletion:
  state: TOMBSTONED
  tombstoned_at: deleted_at
```

へA2 metadata revision update。

revision:

```text
old revision N
→ N + 1
```

### crash / update failure

Ledgerが存在するため削除自体は有効。

startup/background reconciliation:

```text
ledger says DELETED
+
Source says LIVE
→ update Source to TOMBSTONED
```

Source manifestをLIVEへ戻す方向の自動reconciliationは禁止。

## 14. Tombstone payload handling

P0 A6は**logical deletion**。

TOMBSTONED Sourceの`payload/original`はA6だけでは物理削除しない。

理由:

- A1 integrity contractを壊さない
- secure eraseを誤って保証しない
- APFS/SSD/backup上のphysical erasureは別問題
- anti-resurrection correctnessを先に証明する

保証するのは:

```text
Retrieval禁止
Index禁止
Context禁止
Discovery Evidence禁止
```

であって、

```text
secure physical erasure
```

ではない。

Physical purge / cryptographic erase / backup purgeはProduct Proof後のPrivacy/Purge Contractで扱う。

## 15. A5 Index integration

A5のeligibilityを更新する。

旧:

```text
Source manifest LIVE
AND valid
AND not RESTRICTED
```

A6後:

```text
A1 Source valid
AND
DeletionResolver == NOT_DELETED
AND
sensitivity != RESTRICTED
AND
Secret Guard clear
```

### On deletion

Index invalidation request:

```text
source_id
reason = DELETION_LEDGER
```

A5 transaction:

```text
DELETE source_fts
DELETE source_index
UPSERT index_exclusion(DELETION_LEDGER)
```

### Correctness

Index invalidationはUX freshnessのため。

**削除正当性をIndex removalだけに依存しない。**

A7でもDeletionResolverを再確認する。

## 16. Rebuild integration

A5 Full RebuildのCanonical enumerationで各Sourceについて:

```text
DeletionResolver
```

を必ず呼ぶ。

```text
DELETED
→ exclude

NOT_DELETED
→ continue normal eligibility

UNKNOWN_FAIL_CLOSED
→ exclude / rebuild health failure
```

Deletion Ledgerを読まずにSource manifestだけでRebuildするコードpathを禁止する。

## 17. Stale Source resurrection scenario

Scenario:

```text
T0 Source LIVE
T1 user deletes
T2 Ledger committed
T3 Source TOMBSTONED
T4 old backup/iCloud conflict restores Source as LIVE
```

Expected:

```text
Ledger still contains source_id
↓
effective state = DELETED
↓
Index/retrieval deny
↓
reconciliation rewrites Source TOMBSTONED
```

Old Sourceの`updated_at`やrevisionが新しく見えてもLedger precedenceは変わらない。

## 18. TSUZU-managed Restore Contract

Restoreは単純なdirectory overwriteにしない。

概念手順:

```text
1. read + validate current Deletion Ledger
2. stage backup restore
3. read + validate backup Deletion Ledger
4. merged ledger = set union by target object identity
5. validate merged ledger
6. apply merged ledger into staged restored Vault
7. reconcile every restored Source against merged ledger
8. publish restored Vault
9. rebuild A5 Index from restored Vault + merged ledger
```

### Monotonic rule

P0では:

```text
deleted in current
OR
deleted in backup
→ deleted after restore
```

削除履歴を古いbackupで解除しない。

## 19. Manual external restore limitation

UserがTSUZUを通さず、

```text
Vault folderを完全削除
↓
pre-delete backupでfilesystemごと置換
```

し、current Deletion Ledgerも同時に消した場合、P0は削除履歴を知れない。

同一Mac上での防御を強めるため、将来local Deletion Anchor mirrorを追加可能だが、A6 P0必須にはしない。

Remote/cloud deletion ledgerはP0 scope外。

## 20. Sync conflict behavior

同一`source_id`で:

```text
ledger exists
+
Source LIVE/TOMBSTONED/conflicted
```

なら常にDELETED。

Deletion Ledger自体のduplicate/conflict:

### same target + semantically same record
dedupe可能。

### same target + different metadata
削除の有無についてはDELETEDを維持。
conflict metadataはHealthへ出し、自動的に削除を解除しない。

## 21. Corrupt Deletion Record

`system/deletion-ledger/SOURCE/<source_id>.md` が存在するがinvalid:

```text
do not treat as NOT_DELETED
```

P0:

```text
target source deletion state
→ UNKNOWN_FAIL_CLOSED
→ Recall/Index deny
→ Health DELETION_LEDGER_CORRUPT
```

AIやSource manifestからLedger内容を自動再生成しない。

## 22. Missing Source with Ledger Record

Ledger Recordが存在しSource本体がない:

```text
valid state
```

削除済みSourceが物理的に消えている可能性がある。

Index/rebuildでは当然除外。

後日同じ`source_id`のstale Sourceが戻った場合、Ledgerが即座にblockする。

## 23. Unknown Source delete request

Sourceが存在せず、Ledgerにもrecordなし:

```text
NOT_FOUND
```

将来現れるかもしれないIDを予防的にdeleteしない。

Source ID reuseは禁止を維持する。

## 24. Idempotency

### same source deleted repeatedly

valid Ledger exists:

```text
ALREADY_DELETED
```

新Deletion Recordを増やさない。

### same delete idempotency key + same target

same result。

### same idempotency key + different target

```text
IDEMPOTENCY_CONFLICT
```

Deletion Ledger recordはraw idempotency keyを保持しない。
hashのみ。

## 25. User correction / undelete

P0ではundelete APIを実装しない。

Deletion recordはimmutable。

削除した内容を再びTSUZUへ入れたい場合:

```text
user explicitly recaptures content
→ new Source ID
```

旧source_idのDeletion Recordは残る。

これによりanti-resurrection semanticsを単純に保つ。

## 26. Dependency scope in A6

v1.2.1のfull dependency graphは維持するが、Slice Aで存在するDerived dependencyは主に:

```text
Source
↓
SQLite/FTS Index
```

のみ。

したがってA6で実装するinvalidationは:

- source_index
- source_fts
- current context candidate cacheがあればそれ

まで。

Decision / Pattern / Discovery / Learningの再計算は後続Sliceで同じDeletion Resolverへ接続する。

## 27. Recall defense in depth requirement for A7

A7はFTS結果をそのまま返してはいけない。

Candidateごとに:

```text
FTS candidate
↓
Canonical Source validate
↓
DeletionResolver
↓
Sensitivity/Scope/Egress
↓
eligible result
```

DeletionResolverが:

```text
DELETED
UNKNOWN_FAIL_CLOSED
```

なら必ずdrop。

これによりstale Indexが一瞬残ってもdeleted Sourceはexternal contextへ出ない。

## 28. Telemetry

Body禁止。

Allowed:

```text
request_id
source_id
deletion record_id
source revision at delete
state transition
reconciliation result
index invalidation status
restore merged deletion count
error code
duration
```

Not allowed:

```text
source body
payload bytes
full URL
secret
free-form deletion reason
```

Events例:

```text
DELETE_REQUESTED
DELETION_LEDGER_COMMITTED
SOURCE_TOMBSTONED
DELETE_ALREADY_APPLIED
DELETE_REVISION_CONFLICT
DELETE_INDEX_INVALIDATED
TOMBSTONE_RECONCILED
STALE_SOURCE_BLOCKED
DELETION_LEDGER_UNAVAILABLE
DELETION_LEDGER_CORRUPT
RESTORE_LEDGER_MERGED
```

## 29. A6 Golden Cases

### Case 1 — Normal Delete

LIVE indexed Sourceをdelete。

Expected:
- Ledger record durable
- Source TOMBSTONED
- Index removed
- DeletionResolver=DELETED

### Case 2 — Immediate Logical Deletion

Crash after Ledger commit, before Source manifest update.

Expected:
- Source manifest may still say LIVE
- effective deletion is DELETED
- no Recall eligibility
- startup reconciliation tombstones manifest

### Case 3 — Crash Before Ledger Commit

Expected:
- no valid Ledger record
- Source remains LIVE
- delete not acknowledged as durable

### Case 4 — Revision Conflict

Source revision changes before delete transaction.

Expected:
- no deletion record
- REVISION_CONFLICT
- Source unchanged

### Case 5 — Duplicate Delete

Delete same Source twice.

Expected:
- one Ledger record
- second ALREADY_DELETED
- no duplicate semantic effect

### Case 6 — Stale Index

Delete Ledger committed but A5 invalidation intentionally skipped.

Expected:
- raw FTS may temporarily contain row
- DeletionResolver blocks it
- reconcile removes row

### Case 7 — Full Index Rebuild

Deleted Source directory still exists with payload.

Expected:
- rebuild excludes due to Ledger
- no resurrection

### Case 8 — Old LIVE Source Restore

After delete, overwrite Source manifest with old LIVE backup copy.

Expected:
- Ledger wins
- no Index/Recall
- reconciliation returns manifest to TOMBSTONED

### Case 9 — TSUZU-managed Pre-delete Backup Restore

Current Ledger contains deletion; backup predates deletion.

Expected:
- restore preserves current Ledger
- Source from backup remains effectively deleted
- rebuilt Index excludes

### Case 10 — Backup Contains Additional Deletion

Current Vault and backup each contain different deletion records.

Expected:
- union contains both
- both targets deleted after restore

### Case 11 — Corrupt Ledger Record

Ledger target file exists but schema/hash/target mismatch.

Expected:
- UNKNOWN_FAIL_CLOSED
- Source excluded
- no auto repair

### Case 12 — Ledger Root Unavailable

Permission-deny Deletion Ledger root.

Expected:
- retrieval/rebuild eligibility fails closed
- Health error
- no assumption of empty ledger

### Case 13 — Missing Source, Valid Ledger

Expected:
- valid deleted state
- if stale Source later reappears, immediately excluded

### Case 14 — Recapture Deleted Content

User recaptures identical payload intentionally.

Expected:
- new Source ID
- old ID remains deleted
- new ID may be eligible normally

### Case 15 — Ledger Commit Success / Index Failure

Expected:
- deletion remains effective
- index failure does not rollback deletion
- later reconcile removes stale row

## 30. Fault injection points

Minimum:

1. before Source load
2. after Source load before revision check
3. after revision check before Ledger staging
4. during Ledger staging
5. after Ledger fsync before publish
6. after Ledger publish before read-back
7. after Ledger read-back before manifest update
8. during Source TOMBSTONE update
9. after Source TOMBSTONE before Index invalidation
10. during Index invalidation
11. after Index invalidation before mutation receipt
12. during runtime cleanup
13. during startup tombstone reconciliation
14. during restore ledger merge
15. after restore merge before restored Vault publish

Invariant:

```text
If durable Ledger record exists:
  source is never eligible for recall.

If durable Ledger record does not exist:
  delete must not be reported as durably complete.

A6 failure never converts DELETED back to LIVE.
```

## 31. A6 implementation task breakdown

### A6.1 — Deletion Ledger schema + codec

Acceptance:
- immutable one-record-per-source
- malformed/corrupt record detected
- no Source body stored

### A6.2 — DeletionResolver

Acceptance:
- NOT_DELETED / DELETED / UNKNOWN_FAIL_CLOSED
- Ledger precedence over LIVE Source
- unavailable/corrupt ledger fails closed

### A6.3 — Delete Mutation Request + Single Writer integration

Acceptance:
- expected_revision enforced
- Ledger-first ordering
- repeated delete idempotent

### A6.4 — Tombstone manifest reconciler

Acceptance:
- Ledger DELETED + Source LIVE converges to TOMBSTONED
- never auto-reactivates

### A6.5 — A5 index invalidation + rebuild integration

Acceptance:
- deleted Source disappears from Index
- rebuild consults Ledger
- stale Index cannot override Ledger

### A6.6 — TSUZU-managed restore ledger merge

Acceptance:
- current ∪ backup deletion records
- old backup cannot clear deletion
- staged restore reconciles before publish

### A6.7 — Golden / fault tests

Acceptance:
- Cases 1–15
- fault points 1–15
- all anti-resurrection invariants pass

## 32. A6 acceptance criteria

A6 DONE条件:

1. Source TOMBSTONEだけに削除を依存しない。
2. immutable Deletion Ledger RecordをSourceとは独立して保持する。
3. Ledger record存在時はSource LIVEでもeffective DELETED。
4. deleteはSingle Writer boundary経由。
5. expected_revision conflictを検出する。
6. Ledger commitをSource manifest更新より先に行う。
7. Ledger commit直後からRecall eligibilityを失う。
8. Source manifest更新失敗でもDeletionが解除されない。
9. startup reconciliationでLIVE manifestを再TOMBSTONEできる。
10. A5 Index invalidation失敗でもDeletionが有効。
11. A5 full rebuildがDeletion Ledgerを必ず参照する。
12. stale LIVE Source restoreでも復活しない。
13. TSUZU-managed restoreがcurrent/backup Ledgerのunionを維持する。
14. corrupt/unavailable Ledgerをempty扱いしない。
15. deleted Source IDを自動再利用しない。
16. undeleteをP0に入れない。
17. recaptureはnew Source IDになる。
18. physical secure eraseを誤って保証しない。
19. Source bodyをDeletion Ledger/Telemetryへ複製しない。
20. A7がDeletionResolverを最終Eligibility Gateとして利用できる。

## 33. Checkpoint 2 closure

A4-A6完了時のRecoverable Local Core Gate:

```text
Capture Job
→ idempotent Single Writer
→ Canonical Source
→ disposable/rebuildable SQLite/FTS
→ monotonic Deletion Ledger
```

最低確認:

- Worker restartでduplicateなし
- SQLite全削除→VaultからRebuild
- Delete→stale Source/Index/restoreでもRecall復活なし

ここまで成立すればCheckpoint 2は閉鎖可能。

## 34. Explicit non-goals

- secure SSD physical erase guarantee
- backup provider側physical purge
- iCloud remote wipe
- undelete / trash UI
- deletion grace period
- multi-device distributed tombstone service
- new-device anti-resurrection from pre-delete backup with no ledger
- deletion of Decision/Pattern/Discovery objects
- GDPR/enterprise retention policy engine
- legal hold
- cloud deletion audit service

## 35. Gate to A7

A7 Retrieval + Minimal Policy/Egressへ進む条件:

```text
FTS candidate
```

が古い・staleでも、

```text
Canonical Validation
+
DeletionResolver
```

によってdeleted Sourceを必ずdropできること。

A7はDeletion stateをSQLite rowだけから判定してはならない。

## 36. Final A6 one-line contract

> **TSUZUの削除は、Source自身のTOMBSTONEではなく独立したDeletion Ledgerを最終優先の削除事実として保持し、現在のLedgerが存在する限り、古いSource・Index・Backup・Sync内容が戻ってもRecall可能状態へ復活させない。**
