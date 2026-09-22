# TSUZU 正本 v1.2 追補統合版
## Personal Discovery / Conversation Learning / Decision Reconciliation

- Version: v1.2 Addendum
- Date: 2026-09-06
- Base: TSUZU 正本 v1.1
- Status: Decision Baseline / P0 Implementation Contract Update

> 本書は v1.1 を全面的に置き換える再構成ではない。v1.1 の未変更事項はそのまま継承し、本書で明示した差分・上書き事項のみ v1.1 より優先する。

---

# 0. 結論

TSUZUの価値源泉を、単なるRecallやPersonalizationではなく **Personal Discovery** として明確化する。

TSUZUは、ユーザーの過去を再現するためではなく、ユーザー自身の経験・判断・結果・矛盾・例外を材料として、現在の思考を深め、広げ、時には疑うための Personal Experience Infrastructure である。

今回の追補で、次の中核仕様を確定する。

1. Personal Discovery / Aha Engine の目的と生成レーン
2. AI Conversation Chronicle の自動取得・後段バッチ処理
3. AIの提案とユーザー自身のKnowledgeの厳密な分離
4. Decision と Evidence の分離、および Decision Reconciliation
5. Stated Decision と Revealed Decision の併存
6. Knowledge Promotion Lifecycle
7. Repeated Judgment Pattern / Pattern Challenger
8. Structural Analogy / Blind Spot Discovery
9. Web Chat Chronicle のP0 Validation Spike化
10. Discovery中心のProduct Proof更新
11. Runtime / Cost / Latencyを抑えるリアルタイム＋バッチ構成
12. False Personal AssertionをHard Failureとして扱うTrust Contract

新たな重大なProduct Constitution上の懸念は現時点では見つかっていない。残件はHostごとの取得方式、モデル構成、閾値、Retrievalパラメータなど、実装Spikeと実測で確定すべき項目へ収束した。

---

# 1. v1.2で追加する最上位Product Constitution

## 1.1 PersonalizationではなくPersonal Discovery

TSUZUの目的は「過去のユーザーならどう答えるか」を再現することではない。

**過去の自分を正解として使うのではなく、過去の自分を材料として現在の思考を拡張する。**

したがってTSUZUは、次を同時に行う。

- 過去の経験・判断・Outcomeを現在へ接続する
- 繰り返している判断パターンを抽出する
- そのパターンに反する例外・失敗・矛盾を探す
- 別領域の構造的に似た経験を転用する
- まだ検討していない空白・Blind Spotを探す
- 根拠が弱い思考ジャンプは「仮説」として分離して提示する

## 1.2 Past is evidence, not authority

過去のユーザー判断は将来の正解ではない。

古い判断、成功した判断、繰り返しているPreferenceであっても、現在の条件・Stage・目的と一致しなければ再適用しない。

## 1.3 Outcomes over archives

保存件数・検索回数・Recall回数を最終価値としない。

`Experience → Discovery → Decision → Action → Outcome → Learning → 次のDiscovery`

までつながったかを重視する。

## 1.4 Invisible operation

ユーザーに「保存」「分類」「Decision確定」「Outcome登録」を逐一要求しない。

通常行動の裏側でChronicle・Candidate・Reconciliation・Promotionを進め、誤推論リスクが高い場合のみ必要最小限の確認を行う。

## 1.5 Continuity over replacement

TSUZU独自のチャットや作業環境へユーザーを移動させない。

既存AI・既存保存先・既存ツールをExperience Planeとして使い続ける。

---

# 2. Experience Plane / Control Plane の再確認

## 2.1 Experience Plane

日常利用はTSUZU本体ではなく、既存AI・既存情報源で行う。

P0の主要AI Hostは以下とする。

- Claude Code
- Codex
- Cursor

これらはLocal MCP / CLI / Hook / Adapterを通じ、TSUZU Coreと双方向接続する。

また以下はCapture Sourceとして扱う。

- X
- Web / note
- Apple Notes
- Local files
- Share Sheet経由のURL / Text / File
- AI Conversation Chronicle

## 2.2 Control Plane

TSUZU本体の日常UIは、原則として以下に限定する。

