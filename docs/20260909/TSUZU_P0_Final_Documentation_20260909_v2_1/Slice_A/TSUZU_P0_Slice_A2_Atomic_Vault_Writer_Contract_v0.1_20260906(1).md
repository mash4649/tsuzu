# TSUZU P0 Vertical Slice A2 — Atomic Vault Writer Contract v0.1

- Date: 2026-09-06
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1
- Parent: P0 Vertical Slice A / A1 Canonical Source Contract v0.1
- Status: Implementation Contract / Ready to implement
- Scope: A2 only. Canonical Source persistence, revision-safe metadata replacement, local crash consistency, staging recovery.
- Non-goals: Capture UX, Secret classification logic, Background Worker scheduling, SQLite/FTS, Deletion Ledger semantics, MCP.

## 0. Decision

A2のAtomic Vault Writerは、A1で定義したCanonical Sourceを、**Canonical領域に半端な状態を一度も公開せず、既存Objectを暗黙上書きせず、クラッシュ後の再実行でも同一効果へ収束できる唯一のMutable Write Boundary**として実装する。

新規SourceのCommit Unitは `source.md` 単体ではなく、以下の**Source Directory全体**とする。

```text
canonical/sources/<source_id>/
  source.md
  payload/
    original
```

新規作成は、同一Volume内のStagingへSource Directory全体を書き、A1 validation完了後に**Directory単位でatomic publish**する。

Metadata revision更新はRaw payloadを触らず、`source.md`だけをrevision check付きでatomic replacementする。

A2では「atomic」と「durable」を分ける。

- `atomic`: 読み手から見て旧状態または新状態のどちらかであり、half-written Canonicalを見せない。
- `COMMITTED_LOCAL`: platformの同期APIを通過し、local filesystem上でcommitが完了した状態。
- iCloud等のremote sync完了はA2 Commit条件に含めない。
- sudden power lossに対する絶対保証はP0では主張しない。

## 1. A2 Hard Invariants

1. Canonical pathへ直接逐次writeしない。
2. Stagingとfinal destinationは同一filesystem / volumeでなければならない。
3. 新規Object作成時、既存destinationをrenameで置換しない。
4. `revision` mismatch時は必ずfailし、Last-write-winsしない。
5. payloadはcreate後immutable。A2 update APIはpayloadを変更できない。
6. Canonical commit前にA1 validatorを必ず通す。
7. corrupt CanonicalをStagingやAI推測から自動修復しない。
8. retryによりCanonical効果が重複しない。
9. Writer Lockを保持していない処理はCanonical mutationできない。
10. SQLite / queue / telemetryをCanonical truthとして参照しない。
11. `RESTRICTED` Sourceはwriter boundaryでもLIVE commitを拒否する。
12. user-controlled filename / URL / original_nameをfilesystem path componentとして利用しない。

## 2. Physical Layout

```text
<Vault>/
  canonical/
    sources/
      <source_id>/
        source.md
        payload/
          original

  system/
    staging/
      <tx_id>/
        create/
          source.md
          payload/
            original
        update/
          source.md
    write.lock
    quarantine/
```

### Rules

- `<source_id>` はA1のUUIDv4のみ。
- `<tx_id>` はruntime transaction UUID。
- `system/staging` はCanonicalではない。
- Staging contentはRecall / Index / Derived processing対象外。
- `system/quarantine` は人間/Health診断用。Canonicalへ自動昇格させない。

## 3. Writer Boundary

A2で公開するmutation interfaceは最低限以下に限定する。

```text
create_source(CreateIntent) -> WriteResult
update_source_metadata(UpdateIntent) -> WriteResult
inspect_source(source_id) -> SourceIntegrityResult
recover_staging() -> RecoveryReport
```

### CreateIntent

概念上、以下を持つ。

```yaml
source_id: <stable UUIDv4>
created_at: <stable UTC timestamp>
source_metadata: <A1 explicit metadata>
payload_stream_or_file:
```

`source_id` と `created_at` はretry間で固定する。
A3/A4が同じCapture Jobを再配送しても、同じCreateIntentでA2へ到達することを前提とする。

