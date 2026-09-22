# TSUZU P0 Vertical Slice A7 — Retrieval + Minimal Policy / Egress Gate Contract v0.1

- Date: 2026-09-06
- Base: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1
- Parent Plan: P0 Vertical Slice A
- Depends on:
  - A1 Canonical Source Contract v0.1
  - A3 Local Capture Ingress + Secret Guard Contract v0.1
  - A5 SQLite / FTS Derived Index + Rebuild Contract v0.1
  - A6 Minimal Tombstone / Deletion Ledger Contract v0.1
- Status: Implementation Contract / Ready to implement
- Scope: A7 only. Explicit keyword recall, safe FTS query building, candidate revalidation, scope filtering, destination resolution, sensitivity/secret/deletion policy, internal approved-candidate output and body-free policy decision metadata.
- Non-scope: Context bundle formatting, Source Trace presentation, MCP protocol implementation, passive recall, embeddings, LLM query expansion, semantic retrieval, one-time SENSITIVE override UI.

## 0. Decision

Slice AのRetrievalは、SQLite/FTSの検索結果をそのままHostへ返さない。

必ず以下を通す。

```text
Retrieval Request
    ↓
Request Validation
    ↓
Destination Registry Resolution
    ↓
Scope Grant Resolution
    ↓
Safe Local FTS / LIKE Candidate Search
    ↓
Canonical Source Revalidation
    ↓
Deletion Resolver
    ↓
Current Secret Guard
    ↓
Sensitivity Policy
    ↓
Scope Policy
    ↓
Destination / Capability Policy
    ↓
APPROVED internal candidates
    ↓
A8 Context Bundle
    ↓
A9 Claude Code MCP
```

**SQLiteはCandidate Generatorであり、Authorization Sourceではない。**

最終EligibilityはCanonical Source + Deletion Ledger + current policyから毎回決定する。

## 1. Assumptions fixed for A7

1. Slice AはExplicit Recallのみ。Passive Recallはしない。
2. 最初のHostはClaude Code。
3. Claude Code MCP serverがlocal stdioであっても、Claudeへ返したSource本文はExternal AIへ渡るため、Destinationは`TRUSTED_EXTERNAL`として扱う。
4. `TRUSTED_EXTERNAL`は「既知・明示接続された外部Destination」を意味し、「秘密情報を送ってよい」「保持/学習されない」を意味しない。
5. P0ではSENSITIVEのone-time external overrideを実装しない。
6. RESTRICTEDはDestinationを問わずKnowledge Recall禁止。
7. Indexはstale/corruptであり得るため、security decisionをIndex metadataだけで行わない。
8. A7はLLMを使ってquery expansion / rerank / classificationしない。
9. A8はA7がAPPROVEDした候補だけを使い、独自にCanonical payloadを再取得してPolicyを迂回しない。

## 2. Destination classes

v1.2.1のDestination Classを維持する。

```text
LOCAL
TRUSTED_EXTERNAL
UNKNOWN_EXTERNAL
```

### LOCAL

Source本文が外部AI/外部serviceへ出ない、TSUZU local process内のDestination。

例:

```text
local diagnostic/test adapter
future local-only CLI recall
```

### TRUSTED_EXTERNAL

Destination identityがTSUZU local configurationで明示登録され、ユーザーが接続した外部AI/外部service。

Slice A:

```text
claude_code
→ TRUSTED_EXTERNAL
→ capability: RECALL
```

### UNKNOWN_EXTERNAL

- Registryに存在しないdestination_id
- destination classが不明
- adapter identityが検証できない
- runtimeがclassificationを解決できない

すべてfail closed。

## 3. Why Claude Code is External

Claude Codeはlocal stdio MCP serverへ接続できるが、MCP tool resultをClaudeが読む用途で利用する以上、TSUZUは返却本文をexternal model contextへのegressとして扱う。

`local MCP transport == LOCAL destination` とは解釈しない。