- Connection / Connector設定
- Privacy / Sensitivity設定
- Health / Acquisition状態
- Recovery / Deletion
- 必要最小限の確認・修正

検索・チャット・Aha閲覧を主目的とする日常操作UIはP0に置かない。

## 2.3 Web Chat

ChatGPT / Claude / Gemini等のWeb Chatは最終形では重要なExperience Planeであるが、P0で完全双方向連携を必須にしない。

今回の差分として、**Web Chat Chronicle One-way CaptureをP0 Validation Spikeに昇格**する。

- P0 Main: Claude Code / Codex / Cursor = Recall + Injection + Chronicle
- P0 Spike: Web Chat = Chronicle取得可否を検証
- Product Proof後: Web Chat / Mobile AI = Remote MCP / Connector / Cloud Relay等で双方向化を検討

---

# 3. Personal Discovery Engine Contract

## 3.1 Objective

現在の問いに対して、自分自身のExperienceを利用し、一般知識だけでは出にくい「自分固有の発見候補」を生成する。

出力は1つの正解に限定しない。

## 3.2 Current Decision Structure

現在の会話をTopicだけで検索しない。最低限、以下の判断構造へ分解する。

- Problem: 何を解きたいか
- Stage: 探索 / 検証 / 実装 / 運用 / 拡張等
- Desired Outcome: 何を良くしたいか
- Constraints: コスト・時間・UX・Security等
- Options: 現在見えている選択肢
- Trade-offs: 何と何が競合しているか
- Uncertainty: 未知・仮説は何か

これにより、テーマは異なるが判断構造が同じ過去を取得できるようにする。

## 3.3 Candidate生成レーン

P0では4レーンを基本とする。

### Lane A: Grounded Connection
現在の問いと直接関係する過去のExperience / Decision / Outcome。

### Lane B: Pattern / Challenge
繰り返し現れる判断Pattern、矛盾、例外、反証。

### Lane C: Structural Analogy
テーマは異なるが、問題構造・Trade-off・Failure Modeが類似する過去。

### Lane D: Exploratory Jump
複数Experienceの組み合わせ、原則の反転、未探索の可能性から作る仮説。

## 3.4 Rankingは単一Scoreにしない

最低限、以下を分離する。

- Evidence Confidence: 根拠の強さ
- Discovery Distance: 現在の思考からの距離
- Decision Utility: 今の判断への有用性
- Novelty: 既知の反復でないか
- Diversity: 他候補と同じ方向に偏っていないか
- Temporal / Stage Fit: 現在条件に適用可能か

`Evidence Confidence` と `Discovery Distance` は統合しない。

- 高Confidence × 近距離 = 確実な示唆
- 高Confidence × 中〜遠距離 = 強いAha候補
- 低Confidence × 遠距離 = 探索仮説
- 低Confidence × 近距離 = 原則として価値が低い

## 3.5 Diversity Selection

意味的類似度上位だけを並べない。

候補Poolから異なる方向を選び、原則0〜3件程度をAIへ渡す。

例:

- Grounded 1件
- Challenge / Analogy / Jumpから0〜2件

価値ある候補がない場合、Ahaを無理に生成しない。

## 3.6 Output Semantics

AI側は確度を混同しない。

例:

- 「過去の判断から見ると、かなり強い接続があります」
- 「別領域ですが構造が似ています」
- 「少し飛躍しますが、検討価値のある仮説です」
- 「過去の傾向とは逆ですが、この条件では例外かもしれません」

TSUZUはAhaを真実として宣言せず、発見可能性を高める。

---

# 4. AI Conversation Chronicle Contract

## 4.1 Default UX

原則、ユーザーは何もしない。

会話のたびに「保存しますか」「学習しますか」を表示しない。

処理は以下とする。

`Conversation → Chronicle → Episode → Candidate Extraction → Promotion / Reconciliation`

## 4.2 ChronicleとKnowledgeを分離する

Raw Conversationは観測記録であり、そのままユーザーKnowledgeではない。

AIが提案しただけの内容をユーザーのPreference / Decision / Principleとして保存してはならない。

## 4.3 Episode Segmentation

1メッセージ=1Memoryとしない。

