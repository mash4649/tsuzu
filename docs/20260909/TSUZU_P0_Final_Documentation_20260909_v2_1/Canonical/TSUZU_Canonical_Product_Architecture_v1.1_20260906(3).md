# TSUZU 正本｜統合プロダクト・アーキテクチャ設計書 v1.1

**Canonical Product & Architecture Baseline**  
更新日：2026-09-06  
状態：P0 Implementation Baseline / Product Proof前  
正本ルール：本書と過去Savepointが矛盾する場合は、本書を優先する。ただし本書が明示的に「未決」「Product Proof後」とした事項は確定扱いしない。

---

## 0. この版で修正した認識

TSUZUの根本方針は、途中で新たに生まれたものではない。初期構想から一貫して、**既存AI・既存入力行動を置き換えず、その裏側で働くこと**を目指していた。

初期から維持されてきた中核は以下である。

- ChatGPT / Claude / Gemini / Codex / Cursor等、普段使うAIをそのまま使う。
- Web / X / note / PDF / Apple Notes等、普段の入力元をそのまま使う。
- 保存は `Share → TSUZU → 終了` を基本とし、保存後の整理を要求しない。
- TSUZU本体を日常的に開かせない。
- `Connect once. Never summon.` をUX原則とする。
- 情報の保存先争いをせず、既存ツールを置き換えない。
- ユーザーがどこに保存したか、何タグだったか、どのAIで話したかを覚えなくてよい。

したがって、TSUZU本体に「残す」「過去から探す」等の日常操作メニューを置く案は採用しない。Explicit RecallもPassive Recallも、原則として**他AI上で発生する**。TSUZU本体は設定・接続・Privacy・データ管理・Health/Recoveryのための薄いControl Planeとする。

---

# Part I. Product Constitution

## 1. Product Thesis

TSUZUは、特定AI・特定アプリに閉じない、ユーザー所有の **Personal Experience Infrastructure** である。

単なる保存・検索・AI Memoryではなく、以下の循環を継続的に成立させる。

`CAPTURE → UNDERSTAND → RECALL → USE → CONVERSE → DECIDE → LEARN → PROMOTE → 次のRECALL`

最終的な価値は「大量に覚えていること」ではなく、**必要な過去が、必要な瞬間に、信頼できる形で今の判断へ効くこと**にある。

### North Star

> **残すだけ。必要なとき、つながる。**

### UX原則

> **Connect once. Never summon.**  
> **一度残したら、整理もしない。場所も覚えない。**

### TSUZUが解く問題

ユーザーの情報・会話・意思決定・経験は、AI、X、Web、Notes、Drive、ローカルファイル等に分散する。保存しても未来の判断で活用されず、AIを変えるたびに前提を説明し直し、過去の判断理由や結果が失われる。

TSUZUは、この「ツール間・時間間で失われる連続性」を持続的に接続する。

---

## 2. Initial ICP / JTBD

### 初期ICP

P0の主要対象は、以下の傾向を持つ個人ユーザー。

- AIを日常的に利用する。
- URL、X、Web記事、メモ、PDF等を継続的に保存する。
- 複数のテーマ・案件で比較、企画、意思決定を繰り返す。
- 過去情報を探し直す、AIへ再説明する、保存物が死蔵する問題を経験している。
- タグ、フォルダ、Atomic Note等の手動整理を増やしたくない。

一般ライトユーザーをP0の主対象にはしない。

### Core JTBD

> いま考えていることに、過去の自分の情報・判断・経験を自然に効かせたい。だが、それを整理・検索・持ち込みするための手間はかけたくない。

---

## 3. Non-goals / やらないこと

P0では以下を目的にしない。

- 新しいノートアプリを作る。
- Obsidian / Notion / Apple Notes等を置き換える。
- ChatGPT / Claude / Gemini等の代替AIを作る。
- ユーザーにFolder / Tag / Backlink管理をさせる。
- Knowledge Graph UIを主機能にする。
- Inbox Zeroを要求する。
- TSUZUアプリのDAUや滞在時間を最大化する。
- タスク管理アプリになる。
- Team / Enterprise / Remote MCPをP0へ持ち込む。
- 自動自己学習でPolicyを勝手に変更する。

