# TSUZU P0 Vertical Slice A4 — Single Writer Worker Contract v0.1

- Date: 2026-09-06
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1
- Parent Plan: P0 Vertical Slice A
- Depends on:
  - A1 Canonical Source Contract v0.1
  - A2 Atomic Vault Writer Contract v0.1
  - A3 Local Capture Ingress + Secret Guard Contract v0.1
- Status: Implementation Contract / Ready to implement
- Scope: A4 only. Durable Capture Job claim, single-writer materialization, canonical commit, retry/recovery, receipt ledger, cleanup.
- Non-scope: SQLite/FTS indexing, retrieval, MCP, LLM extraction, Decision/Discovery/Outcome.

## 0. Decision

Slice Aでは、Canonical Vaultを変更できる主体を **Single Writer Worker 1系統** に限定する。

A4はA3がdurably acceptedしたCapture Jobを受け取り、

```text
PENDING
→ CLAIMED / PROCESSING
→ VALIDATE
→ MATERIALIZE A1 SOURCE
→ A2 ATOMIC COMMIT
→ COMMIT RECONCILIATION
→ DURABLE RECEIPT
→ QUEUE CLEANUP
```

へ進める。

Workerはat-least-onceで同じJobを処理してよい。
ただしCanonical effectはexactly-once相当へ収束させる。

```text
processing attempts: 1..N
canonical Source effect: 0 or 1
```

「何回実行されたか」ではなく「最終的に1つの完全なCanonical Sourceへ収束したか」をInvariantとする。

## 1. Core invariants

1. **One mutable writer**
   Slice AでCanonical Vaultへcreate/updateできるのはA4から呼ばれるA2 Writerだけ。

2. **Job identity is stable**
   `job_id` / `source_id` はA3で確定済み。A4 retryで再発行しない。

3. **Job payload is immutable**
   A4はA3 jobのpayloadを編集しない。

4. **Canonical source creation is idempotent**
   同じJobを何回処理しても同じ`source_id`へ収束する。

5. **Existing valid canonical wins**
   Crash後にCanonical Sourceが既に存在しJob内容と一致するなら、再作成せず既存Sourceを成功として採用する。

6. **Conflict never overwrites**
   同じ`source_id`に異なるCanonical内容が存在する場合はHARD CONFLICT。上書きしない。

7. **Queue is runtime, not knowledge**
   pending / processing / retry / receipt / quarantine状態をCanonical Knowledgeとして保存しない。

8. **No indexing in A4**
   A4成功条件はCanonical commit + Receiptまで。FTS反映はA5の責務。

## 2. Runtime layout

推奨:

```text
~/Library/Application Support/TSUZU/
  runtime/
    worker/
      worker.lock

    capture-queue/
      pending/
        <job_id>/
          job.json
          runtime.json
          payload/
            original

      processing/
        <job_id>/
          job.json
          runtime.json
          payload/
            original

      retry/
        <job_id>/
          job.json
          runtime.json
          payload/
            original

      quarantine/
        <job_id>/
          job.json
          runtime.json
          payload/
            original

      receipts/
        <idempotency_key_hash>.json
```

`job.json` と `payload/original` はA3で生成されたimmutable accepted input。

`runtime.json` のみA4が更新可能。

## 3. A3 idempotency clarification

A4を閉じるにあたり、A3のidempotencyを完結させるため以下を追加Contractとする。

### 3.1 Request fingerprint

A3はaccepted requestに対してstableな`request_fingerprint`を計算し、`job.json`へ保持する。

Fingerprint対象は最低限:

```text
source.kind
capture_method
payload.sha256
payload.bytes
scope
effective_sensitivity
original_name
origin_locator type/value
```

absolute local file pathはfingerprint対象にしない。

推奨:

```text
request_fingerprint =
SHA256(canonical-json(material request fields))
```

### 3.2 Receipt Ledger

Queue Jobを成功後にcleanupしても同じ`idempotency_key`を識別できるよう、A4はbody-free Receiptを永続化する。

```yaml
receipt_schema_version: "1.0.0"

idempotency_key_hash:
request_fingerprint:

job_id:
source_id:

terminal_state: COMMITTED | BLOCKED_RESTRICTED | QUARANTINED
canonical_revision:

created_at:
updated_at:
```

`idempotency_key` raw valueそのものをfilenameへ使わない。