同一論点について、提案・比較・反論・修正・結論が連続するまとまりをEpisodeとして抽出する。

## 4.4 Candidate Types

会話から以下を抽出可能とする。

- Fact
- Preference
- Decision
- Insight
- Principle
- Hypothesis
- Rejected Option
- Open Question
- Correction
- Outcome
- Judgment Pattern Candidate

## 4.5 Origin

最低限、Originを次で識別する。

- `user_explicit`
- `assistant_generated`
- `jointly_derived`
- `external_source`
- `observed_behavior`

AIとユーザーの共同言語化は `jointly_derived` とする。

## 4.6 User Reaction Semantics

ユーザー反応はEvidenceとして扱うが、単純な肯定判定をしない。

- 「採用」「これで確定」「今後これで」 = 強いDecision Evidence
- 「それがしたかった」「この表現が近い」 = Principle / Insightの強いConfirmation
- 「いいですね」「面白い」 = Positive Reaction。Decision確定ではない
- 無反応 = AcceptanceでもRejectionでもない。`UNKNOWN / UNRESOLVED`

---

# 5. Decision / Evidence / Reconciliation Contract

## 5.1 DecisionとEvidenceを分離する

Observed ActionはDecision Statusではない。

Decision Caseに対するEvidenceとして保持する。

### Decision Evidence例

- AI ConversationでのExplicit Statement
- Observed Action
- Generated Artifact
- Local Project change
- Later Conversation
- Outcome
- External State / Imported Evidence

## 5.2 Decision Assessment

Decision状態は以下を基本とする。

- `UNRESOLVED`
- `STATED`
- `REVEALED`
- `REVISED`
- `SUPERSEDED`

Confidenceは別軸で保持する。

- `LOW`
- `MEDIUM`
- `HIGH`

## 5.3 Stated Decision / Revealed Decision

両者を統合して消さない。

- Stated Decision: ユーザーが明示的に「こうする」と述べた
- Revealed Decision: 実際の行動・成果物・後続処理から採用が観測された

両者が食い違う場合、それ自体をPersonal DiscoveryのEvidenceにする。

## 5.4 Decision Reconciliation

以下のTriggerで未確定Decisionを再評価する。

- 新しいConversation Episodeが入った
- 関連Artifactが作成・更新された
- 観測対象ProjectでActionが起きた
- Outcomeが入った
- Background Batch実行時

例:

会話で980円 / 1,480円が未決でも、その後Pricing・実装・課金設定が980円に揃えば、`REVEALED / HIGH`を構築できる。

ただし推論なので、原Evidenceは保持し、AIが明示的Decisionだったように改変しない。

---

# 6. Knowledge Promotion Lifecycle

## 6.1 States

- `CANDIDATE`: AIが抽出しただけ。強いRecall根拠にしない
- `WORKING`: Evidenceがあるが仮説性が高い
- `PROMOTED`: 明示または十分なEvidenceがあり、積極利用可能
- `SUPERSEDED`: 後から更新された。削除せず履歴保持
- `REJECTED`: 誤抽出・明示棄却等

## 6.2 Promotion原則

- assistant_generatedだけでPROMOTEDにしない
- user_explicitは強いEvidenceだがTemporal Contextを保持する
- observed_behaviorはRevealed Decisionに強いが、内面の信念と断定しない
- jointly_derivedはユーザーの明示確認がある場合に強く扱う
- Patternは複数の独立Decision Caseから形成する

## 6.3 Supersedeは削除ではない

過去の判断が古くなっても削除しない。

「何を重視していたかがどう変わったか」というJudgment Evolutionに使う。

---

# 7. Personal Strategy Model

Personal Discoveryを支える内部モデルとして、次を蓄積する。

- Facts
- Experiences
- Decisions
- Outcomes
- Preferences
- Criteria
- Repeated Judgment Patterns
- Conditional Heuristics
- Contradictions
- Exceptions
- Blind Spots
- Judgment Evolution

これはユーザーを固定的な人格モデルへ閉じ込めるためではない。現在の思考を広げるためのEvidence Modelである。

---

# 8. Repeated Judgment Pattern / Pattern Challenger

## 8.1 Pattern Candidate