---

# Part II. User Experience

## 4. Experience PlaneとControl Plane

TSUZUのUXは2つのPlaneに分離する。

### Experience Plane：ユーザーが普段いる場所

- ChatGPT
- Claude / Claude Code
- Codex
- Cursor
- Gemini
- Web / X / note / PDF
- OS Share Sheet
- Apple Notes / Markdown等の既存情報源

ここで日常価値が発生する。

### Control Plane：TSUZU本体

TSUZU本体は以下だけを担当する。

1. Connection
2. Data Sources / Import
3. Privacy / Permission
4. Storage / Backup / Export / Delete
5. Health / Recovery
6. Advanced settings

TSUZU本体は、日常利用の中心ではない。

---

## 5. Capture UX Contract

### 5.1 基本フロー

`Web / X / note / PDF / text → Share → TSUZU → 「残しました」 → 元アプリへ戻る`

Capture成功は「本文解析まで完了した」ことではなく、**TSUZUが入力を失わない状態で受領した時点**とする。

### 5.2 保存時に要求しないもの

- Folder
- Tag
- Category
- Title修正
- Importance
- Knowledge type
- Sensitivity level
- 保存理由の必須入力

### 5.3 CaptureとAcquisitionを分離

URL保存直後に本文取得できなくてもCaptureは成功とする。取得失敗はBackground Worker側で再試行し、必要に応じて別FetcherやX Rescueへ回す。

ユーザー操作が必要な永久失敗のみ通知対象とする。

### 5.4 X取得

XはP0優先Source。取得手段はAdapter内部で切り替え可能にし、CoreはAPI / Browser / Grok / HTML等の取得方式を知らない。

---

## 6. Recall UX Contract

RecallはTSUZU本体ではなく、原則他AI上で行う。

### 6.1 Explicit Recall

ユーザーは普段のAIへ自然言語で質問する。

例：

- 「前にLocal-firstについてどう決めた？」
- 「半年くらい前に保存したAIメモリのX投稿を探して」
- 「Google Driveをどう扱う方針だった？」

TSUZUはSource、Decision、会話、Knowledge等を横断検索し、AIへContextを返す。

### 6.2 Passive Recall

ユーザーがTSUZUを明示しなくても、現在の相談・判断を有意に変える過去がある場合のみContextを供給する。

Passive Recallは「関連している」だけでは発火させない。以下のどちらかを満たすことを原則とする。

- 現在の回答に必要。
- 現在の判断を変える可能性が高い。

### 6.3 Silent Context / Decision Relevant

- BACKGROUND：裏で利用。ユーザーへ明示不要。
- SUPPORTING：回答根拠として利用。必要に応じてSource Traceを示す。
- DECISION_RELEVANT：以前の決定との衝突、重要なOutcome等。ユーザーへ明示する。

### 6.4 Source Trace

TSUZU由来のContextへ強く依存した場合、元Source・元会話・元Decisionへ戻れること。AI要約のみを正本扱いしない。

---

## 7. First Aha / Cold Start

### First Aha定義

ユーザーが今回明示的に持ち込んでいない過去情報が、実際の相談中にRelevant Contextとして提示され、ユーザーが「自分では思い出していなかった／持ち込まなかった」と認識すること。

### Small Historical Bootstrap

蓄積待ちを避けるため、初期セットアップではApple Notes / Markdown等から最近の30〜100件程度を取り込めるようにする。全面移行は要求しない。

First AhaはTSUZU本体で演出せず、普段使うAI上で自然に発生させる。

---

## 8. Aha / Product Event

AHA_EVENTは以下の4条件を満たす。

1. Past：以前の情報である。
2. Unprompted：今回ユーザーが明示的に持ち込んでいない。
3. Relevant：現在の問題に関連する。
4. Impactful：理解、発想、判断のいずれかに影響した。

内部分類は以下の3段階。

