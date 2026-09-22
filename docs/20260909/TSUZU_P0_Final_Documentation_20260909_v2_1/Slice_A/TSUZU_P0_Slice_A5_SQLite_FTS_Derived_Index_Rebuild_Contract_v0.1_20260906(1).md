# TSUZU P0 Vertical Slice A5 — SQLite / FTS Derived Index + Rebuild Contract v0.1

- Date: 2026-09-06
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1
- Parent Plan: P0 Vertical Slice A
- Depends on:
  - A1 Canonical Source Contract v0.1
  - A2 Atomic Vault Writer Contract v0.1
  - A3 Local Capture Ingress + Secret Guard Contract v0.1
  - A4 Single Writer Worker Contract v0.1
- Status: Implementation Contract / Ready to implement
- Scope: A5 only. Disposable local SQLite metadata index, FTS5 text index, incremental convergence, full rebuild and corruption recovery.
- Non-scope: Deletion Ledger semantics beyond current TOMBSTONE, host egress, MCP, embeddings, LLM extraction, chunking, semantic search.

## 0. Decision

SQLite / FTS is **Canonicalではない**。

```text
Canonical Vault
    ↓ validate/read only
Deterministic Index Projection
    ↓
Local SQLite + FTS5
```

Indexはいつでも削除可能で、Canonical Vaultだけから再生成できなければならない。

Index破損・schema不一致・SQLite version変更・tokenizer変更時は、Canonicalを修復したり複雑なmigrationを行うのではなく、**Indexを捨てて再構築する**ことをP0の第一選択とする。

## 1. Physical storage clarification

A1で示した `<Vault>/index/` は論理的なDerived領域として扱い、P0のlive mutable SQLite databaseはsync対象Vault内へ置かない。

P0 physical path:

```text
~/Library/Application Support/TSUZU/
  index/
    tsuzu.sqlite
    # runtime中のみ tsuzu.sqlite-wal / tsuzu.sqlite-shm が存在し得る
```

Canonical:

```text
<Vault>/
  canonical/
  derived/
  system/
```

### Reason

- Canonicalはユーザー所有Vaultに残す。
- SQLiteは再生成可能なApp Support state。
- WAL databaseをiCloud/File Provider同期単位にしない。
- SQLite DB / WAL / SHMを複数Deviceの同期正本にしない。

これはA1 Canonical Schemaの変更ではない。
Indexの物理配置だけをA5で明確化する。

## 2. SQLite capability gate

Repository / SQLite binding versionは現時点では未固定なので、特定version番号を推測して依存しない。

起動時に実Runtimeへcapability probeを行う。

Required:

```text
SQLite opens
FTS5 available
trigram tokenizer available
transactions work
PRAGMA trusted_schema available
```

Probe例の意味:

```sql
CREATE VIRTUAL TABLE temp.__tsuzu_fts_probe
USING fts5(x, tokenize='trigram');

DROP TABLE temp.__tsuzu_fts_probe;
```

trigram unavailable時に`unicode61`へsilent fallbackしない。

P0は日本語検索を主要ユースケースに含むため、trigram非対応Runtimeは明示的に`INDEX_CAPABILITY_UNAVAILABLE`とする。

## 3. Why trigram

P0のFTS tokenizer:

```text
trigram
case_sensitive = 0
remove_diacritics = 0
```

目的:

- 日本語の空白なし文章をsubstring検索できる。
- 独自MeCab/Kuromoji等をP0へ持ち込まない。
- 英数字・URLにも同一Indexを利用できる。

Known limitation:

- FTS MATCHでは3 Unicode文字未満のsubstringはmatchしない。

A7では短いqueryに対しLIKE等のbounded fallbackを定義する。
A5では独自Tokenizerを追加しない。

## 4. Active database connection policy