```text
idempotency_key_hash = SHA256(idempotency_key)
```

ReceiptはRuntime ledgerでありCanonical Knowledgeではない。

### 3.3 A3 lookup precedence

将来の同一request受理時:

```text
Receipt Ledger
→ active queue job
→ new job creation
```

の順にlookupする。

Receiptがありfingerprint一致:

```text
ALREADY_ACCEPTED / ALREADY_COMMITTED
→ same job_id
→ same source_id
```

Receiptがありfingerprint不一致:

```text
IDEMPOTENCY_CONFLICT
```

これによりJob cleanup後もidempotencyが維持される。

## 4. Single Worker process contract

### 4.1 Process lock

Worker起動時にexclusive `worker.lock` を取得する。

取得成功:
- active workerとして処理開始

取得失敗:
- 2nd workerはCanonical処理を開始しない
- error/standbyとして終了または待機できる
- duplicate processingは禁止

P0ではdistributed lease / heartbeat / leader electionを実装しない。

### 4.2 Why process-wide lock

P0は1 Vault = 1 active mutable writer。

したがって、

```text
job-level lease
distributed lock
heartbeat expiry
multiple consumers
```

を入れるより、

```text
one worker process lock
+
atomic directory claim
```

を採用する。

将来multi-device syncを導入するときは別Contractで再評価する。

## 5. Worker run identity

Worker起動ごとにruntime-only `worker_instance_id` をUUIDv4で発行する。

用途:

- runtime.json
- telemetry
- crash diagnosis

Canonical Sourceには書かない。

## 6. Job state machine

論理状態:

```text
PENDING
  ↓ claim
PROCESSING
  ├─→ COMMITTED → RECEIPT_COMMITTED → CLEANED
  ├─→ RETRY_WAIT
  ├─→ PAUSED_ENVIRONMENT
  ├─→ BLOCKED_RESTRICTED
  └─→ QUARANTINED
```

Queueのphysical directoryが主要stateを表す。

### PENDING
A3 accepted、未claim。

### PROCESSING
A4がclaim済み。

### RETRY_WAIT
一時失敗。再試行可能。

### PAUSED_ENVIRONMENT
disk full / permission / Vault unavailable等、同じ処理を連打しても改善しない環境エラー。

### BLOCKED_RESTRICTED
A4再検査で新たにCredential/Secret判定された。

### QUARANTINED
Integrity mismatch / schema corruption / source ID collision等、automatic retryすべきでない状態。

### COMMITTED / RECEIPT_COMMITTED / CLEANED
terminal successの論理状態。成功Job directory自体は最終的に削除するため、Receiptがterminal stateを保持する。

## 7. Claim contract

Claimは同一runtime filesystem内で、

```text
pending/<job_id>
→
processing/<job_id>
```

のatomic directory moveで行う。

Claim成功後に`runtime.json`をatomic update:

```yaml
state: PROCESSING
worker_instance_id:
attempt:
claimed_at:
last_error_code: null
next_retry_at: null
```

Process lockがあるため通常競合はないが、directory move自体もatomic claim boundaryとする。

## 8. Pre-materialization validation

A4はA3の判断を再設計しないが、Canonical commit直前にjob integrityを必ず再検証する。

最低限:

```text
job schema valid
job_id matches directory identity
source_id valid
payload exists
payload bytes match
payload SHA-256 matches
request_fingerprint recomputes identically
effective_sensitivity != RESTRICTED
```

不整合時はCanonicalへ進まない。

## 9. Secret defense-in-depth

### 9.1 Normal case

A3でCLEARのjobのみQueueへ存在する。

### 9.2 Ruleset changed after ACCEPTED

Jobの`secret_ruleset_version`と現在rulesetが異なる場合、A4はCanonical write直前に最新rulesetで再scanできる。

最新rulesetで`BLOCKED_RESTRICTED`:

- Canonical Sourceを作らない
- Receiptを`BLOCKED_RESTRICTED`
- body-free security event
- queue payloadを通常unlinkで削除
- Source bodyをquarantine保存しない

SSD/APFS上のsecure eraseは保証しない。
「安全な物理消去済み」とは表現しない。

この経路はrare defense-in-depthであり、A3 blocking失敗を通常運用にしない。

## 10. Source materialization

A4はA3 JobからA1 Sourceを機械的に生成する。

AI/LLMを使わない。

### Fixed mappings