Writer自身が以下を計算・強制する。

- `object_type = SOURCE`
- `revision = 1`
- `updated_at = created_at`
- `payload_sha256`
- `payload_bytes`
- fixed `payload_path = payload/original`

caller supplied hash / byte lengthを信頼しない。

### UpdateIntent

```yaml
source_id:
expected_revision:
patch:
  <A1で更新可能なmetadataのみ>
```

A2で許可するpatch対象：

- scope
- sensitivity
- provenance metadata correction
- deletion state field

A2で禁止するpatch：

- object_id
- object_type
- schema_versionの暗黙migration
- created_at
- payload_path
- payload_sha256
- payload_bytes
- raw payload

Deletion Ledger / tombstone propagationの意味論はA6で追加する。A2はrevision-safe manifest replacementのみ提供する。

## 4. Exclusive Writer Contract

A2 mutationは**exclusive writer lock**保持を必須とする。

```text
acquire writer lock
  -> mutate
  -> durability sync
  -> release writer lock
```

P0では同一Vaultに対して**1台のMac / 1 active writer process**を前提とする。

iCloud DriveをVault置き場に使う場合も、iCloudはreplicationでありmulti-writer consensusではない。
複数Macから同一Vaultを同時mutationする機能はP0対象外。

Lock未取得時は `WRITER_LOCK_REQUIRED`。
Lock取得不能時は待ち続けず、bounded timeout後 `WRITER_BUSY` としてcallerへ返す。

A4 Single Writer Workerはこのboundaryの唯一の通常callerになる。

## 5. Filesystem Capability Preflight

Vault初期化時またはwriter起動時に最低限以下を確認する。

1. canonicalとstagingが同一volumeにある。
2. atomic rename / replacementを利用できる。
3. 新規Objectでno-clobber commitを実現できる。
4. local write権限がある。
5. required file coordination strategyを選択できる。

Macでvolumeがexclusive renameをサポートする場合、new Source publishは`RENAME_EXCL`相当のno-clobber primitiveを優先する。

P0で安全なno-clobber semanticsを確保できないfilesystemはCanonical Vaultとしてsupportしない。
SMB / NFS / arbitrary network sharesはSlice A対象外。

## 6. iCloud Drive / File Provider Contract

A1のLocal Folder / iCloud Drive方針を維持する。

ただし、iCloud Drive / File Provider配下ではfilesystem accessが別processと競合し得るため、platform adapterは必要に応じてcoordinated file accessを使う。

重要：

- A2 Commitは**local canonical commit**を意味する。
- remote iCloud upload完了を待たない。
- remote sync statusをCanonical fieldへ書かない。
- iCloud conflict fileを勝手にmergeしない。
- external conflictを検知したらHealth / quarantineへ送り、Canonical推測修復しない。

実装言語固有APIはrepository stack確認後に確定するが、macOS/Foundation実装では`NSFileCoordinator`相当のcoordinated accessを利用可能なadapter boundaryを持つ。

## 7. New Source Transaction

新規Source作成を以下に固定する。

```text
0. acquire writer lock
1. preflight final destination absent / capability check
2. create unique staging transaction directory
3. stream/copy raw payload -> staging/create/payload/original
4. calculate SHA-256 + byte length while writing
5. sync payload file
6. render source.md using calculated integrity metadata
7. write source.md into staging
8. sync source.md
9. sync staging payload/source directories as supported
10. run full A1 validation against staged object
11. no-clobber atomic publish staging/create -> canonical/sources/<source_id>
12. sync canonical/sources parent directory
13. read-back minimum manifest identity/revision
14. return COMMITTED_LOCAL
15. cleanup tx shell
16. release writer lock
```

`source.md`はpayloadが完成してから生成する。
ただしCanonicalへはDirectory単位でpublishするため、staging内のwrite orderをCanonical readerへ露出しない。

## 8. Why Directory-Level Commit

`payload/original` と `source.md` を別々にCanonicalへrenameすると、2回のcommit間に以下の中間状態が見える。

```text
manifest exists / payload missing
OR
payload exists / manifest missing
```

A1のSourceはmanifest + payloadで1 Objectなので、新規作成はSource Directory全体を1 commit unitにする。

