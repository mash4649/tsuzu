# TSUZU P0 Vertical Slice A3 — Local Capture Ingress + Secret Guard Contract v0.1

- Date: 2026-09-06
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1
- Parent Plan: P0 Vertical Slice A
- Depends on:
  - A1 Canonical Source Contract v0.1
  - A2 Atomic Vault Writer Contract v0.1
- Status: Implementation Contract / Ready to implement
- Scope: A3 only. Local Mac test ingress, pre-persistence secret guard, minimum sensitivity boundary, durable capture job.
- Non-scope: URL fetch, extraction, LLM processing, FTS, MCP, UI, iOS Share Extension.

## 0. Decision

Slice AのCapture入口は、ユーザー入力を直接Canonical Vaultへ書かない。

必ず以下を通す。

```text
Capture Request
    ↓
Boundary Validation
    ↓
Local Secret Guard
    ↓
Sensitivity Floor
    ↓
Durable Capture Job
    ↓
A4 Single Writer Worker
    ↓
A2 Atomic Vault Writer
    ↓
Canonical Source
```

A3の責務は「入力を安全に受理し、後続Workerが同じSourceを一度だけCanonical化できるDurable Jobへ変換する」まで。

Secret / Credentialと判定された入力は、Canonical Vault、Derived Index、LLM、外部Hostへ進ませない。

## 1. Core principles

1. **Capture is not canonicalization.**
   IngressはCanonical Writerではない。Canonicalへの書き込みはA4 → A2のみ。

2. **Secret Guard before persistence into knowledge.**
   Credential / SecretはCanonical Knowledgeへ保存しない。

3. **Local-only guard.**
   Secret判定のために入力内容を外部APIへ送らない。

4. **Content is data, never authority.**
   Capture内容を命令として実行・解釈しない。

5. **One user action → one planned Source identity.**
   Accepted時にstable `source_id` を発行し、A4 retryでも同じIDを使う。

6. **No organization burden.**
   Tag / Folder / Category / Title入力をCaptureの必須条件にしない。

7. **Fail closed on strong credential evidence.**
   強いSecret evidenceがある場合、保存より安全性を優先する。

## 2. Capture Core interface

UI/CLI/Share Extension等は以下の論理契約へ変換する。

```yaml
capture_request:
  request_id:
  idempotency_key:
  requested_at:

  input:
    kind: TEXT | URL | FILE
    content_stream:
    original_name:

  user_metadata:
    scope:
      scope_type:
      scope_id:
    sensitivity_override: null | PUBLIC | PERSONAL | SENSITIVE | RESTRICTED
```

### request_id

1 ingress attemptの追跡ID。UUIDv4。

### idempotency_key

同一配送retryを同じ効果にするためのcaller-stable key。

同じidempotency_keyが既にACCEPTEDなら、新しいSourceを作らず既存のjob_id / source_idを返す。

異なるidempotency_keyで同じpayloadをCaptureした場合は、A1のDuplicate Contract通り別Sourceとして扱う。

### source_id

IngressがACCEPTEDを返す前にUUIDv4を1つ発行し、Capture Jobへ固定する。

A4/A2 retryでsource_idを再生成しない。

## 3. P0 Local Mac adapter

P0のテストIngressはCLIでよい。

推奨surface:

```text
tsuzu capture text
tsuzu capture url
tsuzu capture file <path>
```

### TEXT / URL

本文をCLI argumentへ直接渡す方式を基本にしない。
Shell history / process listingへの漏洩を避けるため、stdinから読む。

例:

```bash
printf '%s' '保存したいテキスト' | tsuzu capture text
printf '%s' 'https://example.com/article' | tsuzu capture url
```

### FILE

Pathは入力元の指定にのみ利用する。
Accepted前にqueue用raw copyを完了するため、Canonical Sourceへ元absolute pathを必須保存しない。

P0 default:

- directory: reject
- symlink: reject
- socket/device/special file: reject
- regular file: allow within size limit

Archive展開、macro実行、HTML実行、PDF解析等は行わない。

## 4. Boundary validation