- REMINDER：思い出した。
- CONNECTION：複数の過去がつながった。
- DECISION_SHIFT：判断が変わった。

TSUZUが特に狙うのはCONNECTION以上。

---

# Part III. Architecture Baseline

## 9. Architecture Principle

### Vault-first / Local-first / Adapter-based

- 正本はユーザー所有のVault。
- P0でTSUZU独自サーバーDBを正本にしない。
- iCloud Drive / Local FolderをVault候補とする。
- SQLite / FTS / Embeddingは再生成可能なLocal Index。
- AI Host、Capture Source、FetcherはAdapterとしてCoreから分離する。

Local-firstは「端末から一切出ない」という意味ではない。iCloudや外部AIを使う場合は外部送信が発生する。意味は**TSUZU独自Cloud DBを唯一の正本にしない**こと。

---

## 10. P0 Topology

```text
Capture Sources
X / Web / note / PDF / Apple Notes / text
        ↓
Capture Inbox
        ↓
Boundary Validation / Secret Guard
        ↓
Canonical Vault
        ↓
Single Mac Worker
        ↓
Derived / Candidate / Lifecycle
        ↓
Local Index / FTS
        ↓
Retrieval
        ↓
Policy / Trust / Egress Gate
        ↓
Context Compiler
        ↓
ONE AI Host
        ↓
Usage / Aha / Impact Measurement
```

Control Planeとして薄いTSUZU Settings Appを横に置く。

---

## 11. P0 Module Boundary

### P0 Required

- Capture
- Acquisition
- Canonical Source
- Secret/Sensitivity Guard
- Vault
- Single Writer Background Worker
- Derived Processing
- Knowledge Lifecycle
- Local Index / FTS
- Retrieval
- Context Compiler
- 1 AI Host Adapter
- Product Proof logging
- Integrity / Backup / Recovery
- Settings / Health Control Plane

### Interface Only

- Host Adapter Interface
- Fetcher Adapter Interface
- Capability Router Interface
- Destination-aware Context Compiler Interface

### Product Proof後

- 3 Host本格対応
- Remote MCP
- Cloud Relay
- Auto Harness / Self-learning policy
- Team
- Enterprise
- Context API / SDK
- Advanced redaction / DLP
- Multi-writer editing

---

# Part IV. Knowledge Lifecycle & Trust

## 12. Canonical / Derived

TSUZUでは、原文・ユーザー明示情報とAI解釈を混ぜない。

- Canonical：原文、ユーザー明示、確定したDecision等。
- Derived：AI要約、推論、構造化、Candidate等。

Derivedは再生成可能であり、Canonicalを書き換えない。

---

## 13. Lifecycle Contract

P0 Lifecycleは6状態に限定する。

`CAPTURED → DERIVED → CANDIDATE → ACTIVE → DEPRECATED → TOMBSTONED`

- CAPTURED：受領した原文・入力。
- DERIVED：AI抽出・要約・構造化。
- CANDIDATE：長期記憶候補。
- ACTIVE：現在有効なKnowledge。
- DEPRECATED：過去には有効だったが現在の通常判断には使わない。
- TOMBSTONED：削除済み。Recall禁止。

External Source / AI DerivedからACTIVEへの直接昇格は禁止する。

---

## 14. Provenance / Trust / Sensitivity / Temporal

Lifecycleとは別に以下を保持する。

### Provenance

- USER_EXPLICIT
- EXTERNAL_SOURCE
- AI_DERIVED
- SYSTEM_OBSERVED
- IMPORTED

### Trust

- UNTRUSTED
- INFERRED
- ASSERTED
- OBSERVED

Trustは真偽そのものではない。ASSERTEDは「ユーザーがそう述べた」、OBSERVEDは「システムが観測した」を表す。

### Sensitivity

- PUBLIC
- PERSONAL
- SENSITIVE
- RESTRICTED

### Temporal

`valid_from` / `valid_until` を任意で保持する。古い情報を現在Factとして誤利用しない。

---

## 15. Promotion / Conflict / Forget

### Promotion

