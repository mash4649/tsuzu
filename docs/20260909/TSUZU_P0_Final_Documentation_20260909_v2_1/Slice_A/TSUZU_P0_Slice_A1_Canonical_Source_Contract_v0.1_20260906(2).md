# TSUZU P0 Vertical Slice A1 — Canonical Source Contract v0.1

- Date: 2026-09-06
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1
- Parent Plan: P0 Vertical Slice A
- Status: Implementation Contract / Ready to implement
- Scope: A1 only. No LLM extraction, fetcher, index, host adapter, decision/discovery/outcome processing.

## 0. Decision

Slice AのCanonical Sourceは、**ユーザーがCaptureした原入力を失わず、AI解釈を混ぜず、Vault単独から検証・再構築できる永続Source Object** とする。

物理保存は `Markdown Canonical + raw payload` とし、SQLite/FTSはCanonicalに含めない。

各Captureは新しいSource Objectとして保存する。同一payloadでも自動merge/overwriteしない。`sha256` はIntegrity確認と後段の重複検知にのみ使う。

## 1. Assumptions fixed for A1

1. P0 VaultはLocal Folder / iCloud Drive配下のユーザー所有領域を想定する。
2. CanonicalはMarkdown中心を維持し、任意バイナリはraw payloadとして隣接保存する。
3. Slice AのCapture kindは `TEXT | URL | FILE` の3種のみ。
4. URLはA1ではFetchしない。元URLをSourceとして保存するだけ。
5. AI要約、タグ、Meaning、Embedding、Candidate等はCanonical Sourceへ書かない。
6. `object_id` はPath/File nameから独立したUUIDv4とする。
7. Raw payloadは作成後immutable。内容変更は新Sourceを作る。

## 2. Canonical storage layout

```text
<Vault>/
  canonical/
    sources/
      <source_id>/
        source.md
        payload/
          original
  derived/
  index/
  system/
```

`source.md` はCanonical Object Envelope + Source固有metadataを持つMarkdown manifest。
`payload/original` はCapture時の原入力を保持する。

Storage PathはIdentityではない。Identityはmanifest内の `object_id`。

## 3. Canonical Source schema

```yaml
---
object_id: "4b607ca3-4f40-4cd0-8c79-97bfda8861c3"
object_type: "SOURCE"
schema_version: "1.0.0"
created_at: "2026-09-06T07:10:00.000Z"
updated_at: "2026-09-06T07:10:00.000Z"
revision: 1

scope:
  scope_type: "GLOBAL"
  scope_id: null

provenance:
  origin: "USER_EXPLICIT"
  source_refs: []
  actor: "USER"
  explicitness: "EXPLICIT"

trust:
  level: "ASSERTED"
  confidence: 1.0

sensitivity:
  level: "PERSONAL"

temporal:
  valid_from: null
  valid_until: null

deletion:
  state: "LIVE"
  tombstoned_at: null

source:
  kind: "TEXT"
  capture_method: "LOCAL_TEXT"
  media_type: "text/plain"
  encoding: "utf-8"
  original_name: null
  origin_locator:
    type: "NONE"
    value: null
  payload_path: "payload/original"
  payload_sha256: "<sha256>"
  payload_bytes: 1234
  captured_at: "2026-09-06T07:10:00.000Z"
---
```

`source.md` 本文にはAI生成内容を置かない。Slice AではfrontmatterをCanonical manifestとして扱う。

## 4. Allowed enum values in A1

### source.kind

- `TEXT`
- `URL`
- `FILE`

### source.capture_method

- `LOCAL_TEXT`
- `LOCAL_URL`
- `LOCAL_FILE`

### provenance.origin

既存Contractを継承する。A1で主に使用するのは以下。

- `USER_EXPLICIT`
- `IMPORTED`

将来Adapterでは `EXTERNAL_SOURCE / SYSTEM_OBSERVED` 等を使えるが、A1実装のために挙動を増やさない。

### trust.level

既存Contractを継承する。

- `UNTRUSTED`
- `INFERRED`
- `ASSERTED`
- `OBSERVED`

A1の明示Captureは原則 `ASSERTED`。
ここでのconfidenceは「内容が真実である確率」ではなく、**このpayloadが当該provenanceからCaptureされたことへの確度**として扱う。

### sensitivity.level

- `PUBLIC`
- `PERSONAL`
- `SENSITIVE`
- `RESTRICTED`

A3 Secret/Sensitivity Guardで確定させる。明示指定がない通常Captureは `PERSONAL` をfloorとする。
`RESTRICTED` 判定payloadはCanonical VaultへLIVE Sourceとして保存してはならない。

### deletion.state

- `LIVE`
- `TOMBSTONED`

A1はfieldだけ実装し、実際のDeletion Ledger / invalidationはA6で閉じる。

## 5. Source kind specific contract

### TEXT

`payload/original` にCaptureされたUTF-8 textを保存する。
A1では要約・Markdown整形・改行正規化・Unicode正規化を行わない。

### URL

