# TSUZU 正本 v1.2.1 Closing Addendum
## Implementation Contract Closure

- Version: v1.2.1 Closing Addendum
- Date: 2026-09-06
- Base: TSUZU 正本 v1.1 + v1.2 Addendum
- Status: P0 Implementation Contract / Closed
- Precedence:
  1. 本書 v1.2.1
  2. v1.2 Addendum
  3. v1.1 Canonical Product & Architecture Baseline
  4. それ以前のSavepoint
- Purpose: v1.1 / v1.2横断監査で残った、実装時に解釈が割れるContractだけを閉じる。新しいProduct Scopeは追加しない。

---

# 0. 結論

v1.1 / v1.2のProduct Constitutionは維持する。

今回のClosing Addendumでは、以下を確定する。

1. Canonical Object Envelope
2. Lifecycle / Promotion / Deletion Stateの責務分離
3. Decision Assertion / Decision Evidence / Reconciliation Contract
4. Experience Trace / Action / Outcome / Learning Contract
5. Dependency-aware Delete / Invalidation / Recompute
6. Observation Permission / Credential / Local Security Contract
7. Product Proof Measurement Contract
8. P0 Host Scope / Target Connector Roadmap

これにより、v1.1 / v1.2間に残っていた状態管理・削除・Evidence・Outcome・Security・計測・P0範囲の曖昧さを閉じる。

本書以降、P0実装前に新たな大規模Product Contractを追加しない。
次のフェーズはIssue / Task分解とVertical Slice実装とする。

---

# 1. Canonical Object Envelope

## 1.1 原則

v1.2で追加されたExperience Candidate / Decision Case / Pattern Candidate / Discovery Candidate等は、個別Schemaだけで完結しない。

TSUZU内で永続化または追跡対象となる全Objectは、共通Envelopeを継承する。

これにより、Scope / Provenance / Sensitivity / Temporal / Revision等の既存Contractが、新規Object追加のたびに抜け落ちることを防ぐ。

## 1.2 共通必須属性

最低限、以下を共通属性とする。

```yaml
object_id:
object_type:
schema_version:
created_at:
updated_at:
revision:

scope:
  scope_type:
  scope_id:

provenance:
  origin:
  source_refs: []
  actor:
  explicitness:

trust:
  level:
  confidence:

sensitivity:
  level:

temporal:
  valid_from:
  valid_until:

deletion:
  state:
  tombstoned_at:
```

### object_id
永続ID。File nameやPathをIdentityにしない。

### object_type
Source / Episode / Candidate / DecisionCase / DecisionAssertion / Evidence / Pattern / Discovery / ExperienceTrace等。

### revision
mutable objectの競合検知に使う。Last-write-winsは禁止。

### scope
Project / Topic / Person / Global等の適用範囲。

### provenance
どこから来た情報かを追跡する。

### trust
真偽ではなく、Evidenceと推論強度を追跡する。

### sensitivity
v1.1のPUBLIC / PERSONAL / SENSITIVE / RESTRICTEDを継承する。

### temporal
古い判断や条件依存Knowledgeを現在Factとして誤利用しないために使う。

## 1.3 Optionalではなく継承

個別Schemaに同フィールドを毎回重複記載しなくてよい。
ただし、**全永続ObjectがCanonical Object Envelopeを継承すること自体は必須**とする。

---

# 2. Lifecycle / Promotion / Deletion State Contract

## 2.1 二重Lifecycleを廃止する

v1.1の

`CAPTURED → DERIVED → CANDIDATE → ACTIVE → DEPRECATED → TOMBSTONED`

と、v1.2の

`CANDIDATE → WORKING → PROMOTED → SUPERSEDED → REJECTED`

は、1本のState Machineとして統合しない。

責務が異なるため、以下の3軸へ分離する。

---

## 2.2 Processing State

データ処理段階を表す。

- `CAPTURED`
- `DERIVED`

必要に応じてRuntime上でPROCESSING / FAILED等を持ってよいが、Canonical Knowledge状態とは分離する。

---

## 2.3 Promotion State

「ユーザーの現在のKnowledgeとしてどこまで積極利用できるか」を表す。

- `CANDIDATE`
- `WORKING`
- `PROMOTED`
- `SUPERSEDED`
- `REJECTED`

### CANDIDATE
AI抽出・推論段階。強いRecall根拠にしない。