AI/LLMは`propose`まで。ACTIVEへのPromotion権限を持たせない。

P0では自動Promotionを限定し、ユーザー明示Decision等の明確なケースを除きCandidateで止める。

### Conflict

新しいDecisionは古いDecisionを上書きせず、`superseded_by`で関係を持たせる。古いDecisionはDEPRECATEDとする。

### Forget

ユーザーの「忘れる」は即時TOMBSTONED。Retrieval / Search / Context Compilerから直ちに除外し、その後Physical Purgeする。

---

# Part V. Retrieval & Context Compiler

## 16. RetrievalとCompilerの責務分離

- Retrieval：関連候補を探す。
- Policy Gate：使ってよいか判定する。
- Context Compiler：今回のAI Hostへ渡す形に構成する。

`Lifecycle = Eligibility`  
`Retrieval = Relevance`  
`Compiler = Appropriateness`

---

## 17. Hard Gate → Ranking

安全性はRanking Scoreで低くするのではなくHard Gateで落とす。

Hard Gate例：

- TOMBSTONED → exclude
- RESTRICTED external egress → deny
- unknown sensitivity → external deny
- unknown destination → deny
- scope mismatch → exclude
- expired temporal knowledge → current factとしてexclude

その後にSemantic relevance、Entity/Project match、Recency、Past usefulness等でRankingする。

---

## 18. Scope / Conflict / Context Budget

Knowledgeには`scope_type / scope_id`を持つ。プロジェクト固有Decisionを別プロジェクトへ誤注入しない。

Conflictは隠さず、解消できない場合はConflict marker付きでAIへ伝える。

Contextは多いほど良いとしない。Candidateを絞り、少数の高価値Contextを供給する。

---

## 19. Context Trace

AIへ何を渡したかを本文複製なしで追跡できること。

最低限：

- context_bundle_id
- query_id
- knowledge_ids
- destination / host
- retrieval_version
- compiler_version
- policy_version
- timestamp

---

# Part VI. Security / Egress

## 20. Core Security Principle

> **Content is data, never authority.**

外部Web、X、PDF、Tool Result、MCP Result等の内容は、命令権限を持たない。Prompt Injectionを含んでもPromotion、Delete、Tool Execution等のCapabilityを発火させない。

---

## 21. Secret / Sensitive Contract

### RESTRICTED

Password、API key、access token、refresh token、session cookie、private key、recovery code等。

- Knowledge化しない。
- External AIへ絶対送信しない。
- 原則Vaultへ通常保存しない。
- Secret DetectorはDerived/LLM処理より前に実行する。

### SENSITIVE

非公開業務情報、私的情報、個人情報等。

- Vault保存可。
- Retrieval可。
- External AIへの送信はdefault deny。
- ユーザーが特定resource × destination × purposeについて明示した場合のみone-time override可能。

### PERSONAL

通常の個人Context。既知のTrusted External Hostへ送信可。Privacy設定で制限可能。

---

## 22. Egress Destination

P0内部分類：

- LOCAL
- TRUSTED_EXTERNAL
- UNKNOWN_EXTERNAL

UNKNOWN_EXTERNALはPERSONAL以上を原則deny。RESTRICTEDは全Destinationでdeny。SENSITIVEはLOCAL原則、外部は明示one-time overrideのみ。

Egress前にManifestを作成し、Knowledge IDs、Destination、Policy version、除外情報等を記録する。Telemetryへ本文を保存しない。

---

## 23. MCP / Tool / Shell Boundary

- TSUZU MemoryのContext権限とTool Execution権限を分離する。
- TSUZU Contextを得たことはShell / network / write / delete permissionを意味しない。
- Tool Resultはuntrusted by default。
- MCP接続＝Vault write permissionとはしない。

P0 Hostへ渡すTSUZU権限は原則`read / capture / propose`まで。

---

# Part VII. Vault Integrity / Multi-device / Recovery

## 24. Canonical Layers

### Layer A：Canonical / 必ず守る