```yaml
object_id: job.source_id
object_type: SOURCE
schema_version: A1 Source schema version
revision: 1

created_at: job.created_at
updated_at: job.created_at

scope: job.source_plan.scope

provenance:
  origin: USER_EXPLICIT
  source_refs: []
  actor: USER
  explicitness: EXPLICIT

trust:
  level: ASSERTED
  confidence: 1.0

sensitivity:
  level: job.source_plan.effective_sensitivity

temporal:
  valid_from: null
  valid_until: null

deletion:
  state: LIVE
  tombstoned_at: null
```

Source固有fieldはA3 source_plan / payload metadataから生成する。

`created_at = job.created_at` としてretryでもmaterialized manifestのsemantic resultを安定させる。

`captured_at` はA3 captured_atを維持する。

## 11. Canonical commit

Materialized SourceをA1 validatorへ通した後、A2 Writerへ渡す。

A2 resultを以下へ正規化する。

### CREATED

新Sourceがatomic commitされた。

### ALREADY_COMMITTED

同じsource_idに、jobからmaterializeされる内容と一致するvalid Canonical Sourceが既にある。

Crash/retry reconciliation上、成功相当。

### REVISION_CONFLICT

A4 createでは通常発生しない。
既存Objectの状態をinspectし、same semantic sourceでなければQUARANTINE。

### OBJECT_ID_COLLISION / CONTENT_MISMATCH

HARD CONFLICT。
絶対にoverwriteしない。

## 12. Commit reconciliation

A4は「A2 callが成功responseを返したか」だけで成功判定しない。

理由:

```text
A2 canonical publish
↓
process crash
↓
success response未受領
```

があるため。

Recovery/retry時は必ず、

```text
canonical source exists?
    │
    ├─ NO
    │   → retry A2
    │
    └─ YES
        ↓
     A1 validate
        ↓
     source_id match
        ↓
     payload SHA match
        ↓
     expected manifest semantics match
        │
        ├─ YES → ALREADY_COMMITTED
        └─ NO  → HARD CONFLICT / QUARANTINE
```

とする。

## 13. Success ordering

成功処理順序を固定する。

```text
1. A2 Canonical Source committed or reconciled
2. Canonical read-back validation
3. Durable Receipt write
4. Success telemetry
5. processing Job directory cleanup
```

この順序を逆にしない。

### Why Receipt before cleanup

Canonical成功後、Jobを先に削除してReceipt書込前に落ちると、
idempotency mappingが失われるため。

## 14. Receipt Writer

Receiptもruntime durable state。

書き込みは最低限:

```text
stage
→ validate
→ atomic replace/create
→ durability sync
→ read-back
```

A2 Canonical Writerと同じatomic primitiveを共有してよいが、Canonical storage APIとは分離する。

Receipt本文にpayload/source bodyを保存しない。

## 15. Crash recovery

Workerはprocess lock取得後、通常PENDING処理より先に`processing/`残骸をrecoverする。

Single Worker contract上、新worker起動時に残っているPROCESSINGはすべてorphanとして扱える。

### Case A: processing job + Canonical absent

Job integrity valid:
- pending/retryへ戻して再処理

Job integrity invalid:
- quarantine

### Case B: processing job + matching Canonical exists

- Canonical read-back validate
- missing Receiptを作成
- Job cleanup
- 新Canonicalは作らない

### Case C: processing job + conflicting Canonical exists

- quarantine
- Canonicalを変更しない
- HARD_CONFLICT event

### Case D: Receipt already COMMITTED + job remains

- Receipt/source consistency確認
- job cleanupだけ行う

## 16. Retry classification

全Errorを同じretry loopへ入れない。

### RETRYABLE_TRANSIENT

例:

- temporary filesystem busy
- transient coordination failure
- short-lived I/O failure

処理:
- `retry/`へmove
- bounded backoff
- attempt count increment

P0 default:
- automatic attempt上限: 5

backoffの具体秒数はimplementation constantとし、Product Contractにはしない。

### PAUSED_ENVIRONMENT

例:

- disk full
- Vault unavailable
- permission denied
- runtime root unavailable

処理:
- tight loopで再試行しない
- jobを失わない
- Healthへ環境エラーを出せる状態にする
- environment回復またはexplicit retryで再開

### TERMINAL_SECURITY

- latest Secret Guard BLOCKED_RESTRICTED