### WORKING
一定のEvidenceがあるが、条件依存・仮説性・未確定性が残る。

### PROMOTED
明示または十分なEvidenceがあり、通常Recall / Discoveryへ積極利用可能。

### SUPERSEDED
後続Decision / Knowledgeに置き換えられた。削除しない。Judgment Evolutionへ利用可能。

### REJECTED
誤抽出、ユーザー訂正、明示棄却等。通常Recallへ利用しない。

---

## 2.4 Deletion State

DeletionはPromotionとは独立させる。

- `LIVE`
- `TOMBSTONED`

`TOMBSTONED`は全状態より優先する。

TOMBSTONED Objectは、

- Retrieval禁止
- Context Compiler利用禁止
- Discovery Evidence利用禁止
- Pattern形成利用禁止
- 新規Promotion根拠利用禁止

とする。

---

## 2.5 ACTIVE / DEPRECATEDの扱い

v1.1の概念は以下へ読み替える。

- `ACTIVE` ≒ `PROMOTED + LIVE`
- `DEPRECATED` ≒ `SUPERSEDED + LIVE`

以後、新規実装ではACTIVE / DEPRECATEDを独立Stateとして増やさない。

---

# 3. Decision Model Contract

## 3.1 Decision CaseとDecision Assertionを分離する

1つのDecision Caseに単一の`assessment_status`だけを持たせる設計は採用しない。

理由は、以下が同時に成立し得るため。

- ユーザーはAと言った
- 実際にはBを実行した
- 後からCに変更した

これを1つの状態へ潰すとPersonal Discoveryの重要なEvidenceが失われる。

---

## 3.2 Decision Case

Decision Caseは「判断対象そのもの」を表す。

```yaml
decision_case_id:
problem:
stage:
desired_outcome:
options: []
constraints: []
tradeoffs: []
uncertainties: []
assertion_refs: []
evidence_refs: []
current_assessment:
supersedes:
superseded_by:
```

---

## 3.3 Decision Assertion

Decision Caseには複数Assertionを保持できる。

```yaml
assertion_id:
decision_case_id:
assertion_type:
option_or_statement:
actor:
explicitness:
confidence:
source_refs: []
observed_at:
promotion_state:
```

### assertion_type

- `STATED`
- `REVEALED`
- `REVISED`
- `SUPERSEDED`

### STATED
ユーザーが明示的に述べた判断。

### REVEALED
行動・成果物・後続処理等から観測された判断。

### REVISED
後から明示的または十分なEvidenceで変更された。

### SUPERSEDED
現在判断としては置き換えられた。

---

## 3.4 Stated ≠ Revealed

STATEDとREVEALEDは統合して消さない。

例:

```text
STATED:
「まず検証してから作る」

REVEALED:
直近4案件で、検証前に実装を開始

Reconciliation:
原則としては検証優先を明言しているが、
実行では実装先行が繰り返し観測されている
```

この差分自体をPersonal Discovery Evidenceとして利用できる。

---

# 4. Decision Evidence Contract

## 4.1 EvidenceはReference文字列ではなくObjectとして扱う

最低限、以下を保持する。

```yaml
evidence_id:
evidence_type:
decision_case_id:
source_ref:
actor:
observed_at:
explicitness:
confidence:
scope:
sensitivity:
supports_assertion_refs: []
contradicts_assertion_refs: []
```

## 4.2 evidence_type

P0では最低限以下。

- `CONVERSATION_STATEMENT`
- `OBSERVED_ACTION`
- `GENERATED_ARTIFACT`
- `PROJECT_CHANGE`
- `LATER_CONVERSATION`
- `OUTCOME`
- `IMPORTED_EXTERNAL_STATE`

## 4.3 沈黙

ユーザー無反応はEvidenceではあるが、

- Acceptanceではない
- Rejectionでもない

基本状態は`UNKNOWN / UNRESOLVED`。

---

# 5. Decision Reconciliation Contract

## 5.1 目的

未確定Decisionを、後続Evidenceによって後から再評価する。

リアルタイムで全判断を確定させる必要はない。

## 5.2 Trigger

- 新Conversation Episode
- Artifact作成・更新
- 明示観測対象ProjectでのAction
- Outcome追加
- Background Batch

## 5.3 Reconciliation結果

単一の真実へ強制統合しない。

最低限、

- current best assessment
- supporting assertions
- contradicting assertions
- unresolved alternatives
- confidence

を保持する。