- Raw Source / User Input
- Promoted Knowledge
- Decision / Outcome
- Lifecycle Event
- Tombstone / Deletion Ledger

### Layer B：再生成可能

- Derived summary
- Embedding
- Search Index

### Layer C：Runtime

- Queue
- Cache
- Worker lock
- temporary telemetry state

SQLite / FTS / EmbeddingをiCloud同期しない。

---

## 25. Single Mutable Writer

P0ではMac TSUZU Coreのみがmutable writer。

Mobile / iPhone側はcreate-only Capture。

これによりP0でCRDT、distributed lock、custom sync engine、automatic mergeを不要にする。

---

## 26. Integrity Contract

全Objectに永続ID、schema_version、created_atを持つ。更新Objectはrevision / updated_atを持つ。

- File nameをIdentityにしない。
- Atomic write：temp → validate → atomic rename。
- Worker：at-least-once + idempotent。
- Last-write-wins禁止。
- Revision mismatch時はoverwriteせずConflictとして保存。
- Exact duplicateのみ自動統合。
- Semantic duplicateは自動Merge禁止。
- Source Versionはimmutable。

---

## 27. Deletion / Restore

Tombstoneは通常状態より優先し、古いSyncやBackupから削除済みObjectを自動復活させない。

Deletion LedgerをCanonicalとして独立管理する。

Delete Cascade対象：Source → Derived → Candidate → Knowledge → Index / Embedding → Cache。

Restoreはin-place overwriteせず、Temporary Vaultへ復元し、Integrity Check、Deletion Ledger適用、Schema compatibility確認、Index rebuild、Smoke Test後に切り替える。

---

## 28. Recovery / Migration

- SQLite破損 → discard → Canonical Vaultからrebuild。
- Derived破損 → parent Sourceからregenerate。
- Canonical破損 →重大障害としてBackupから復旧。
- Schema Migration前にBackup必須。
- Readerは原則N-1 schemaを読める。
- CanonicalをAI推測で自動修復しない。

Release GateとしてRestore Test / Failure Injection Testを実施する。

---

# Part VIII. AI Conversation / Experience Loop

## 29. Conversation Chronicle

AIとの対話はTSUZUの糧になり得るが、Assistant発言単独をUser DecisionやFactに昇格させない。

- Assistant提案 → AI_DERIVED / Candidate。
- User明示承認・判断 → USER_EXPLICIT。
- 必要に応じて両者を結合しDecision Candidate化。

会話全文を無条件にPromoted Knowledgeへしない。Noise、Hallucination、Secret、Prompt Injectionを避ける。

---

## 30. Experience Model

TSUZUは単なるKnowledge Graphではなく、時間軸上のExperienceを保持する。

`State / Problem → Information → Decision / Intervention → Observed Outcome → Possible Explanation → Learning`

ただしIntervention後にOutcomeが変化したことを即座に因果関係とは扱わない。

---

# Part IX. Product Proof

## 31. 現在の事業判定

現時点は**事業GOではなくProduct Proof / TEST**。

最大の未証明点は技術ではなく、以下。

1. Pain：AIヘビーユーザーに十分な痛みがあるか。
2. Compounding：過去が蓄積するほど本当に回答・判断が良くなるか。
3. Invisible UX：TSUZUを意識せずに価値が発生するか。
4. WTP：その価値へ継続課金するか。

---

## 32. Product Proof Funnel

中心イベント：

`CAPTURED → SURFACED → USED → AHA → IMPACTED → REUSED → WOULD_PAY`

AHAは必ずしも直列必須ではないが、TSUZUのKiller Experienceを測る中心イベント。

App Opens / DAU / Session Lengthは主要KPIにしない。

### 重要指標

- Useful Recall Rate
- Noise Rate
- Context Use Rate
- Aha Connection Rate
- Decision Impact Rate
- Cross-time Reuse Rate
- WTP

---

## 33. Founder Product Proof仮Gate

初期10人程度が十分なデータ量を持った場合の仮Gate：