Destination classificationはtransport locationではなく、**最終的にSource contentを処理する主体**で決める。

## 4. Destination Registry

Destination classをMCP tool argumentやSource本文から決めない。

P0 local Control Plane config:

```yaml
destinations:
  local_test:
    class: LOCAL
    capabilities:
      - RECALL

  claude_code:
    class: TRUSTED_EXTERNAL
    capabilities:
      - RECALL
```

最低属性:

```yaml
destination_id:
class:
capabilities: []
policy_profile_version:
enabled:
```

### Invariant

callerが

```text
destination_class=LOCAL
```

と自己申告してPolicyを下げるAPIを作らない。

Adapterは`destination_id`のみを提示し、classはlocal registryが解決する。

## 5. Vendor privacy settings are not an authorization boundary

Consumer/Commercial plan、training opt-in、retention設定等は変化し得る。

したがってP0では、外部AIの現在のprivacy optionを見てSENSITIVE送信を自動ALLOWする設計にしない。

```text
known vendor
≠
LOCAL
≠
SENSITIVE egress allowed
```

将来Enterprise/ZDR等を扱う場合も別Policy Profileとして明示設計する。

## 6. Retrieval Request contract

A7 Core interface:

```yaml
retrieval_request:
  request_id:
  query:

  adapter_context:
    destination_id:
    capability: RECALL

    granted_scope:
      scope_type: GLOBAL | PROJECT
      scope_id:

  requested_scope: null | {
    scope_type: GLOBAL | PROJECT
    scope_id:
  }

  limits:
    max_results: 10
```

### request_id

UUIDv4。Telemetry/Trace correlation用。

### query

keyword / phrase retrieval用の文字列。

A7では「自然文から最適検索語をAIで作る」処理はしない。
Claude Code/A9がtool call時に検索語を渡せる。

### destination_id

A9 adapter identityから設定。
Model/userが任意のdestination classを指定できない。

### capability

Slice Aは`RECALL`のみ。

### granted_scope

Host Adapter / local configが解決した最大Scope。

### requested_scope

呼出側がさらに狭めることはできるが、granted_scopeを広げられない。

## 7. Query validation

P0 default:

```text
UTF-8
trimmed non-empty
max UTF-8 bytes: 4096
max logical terms: 16
```

Reject:

```text
empty
invalid UTF-8
oversize
NUL/control abuse that parser cannot safely handle
```

Raw queryをTelemetryへ保存しない。

## 8. Safe FTS query builder

User/Host queryをそのままFTS5 MATCH grammarへ流さない。

FTS5にはAND/OR/NOT/NEAR/column filter等の独自syntaxがあるため、A7は**検索語をdataとしてquoteする**。

### 8.1 Term split

P0:

- Unicode whitespaceで分割
- empty term除去
- 最大16 term
- term内部の文字は原則保持

Host側には1〜数個のkeyword/phraseを渡すようtool descriptionで誘導する。

### 8.2 FTS-safe string

3 Unicode codepoint以上のtermは:

```text
"term"
```

としてFTS string化。

term内の`"`はFTS5 ruleに従い`""`へescape。

SQL自体は必ずparameter binding。

```sql
... WHERE source_fts MATCH ?
```

SQL string concatenationへuser queryを埋め込まない。

### 8.3 Primary retrieval

複数keyword:

```text
"term1" AND "term2"
```

を第一passとする。

0件の場合のみ:

```text
"term1" OR "term2"
```

へbounded fallback可能。

目的は高度なsearch engineではなくSlice A exact/keyword recall。

## 9. Short query fallback

A5 trigramは3 Unicode文字未満のsubstring MATCHを保証しない。

Queryに3文字未満termが含まれる場合はbounded LIKE pathを使用できる。

### LIKE safety

- SQL parameter binding必須
- `%` / `_` / escape charをliteral扱いするescaping
- `ESCAPE`を明示
- LIMIT必須