同一会話内の反復だけでは成立させない。

初期ヒューリスティックとして、複数の独立Decision Case、目安として3 Case以上から候補化する。可能なら2 Context以上を要求する。

これは固定閾値ではなくP0実測で調整する。

## 8.2 Patternには反証を必須で持たせる

- Supporting Cases
- Contradicting Cases
- Exceptions
- Context
- Temporal Trend

Personal Discovery時には「あなたはXを重視する」で終えず、条件付きで提示する。

例:

「Xを優先する傾向があります。ただし初期探索フェーズでは逆の判断をしている例があります。」

## 8.3 Pattern Challenger

過去のPatternをそのまま強化せず、次を探索する。

- その原則が失敗した事例
- 成功条件と失敗条件
- 最近の変化
- 反対方向を選んだ例外
- 今回のStageとの不一致

これをエコーチェンバー防止の中核Guardrailとする。

---

# 9. Structural Analogy / Blind Spot Discovery

## 9.1 Structural Analogy

ExperienceをConcrete Topicだけでなく、抽象構造へ投影する。

例:

- Proxy Metric Problem
- Cold Start
- Exploration vs Exploitation
- Cost vs UX
- Speed vs Trust
- Product Proof before Expansion
- Reversibility
- Outcome Optimization

これにより、採用広告の「応募数ではなく面接Outcomeを見る」という経験を、別プロダクトの「Recall数ではなくDecision Impactを見る」へ転用できる。

## 9.2 Blind Spot Discovery

TSUZUが観測できた複数Caseにおいて、繰り返し抜けている検討軸を候補化する。

ただし、`not observed != not considered` を厳守する。

出力時にはEvidence Coverageを考慮し、「TSUZUが観測できた範囲では」と扱う。

---

# 10. Runtime / Batch Processing Contract

## 10.1 二層処理

毎ターンDeep Discoveryを実行しない。

### Realtime Light Path
- Current Context / Intent検知
- 既存Precomputed Modelの軽い参照
- Decision / Exploration / StrategyのTrigger判定

### Deep Discovery Path
必要なときだけ、Personal Evidence Retrieval / Candidate Generation / Challenge / Diversity Selectionを実行する。

## 10.2 Background Batch

以下は原則バッチへ寄せる。

- Episode Segmentation
- Candidate Extraction
- Pattern Extraction
- Contradiction Detection
- Decision Reconciliation
- Promotion Review
- Blind Spot Candidate生成
- Index / derived view再構築

## 10.3 Processing Philosophy

**蓄積時に深く考え、利用時は必要な分だけ軽く呼び出す。**

これによりAPI CostとLatencyを抑えつつ、Aha品質を維持する。

---

# 11. Trust / Provenance / Safety Contract 更新

## 11.1 Provenance必須

すべてのDerived Knowledgeは最低限以下を追跡可能にする。

- Source / Conversation / Artifact
- Actor: user / assistant / external / observed
- Timestamp
- Explicit vs inferred
- Confidence
- Promotion State
- Superseded relation

## 11.2 Canonical / Derived分離

原文・明示情報をCanonicalとし、AI解釈はDerivedとする既存原則を維持する。

AI推論でCanonicalを書き換えない。

## 11.3 False Personal Assertion = Hard Failure

実際にはEvidenceがない内容を、AIが以下のように断言することを重大障害とする。

- 「あなたはXを重視しています」
- 「以前あなたはAを決定しました」
- 「あなたはBを嫌っています」

Evidenceが不足する場合は「可能性」「観測範囲」「仮説」と明示する。

## 11.4 Memory Poisoning対策

外部SourceやAI回答内の命令文・自己参照的記述をユーザーPrincipleへ昇格させない。

Assistant-generated contentは原則Candidate以下から始め、ユーザーEvidenceなしでPromotionしない。

## 11.5 P0 Observation Boundary

P0で観測対象とするのは以下まで。

- 対応AI Host内のConversation
- TSUZU Vault
- Share / ImportされたSource
- 対応Hostが生成したArtifact
- 明示的に観測対象となったLocal Project

以下を勝手に監視しない。

- OS全操作
- 全ブラウザ履歴
- 全メール
- 全ローカルファイル
- ユーザーが接続していない外部サービス