Active DB open時のP0 default:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA trusted_schema = OFF;
```

`busy_timeout`はbindingで適切な有限値を設定する。

### Rationale

- WALによりreaderとwriterの同時利用を許容する。
- IndexはDerivedなので、power lossで最新Index transactionが失われてもCanonicalから再生成できる。
- `synchronous=NORMAL`でもWALはconsistencyを維持し、Index durability不足はRebuildで回復可能。
- trusted_schemaはOFF。

OFF journal/synchronousは使用しない。

## 5. Index ownership

SQLiteへ書き込めるのはA5 Index Manager 1系統。

```text
A4 Canonical Writer
    ↓ canonical commit + receipt
A5 Index Manager
    ↓
SQLite
```

A4 Canonical成功はA5成功へ依存しない。

つまり:

```text
Canonical commit success
+
Index update failure
=
Canonical success remains success
```

Index failureを理由にCanonical Sourceをrollbackしない。

## 6. Index schema

P0 schema generation: 1

### 6.1 index_meta

```sql
CREATE TABLE index_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

最低限:

```text
index_contract_version
index_schema_generation
tokenizer
projection_version
vault_locator_hash
generation_id
built_at
```

`vault_locator_hash`はlocal cache association用。
Canonical identityではない。

Vault pathが変わった場合は別cache/rebuildになってよい。

### 6.2 source_index

```sql
CREATE TABLE source_index (
  source_id TEXT PRIMARY KEY,

  source_revision INTEGER NOT NULL,
  source_schema_version TEXT NOT NULL,

  source_kind TEXT NOT NULL,
  media_type TEXT NOT NULL,

  scope_type TEXT NOT NULL,
  scope_id TEXT,

  sensitivity TEXT NOT NULL,
  deletion_state TEXT NOT NULL,

  captured_at TEXT NOT NULL,

  payload_sha256 TEXT NOT NULL,
  payload_bytes INTEGER NOT NULL,

  original_name TEXT,
  canonical_relpath TEXT NOT NULL,

  projection_mode TEXT NOT NULL,
  projection_reason TEXT,

  index_text_sha256 TEXT,
  index_fingerprint TEXT NOT NULL,

  indexed_at TEXT NOT NULL
);
```

`canonical_relpath`はVault rootからのrelative path。
Absolute pathをIndex resultやTelemetryの必須情報にしない。

### 6.3 source_fts

```sql
CREATE VIRTUAL TABLE source_fts USING fts5(
  source_id UNINDEXED,
  name,
  body,
  tokenize='trigram'
);
```

P0では通常content FTS5 tableを使う。

external-content / contentless FTS5は採用しない。

理由:

- Trigger同期を増やさない。
- update/delete contractを単純にする。
- Index自体が使い捨てなのでcontent重複を許容できる。

### 6.4 index_exclusion

Bodyを持たないHealth用。

```sql
CREATE TABLE index_exclusion (
  source_id TEXT PRIMARY KEY,
  source_revision INTEGER,
  reason_code TEXT NOT NULL,
  observed_at TEXT NOT NULL
);
```

P0 reason例:

```text
TOMBSTONED
CORRUPT_CANONICAL
RESTRICTED
SECRET_RECLASSIFIED
UNSUPPORTED_BODY_PROJECTION
OVERSIZE_BODY
```

Secret/source bodyを保存しない。

## 7. Application identity / schema handling

SQLite DBはTSUZU Index専用と識別できるapplication_idを設定する。

`user_version`をIndex schema generationとして使用してよい。

P0原則:

```text
expected application_id mismatch
→ do not trust DB
→ discard/rebuild

user_version unsupported
→ no complex migration
→ discard/rebuild
```

Canonicalに影響しないため、Migration FrameworkをP0へ作らない。

## 8. Canonical eligibility

Index source of truthはA1 Canonical Source。

最低条件:

```text
A1 schema valid
payload exists
payload hash valid
payload bytes valid
object_type == SOURCE
deletion.state == LIVE
sensitivity != RESTRICTED
```

A6導入後はDeletion Ledgerをさらに適用する。

```text
eligible_after_A6
=
A5 eligibility
AND
not deleted by Deletion Ledger
```

A5だけでA6のDeletion Ledgerを先回り実装しない。