Canonical readerは、final `<source_id>/` directoryが存在するものだけをObject候補として扱う。

## 9. Metadata Revision Transaction

既存Source metadata更新はpayloadをcopyし直さない。

```text
0. acquire writer lock
1. load current canonical Source
2. full A1 integrity validation
3. if current.revision != expected_revision -> REVISION_CONFLICT
4. validate requested patch allowlist
5. construct new manifest:
     revision = current + 1
     updated_at = now UTC
     payload integrity fields unchanged
6. write staging/update/source.md
7. sync staged manifest
8. validate staged manifest against existing immutable payload
9. re-check current revision immediately before commit
10. atomic replace canonical source.md
11. sync source directory
12. read-back revision
13. return COMMITTED_LOCAL
14. release writer lock
```

同一writer lock下でrevision checkからcommitまでを行うため、TSUZU内部のparallel write raceを作らない。

external/manual modificationを検知した場合は`CANONICAL_CHANGED_EXTERNALLY` / `CANONICAL_CORRUPT`としてfail closedする。

## 10. Retry / Idempotency Contract

A4はat-least-once retryを行える。そのためA2はretry-safeでなければならない。

### Create retry

final destinationが既に存在するとき：

1. existing SourceをA1 validateする。
2. `object_id` が同一か確認する。
3. immutable payload hash / bytesおよびCreateIntentのcanonical immutable metadataが一致するか確認する。

一致：

`ALREADY_COMMITTED` としてsuccess-equivalentを返す。新Sourceは作らない。

不一致：

`OBJECT_ID_COLLISION` または `CANONICAL_CONFLICT`。既存Objectを上書きしない。

### Update retry

current revisionが `expected_revision + 1` で、requested patchが既に反映済みなら `ALREADY_COMMITTED` を許可する。

それ以外のrevision差は `REVISION_CONFLICT`。

## 11. Commit Result States

最低限以下を区別する。

```text
COMMITTED_LOCAL
ALREADY_COMMITTED
REVISION_CONFLICT
OBJECT_ALREADY_EXISTS
OBJECT_ID_COLLISION
VALIDATION_FAILED
CANONICAL_CORRUPT
CANONICAL_CHANGED_EXTERNALLY
WRITER_BUSY
WRITER_LOCK_REQUIRED
FILESYSTEM_UNSUPPORTED
IO_FAILED
COMMIT_UNCERTAIN
```

`COMMIT_UNCERTAIN` は、atomic publish自体は成功した可能性があるが、その後のsync/read-backでI/O error等が発生し、callerがsuccessを断定できない場合。

callerは同じstable source_id / intentで再concileする。

## 12. Durability Semantics

A2は「half-written Canonicalを防ぐ」ことをhard guaranteeとする。

P0 `COMMITTED_LOCAL` の意味：

- staged filesのwriteが完了している。
- platformのstandard file synchronization APIが成功している。
- atomic namespace publish / replacementが成功している。
- containing directoryのsynchronizationを要求し、成功している。
- post-commit read-backが成功している。

ただしこれは：

- iCloud remote replication完了
- hardware firmware cacheまで含む絶対power-loss durability

を意味しない。

macOSではstandard `fsync`より強い`F_FULLFSYNC`が利用可能だが、P0必須条件にはしない。実装時にnative stackから低コストで利用できる場合はstrict durability optionとして追加できる。

UI / logsでは`Saved`をremote backup完了の意味に使用しない。

## 13. Crash Matrix

### C0 — staging作成前にprocess crash

Canonical effect: none.
Recovery: caller/job retry。

### C1 — payload書込途中でcrash

Canonical effect: none.
Staging: incomplete可能。
Recovery: staging cleanup。Canonicalへpromoteしない。

### C2 — payload完成、manifest途中/validation前でcrash

Canonical effect: none.
Recovery: staging cleanup。caller retry。

### C3 — validation完了、atomic publish直前でcrash

Canonical effect: none.
Recovery: staging cleanup。caller retry。

### C4 — atomic publish成功後、directory sync/response前でcrash