- 7/10：保存操作を負担と感じない。
- 6/10：Explicit Recall成功経験。
- 5/10：Passive Recallを実利用。
- 4/10：Aha Connection経験。
- 3/10：Decision Impact経験。
- 3/10：Cross-time Reuse経験。
- 3/10：月980円程度の継続意向。

数値はFounder Test後に再校正する。

### Kill / Pivot Signals

- 50〜100件蓄積しても「知っている情報が出るだけ」でAhaがない。
- Passive RecallのNoiseが高く、ユーザーの思考を邪魔する。
- Explicit Searchとして便利でもConnection / Decision Impactが発生しない。
- ImpactはあるがWTPがない。

---

# Part X. Business / Monetization Baseline

## 34. Monetization Principle

保存容量そのものではなく、**記憶が使える状態になること、AIをまたいで続くこと、将来組織で経験が育つこと**に課金する。

優先順位：

1. Personal Pro
2. Advanced AI / Connector Tier
3. Team Knowledge / Experience OS
4. Enterprise / Private / Governance
5. Context API / Agent Infrastructure

広告、ユーザーデータ販売、推薦を歪めるAffiliateをBase Caseにしない。

---

## 35. Personal → Team → Platform

P0はPersonalで閉じる。

PersonalでExperience Loopの価値が証明された後、Teamでは「社員が辞めても判断理由・Outcome・Learningが残る」価値へ拡張できる。

Context API / SDK / Remote MCP等は大きなOption Valueだが、Product Proof前には実装しない。

---

# Part XI. Settings / Control Plane

## 36. TSUZU本体の画面原則

本体は日常操作アプリではなくControl Plane。

トップはHealth Summary＋設定導線程度でよい。

例：

```text
TSUZU

● 正常に動作しています
最終処理：数分前

接続                >
データソース         >
プライバシー         >
保存とバックアップ   >
データ管理           >
詳細設定             >
```

処理待ち件数をInboxとしてユーザーへ背負わせない。通常はGreen / Yellow / Red程度のHealth表現とし、ユーザー介入が必要な場合のみ詳細を見せる。

---

## 37. Settings Scope

### Connection

AI Host、Source Connectorの接続状態。

### Privacy

内部の4段階Sensitivityをそのまま露出せず、例えば「標準」「厳格」等の簡単なPrivacy Modeで表現する。

### Data Management

Import、Export、Backup、Forget/Delete。

### Health / Recovery

Vault、Index、Backup、Connector等の状態。ただし通常ユーザーへ管理作業を要求しない。

---

# Part XII. Implementation Baseline

## 38. 推奨実装順序

1. Canonical Object Contract
2. ID / Revision / Schema
3. Atomic Writer
4. Capture Inbox
5. Secret / Sensitivity Guard
6. Single Writer Background Worker
7. Acquisition / Fetcher Adapter
8. Idempotency / Dedup
9. Canonical / Derived Processing
10. Knowledge Lifecycle / Provenance
11. Local SQLite / FTS Index
12. Deletion Ledger / Integrity Check
13. Backup / Restore
14. Retrieval
15. Context Compiler / Egress Policy
16. ONE AI Host Adapter
17. Usage / Aha / Impact Measurement
18. Thin Settings / Health Control Plane

---

## 39. Implementation Gates

正式AI Host連携前に最低限以下を満たす。

- Secret ScannerがLLM前に走る。
- RESTRICTEDをKnowledge化しない。
- SENSITIVE external egress default deny。
- Unknown sensitivity / destinationはfail closed。
- External Content / Tool Resultはuntrusted。
- AIからPromote / Delete不可。
- Atomic Write / Revision check。
- Idempotent Worker。
- Tombstone resurrection防止。
- Context Trace / Egress Manifest。
- Telemetry本文保存禁止。
- Restore Test成功。
- Failure Injection Test成功。

---

# Part XIII. Decision Ledger

## 40. 【確定】Product / UX