P0 data量ではperformanceよりcorrectness/securityを優先する。

独自Japanese tokenizerは追加しない。

## 10. Candidate pool

P0 defaults:

```text
INDEX_CANDIDATE_LIMIT = 50
FINAL_APPROVED_LIMIT = min(request.max_results, 10)
```

Index queryは50件で止める。

Policy denyされた候補があれば次候補を評価し、最大10件のAPPROVEDまで進める。

無制限scanをしない。

## 11. Index ranking

A7 P0は高度なranking tuningをしない。

Primary FTS result:

```text
ORDER BY rank ASC
```

同score tie-break:

```text
captured_at DESC
source_id ASC
```

FTS5の`rank`は既定でbm25相当を利用できる。

Recency boost、personal importance、embedding similarity、Aha score等は入れない。

## 12. Index prefilter is optimization only

SQLite metadataで以下をpre-filterしてよい。

```text
scope
sensitivity
projection_mode
deletion state
```

ただしIndex metadataはAuthorization Evidenceにならない。

例:

```text
Index says PERSONAL
Canonical says SENSITIVE
→ Canonical SENSITIVEが勝つ
```

```text
Index says LIVE
Deletion Ledger says DELETED
→ DELETEDが勝つ
```

## 13. Canonical candidate revalidation

FTS candidateごとに必ずA1 Sourceを読み直す。

最低条件:

```text
Source exists
A1 schema valid
object_type == SOURCE
object_id == candidate source_id
payload exists when required
payload bytes/hash valid
schema_version supported
```

失敗:

```text
DROP candidate
Health event
no egress
```

SQLite本文からCanonical payloadを復元してはいけない。

## 14. Deletion Gate

A6 `DeletionResolver`を必ず利用。

```text
NOT_DELETED
→ continue

DELETED
→ DENY

UNKNOWN_FAIL_CLOSED
→ DENY
```

Source manifestだけ、SQLite deletion flagだけで判定しない。

### In-flight semantics

P0ではPolicy decisionはrequest snapshotとして扱う。

Deletion Ledger commitより**後に開始した新規Retrieval**は必ずdeny。

すでにfinal egress authorization済みでserialization中のrequestを途中cancelするdistributed revocationまではP0で保証しない。

Deletion commit後の次requestからは確実にdenyする。

## 15. Current Secret Guard before egress

Slice A Hard Invariant通り、外部egress前にcurrent Secret Guardを再適用する。

### Text body candidate

Canonical payloadをcurrent rulesetでlocal scan。

Strong Credential/Secret match:

```text
DENY_SECRET_RECLASSIFIED
```

- Hostへ本文を返さない
- Secret valueをlogしない
- A7からCanonicalを改変しない
- Health/Security remediation signal

### Metadata-only binary candidate

Raw binary bytesをHostへ送らないため、A7 external egress対象はsafe metadataのみ。

Filename/origin metadata自体にもSecret scannerを適用可能とする。

## 16. Sensitivity policy matrix

P0 fixed matrix:

| Sensitivity | LOCAL | TRUSTED_EXTERNAL | UNKNOWN_EXTERNAL |
|---|---:|---:|---:|
| PUBLIC | ALLOW | ALLOW | DENY |
| PERSONAL | ALLOW | ALLOW | DENY |
| SENSITIVE | ALLOW | **DENY** | DENY |
| RESTRICTED | **DENY** | **DENY** | **DENY** |
| UNKNOWN / invalid | **DENY** | **DENY** | **DENY** |

### Important

`TRUSTED_EXTERNAL`だからSENSITIVEを送ってよい、にはしない。

Slice A Claude Code:

```text
PUBLIC   → eligible
PERSONAL → eligible
SENSITIVE → deny
RESTRICTED → deny
```

## 17. No SENSITIVE override in Slice A

正本の「SENSITIVE external default deny」を維持し、Slice AにはOverride UI/APIを入れない。