## 5.4 AIがCanonicalを書き換えない

ReconciliationはDerived Assessment。

元Conversation、Action、Artifact、Outcome等のCanonical Evidenceは改変しない。

---

# 6. Correction Contract

## 6.1 User CorrectionはCanonical Event

ユーザーが、

- 「それは違う」
- 「その判断はしていない」
- 「今は方針が変わった」
- 「そのパターンは誤認」

等を明示した場合、Correction EventをCanonicalとして保存する。

## 6.2 Correctionの効果

対象Derived Objectを必要に応じて、

- `REJECTED`
- `REVISED`
- `SUPERSEDED`

へ変更する。

Correctionは原Evidenceを物理改変しない。

## 6.3 下流再計算

訂正対象が以下に使われていた場合、

- Pattern
- Discovery Candidate
- Decision Assessment
- Personal Strategy Model
- Derived Learning

をInvalidationし、必要に応じて再計算する。

---

# 7. Experience Trace / Outcome Contract

## 7.1 Outcomes over Archivesを実装Schemaへ落とす

TSUZUはタスク管理アプリにはしない。

ただし、Experience Loopを成立させるため最低限のExperience Traceを保持する。

```yaml
experience_trace_id:

before_state:
problem:

decision_refs: []
action_or_intervention:

observed_after_state:
outcome:

possible_explanations: []
learning_candidates: []

evidence_refs: []
scope:
confidence:
```

## 7.2 Action

Actionは「ユーザーが何かを決断した」ことと同義ではない。

Observed ActionはEvidenceとしてDecision Caseへ接続する。

## 7.3 Outcome

Outcomeは観測結果。

Intervention後に変化しただけで因果を断定しない。

## 7.4 Possible Explanation

因果推論ではなく候補。

例:

> 広告変更後にCVRが改善した。ただし同時期にLPも変更されているため、広告変更単独の効果とは断定できない。

## 7.5 Learning

Outcomeから生成されたLearningは原則`CANDIDATE`または`WORKING`から始める。

単一Caseから一般原則へ自動Promotionしない。

---

# 8. Pattern Contract補強

## 8.1 Pattern成立

原則として、

- 独立Decision Case複数
- 初期目安3 Case以上
- 可能なら2 Context以上

を候補条件とする。

固定ThresholdではなくP0実測で調整する。

## 8.2 Patternは反証込み

必須構造：

```yaml
supporting_cases: []
contradicting_cases: []
exceptions: []
context_conditions: []
temporal_trend:
```

## 8.3 Evidence削除時

支持Evidenceが減った場合、Patternを自動削除せず、

- confidence低下
- WORKINGへ降格
- 条件によってREJECTED

等を再評価する。

---

# 9. Dependency-aware Delete / Invalidation / Recompute

## 9.1 単純Cascade Deleteだけでは扱わない

v1.2で増えたDerived Objectは複数Sourceを根拠にするため、親Object削除時に全てを無条件削除しない。

---

## 9.2 Dependency Graph

最低限、以下の依存関係を追跡する。

```text
Source / Conversation / Artifact
        ↓
Episode
        ↓
Evidence / Candidate
        ↓
Decision Assessment / Pattern
        ↓
Discovery Candidate / Learning
        ↓
Index / Context Bundle
```

---

## 9.3 Tombstone後

Source等がTOMBSTONEDされたら、そのEvidenceを下流Objectから利用不可にする。

その後、

1. dependency invalidation
2. remaining evidence再評価
3. confidence再計算
4. promotion state再評価
5. index / derived view rebuild

を行う。

---

## 9.4 Derived Objectの扱い

### 根拠が全て消えた
ObjectをTOMBSTONEDまたはREJECTED相当へ移行しRecall禁止。

### 根拠が一部残る
再評価して残すことができる。

### Pattern / Discovery
削除されたEvidenceを「存在したもの」として再利用しない。

---

## 9.5 Deletion Ledger

v1.1のDeletion Ledgerを維持する。

Backup / Sync / Restoreから古いEvidenceが戻っても、Deletion Ledgerを再適用して自動復活させない。

---

# 10. Observation Permission Contract

## 10.1 接続 = 全観測権限ではない

AI HostやLocal Projectへの接続によって、ユーザー環境全体の監視権限を取得したものと解釈しない。

## 10.2 Allowlist単位

原則として以下の粒度で権限を持つ。