## 9. Secret defense-in-depth before indexing

Slice A Hard Invariant「Secret scan before indexing」を維持する。

A5 projection前にcurrent Secret Guardを再利用可能とする。

現在rulesetでCredential/Secret strong match:

```text
do not index body
do not index source metadata as normal eligible source
reason = SECRET_RECLASSIFIED
Health/Security event
CanonicalはA5から変更しない
```

A5がCanonicalを削除・改変・修復しない。

Legacy/new-ruleset secretがCanonicalに見つかった場合は後続Security remediation対象。

## 10. Deterministic projection

A5はAI/LLMを使わない。

Canonical SourceからFTS documentへdeterministic projectionする。

### TEXT

```text
name = ""
body = exact UTF-8 payload
projection_mode = BODY
```

A1通りMarkdown整形・要約・Unicode意味変換を行わない。

### URL

```text
name = ""
body = exact captured URL string
projection_mode = BODY
```

HTTP fetchしない。

### FILE — text-like

P0でbody indexing可能条件:

```text
payload_bytes <= MAX_INDEXABLE_TEXT_FILE_BYTES
AND
media type is explicitly text-like
AND
payload decodes as UTF-8
```

P0 default:

```text
MAX_INDEXABLE_TEXT_FILE_BYTES = 4 MiB
```

text-likeの最小allowlist例:

```text
text/*
application/json
application/xml
application/javascript
```

拡張子だけをsecurity boundaryにしない。

projection:

```text
name = original_name or ""
body = decoded payload
projection_mode = BODY
```

### FILE — binary / unsupported / oversize

```text
name = original_name or ""
body = ""
projection_mode = METADATA_ONLY
projection_reason =
  UNSUPPORTED_BODY_PROJECTION
  or OVERSIZE_BODY
```

PDF/OCR/Office/archive parsingはA5では行わない。

「先頭だけtruncateしてbody indexing」はしない。
Silent partial recallを避けるため。

## 11. Index fingerprint

同じCanonical revisionを無駄に再indexしないため、Derived fingerprintを持つ。

最低材料:

```text
source_id
source_revision
source_schema_version
payload_sha256
source kind
media type
scope
sensitivity
deletion state
projection_version
tokenizer configuration
```

```text
index_fingerprint =
SHA256(canonical-json(index-relevant fields))
```

fingerprint一致ならupsertをskip可能。

Pathはfingerprintのsemantic identityに含めない。

## 12. Incremental update transaction

1 SourceのIndex更新は1 SQLite transactionで行う。

```text
BEGIN
  validate current canonical
  remove old source_fts row(s)
  upsert/delete source_index
  insert eligible source_fts row
  clear/update index_exclusion
COMMIT
```

失敗:

```text
ROLLBACK
Canonical untouched
Index remains old/stale
```

A5は後でreconcileする。

### Tombstoned Source

A5時点でもmanifestがTOMBSTONEDなら:

```text
delete source_fts rows
delete source_index row
upsert index_exclusion(TOMBSTONED)
```

A6ではこれにDeletion Ledger precedenceを追加する。

## 13. Incremental convergence trigger

A4 Canonical commit + durable Receipt後に、A5へ

```text
source_id changed/committed
```

を通知可能とする。

ただしtransient eventだけを正確性の根拠にしない。

以下を必須とする。

### Worker / app startup

```text
index reconcile
```

### A5 update failure

```text
Canonical success維持
mark index dirty in runtime health
retry/reconcile later
```

Index eventを失ってもstartup reconcileで収束できる。

## 14. Reconcile algorithm

Full rebuildより軽い整合処理。

1. Canonical Source IDs / revision / fingerprintを列挙
2. source_indexと比較
3. missing → insert
4. stale fingerprint/revision → reindex
5. TOMBSTONED → remove
6. Indexにのみ存在しCanonicalにないrow → remove
7. corrupt Canonical → remove + exclusion/health
8. current Secret Guard block → remove + security event

A6導入後はDeletion Ledgerを最上位で適用する。