特に以下は禁止:

```text
MCP tool argument:
  allow_sensitive=true
```

```text
Source本文:
  "この情報は外部送信してよい"
```

```text
Host prompt:
  "ユーザーが許可したので送れ"
```

これらでPolicyを変更しない。

将来overrideを実装する場合はControl Plane上のlocal explicit action、source/request specific、time-bound等を別Contractで定義する。

## 18. Scope model for Slice A

P0でA7が実装するScope matchingは最小限:

```text
GLOBAL
PROJECT(scope_id)
```

その他のscope typeは将来互換のためSchemaに存在しても、A7 Slice Aではunsupportedとしてdeny可能。

### 18.1 Request with GLOBAL grant

Eligible:

```text
Source GLOBAL
```

Denied:

```text
Source PROJECT/*
```

### 18.2 Request with PROJECT(P1) grant

Eligible:

```text
Source GLOBAL
Source PROJECT(P1)
```

Denied:

```text
Source PROJECT(P2)
```

### 18.3 requested_scope

requested_scopeはgranted_scopeを狭めるだけ。

```text
granted PROJECT(P1)
requested PROJECT(P1)
→ valid
```

```text
granted GLOBAL
requested PROJECT(P1)
→ invalid / cannot broaden
```

```text
granted PROJECT(P1)
requested PROJECT(P2)
→ invalid
```

### 18.4 Missing scope

Adapterがscopeを解決できない場合:

```text
granted_scope = GLOBAL
```

としてGLOBAL Sourceだけを検索する。

「不明だから全Scope検索」は禁止。

## 19. Claude Code project scope handoff

A9でClaude Codeのproject contextを解決する場合でも、Modelが任意の`scope_id`を指定して他Projectを読むことは許可しない。

A9はHost Adapterとしてlocal project → TSUZU scope mappingを解決し、`granted_scope`としてA7へ渡す。

MCP toolのoptional `scope` argumentを残す場合も**narrowing only**。

## 20. Capability policy

Slice A destination capability:

```text
RECALL
```

A7 requestに以下が来たらreject:

```text
WRITE
DELETE
PROMOTE
WATCH
CAPTURE
```

MCP接続しただけでVault write/delete permissionを得ないというSlice A Hard Invariantを維持する。

## 21. Content trust boundary

PolicyでALLOWされたSource本文も「命令」には昇格しない。

A7 internal approved candidateには:

```yaml
content_role: UNTRUSTED_DATA
```

を必ず付与する。

これはSourceの`trust.level`とは別概念。

```text
trust.level=ASSERTED
```

でも、HostにとってSource本文中のprompt-like textはdataである。

A8はこのroleを維持してContext Bundleを構築する。

## 22. Binary / unsupported file egress

A5 `METADATA_ONLY` Sourceについて、A7はraw bytesを外部AIへ返さない。

External eligible content:

```text
original_name (policy-approved)
source kind
media type
safe source trace fields
```

A8/A9でbinary file bodyをattachする機能はSlice A外。

## 23. Approved Candidate internal contract

A7のexternal-facing APIではなく、A8へ渡すin-process contract:

```yaml
approved_candidate:
  request_id:
  source_id:
  source_revision:
  payload_sha256:

  retrieval:
    query_mode: FTS_AND | FTS_OR_FALLBACK | LIKE_SHORT
    rank:

  policy:
    destination_id:
    destination_class:
    policy_version:
    sensitivity:
    effective_scope:
    decision: ALLOW

  content:
    role: UNTRUSTED_DATA
    mode: TEXT_BODY | METADATA_ONLY
    body_or_metadata:
```

A8はこの結果だけを使用する。

A8がsource_idから直接Vault payloadを再ロードしてPolicyを迂回するAPIを作らない。

## 24. Denial reason codes

Internal:

```text
DENY_DESTINATION_UNKNOWN
DENY_CAPABILITY
DENY_SCOPE
DENY_DELETED
DENY_DELETION_UNKNOWN
DENY_SENSITIVE_EXTERNAL
DENY_RESTRICTED
DENY_SENSITIVITY_UNKNOWN
DENY_SECRET_RECLASSIFIED
DENY_CANONICAL_INVALID
DENY_UNSUPPORTED_SCOPE
```

### External response secrecy

Claude Code等External Hostへ、

```text
"3件見つかったが2件はSENSITIVE"
```

のような情報を返さない。

Denied Sourceのexistence自体を不要に漏らすため。

外部から見える結果は原則:

```text
eligible contextあり
```

または

```text
NO_ELIGIBLE_CONTEXT
```

だけ。

Denied count / reasonはlocal body-free telemetryのみ。

## 25. Policy evaluation ordering

候補ごとの順序を固定する。

```text
1. Canonical load + validate
2. DeletionResolver
3. Source scope validate
4. Destination registry/capability validate
5. Sensitivity validate
6. Current Secret Guard
7. Content mode validate
8. ALLOW
```

Performance prefilterはこれ以前に入れてよいが、最終decision orderは省略しない。

## 26. Policy versioning

A7 Policyはversioned。

```text
policy_version = "a7-p0-1"
```

最低限version対象:

- destination matrix
- sensitivity matrix
- scope rules
- secret ruleset version
- query builder generation

後からPolicyが変わっても、どのruleでegressしたか追跡できるようにする。

## 27. Policy Decision Manifest

A7はbody-free decision metadataを生成し、A8へ渡す。

```yaml
policy_manifest:
  request_id:
  policy_version:
  destination_id:
  destination_class:
  capability:
  evaluated_at:

  query:
    mode:
    byte_length:
    term_count:

  approved:
    - source_id:
      source_revision:
      sensitivity:
      scope_type:
      scope_id:

  denied_summary:
    total_count:
    reason_counts:
```

Raw query / Source body / Secretは含めない。

A8でfinal Context Bundleが確定した後、これをEgress Manifest / Context Traceへ接続する。

## 28. Telemetry contract

Allowed:

```text
request_id
destination_id
destination_class
policy_version
query byte length
query mode
term count
candidate count
approved source IDs
denial reason counts
latency
scope type/id where safe locally
```

Not allowed:

```text
raw query
source body
FTS snippet
full URL query string
secret value
binary bytes
SENSITIVE body
```

## 29. Retrieval output size / DoS boundary

A7はunbounded body accumulationをしない。

P0:

```text
candidate pool <= 50
approved candidates <= 10
```

A5でBODY projection対象にならないoversize/binary payloadはMETADATA_ONLY。

A7はapproved bodyをA8へ渡すが、A8がContext excerpt/minimizationを行う。

A8がfull bodyを無条件external送信することは認めない。

## 30. Failure behavior

### Index unavailable

```text
RETRIEVAL_INDEX_UNAVAILABLE
```

Canonicalを全件scanして代替検索するfallbackはSlice Aでは作らない。

理由:

- 故障経路が増える
- Policy/性能挙動が二重化する

A5 rebuild/reconcileを行う。

### Destination unavailable/unknown

fail closed。

### Deletion Ledger unavailable

A6通りfail closed。

### Canonical invalid

candidate drop + Health。

### Secret Scanner unavailable

External egressはfail closed。

LOCAL retrievalもRESTRICTED prohibitionを守れない場合はfail closedを基本とする。

## 31. A7 Golden Policy Matrix

### Matrix A — Sensitivity × Destination

| Fixture | LOCAL | Claude Code / TRUSTED_EXTERNAL | UNKNOWN_EXTERNAL |
|---|---:|---:|---:|
| PUBLIC | ALLOW | ALLOW | DENY |
| PERSONAL | ALLOW | ALLOW | DENY |
| SENSITIVE | ALLOW | DENY | DENY |
| RESTRICTED | DENY | DENY | DENY |
| invalid/unknown | DENY | DENY | DENY |