Secret scanより前に最低限の構造検証を行う。

### TEXT

- UTF-8として受理できること
- empty input reject
- P0 default max: 1 MiB

大きなtextはFILEとしてCapture可能。

### URL

- UTF-8
- empty reject
- `http` / `https` のみ
- credentialsを含むuserinfo URLはSecret Guard対象
- P0 default max: 16 KiB
- fetch / redirect解決 / canonicalizationはしない

### FILE

- regular file only
- symlink reject
- P0 default max: 100 MiB
- extensionをsecurity boundaryにしない
- MIME不明なら `application/octet-stream`
- unknown file typeでもraw Sourceとしては許可可能

Limitsはconfigurable constantとするが、P0で無制限入力は許可しない。

## 5. File TOCTOU contract

FILE入力は、

```text
pathを検査
↓
file handleをopen
↓
fstatでregular file / size確認
↓
同一open handleをstream scan
↓
rewind
↓
同一handleからqueue payloadへcopy
```

とする。

scan後にPathを再openしてcopyする方式は採用しない。
scan対象と保存対象がすり替わるTOCTOUを避けるため。

## 6. Secret Guard

### 6.1 Purpose

Secret Guardは「一般的な個人情報分類器」ではない。

目的はCredential / SecretをKnowledge Pipelineへ入れないこと。

P0でblocking対象とするのは、**高精度でCredentialと判断できるもの**に限定する。

### 6.2 Execution constraints

Secret Scannerは以下を必須とする。

- local-only
- deterministic for same input + same ruleset
- ruleset versioned
- no network verification
- no secret value logging
- streaming scan capable for FILE
- result is metadata only

外部サービスへCredential candidateを送って「有効なtokenか確認する」方式は禁止。

### 6.3 Strong blocking classes

最低限、以下の強いsignalをRESTRICTEDとしてblockする。

- PEM / OpenSSH private key material
- private-key containerとして明確な内容
- known credential/token prefix + plausible body
- bearer/access tokenとして高確度な形式
- JWT-like access credential
- URL embedded username/password
- signed/auth URL query patterns with strong credential semantics
- common secret assignment key + sufficiently credential-like value
- explicit password/token/secret blocks where value structure strongly supports credential interpretation

Rule IDはversioned registryとして持つ。

具体的vendor prefixの追加・削除はruleset updateで行い、Canonical schema変更にはしない。

### 6.4 What is NOT enough to block

以下だけではRESTRICTED確定にしない。

- 単なる長いrandom-looking文字列
- UUID
- SHA hash
- ordinary base64
- email address
- phone number
- ordinary account ID
- filenameだけに `secret` という語がある

false positiveで通常Captureを壊さないため。

### 6.5 Secret result

```yaml
secret_guard:
  outcome: CLEAR | BLOCKED_RESTRICTED
  ruleset_version:
  matched_rule_ids: []
```

matched substring自体は保存・logしない。

`BLOCKED_RESTRICTED` の場合:

- Canonical Source: createしない
- Durable Capture Job: createしない
- queue raw payload: persistしない
- index: 送らない
- LLM: 送らない
- external host: 送らない

許可するtelemetryはbodyなしの以下程度。

```yaml
event: CAPTURE_BLOCKED_RESTRICTED
request_id:
input_kind:
ruleset_version:
matched_rule_ids:
bytes_scanned:
occurred_at:
```

## 7. Two-pass handling for FILE

Credentialをqueueへ一度保存してからscanする設計は禁止する。

FILEは原則:

```text
existing user file
↓
stream scan (read-only)
↓
CLEAR
↓
durable queue copy
```

とする。

これによりTSUZU自身がSecretの追加disk copyを作る前にblockできる。

TEXT / URLはprocess memory上でguard後にqueueへ保存する。

## 8. Sensitivity contract

SecretとSensitivityを分ける。

### 8.1 Ordering

```text
PUBLIC < PERSONAL < SENSITIVE < RESTRICTED
```

### 8.2 Default

明示指定なし:

```text
PERSONAL
```

A1のfloorを維持する。