Evidence不足は `UNKNOWN` のまま保持してよい。

---

# 12. Product Proof Contract 更新

## 12.1 Discovery Level

従来のSURFACED / USED / IMPACTED / OUTCOME_LINKED / REUSEDを維持しつつ、Aha品質を以下で観測する。

1. `REMEMBERED` — 忘れていた過去を思い出せた
2. `CONNECTED` — 自分では結びつけていなかったものがつながった
3. `REFRAMED` — 問題の見方が変わった
4. `EXPANDED` — 新しい選択肢・可能性が増えた
5. `CHANGED_DECISION` — 実際の判断が変わった
6. `OUTCOME_HELPED` — 結果として役立った
7. `REUSED` — 後の別判断でも再利用された

## 12.2 Core Proof

TSUZU固有価値の最低ラインは `CONNECTED` 以上とする。

特に `REFRAMED / EXPANDED / CHANGED_DECISION` を強いProduct Evidenceとして扱う。

REMEMBEREDだけが多い場合、良いRecallシステムではあってもPersonal DiscoveryのProofには不足する。

## 12.3 Hard Failure Metrics

- False Personal Assertion
- Unsupported Decision Claim
- Sensitive Egress Violation
- Repeated irrelevant Aha
- Old / Superseded Principleの誤適用

## 12.4 数値Gate

30〜50件程度のFounder P0で分布を観測する既存方針を維持する。

CONNECTED以上の発生率等のGO / KILL数値は、現時点で恣意的に固定せず、実測後にGate化する。

---

# 13. P0 Scope 更新

## 13.1 P0 Required

- Local-first Vault / Single Writer
- Canonical / Derived separation
- Local Index / FTS / Retrieval
- Claude Code / Codex / Cursor Adapter
- AI Conversation Chronicle
- Episode / Candidate Extraction
- Minimal Personal Discovery 4 Lanes
- Evidence / Provenance
- Decision Reconciliation
- Knowledge Promotion Lifecycle
- Basic Pattern Challenger
- Product Proof Event logging
- Prompt Injection / Memory Poisoning Guardrail

## 13.2 P0 Validation Spike

- Web Chat Chronicle One-way Capture
- HostごとのConversation Hook方式
- Discovery Prompt / Model構成
- Structural Analogy retrieval方式
- Confidence / Promotion閾値
- Retrieval / Diversityパラメータ

## 13.3 Product Proof後

- Web Chat完全双方向連携
- Mobile AI完全連携
- Remote MCP / Cloud Relay
- Team Knowledge OS
- Context API / SDK
- 自動外部Action監視の拡張
- 高度なBlind Spot定期通知

---

# 14. 実装用最小データ契約

## 14.1 Experience Candidate

最低限保持する。

- `candidate_id`
- `type`
- `origin`
- `content`
- `source_refs[]`
- `created_at`
- `confidence`
- `promotion_state`
- `sensitivity`

## 14.2 Decision Case

- `decision_case_id`
- `problem`
- `stage`
- `options[]`
- `constraints[]`
- `tradeoffs[]`
- `assessment_status`
- `confidence`
- `evidence_refs[]`
- `supersedes / superseded_by`

## 14.3 Pattern Candidate

- `pattern_id`
- `statement`
- `supporting_cases[]`
- `contradicting_cases[]`
- `exceptions[]`
- `context_conditions[]`
- `temporal_trend`
- `confidence`
- `promotion_state`

## 14.4 Discovery Candidate

- `discovery_id`
- `lane`
- `statement`
- `evidence_refs[]`
- `evidence_confidence`
- `discovery_distance`
- `decision_utility`
- `novelty`
- `temporal_fit`
- `status: grounded / hypothesis`

これらはLogical Contractであり、P0の物理Storage Schemaを過度に複雑化する要求ではない。Markdown Canonical + SQLite Derived Indexという既存原則に合わせて最小実装する。

---

# 15. Decision Ledger — 今回の確定事項

## 【確定】