全cellをtestする。

## 32. A7 Golden Cases

### Case 1 — Personal → Claude Code

PERSONAL + LIVE + GLOBAL + clean.

Expected:
- APPROVED

### Case 2 — Sensitive → Claude Code

Expected:
- denied internally `DENY_SENSITIVE_EXTERNAL`
- external result does not reveal sensitive candidate existence

### Case 3 — Restricted

Expected:
- denied for LOCAL and EXTERNAL

### Case 4 — Unknown Destination

Expected:
- all candidates denied
- no fallback to TRUSTED_EXTERNAL

### Case 5 — Deleted Stale FTS Candidate

FTS row intentionally left stale after delete.

Expected:
- candidate found by Index
- A6 DeletionResolver denies
- no body egress

### Case 6 — Deletion Ledger Unavailable

Expected:
- fail closed
- no candidate egress

### Case 7 — Canonical Sensitivity Changed After Index

Index says PERSONAL, Canonical says SENSITIVE.

Expected:
- Claude deny

### Case 8 — Secret Rule Upgrade

Index contains Source; current scanner newly detects Credential.

Expected:
- deny
- secret body absent from telemetry

### Case 9 — Scope Global

GLOBAL grant.

Expected:
- GLOBAL eligible
- PROJECT denied

### Case 10 — Project Scope

PROJECT(P1) grant.

Expected:
- GLOBAL + PROJECT(P1) eligible
- PROJECT(P2) denied

### Case 11 — Scope Broadening Attempt

Host requests P2 while granted P1.

Expected:
- invalid scope / no P2 access

### Case 12 — FTS Syntax Injection

Query contains:

```text
OR NOT NEAR() " : *
```

Expected:
- treated as quoted data / safely rejected as invalid term
- never changes SQL structure
- no SQL/FTS grammar privilege escalation

### Case 13 — Japanese Exact Keyword

Query:

```text
面接設定率
```

Expected:
- FTS5 trigram result
- approved if policy passes

### Case 14 — Short Japanese Query

Query:

```text
広告
```

Expected:
- bounded LIKE path
- parameterized/escaped

### Case 15 — Denied Existence Non-disclosure

Only matching Source is SENSITIVE.

Expected external:

```text
NO_ELIGIBLE_CONTEXT
```

not:

```text
SENSITIVE source found but blocked
```

### Case 16 — Binary Metadata-only

Binary Source filename matches.

Expected:
- raw bytes never returned
- safe metadata only if policy allows

### Case 17 — Index/Canonical ID mismatch

Expected:
- candidate dropped
- Health event

### Case 18 — Secret Scanner Failure

Expected:
- no Claude egress
- fail closed

## 33. Fault / adversarial test points

Minimum:

1. malformed retrieval request
2. oversize query
3. raw FTS operators/punctuation
4. SQL wildcard/control query
5. destination registry lookup failure
6. destination disabled between calls
7. FTS result with missing Canonical
8. FTS result with hash-corrupt Canonical
9. deletion after Index result
10. stale sensitivity in Index
11. Secret Scanner unavailable
12. scope mapping missing
13. cross-project scope request
14. policy manifest write/forward failure
15. all candidates denied
16. candidate limit exhaustion

Invariant:

```text
No failure path may convert UNKNOWN into ALLOW.
```

## 34. A7 implementation task breakdown

### A7.1 — RetrievalRequest validator + limits

Acceptance:
- malformed/oversize query reject
- max result bounds enforced
- raw query not logged

### A7.2 — Safe FTS / LIKE Query Builder

Acceptance:
- parameterized SQL
- FTS terms quoted/escaped
- Japanese trigram path
- short query bounded fallback
- adversarial syntax tests

### A7.3 — Destination Registry + resolver

Acceptance:
- Claude Code = TRUSTED_EXTERNAL
- caller cannot self-declare LOCAL
- unknown disabled destination fails closed