### 8.3 Explicit override

ユーザーはCapture時に、

- PUBLIC
- PERSONAL
- SENSITIVE
- RESTRICTED

を明示できる。

ただしscanner/security ruleがより高いlevelを要求する場合、ユーザー指定でdowngradeできない。

```text
effective_sensitivity
=
max(
  default_or_user_explicit,
  local_security_floor
)
```

### 8.4 RESTRICTED

effective sensitivityがRESTRICTEDなら、Canonical Knowledgeとして受理しない。

### 8.5 SENSITIVE

SENSITIVEはLocal Canonicalへ保存可能。
ただしA7でexternal egress default deny。

A3だけで包括的なPII/health/financial classifierを作らない。
P0では、explicit SENSITIVE指定と、少数の高確度local ruleによるupgradeで十分とする。

## 9. Durable Capture Job

Guardを通過した入力だけをDurable Jobへ変換する。

Runtime stateでありCanonical Knowledgeではない。

推奨layout:

```text
~/Library/Application Support/TSUZU/
  runtime/
    capture-queue/
      pending/
        <job_id>/
          job.json
          payload/
            original
```

将来iOS App Group等へStorage Adapterを差し替えられるが、A3でiOS要件を持ち込まない。

### Capture Job schema

```yaml
job_id:
job_schema_version: "1.0.0"

request_id:
idempotency_key:
source_id:

created_at:
state: PENDING

source_plan:
  kind: TEXT | URL | FILE
  capture_method: LOCAL_TEXT | LOCAL_URL | LOCAL_FILE
  media_type:
  original_name:
  origin_locator:
  scope:
  effective_sensitivity:
  captured_at:

payload:
  relative_path: "payload/original"
  sha256:
  bytes:

guard:
  secret_ruleset_version:
  matched_rule_ids: []
```

`guard.matched_rule_ids` はCLEARなら通常空。
将来sensitivity upgrade rule IDsを別fieldで持ってよいが、secret valueは持たない。

## 10. Durable acceptance boundary

Ingressがユーザーへ `ACCEPTED` を返してよいのは、最低限以下の後。

```text
validation success
↓
secret guard CLEAR
↓
stable source_id issued
↓
queue payload fully written
↓
job.json written
↓
queue object validated
↓
queue directory atomically published
↓
durability sync
↓
read-back success
↓
ACCEPTED
```

Canonical Sourceの生成完了を待つ必要はない。

つまりユーザー体験上:

```text
ACCEPTED
=
TSUZUが入力を失わず後続処理できる状態
```

であり、

```text
ACCEPTED != INDEXED
ACCEPTED != RECALLABLE
```

とする。

## 11. Queue atomicity

Queue jobも複合ObjectなのでA2と同じ思想を使う。

```text
runtime staging
↓
job + payload
↓
validate
↓
atomic directory publish to pending/
```

half-written `pending/<job_id>` を作らない。

ただしQueueはCanonicalではないため、A2 Canonical Writerそのものを流用する必要はない。
Atomic directory-publish primitiveを共有できる設計を推奨する。

## 12. Idempotency contract

### same idempotency_key + same accepted request

既存jobを返す。

```yaml
result: ALREADY_ACCEPTED
job_id: existing
source_id: existing
```

新しいSourceは作らない。

### same idempotency_key + conflicting input

fail closed。

```text
IDEMPOTENCY_CONFLICT
```

同一keyで異なるpayloadへ差し替えない。

### different idempotency_key + same payload

新Job / 新Source ID。

A1 Duplicate Contractを維持する。

## 13. Capture result contract

最低限:

### ACCEPTED

```yaml
status: ACCEPTED
job_id:
source_id:
```

### ALREADY_ACCEPTED

```yaml
status: ALREADY_ACCEPTED
job_id:
source_id:
```

### REJECTED_RESTRICTED

```yaml
status: REJECTED_RESTRICTED
reason_codes:
```

Secret値を返さない。

### REJECTED_INVALID_INPUT

URL不正、empty、invalid encoding等。