Reconcile結果はCanonicalを変更しない。

## 15. Full rebuild contract

Full rebuildは「現在DBをその場でDROP/再作成」しない。

side-by-side candidate DBを作る。

```text
active:    tsuzu.sqlite
candidate: tsuzu.rebuild.<generation_id>.sqlite
```

### 15.1 Candidate creation

Candidate DBはpublish前なので、単一fileへ確定しやすいjournal modeで構築してよい。

推奨:

```text
journal_mode = DELETE
synchronous = FULL
```

Candidateはlive queryへ公開しない。

### 15.2 Rebuild steps

```text
1. create candidate DB
2. create schema/meta
3. enumerate Canonical Sources deterministically
4. validate each A1 Source
5. current Secret Guard
6. apply LIVE/TOMBSTONED eligibility
7. deterministic projection
8. insert eligible source_index/source_fts
9. record exclusions
10. finish writes
11. PRAGMA integrity_check
12. semantic rebuild verification
13. mark candidate READY
14. close candidate DB
15. exclusive index swap
16. reopen live DB in WAL mode
17. post-swap reconcile
```

## 16. Why post-swap reconcile exists

Canonical writes may occur whileCandidateを構築している。

そのためRebuild snapshotだけを永久的な真実にしない。

```text
candidate built
↓
atomic swap
↓
reconcile against current Canonical
```

で最終収束させる。

Incremental index updateとfull rebuild writeは`index.lock`でserial化する。

Index lockはCanonical Writer lockとは別。

Index rebuild待ちを理由にCanonical commitをrollbackしない。

## 17. Atomic index swap

Index Managerが全SQLite connectionを所有する。

Swap時:

```text
1. acquire exclusive index lock
2. stop new index reads briefly
3. close active SQLite connections
4. ensure old WAL/SHM are no longer active
5. remove stale old sidecars only after clean close
6. candidate has no WAL sidecar
7. atomic replace candidate main DB → tsuzu.sqlite
8. reopen
9. set WAL/NORMAL/trusted_schema=OFF
10. release read gate / index lock
```

Open WAL connectionを残したままmain DBだけ差し替えない。

## 18. Rebuild equivalence

「再構築できた」をSQLite file byte equalityで判定しない。

Semantic equivalenceで判定する。

最低限:

```text
eligible source_id set
source_id → source_revision
source_id → payload_sha256
source_id → index_fingerprint
source_id → projection_mode
fixed Golden Queries → expected source_id set
```

が期待どおりであること。

SQLite internal page layout / row order / generation_idの一致は要求しない。

## 19. Corruption handling

Open/startup時にminimum health check。

```text
application_id
user_version
required tables
required FTS capability
PRAGMA quick_check
```

明示Rebuild/Golden Gateでは:

```text
PRAGMA integrity_check
```

Corrupt / wrong DB:

```text
close
discard local derived DB + sidecars
body-free health event
rebuild from Canonical
```

Corrupt Indexをdebug uploadしない。

CanonicalへIndex内容から逆修復しない。

## 20. Local security

P0 Index directory/fileはユーザー専用local App Support stateとして扱う。

目標permission:

```text
index directory: owner-only
DB / WAL / SHM: owner-only
```

Custom encryption engineはP0外。

IndexはCanonical本文のDerived copyを持ち得るため、Telemetryや外部support bundleへDBを自動添付しない。

## 21. Search contract boundary

A5はIndex構築を担当する。

A7がRetrieval query builder / ranking / policyを担当する。

A5が保証するのは:

```text
MATCH / LIKEの基礎検索が可能
source_idへ戻れる
metadata filter材料がある
```

まで。

### Ranking

FTS5の`rank` / `bm25()`をA7で使用可能だが、
A5ではranking weightをProduct Contractとして固定しない。

### Query syntax

User文字列をそのままFTS5 MATCH grammarへ流し込まない。
escaping/tokenization/query builderはA7責務。

## 22. Japanese / short-query behavior

A5 Golden fixtureに日本語を必須化する。

例:

```text
本文:
「応募単価より面接設定率を優先して判断する」

query:
「面接設定率」
```

Expected:
- source_id match

3文字未満queryはtrigram MATCHだけで保証しない。

A7で:

```text
short query
→ bounded LIKE fallback / exact metadata match
```

を閉じる。

## 23. Duplicate behavior

A1のDuplicate Contractを維持する。

Same payload / different source_id:

```text
Indexにも2 Sourceとして存在
```

A5でCanonical multiplicityをmergeしない。

検索結果の表示上のdedup/groupingはA7以降のDerived behavior。

## 24. Index freshness semantics

Canonical commit直後にIndexが必ず同期済みとは仮定しない。

状態:

```text
CANONICAL_COMMITTED
↓
INDEX_PENDING
↓
INDEX_CURRENT
```

ただしこの状態をCanonical Sourceに書かない。

Recall時にIndex generation / freshnessをHealthとして確認可能にする。

Slice Aでは最終的整合性でよいが、
Golden Caseではworker/index processing完了を待ってからRecallする。

## 25. Telemetry

Body禁止。

Allowed:

```text
source_id
source_revision
index generation
projection mode
exclusion reason
index duration
rebuild counts
SQLite error code
quick_check/integrity result
tokenizer/projection version
```

Not allowed:

```text
source body
FTS body
query result source text
full URL query string
secret
database file upload
```

## 26. A5 Golden Cases

### Case 1 — TEXT FTS

Capture + Canonical TEXT.

Expected:
- source_index row
- source_fts row
- known phrase match

### Case 2 — Japanese Trigram

Japanese body with unique 3+ character phrase.

Expected:
- MATCH returns source_id

### Case 3 — URL

URL Source.

Expected:
- captured URL substring searchable
- no page fetch happened

### Case 4 — Text File

small UTF-8 text-like FILE.

Expected:
- original_name searchable
- body searchable

### Case 5 — Binary File

binary FILE.

Expected:
- metadata row
- filename searchable
- binary body not interpreted

### Case 6 — Duplicate Payload

same payload, two source IDs.

Expected:
- two source_index rows
- no canonical merge

### Case 7 — Tombstone

LIVE Source indexed, then manifest TOMBSTONED.

Expected:
- reconcile removes FTS/source_index
- rebuild also excludes

### Case 8 — Corrupt Canonical

payload hash mismatch.

Expected:
- not indexed
- index_exclusion / health
- no repair from old SQLite

### Case 9 — Secret Reclassification

Canonical source that now hits current Secret rule.

Expected:
- not indexed
- security event
- source body not logged

### Case 10 — Incremental Crash

Canonical+Receipt succeeds, Index update is skipped/crashes.

Expected:
- startup reconcile detects missing source
- Index converges without Canonical rewrite

### Case 11 — Delete DB / Rebuild

Delete `tsuzu.sqlite` and sidecars.

Expected:
- rebuild from Vault
- semantic source set restored
- Golden queries restored

### Case 12 — Wrong Schema

Set unsupported user_version/application identity.

Expected:
- no silent migration
- local DB discarded/rebuilt

### Case 13 — Corrupt SQLite

damage derived DB fixture.

Expected:
- health check fails
- Canonical unchanged
- fresh rebuild recovers

### Case 14 — Rebuild While New Source Commits

Candidate rebuild begins; new Source commits before swap.

Expected:
- candidate may initially omit it
- post-swap reconcile adds it
- no permanent loss

## 27. Fault injection points

Minimum:

1. before incremental transaction
2. after DELETE old FTS before INSERT
3. before incremental COMMIT
4. after incremental COMMIT before caller acknowledgment
5. during candidate schema create
6. midway canonical enumeration
7. midway candidate insert
8. before integrity_check
9. after candidate READY before swap
10. after active connections close
11. immediately after atomic swap
12. before reopen WAL
13. during post-swap reconcile

Invariant:

```text
Canonical never changes due to A5 failure.

Live Index is either:
- previous valid generation
- new valid generation
- unavailable and rebuildable

Never:
- Canonical reconstructed from SQLite
- corrupt candidate published as valid
```