`payload/original` にユーザーがCaptureしたURL文字列を保存する。
HTTP/HTTPSとしてparse可能かだけ検証する。
URL canonicalization、redirect解決、page fetch、本文抽出はA1では行わない。

### FILE

`payload/original` に元File bytesをcopyする。
元FileのPathはIdentityに使わない。
`original_name` と `origin_locator` はSource Trace用metadataとして保持できるが、元Fileが移動・削除されてもCanonical Sourceは壊れない。

## 6. Immutability and revision contract

Raw payloadはimmutable。

以下の変更は同じSourceのrevision updateとして許可する。

- scope修正
- sensitivity修正
- provenance metadataの明示訂正
- deletion state変更

更新は `expected_revision` を要求し、一致時だけ `revision + 1` とする。
Last-write-winsは禁止。

Raw content自体を変えたい場合は既存Sourceを書き換えず、新しいSource Objectを作る。

## 7. Duplicate contract

同じ `payload_sha256` のSourceが既に存在しても、Captureを自動mergeしない。

```text
Capture A -> Source ID A --┐
                           ├-> same payload_sha256
Capture B -> Source ID B --┘
```

理由：

- Capture時刻が異なる
- Capture経路が異なる可能性がある
- 後に「何度も保存した」という行為がEvidenceになり得る
- Canonical mergeは不可逆な意味消失になる

重複抑制はSQLite/FTSの検索表示層または将来Derived層で行う。

## 8. Integrity contract

Canonical Sourceは最低限以下で自己検証できなければならない。

```text
manifest schema valid
AND
payload exists
AND
payload byte length matches
AND
SHA-256(payload) == payload_sha256
AND
manifest object_id == expected source identity
```

不整合があるObjectはSQLite/FTSへ投入しない。
CanonicalをSQLiteやAI推測から自動修復しない。
Health上でcorruptとして報告する。

## 9. Source Trace minimum

後段A8で、任意のRecall結果から最低限以下へ戻れることを保証する。

```text
source_id
capture_method
captured_at
source.kind
original_name (if any)
origin_locator (if any)
payload_sha256
canonical manifest path
```

Hostへ渡すContextに絶対Local Pathを含めるかはA7 Policy/Egressで判定する。

## 10. Canonical vs Derived boundary

Canonical Sourceへ入れてよいもの：

```text
raw payload
explicit user metadata
capture provenance
scope
sensitivity
integrity metadata
temporal metadata
deletion state
```

Canonical Sourceへ入れてはいけないもの：

```text
AI summary
generated title
tags
meaning
entities
embedding
importance score
similarity
pattern
decision inference
discovery
LLM confidence
```

これらはすべてDerived側。

## 11. Failure behavior

A1 loader/writerはfail closedを基本とする。

- schema invalid -> reject / no index
- payload missing -> corrupt / no index
- hash mismatch -> corrupt / no index
- unsupported schema_version -> no silent migration
- object_id mismatch -> corrupt / no index
- RESTRICTED payload -> A3でreject、LIVE Source作成禁止

## 12. A1 acceptance criteria

A1完了条件：

1. TEXT / URL / FILEの各Sourceを同じCanonical Envelopeで表現できる。
2. object_idはPathやfilenameから独立している。
3. raw payloadとmetadataのSHA-256/byte length検証ができる。
4. 同一payloadを2回Captureしても別source_idとして保存できる。
5. Raw payloadのin-place update APIが存在しない。
6. Manifestのrevision競合を検出できる契約になっている。
7. SourceにAI Derived fieldが混在しない。
8. Canonical Sourceだけから後段Indexを再構築できる情報が揃っている。
9. 原File削除後もCanonical copyは残る。
10. tamper / missing payload / invalid schemaをsilent acceptしない。

## 13. Explicit non-goals for A1

- URL本文取得
- X取得
- PDF/OCR解析
- MIME content extraction
- LLM extraction
- title/tag生成
- Embedding
- FTS
- Tombstone propagation
- Backup/Restore
- MCP
- Claude Code接続

これらをA1に持ち込まない。

## 14. Implementation task breakdown

### A1.1 — Schema

Canonical Object Envelopeを継承するSource schemaとenumを定義する。

Acceptance: malformed objectをvalidatorがrejectできる。

### A1.2 — Source codec

`source.md` frontmatterのserialize/parseを1系統に固定する。

Acceptance: serialize -> parseでsemantic equalityが成立する。

### A1.3 — Payload integrity

SHA-256 / byte length計算とvalidationを実装する。

Acceptance: 1 byte改変でもcorruptを検出する。

### A1.4 — Golden fixtures

TEXT / URL / FILE / duplicate / corruptのfixtureを用意する。

Acceptance: 後続A2-A10が同じfixtureを再利用できる。

## 15. Gate to A2

A2 Atomic Vault Writerへ進む条件は、A1.1〜A1.4のContractに実装上の解釈余地が残っていないこと。

A2ではこのSource Objectを、`stage -> validate -> fsync/write -> atomic commit` で壊さず保存する方法だけを扱う。Schema自体をA2で再設計しない。