### REJECTED_TOO_LARGE

size limit超過。

### REJECTED_UNSUPPORTED_INPUT

directory / symlink / special file等。

### IDEMPOTENCY_CONFLICT

same idempotency keyに異なるinput。

Internal stack trace / raw payloadをuser-facing errorへ出さない。

## 14. Provenance mapping to A1

A4はCapture JobからA1 Canonical Sourceを生成する。

### TEXT

```yaml
source.kind: TEXT
source.capture_method: LOCAL_TEXT
provenance.origin: USER_EXPLICIT
provenance.actor: USER
provenance.explicitness: EXPLICIT
```

### URL

```yaml
source.kind: URL
source.capture_method: LOCAL_URL
origin_locator:
  type: URL
  value: <captured URL>
```

URLがCredentialを含む場合はA3でblock済みであること。

### FILE

```yaml
source.kind: FILE
source.capture_method: LOCAL_FILE
original_name: <basename>
origin_locator:
  type: NONE
  value: null
```

P0ではabsolute local pathをCanonical metadataへ必須保存しない。
不要な個人環境情報を長期保存しないため。

## 15. No execution / parsing rule

A3ではraw bytesを保存するだけ。

以下をしない。

- shell execute
- HTML render
- JavaScript execute
- macro execute
- archive unpack
- document parser execution
- PDF OCR
- image model
- embedded link follow
- remote fetch
- prompt interpretation

悪意あるfileでも、A3時点では「bytes」。

## 16. Logging / telemetry contract

本文禁止。

Allowed:

```text
request_id
job_id
source_id
input_kind
byte count
status
error code
rule IDs
timing
ruleset version
```

Not allowed:

```text
source body
matched secret
full URL query string in generic telemetry
file bytes
Authorization headers
absolute file path by default
```

URL traceが必要な場合もCanonical Source内に限定し、generic telemetryへ複製しない。

## 17. Cleanup ownership

A3はqueueへPENDING Jobを置くところまで。

A4がCanonical commitに成功した後、

- job state transition
- queue payload cleanup
- retry
- dead-letter / quarantine

を所有する。

A3が後続Jobを勝手にDONE扱いしない。

## 18. Security failure philosophy

### False negative

最も危険。
A7 egress時に再度Secret Guardを適用してdefense in depthする。

### False positive

Capture UXを壊す。
そのためP0 blocking ruleはhigh-confidence credential detectionに限定する。

### Unknown

Secretとして確定できないだけならPERSONALを基本とする。
Sensitivityがunknownという状態は作らない。

## 19. A3 Golden Cases

### Case 1 — Plain Text

input:
ordinary UTF-8 text

expected:
- ACCEPTED
- durable job exists
- stable source_id
- payload hash/bytes match
- no Canonical Source yet if A4 not running

### Case 2 — URL

input:
normal HTTPS URL

expected:
- ACCEPTED
- no network fetch
- captured URL preserved exactly

### Case 3 — File

input:
regular local file

expected:
- scan same open handle
- queue copy matches source bytes
- original file can be deleted after ACCEPTED without losing pending job

### Case 4 — Private Key

input:
PEM/OpenSSH private key fixture

expected:
- REJECTED_RESTRICTED
- no queue payload
- no Canonical Source
- no body in telemetry

### Case 5 — Token in URL

input:
credential-bearing/signed URL fixture

expected:
- REJECTED_RESTRICTED
- URL not copied into generic telemetry

### Case 6 — Duplicate Delivery

input:
same request + same idempotency_key twice

expected:
- second call ALREADY_ACCEPTED
- same job_id/source_id
- one durable queue object

### Case 7 — Same Content, New User Action

input:
same payload, different idempotency_key

expected:
- two jobs
- two source_ids

### Case 8 — Idempotency Conflict

input:
same idempotency_key, different payload

expected:
- IDEMPOTENCY_CONFLICT
- original accepted job unchanged

### Case 9 — Symlink

input:
symlink to regular file

expected:
- REJECTED_UNSUPPORTED_INPUT

### Case 10 — Explicit Sensitive