- TSUZUはPersonal Experience Infrastructure。
- North Starは「残すだけ。必要なとき、つながる。」
- Connect once. Never summon.
- TSUZU本体を日常的に操作させない。
- Experience Planeは他AI・既存入力経路。
- TSUZU本体はSettings / Control Plane。
- Share → TSUZU → 終了。
- 保存時の手動整理不要。
- Explicit Recall / Passive Recallは他AI上。
- First Ahaは他AI上の実相談で発生させる。
- App DAUを主要KPIにしない。

## 41. 【確定】Architecture

- Vault-first / Local-first / Adapter-based。
- Canonical Vaultが正本。
- SQLite / FTS / Embeddingは再生成可能。
- P0 Single Mutable Writer。
- Mobileはcreate-only Capture。
- Capture / Acquisition分離。
- Canonical / Derived分離。
- Lifecycle / Provenance / Trust / Sensitivity / Temporal分離。
- Retrieval / Policy / Compiler責務分離。
- Content is data, never authority.
- AIはproposeまで。Promote/Delete権限なし。
- Restore可能性を性能より優先する。

## 42. 【確定】Security / Integrity

- External → ACTIVE直接禁止。
- AI → ACTIVE直接禁止。
- RESTRICTED Knowledge化禁止。
- Secret DetectionはLLM前。
- SENSITIVE external default deny。
- Egress Manifest / Context Trace。
- Telemetry本文保存禁止。
- Tombstone即時Recall除外。
- Physical purge / Derived delete cascade。
- Deletion Ledger再適用。
- Atomic Write / Idempotency / Revision check。
- Last-write-wins禁止。
- CRDT / Custom Sync EngineはP0不要。

## 43. 【P0 Interface Only】

- Capability Router
- Multi-host Adapter abstraction
- Destination-aware Context Compiler
- Fetcher strategy abstraction

## 44. 【Product Proof後】

- 3 Host本格対応
- Remote MCP / Cloud Relay
- Automatic self-learning policy
- Team / Enterprise
- Context API / SDK
- Strict Local Mode商品化
- Multi-writer editing
- Advanced Redaction / DLP

## 45. 【やらない / P0禁止】

- TSUZU本体に日常操作Dashboardを作る。
- Folder / Tag / Graph管理をユーザーへ要求。
- Candidate件数をInboxとして管理させる。
- AIに自動Promote/Deleteさせる。
- SQLiteをiCloud同期する。
- Semantic duplicateの自動Merge。
- External ContentにTool権限を与える。
- Product Proof前に複雑なSelf-learning Harnessを動かす。

---

# Part XIV. 正本としての解釈ルール

## 46. 判断に迷ったときの優先順位

今後、新しい機能や設計判断で迷った場合は以下の順に優先する。

1. **Invisible UX**：既存行動を増やさないか。
2. **User Ownership**：ユーザーの正本・可搬性を損ねないか。
3. **Trust**：誤記憶・秘密漏洩・権限越境を起こさないか。
4. **Compounding Value**：未来のRecall / Decision / Outcomeへ効くか。
5. **Structural Simplicity**：複雑な処理追加より構造で問題を消せないか。
6. **Recoverability**：壊れても戻せるか。
7. **Product Proof**：今の最大仮説を検証するのに必要か。
8. **Future Extensibility**：上記を壊さない範囲で将来拡張できるか。

将来拡張性を理由にP0のUX・安全性・検証可能性を犠牲にしない。

---

## 47. 現在の一文定義

> **TSUZUは使うアプリではない。普段使うAIと情報保存の裏側で、ユーザー自身の経験を安全に残し、必要な瞬間に信頼できる過去をつなぎ直す、ユーザー所有のPersonal Experience Infrastructureである。**

---

## 48. 次の実行フェーズ

本書を正本として、これ以上大きなProduct Contractを増やすより、P0をIssue / Taskへ分解し、最小Vertical Sliceで実装する。

最初のVertical Sliceは以下。

`Share/Local Capture → Canonical Vault → Single Worker → Local Index → Explicit Recall via ONE AI Host → Source Trace`

このSliceでIntegrity / Secret Guard / Loggingを最初から通し、その後Passive Recall、Aha計測、Outcome/Learningを段階的に追加する。