### A7.4 — Scope Grant Resolver

Acceptance:
- GLOBAL / PROJECT exact matching
- requested scope can narrow only
- cross-project denied

### A7.5 — Canonical + Deletion revalidation

Acceptance:
- stale Index cannot bypass A1/A6
- invalid/deleted/unknown deletion candidate denied

### A7.6 — Sensitivity + Secret Egress Policy

Acceptance:
- full policy matrix passes
- SENSITIVE Claude deny
- RESTRICTED all deny
- current secret scan before egress

### A7.7 — ApprovedCandidate + Policy Manifest

Acceptance:
- approved content marked UNTRUSTED_DATA
- body-free decision metadata
- denied existence not exposed externally

### A7.8 — Golden / adversarial tests

Acceptance:
- Policy matrix all cells
- Cases 1–18
- fault/adversarial points 1–16

## 35. A7 acceptance criteria

A7 DONE条件:

1. User/Host queryをSQL/FTS grammarへraw注入しない。
2. Japanese 3+ char keywordをtrigram FTSで検索できる。
3. short keywordをbounded safe fallbackで検索できる。
4. IndexはCandidate Generatorに限定し、Authorization Sourceにしない。
5. CandidateごとにCanonicalを再検証する。
6. A6 DeletionResolverを最終Gateとして使う。
7. stale FTS rowからdeleted Sourceを返さない。
8. current Secret Guardをegress前に再適用する。
9. PUBLIC/PERSONALはClaude CodeへALLOW可能。
10. SENSITIVEはClaude Codeへdefault DENY。
11. RESTRICTEDはLOCALを含めRecall禁止。
12. unknown sensitivityはDENY。
13. unknown destinationは全DENY。
14. Claude CodeをLOCAL扱いしない。
15. destination classをcaller/modelが自己申告できない。
16. GLOBAL / PROJECT scopeを越境しない。
17. Model-supplied scopeはgranted scopeを広げられない。
18. MCP接続からwrite/delete/promote capabilityを得ない。
19. Allowed contentもUNTRUSTED_DATAとして扱う。
20. binary raw bytesをSlice A Claudeへ送らない。
21. denied Source existence / sensitivityを外部responseへ漏らさない。
22. raw query / Source body / SecretをTelemetryへ保存しない。
23. A8へAPPROVED Candidateとbody-free policy metadataを渡せる。
24. No failure path converts UNKNOWN to ALLOW.

## 36. Explicit non-goals

- embeddings / vector search
- LLM query rewriting
- LLM reranking
- semantic similarity
- personal importance ranking
- recency tuning
- passive recall
- Source auto-summary
- SENSITIVE one-time override
- vendor plan auto-detection
- ZDR/Enterprise privacy profile automation
- remote policy service
- multi-user ACL
- Team workspace permission model
- binary file attachment to Host
- Source instruction/prompt execution

## 37. Gate to A8

A8へ進む条件:

```text
query
→ Index candidates
→ Canonical validation
→ Deletion
→ Scope
→ Destination
→ Sensitivity
→ Secret Guard
→ APPROVED candidates
```

までが、stale Index / cross-scope / unknown destination / secret reclassificationを含めfail closedで成立すること。

A8は以下だけを行う。

```text
APPROVED candidates
→ minimum excerpts/context
→ safe Source Trace metadata
→ Context Bundle
→ Egress Manifest / Context Trace
```

A8がPolicyを再解釈したり、denied Sourceを直接Vaultから読み出したりしない。

## 38. Final A7 one-line contract

> **TSUZUのRetrievalはSQLiteを検索候補生成にだけ使い、外部AIへ出す直前にCanonical・Deletion Ledger・Scope・Destination・Sensitivity・Secretを再検証し、既知のClaude CodeであってもPERSONALまでしか既定許可せず、UNKNOWNを一度もALLOWへ倒さない。**