処理:
- Canonicalなし
- body-free Receipt
- payload cleanup
- auto retryしない

### TERMINAL_INTEGRITY / HARD_CONFLICT

例:

- payload hash mismatch
- job schema corruption
- request fingerprint mismatch
- source ID collision
- existing Canonical mismatch

処理:
- quarantine
- auto retryしない
- Canonicalを自動修復しない

## 17. Retry wake-up

P0では高度なschedulerを作らない。

Worker loopは、

- pending
- retry eligible
- environment state change / manual retry

を順に処理できればよい。

OS-level launchd登録、background login item UX、mobile background executionはA4 scope外。

## 18. Quarantine contract

Quarantineは通常失敗の置き場ではない。

対象:

- integrity anomaly
- impossible state
- ID collision
- conflicting canonical
- malformed accepted job

Quarantine content:

- local runtime only
- index禁止
- LLM禁止
- external egress禁止
- automatic promotion禁止

Security-blocked Secret payloadはquarantineへ残さない。

P0のquarantine retention期間は固定しない。
後続Control Plane/Health Contractでpurge操作を定義できる。

## 19. Cleanup contract

Canonical commit + Receipt durable成功後のみ、successful processing job payloadを削除可能。

削除失敗:
- Canonical/Receipt成功をrollbackしない
- orphan cleanup対象
- future recoveryでcleanup

Cleanup failureをCanonical failureにしない。

## 20. Worker shutdown

正常shutdown:

1. 新規claim停止
2. 現在のA2 transaction完了または安全にabort
3. runtime state flush
4. worker lock release

強制kill/crash:
- next startup recoveryが処理

「shutdown時に必ずJobをPENDINGへ戻す」ことを安全性の前提にしない。

## 21. Telemetry / logging

Body禁止を維持。

Allowed:

```text
worker_instance_id
job_id
source_id
request_id
attempt
state transition
error code
duration
payload byte count
ruleset version
receipt state
canonical revision
```

Not allowed:

```text
payload body
secret values
full URL query string
file bytes
absolute source file path
raw idempotency key
```

Event例:

```text
JOB_CLAIMED
JOB_VALIDATION_FAILED
CANONICAL_CREATED
CANONICAL_RECONCILED
RECEIPT_COMMITTED
JOB_RETRY_SCHEDULED
JOB_PAUSED_ENVIRONMENT
JOB_SECURITY_BLOCKED
JOB_QUARANTINED
JOB_CLEANED
WORKER_RECOVERY_COMPLETED
```

## 22. A4 Golden Cases

### Case 1 — Happy Path

PENDING plain text job

Expected:
- one Source
- valid receipt
- pending/processing job cleaned
- no index required

### Case 2 — Worker Double Start

2 worker processes start

Expected:
- one obtains worker lock
- second does not process jobs
- one Canonical effect

### Case 3 — Crash After Claim

Crash immediately after pending→processing

Expected next start:
- orphan detected
- Canonical absent
- job retried
- one valid Source

### Case 4 — Crash During A2 Before Publish

Expected:
- no half-written Canonical
- job remains recoverable
- retry creates one Source

### Case 5 — Crash After Canonical Commit Before Receipt

Expected next start:
- matching Canonical detected
- no second Source
- receipt created
- job cleaned

### Case 6 — Crash After Receipt Before Cleanup

Expected next start:
- receipt/source match
- no Canonical write
- cleanup only

### Case 7 — Same Job Reprocessed

Force same accepted job through worker twice.

Expected:
- same source_id
- second pass ALREADY_COMMITTED/reconciled
- one Canonical Source

### Case 8 — Payload Tamper

Modify queued payload after A3 ACCEPTED.

Expected:
- hash mismatch
- no Canonical change
- quarantine
- no automatic repair

### Case 9 — Existing Source ID Collision

Place valid different Source under same source_id before processing.

Expected:
- HARD CONFLICT
- existing Source untouched
- job quarantined

### Case 10 — Environment Failure

Simulate disk full / permission failure.

Expected:
- no half Source
- job preserved
- no tight infinite retry
- state PAUSED_ENVIRONMENT or equivalent

### Case 11 — Ruleset Upgrade Blocks Job

A3 accepted under old ruleset; latest scanner blocks before Canonical.

Expected:
- no Canonical Source
- BLOCKED_RESTRICTED receipt
- payload removed from queue
- no secret body in telemetry