```text
host
×
workspace / project / repository / session scope
×
capability
```

capability例:

- `read`
- `capture`
- `recall`
- `watch`
- `propose`

## 10.3 P0 Default

P0で自動観測対象にできるのは、

- 明示接続されたAI Host
- 明示Scope内Conversation
- TSUZU Vault
- Share / ImportされたSource
- 明示観測対象Project
- 対応HostがそのScope内で生成したArtifact

まで。

以下はDefaultで観測しない。

- OS全操作
- 全ブラウザ履歴
- 全メール
- 全ローカルファイル
- 接続していない外部サービス

---

# 11. Credential / Local Security Contract

## 11.1 CredentialはKnowledgeではない

API Key、OAuth Token、Refresh Token、Session Cookie、Private Key等は、

- Canonical VaultへKnowledgeとして保存しない
- Markdown Memoryへ保存しない
- Derived Processingへ送らない
- External AIへ送らない

## 11.2 Credential Storage

P0ではOS Keychain等のCredential Storeを利用する。

Vault内へ平文Credentialを置く設計は禁止。

## 11.3 Vault Protection

Local-firstは無保護を意味しない。

P0では少なくとも、

- OS account / filesystem protectionを前提
- BackupにSensitive dataを含むことを明示
- Backup destinationごとのPrivacy Riskを表示可能にする
- 将来のVault encryptionを妨げないStorage Boundary

を確保する。

Full custom encryption engineをP0必須にはしない。

## 11.4 Secret Detection

v1.1通り、Secret DetectorはLLM / Derived Processingより前。

誤ってCaptureされたSecretはKnowledge化しない。

---

# 12. Context Usage / Product Proof Event Contract

## 12.1 Discoveryを生成しただけでは価値証明にしない

最低限、以下を区別する。

```text
RETRIEVED
↓
INCLUDED_IN_BUNDLE
↓
SURFACED
↓
USED_BY_HOST
↓
USER_ACKNOWLEDGED
↓
CONNECTED / REFRAMED / EXPANDED
↓
CHANGED_DECISION
↓
OUTCOME_HELPED
↓
REUSED
↓
WOULD_PAY
```

すべてが直列必須ではない。

---

## 12.2 Event Semantics

### RETRIEVED
Retrieval候補に入った。

### INCLUDED_IN_BUNDLE
Context CompilerがHostへ渡した。

### SURFACED
回答上でユーザーが認識可能な形で利用された。

### USED_BY_HOST
Host回答生成へ実際に利用されたことが確認可能。

### USER_ACKNOWLEDGED
ユーザー反応から「役立った / 接続を認識した」Evidenceがある。

### CONNECTED
自分では結び付けていなかった過去がつながった。

### REFRAMED
問題の見方が変わった。

### EXPANDED
新たな選択肢が増えた。

### CHANGED_DECISION
実際の判断が変わったEvidenceがある。

### OUTCOME_HELPED
結果改善への寄与が示唆された。

### REUSED
後続の別判断でも利用された。

### WOULD_PAY
WTP Evidence。

---

## 12.3 Hard Failure Events

別系列で必ず計測する。

- `FALSE_PERSONAL_ASSERTION`
- `UNSUPPORTED_DECISION_CLAIM`
- `SENSITIVE_EGRESS_VIOLATION`
- `IRRELEVANT_AHA_REPEAT`
- `SUPERSEDED_KNOWLEDGE_MISAPPLIED`

Sensitive Egress ViolationはSecurity Incident扱い。

---

# 13. Product Proof母数Contract

## 13.1 混同しない母数

以下を別々に記録する。

- `users`
- `captured_sources`
- `conversation_episodes`
- `eligible_discovery_opportunities`
- `surfaced_discoveries`
- `connected_or_above_events`
- `decision_impact_events`
- `reused_events`
- `wtp_responses`

「30〜50件」は単独のGate名として使わない。

---

## 13.2 Founder P0

v1.1のPain / Invisible UX / WTP検証を維持し、v1.2のDiscovery Qualityを追加する。

したがってProduct Proofは少なくとも4軸で見る。

1. Pain
2. Invisible UX
3. Personal Discovery / Compounding
4. WTP

---

## 13.3 Discovery最低ライン

TSUZU固有価値としては`CONNECTED`以上を最低ラインとする。

REMEMBERED中心なら、Recall Productとしては価値があってもPersonal Discovery Proofとしては不十分。

---