Canonical effect: final object may already exist.
Recovery: retryでexisting objectをvalidateし、一致なら`ALREADY_COMMITTED`。

### C5 — COMMITTED_LOCAL後、caller response受領前にcaller側crash

Canonical effect: committed.
Recovery: same as C4。

### C6 — metadata manifest replacement前にcrash

Canonical effect: old revision remains.
Recovery: retry update。

### C7 — manifest replacement後、response前にcrash

Canonical effect: new revision may exist.
Recovery: revision + patch reconciliationで`ALREADY_COMMITTED`。

## 14. Staging Recovery Contract

`recover_staging()` はwriter lock取得後のみ実行する。

各staging txについて：

### final Source absent

- Canonicalへ自動commitしない。
- stagingを削除、またはdiagnostic quarantineへ移動。
- A4 durable jobが存在すればjob retryに任せる。

### final Source present and staged object matches

- finalを正としてvalidate。
- stagingをcleanup。

### final Source present but mismatch

- finalを上書きしない。
- stagingをquarantine。
- Health errorを出す。

### final Source corrupt

- stagingから自動修復しない。
- finalをcorruptとして隔離対象に記録。
- human-visible recovery pathへ送る。

StagingはCanonical backupではない。

## 15. Corruption / Tamper Rules

Writerは以下をsilent acceptしない。

- source directoryがsymlink
- source.mdがsymlink
- payload/originalがsymlink
- object_idとdirectory ID不一致
- payload hash mismatch
- payload byte length mismatch
- unsupported schema_version
- manifest parse failure
- unexpected payload path
- revision regression

`original_name` 等のuser inputはpath生成に使わない。

Writerはsymlink-followingによるVault外write/readを避ける。

## 16. Permission Baseline

Local Vaultでは可能な範囲でowner-onlyを初期値とする。

- directory: 0700相当
- canonical file: 0600相当

File Provider / iCloud等でPOSIX modeがそのまま保証されない場合はplatform protectionへ委ね、Healthでprotection capabilityを表示可能にする。

Permission failureを理由にCanonical内容を別の無保護場所へfallback保存しない。

## 17. Telemetry / Health Events

Body textを保存せず、最低限以下を記録可能とする。

```text
VAULT_WRITE_STARTED
VAULT_WRITE_COMMITTED
VAULT_WRITE_ALREADY_COMMITTED
VAULT_WRITE_REVISION_CONFLICT
VAULT_WRITE_VALIDATION_FAILED
VAULT_WRITE_COMMIT_UNCERTAIN
VAULT_WRITE_IO_FAILED
VAULT_WRITE_CORRUPT
STAGING_RECOVERED
STAGING_QUARANTINED
```

Allowed metadata例：

- tx_id
- source_id
- operation=create|update
- expected_revision / resulting_revision
- timestamps
- error code
- duration

禁止：payload body / full captured text / credentials。

## 18. Failure Injection Test Matrix

A2 unit/integration testでは少なくとも以下のfailure pointを注入する。

1. payload open前
2. payload write中
3. payload sync後
4. manifest write中
5. manifest sync後
6. validation後
7. atomic publish直前
8. atomic publish直後
9. parent directory sync時
10. post-commit read-back時
11. metadata replace直前
12. metadata replace直後

各failureで確認：

- Canonicalにhalf objectがない。
- old revisionまたはnew revisionのどちらかだけが見える。
- retryで1 logical effectへ収束する。
- unexpected existing objectを上書きしない。

## 19. Golden Tests

### A2-G1 — New Source Atomicity

TEXT fixtureをcreateし、commit後のみcanonical Source directoryが出現する。

### A2-G2 — Crash Before Publish

publish直前にkill。
Canonical Sourceなし。retryで1件だけ作成。

### A2-G3 — Crash After Publish

publish直後にkill。
retryで新規作成せず`ALREADY_COMMITTED`。

### A2-G4 — Revision Conflict

revision=3に対しexpected_revision=2でupdate。
既存manifestは一切変化しない。

### A2-G5 — Revision Atomicity

manifest replace中のfailure injectionでrevision 4のpartial manifestがCanonicalに現れない。

### A2-G6 — Tampered Payload