### Case 12 — Receipt Survives Queue Cleanup

Complete job, remove queue object, resend same idempotency request.

Expected:
- Receipt lookup returns same source_id/job_id
- no new Source

## 23. Fault injection matrix

最低限以下へfailure injection:

1. before claim
2. after claim before runtime update
3. after runtime update before validation
4. during payload validation
5. after validation before materialization
6. after materialization before A2
7. during A2 staging
8. after A2 publish before A2 response
9. after A2 response before read-back
10. after read-back before Receipt staging
11. after Receipt publish before response/log
12. after Receipt before cleanup
13. during cleanup

Invariant:

```text
Canonical:
  absent
  OR
  one complete valid Source

Never:
  duplicate Source for same source_id
  overwrite conflicting Source
  half-written Source accepted as valid
```

## 24. A4 implementation task breakdown

### A4.1 — Worker process lock + startup recovery skeleton

Acceptance:
- double startで1 workerだけactive
- orphan PROCESSINGを列挙できる

### A4.2 — Queue state mover + runtime.json codec

Acceptance:
- pending→processing→retry/quarantine moveがatomic
- job.json/payloadはimmutable

### A4.3 — Job validator + Source materializer

Acceptance:
- A3 jobからA1 Sourceをdeterministicに生成
- tamperを検出

### A4.4 — Canonical commit reconciliation

Acceptance:
- CREATED / ALREADY_COMMITTED / HARD_CONFLICTを区別
- crash after publishをduplicateなしでrecover

### A4.5 — Capture Receipt Ledger

Acceptance:
- queue cleanup後もidempotencyを維持
- fingerprint conflictを検出
- body-free

### A4.6 — Retry / pause / quarantine policy

Acceptance:
- transientのみbounded auto retry
- environment failureはtight loopしない
- terminal anomalyはauto retryしない

### A4.7 — Cleanup + shutdown

Acceptance:
- Receipt前にjobを削除しない
- cleanup failureがCanonical成功をrollbackしない

### A4.8 — Golden / fault injection tests

Acceptance:
- Case 1〜12
- fault point 1〜13
- all invariants pass

## 25. A4 acceptance criteria

A4 DONE条件:

1. Canonical writerはWorker経由1系統に限定される。
2. 2 worker同時起動でも1つしか処理しない。
3. pending jobをatomic claimできる。
4. job payloadを変更せずA1 Sourceへmaterializeできる。
5. retryでsource_idを再生成しない。
6. A2 commit後のresponse lossをALREADY_COMMITTEDとしてreconcileできる。
7. same jobをN回処理してもCanonical effectが1つ。
8. source_id collision時にoverwriteしない。
9. payload tamperをCanonical化しない。
10. Canonical成功後にdurable Receiptを残す。
11. Queue cleanup後もidempotencyを維持する。
12. crash後のPROCESSING orphanを自動recoveryできる。
13. transient/environment/terminal errorを区別する。
14. ordinary failureでuser-facing inbox管理を要求しない。
15. secret body / source bodyをtelemetryへ出さない。
16. A5 IndexがなくてもA4単独でCanonical correctnessを検証できる。
17. A1/A2のCanonical Contractを変更していない。

## 26. Explicit non-goals

- multiple concurrent worker consumers
- distributed locking
- cloud queue
- multi-Mac concurrent write
- launchd/Login Item productization
- FTS/index update
- LLM extraction
- Background semantic processing
- Decision/Discovery
- user-facing retry inbox
- remote admin
- secure physical erase guarantee

## 27. Gate to A5

A5 SQLite / FTSへ進む条件:

```text
A3 accepted job
→ A4 claim
→ A1 Source materialization
→ A2 atomic canonical commit
→ Receipt
→ cleanup
```

が、

- crash
- retry
- duplicate process start
- existing source reconciliation
- environment failure

を含めて1つのCanonical Sourceへ収束すること。

A5はこのCanonical Vaultを**read-only input**として扱う。

A5のIndex生成失敗を理由にA4 Canonical commitをrollbackしない。

## 28. Final A4 one-line contract

> **TSUZUのSingle Writer Workerは、Durable Capture Jobを何度受け取っても同じSource identityへ収束させ、途中で落ちても既存Canonicalを照合して続きから回復し、Canonical成功をReceiptで確定してからQueueを片付ける、唯一のmutable write boundaryである。**