## 13.4 数値Gate

GO / PIVOT / KILL ThresholdはFounder実測前に固定しない。

ただし、分母・イベント定義を先に固定し、後から数字を都合よく読み替えない。

---

# 14. P0 Host Scope Contract

## 14.1 衝突の解消

v1.1の「ONE AI Host」とv1.2の「Claude Code / Codex / Cursor P0 Required」は以下のように統一する。

### Vertical Slice
**1 HostのみでEnd-to-Endを完成させる。**

### Architecture Contract
Claude Code / Codex / Cursorの3 Hostを同じAdapter Interfaceで扱える設計をP0で固定する。

### P0 Expansion
1 HostのProduct Proof可能な動作確認後、残り2 Hostを順次追加できる。

### Gate
3 Host全ての正式QA完了を、最初のFounder Test開始条件にはしない。

---

## 14.2 最初のHost選定

最初のHostは、

- Chronicle取得
- Context Injection
- Local Tool / MCP / CLI接続
- Debuggability
- Artifact観測

を最小工数で成立させられるHostを選ぶ。

特定Host名はImplementation Spikeで確定してよい。

---

# 15. Target Source / Connector Roadmap

## 15.1 P0 Main

- X
- Web
- note
- Apple Notes Import / Bridge
- Local files
- Share Sheet URL / Text / File
- AI Conversation Chronicle

## 15.2 P0 Validation / Spike

- Web Chat Chronicle One-way
- HostごとのConversation Hook
- X Fetcher strategy
- Grok / Browser等のRescue Route

## 15.3 Product Proof後の主要Target

過去に対象と定めていた以下は、戦略上のTarget Sourceとして維持する。

- Google Drive
- Notion
- Obsidian / Markdown Vault
- その他の主要AI Host
- Mobile AI
- Remote MCP / Cloud Relay

P0で実装しないことと、将来対象から外すことを混同しない。

---

# 16. Context Compiler / Egress継承ルール

v1.2のDiscovery Candidateも、v1.1のEgress / Policy Gateを必ず通る。

Discoveryだから特別扱いしない。

以下を維持する。

- RESTRICTED external egress禁止
- SENSITIVE external default deny
- unknown sensitivity fail closed
- unknown destination fail closed
- TOMBSTONED evidence利用禁止
- SUPERSEDED knowledgeのCurrent Fact誤適用禁止
- Egress Manifest
- Context Trace
- Telemetry本文保存禁止

Discovery Candidateの面白さ・Noveltyを理由にSecurity Gateを迂回しない。

---

# 17. Implementation Order 更新

P0実装順を以下に固定する。

1. Canonical Object Envelope
2. ID / Revision / Schema
3. Atomic Writer
4. Capture Inbox
5. Secret / Sensitivity Guard
6. Single Writer Background Worker
7. Acquisition / Fetcher Adapter
8. Canonical / Derived separation
9. Episode / Candidate extraction
10. Decision Assertion / Evidence
11. Minimal Reconciliation
12. Experience Trace / Outcome
13. Promotion State
14. Tombstone / Dependency tracking / Invalidation
15. Local SQLite / FTS Index
16. Backup / Restore / Rebuild
17. Retrieval
18. Context Compiler / Policy / Egress
19. ONE Host Vertical Slice
20. Minimal Personal Discovery 4 Lanes
21. Product Proof Event logging
22. False Personal Assertion / Prompt Injection tests
23. Founder Golden Cases
24. 2nd / 3rd Host Adapter追加
25. Web Chat Chronicle Spike

---

# 18. Updated Implementation Gates

Founder Test前に最低限以下を満たす。

## Data / Integrity

- Canonical Object Envelope適用
- Atomic Write
- Revision check
- Idempotent Worker
- Dependency tracking
- Tombstone resurrection防止
- Restore Test成功
- Index rebuild成功

## Knowledge / Decision

- Assistant-generatedのみでPROMOTED不可
- STATED / REVEALED併存可能
- SilenceをAcceptance扱いしない
- EvidenceなしDecision断言禁止
- CorrectionからDerived再計算可能

## Security

- Secret ScannerがLLM前
- CredentialをVault Knowledgeへ保存しない
- RESTRICTED Knowledge化禁止
- SENSITIVE external default deny
- unknown sensitivity / destination fail closed
- Observation Scope allowlist
- Context Trace / Egress Manifest
- Telemetry本文保存禁止

## Discovery