payloadを1 byte変更後にmetadata update。
`CANONICAL_CORRUPT`で停止し、manifestを書き換えない。

### A2-G7 — Existing Destination Collision

同一source_idに異なるpayloadのCreateIntent。
既存Objectを保持し`OBJECT_ID_COLLISION`。

### A2-G8 — Staging Recovery

incomplete staging + valid final + mismatched stagingの3種をrecoverし、auto-promotion/overwriteが起きない。

## 20. A2 Acceptance Criteria

A2完了条件：

1. 新規SourceがDirectory単位でatomic publishされる。
2. Canonical pathへpartial payload/manifestが露出しない。
3. final destinationが既存なら暗黙置換しない。
4. same CreateIntent retryが`ALREADY_COMMITTED`へ収束する。
5. different content / same source_idがhard conflictになる。
6. metadata updateはexpected_revision必須。
7. revision conflictで既存Sourceが一切変更されない。
8. metadata updateはpayloadを変更しない。
9. commit前にA1 full validationを通る。
10. crash injection全pointでhalf-written Canonicalが生じない。
11. post-publish crash後のretryでduplicate effectが生じない。
12. staging recoveryがCanonicalを勝手にpromote/repairしない。
13. iCloud remote syncをlocal commitと混同しない。
14. unsupported filesystemではfail closedする。
15. telemetryにbody/secretを保存しない。

## 21. Explicit Non-goals

A2では以下を実装しない。

- Secret detection algorithm
- Capture inbox / durable job queue
- Worker retry scheduler
- FTS / SQLite
- Deletion Ledger
- Backup / Restore
- LLM processing
- MCP
- multi-device writer consensus
- remote lock service
- iCloud sync conflict auto-merge
- custom encryption

## 22. Implementation Task Breakdown

### A2.1 — Filesystem capability + writer lock boundary

Acceptance:
- same-volume staging/finalを検証。
- exclusive writer lockなしmutation不可。
- unsupported filesystemをfail closed。

### A2.2 — Create transaction

Acceptance:
- stream payload -> hash -> manifest -> staged validation -> directory atomic publish。
- existing destinationを置換しない。

### A2.3 — Metadata revision transaction

Acceptance:
- expected_revision mandatory。
- atomic manifest replacement。
- immutable payload untouched。

### A2.4 — Retry reconciliation

Acceptance:
- committed retry -> ALREADY_COMMITTED。
- collision -> hard fail。

### A2.5 — Crash/staging recovery

Acceptance:
- incomplete stage cleanup。
- no auto-promotion。
- mismatch quarantine。

### A2.6 — Fault injection suite

Acceptance:
- defined 12 failure pointsを自動テスト可能。
- no half-canonical / no silent overwrite。

## 23. Gate to A3

A3 `Local Capture Ingress + Secret Guard`へ進む条件：

- A1 Source ObjectをA2経由で安全にcreate/updateできる。
- crash before/after publishの両方でretryが1 logical effectへ収束する。
- revision conflictが明示failする。
- staging残骸からCanonicalを自動生成しない。
- filesystem capability / iCloud local-commit境界が明文化されている。

A3はこのWriterを唯一のCanonical persistence APIとして使い、Capture inputを直接`canonical/`へ書かない。

## 24. External Platform Notes (implementation evidence)

- POSIX `rename()` / directory operations provide atomic namespace change semantics, but atomicity and durability are separate concerns.
- POSIX rationale recommends syncing the new file, renaming it, and syncing the containing directory when durability of the directory modification matters.
- Apple documents `fsync()` as moving modified data/attributes toward permanent storage, while warning that stronger power-loss guarantees may require `F_FULLFSYNC`.
- Apple Foundation provides `FileManager.replaceItemAt` for no-data-loss item replacement and recommends a unique temporary location, preferably same directory when necessary.
- Apple exposes whether a volume supports `RENAME_EXCL` via `volumeSupportsExclusiveRenaming`.
- Apple recommends `NSFileCoordinator` for safe coordinated access when multiple processes/file presenters may touch files, including iCloud/File Provider-backed locations.

These notes constrain implementation choices but do not expand Slice A scope.