## 28. A5 implementation task breakdown

### A5.1 — SQLite capability probe + DB bootstrap

Acceptance:
- FTS5/trigram verified
- WAL active DB
- trusted_schema OFF
- unsupported Runtime fails visibly

### A5.2 — Index schema + codecs

Acceptance:
- index_meta/source_index/source_fts/index_exclusion created
- application/schema generation recognized

### A5.3 — Deterministic Source Projection

Acceptance:
- TEXT / URL / text FILE / binary FILE handled without LLM
- projection hash deterministic
- no silent truncation

### A5.4 — Incremental Index Upsert

Acceptance:
- one Source update is transactional
- duplicate retry produces one row per source_id
- Canonical success independent from Index failure

### A5.5 — Startup Reconcile

Acceptance:
- missing/stale/extra/tombstoned/corrupt rows converge to Canonical

### A5.6 — Full Candidate Rebuild + Atomic Swap

Acceptance:
- live DB not destroyed before candidate validation
- integrity_check required
- WAL sidecar mixing prevented
- post-swap reconcile executes

### A5.7 — Health / Corruption Recovery

Acceptance:
- quick_check/schema mismatch detects unusable DB
- disposable DB can be removed and rebuilt

### A5.8 — Golden + Fault Tests

Acceptance:
- Cases 1–14
- fault points 1–13
- semantic rebuild equivalence passes

## 29. A5 acceptance criteria

A5 DONE条件:

1. SQLite/FTSがCanonicalではない。
2. live SQLite DBはsyncable Vault/iCloudへ置かない。
3. FTS5 + trigram capabilityを起動時に検証する。
4. 日本語3文字以上のsubstring fixtureを検索できる。
5. TEXT / URL / small text FILEをdeterministically indexできる。
6. Binary/unsupported FILEを実行・解析せずmetadata-onlyにできる。
7. same payload / different source IDsをmergeしない。
8. TOMBSTONED SourceをIndexから除外できる。
9. corrupt CanonicalをIndexへ入れず、自動修復しない。
10. current Secret Guard blockをIndexへ入れない。
11. Incremental updateがSQLite transaction単位でatomic。
12. Index update failureがCanonicalをrollbackしない。
13. startup reconcileでlost eventから回復できる。
14. DBを丸ごと削除してCanonicalから再構築できる。
15. rebuild candidateを検証前にliveへ出さない。
16. active WAL sidecarとnew candidateを混在させない。
17. semantic rebuild equivalenceを検証できる。
18. unsupported Index schemaは複雑migrationせずrebuildできる。
19. Index/FTS本文をTelemetryへ複製しない。
20. A7がsource_id / metadata / local FTSを使ってRetrievalを実装できる。

## 30. Explicit non-goals

- vector embeddings
- semantic search
- LLM-generated title/summary
- text chunking
- PDF/OCR parsing
- Office parsing
- archive extraction
- custom Japanese tokenizer
- cross-device Index sync
- cloud database
- Index as backup
- user-facing search UI
- query ranking tuning
- deletion forensic-erasure guarantee
- complex DB migrations

## 31. Gate to A6

A6へ進む条件:

```text
Canonical Vault
→ eligibility
→ deterministic projection
→ SQLite/FTS
```

がincremental/rebuild双方で同じeligible Source集合へ収束すること。

A6では、

```text
TOMBSTONE
+
Deletion Ledger
+
stale backup/restore
```

のprecedenceを追加する。

A6後のrebuild eligibilityは:

```text
A5 Canonical eligibility
AND
Deletion Ledger says not deleted
```

になる。

## 32. Final A5 one-line contract

> **TSUZUのSQLite/FTSは、Canonical Vaultから決定論的に作り直せるMacローカル専用の検索キャッシュであり、壊れたら捨て、消したら再構築し、日本語検索のためtrigram FTSを使いながら、Index側の失敗や古さをCanonicalへ逆流させない。**