- Grounded / Challenge / Analogy / Jumpを識別
- Evidence ConfidenceとDiscovery Distanceを分離
- No Ahaを許容
- PatternにContradiction / Exception保持
- Superseded Principle誤適用防止

## Product Proof

- Context Usage Event記録
- CONNECTED以上のDiscovery Level記録
- False Personal Assertion計測
- Decision Impact / Reuse / WTP記録

---

# 19. Final Decision Ledger

## 【確定：Product Constitution】

- PersonalizationではなくPersonal Discovery
- Past is evidence, not authority
- Outcomes over archives
- Invisible operation
- Continuity over replacement
- TSUZU本体はControl Plane
- Experience Planeは既存AI・既存入力経路
- Connect once. Never summon.

## 【確定：Data / Knowledge】

- Canonical / Derived分離
- Canonical Object Envelope
- Processing / Promotion / Deletion State分離
- AIはproposeまで
- STATED / REVEALEDを併存
- DecisionとEvidenceを分離
- CorrectionはCanonical Event
- Patternは反証・例外込み
- Experience Traceを保持
- Outcomeから因果を自動断定しない

## 【確定：Delete / Recovery】

- TOMBSTONEDは全状態より優先
- Dependency-aware invalidation
- 残Evidenceで再計算
- Deletion Ledger再適用
- CanonicalをAI推測で修復しない

## 【確定：Security】

- Content is data, never authority
- CredentialはKnowledgeではない
- OS Credential Store利用
- Secret DetectorはLLM前
- SENSITIVE external default deny
- ObservationはAllowlist
- 接続 = 全観測権限ではない
- Telemetry本文保存禁止

## 【確定：P0 Scope】

- 最初のVertical Sliceは1 Host
- 3 Host Adapter ContractはP0で維持
- 3 Host正式QAはFounder Test開始条件にしない
- Web Chat ChronicleはValidation Spike
- Drive / Notion / ObsidianはPost-proof Targetとして維持
- Team / Enterprise / Remote MCP / Cloud RelayはProduct Proof後

## 【確定：Product Proof】

- Pain / Invisible UX / Discovery / WTPを同時に見る
- CONNECTED以上がTSUZU固有価値の最低ライン
- Context Usageを技術ログだけでなくProduct Eventとして扱う
- False Personal AssertionをHard Failure
- GO / KILL数値は分母定義後、Founder実測から校正

---

# 20. 閉鎖判定

v1.1 / v1.2横断監査で検出した以下の論点は、本書で閉鎖した。

- Lifecycle二重化
- ONE Host / 3 Host衝突
- STATED / REVEALED Schema不足
- Decision Evidence Schema不足
- v1.2 ObjectのDelete Cascade不足
- 共通Scope / Provenance / Temporal / Sensitivity継承不足
- Outcome Contract不足
- False Personal Assertion訂正処理不足
- Observation Permission不足
- Credential / Local Security不足
- Product Proof母数の曖昧さ
- Drive / Notion / Obsidian Roadmap消失
- Context Usage Event Contractの弱体化

**現時点で、P0 Vertical Slice開始を止める未閉鎖Product / Architecture Blockerはない。**

今後、新しい論点が出た場合も、まずv1.1 → v1.2 → v1.2.1の既存Contractで解けないかを確認し、将来拡張性のみを理由にP0 Scopeを増やさない。

---

# 21. 次の一手

次は新規設計ではなく、

`v1.1 + v1.2 + v1.2.1`

をImplementation Baselineとして、

**最小Vertical SliceをIssue / Taskへ分解して実装を開始する。**

最初のSliceは維持する。

`Share / Local Capture`
→ `Canonical Vault`
→ `Single Worker`
→ `Local Index`
→ `Explicit Recall via ONE Host`
→ `Source Trace`

その上に順次、

`Conversation Chronicle`
→ `Decision Evidence / Reconciliation`
→ `Personal Discovery`
→ `Outcome / Learning`
→ `Product Proof`

を重ねる。

---

# 22. v1.2.1時点の一文定義

> **TSUZUは使うアプリではない。普段使うAIと情報保存の裏側で、ユーザー自身の経験・判断・行動・結果を、事実と推論を混同せず安全に残し、過去を正解として再生するのではなく、現在の思考を深め、広げ、時には疑うPersonal Discoveryへ変換し続ける、ユーザー所有のPersonal Experience Infrastructureである。**