input:
normal text + sensitivity_override=SENSITIVE

expected:
- ACCEPTED
- effective_sensitivity=SENSITIVE
- later A7 external egress must deny by default

## 20. Fault injection points

最低限:

1. after validation before scan
2. during scan
3. after scan before queue staging
4. during payload copy
5. after payload copy before job manifest
6. after job manifest before validation
7. after validation before publish
8. after publish before durable sync
9. after durable sync before response

Invariant:

```text
REJECTED
→ no durable pending job

or

ACCEPTED/unknown-response-after-crash
→ one complete durable pending job
```

half-written pending jobを正式Jobとして扱わない。

## 21. A3 implementation task breakdown

### A3.1 — CaptureRequest validator

- TEXT / URL / FILE validation
- size limits
- special-file rejection

Acceptance:
invalid boundary inputがqueueへ入らない。

### A3.2 — SecretScanner interface + ruleset registry

Contract:

```text
scan(stream) -> CLEAR | BLOCKED_RESTRICTED
```

Acceptance:
same input/rulesetでdeterministic。
secret bodyをresult/logへ含めない。

### A3.3 — FILE safe-read path

- open once
- fstat
- stream scan
- rewind
- same handle copy

Acceptance:
scan対象とqueued bytesが同一であることをhashで確認可能。

### A3.4 — Sensitivity resolver

- default PERSONAL
- explicit override
- security floor
- downgrade禁止

Acceptance:
scanner resultより低いlevelへならない。

### A3.5 — Durable Capture Queue writer

- stable source_id
- atomic job directory publish
- idempotency lookup

Acceptance:
crash時にhalf-written pending jobを生成しない。

### A3.6 — CLI adapter

- stdin TEXT
- stdin URL
- FILE path
- optional sensitivity flag

Acceptance:
Core CaptureRequest以外へbusiness logicを置かない。

### A3.7 — Golden + fault tests

Case 1〜10 + fault injection。

Acceptance:
A3 invariantsをすべてpass。

## 22. A3 acceptance criteria

A3 DONE条件:

1. Local TEXT / URL / FILEをCapture Requestとして受けられる。
2. Tag / folder / title入力が不要。
3. Credential/Secret strong matchはCanonical/queueへ保存されない。
4. Secret Scannerはlocal-onlyで外部へ内容を送らない。
5. Accepted jobはstable source_idを持つ。
6. same idempotency key retryでduplicate canonical effectの原因を作らない。
7. different user actionのsame payloadは別Source計画になる。
8. explicit SENSITIVEを保持できる。
9. RESTRICTEDはCanonical Source計画にならない。
10. FILEはscan後に同一open handleからcopyする。
11. queue jobはcrash-safeにdurable acceptanceされる。
12. original Source body / secret / full URL queryをgeneric telemetryへ保存しない。
13. A4が同じjobをretry可能な情報がすべて揃う。
14. A1 schema / A2 Canonical Writer contractを変更していない。

## 23. Explicit non-goals

- PII完全自動分類
- user-facing review UI
- iOS Share Extension
- X / Web fetch
- archive extraction
- PDF解析
- OCR
- LLM classification
- Embeddings
- Context retrieval
- MCP
- OS全体監視
- KeychainからCredentialを取り込む機能

## 24. Gate to A4

A4 Single Writer Workerへ進む条件:

```text
Capture Request
→ local validation
→ Secret Guard
→ sensitivity resolution
→ durable PENDING job
```

までがcrash-safe / idempotentに成立していること。

A4ではこのJobを受け取り、

```text
PENDING
→ claim
→ A1 Source materialization
→ A2 atomic canonical commit
→ success / retry
```

だけを扱う。

A4でCapture validationやSecret classificationを再設計しない。

## 25. Final A3 one-line contract

> **TSUZUの入口は、何でも簡単に預けられる。ただしCredentialだけはKnowledge Pipelineへ入れず、受理した入力にはその場でstable Source identityを与え、後続処理が何度再実行されても同じCanonical結果へ収束できるDurable Capture Jobへ変換する。**