- TSUZUの価値中心をPersonal Discoveryとして定義する
- 過去を再現するのではなく、過去を現在の思考材料として利用する
- 出力候補は1つに限定しない
- Grounded / Pattern-Challenge / Structural Analogy / Exploratory Jumpの複数レーンを持つ
- Evidence ConfidenceとDiscovery Distanceを分離する
- 良いAhaがない場合は生成しない
- AI Conversationは重要なExperience Sourceとして扱う
- ユーザーは原則保存操作をしない
- Chronicleは自動、Meaning Extraction / Reconciliationは主に後段バッチ
- AI生成内容とユーザーKnowledgeを分離する
- 沈黙はAcceptanceでもRejectionでもない
- DecisionとEvidenceを分離する
- Stated Decision / Revealed Decisionを併存させる
- Decision Reconciliationで後続Evidenceから判断を更新する
- Knowledge Promotionを段階制にする
- Superseded Knowledgeを削除せずJudgment Evolutionへ利用する
- Repeated Judgment Patternには反証・例外を持たせる
- Pattern Challengerをエコーチェンバー防止に使う
- Blind Spotは「観測されなかった＝考えていない」と断定しない
- False Personal AssertionをHard Failureとする
- Web Chat完全連携はP0必須としない
- Web Chat Chronicle One-way CaptureはP0 Validation Spikeとする
- Product Proofの中心をCONNECTED以上へ更新する

## 【実装Spikeで確定】

- Web Chat Chronicle取得方式
- 各AI HostのConversation Hook方式
- Discovery EngineのPrompt / Model分割
- Vector / FTS / Structural Retrievalの組み合わせ
- Candidate / Promotion / Confidence閾値
- Diversity Selectionパラメータ
- Pattern成立閾値
- Product Proof GO / KILL数値

## 【Product Proof後】

- Web Chat / Mobile AI完全双方向
- Remote MCP / Cloud Relay
- Team / Enterprise
- Context API
- 高度な外部行動Connector

---

# 16. 残る懸念と扱い

現時点で新たな致命的懸念はないが、次のリスクは実装時に必ず監査する。

### 16.1 過剰推論
行動から内面のPreferenceまで断定しない。EvidenceとInferenceを分離する。

### 16.2 Aha Hallucination
Ahaを毎回出すKPIにしない。根拠なしの面白さより、No Ahaを許容する。

### 16.3 Echo Chamber
Pattern Challenger / Contradicting Casesを必須化する。

### 16.4 Observation Bias
TSUZUが観測できる範囲だけで人格全体を断定しない。

### 16.5 Privacy Scope Creep
Decision精度を上げるために無制限の監視へ拡張しない。

### 16.6 Latency / Cost
毎ターンDeep Discoveryをせず、Precompute + Triggered Deep Pathを採用する。

### 16.7 Host Coverage Bias
一部AI HostだけChronicle取得できる場合、その偏りをEvidence Coverageとして認識する。

これらはBlockerではなく、今回確定したContractで制御可能な実装リスクとする。

---

# 17. 次の実装順序

次に新規構想を増やすのではなく、以下の順でVertical Sliceへ移る。

1. Chronicle / Episode / CandidateのLogical Schema
2. Provenance / Promotion / Decision Evidence Schema
3. 1 HostでConversation Chronicle end-to-end
4. Minimal Decision Reconciliation
5. Minimal Personal Discovery 4-Lane retrieval
6. Context CompilerへDiscovery Candidateを注入
7. False Personal Assertion / Prompt Injectionテスト
8. FounderデータでGolden Casesを作成
9. CONNECTED / REFRAMED / EXPANDED計測
10. Web Chat Chronicle One-way Spike
11. 実測結果で閾値・Rankingを調整

P0の目的はアルゴリズムを完成させることではない。

**「自分では今回持ち込まなかった過去の経験が、自分だけでは出にくかった新しい接続・見方・可能性を生み、それが実際の判断に使われる」ことを最小構成で証明する。**

---

# 18. v1.2時点の一文定義

> **TSUZUは使うアプリではない。普段使うAIと情報保存の裏側でユーザー自身の経験を安全に残し、その経験を正解として再生するのではなく、現在の思考を深め、広げ、時には疑うためのPersonal Discoveryへ変換し続ける、ユーザー所有のPersonal Experience Infrastructureである。**
