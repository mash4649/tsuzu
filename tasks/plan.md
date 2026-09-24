# TSUZU 実装計画（Claude 対応を除外）

## 目的

現状の TSUZU を、Mac TSUZU Core/Python single-writer を唯一の Canonical 所有者としたまま、Codex/Tauri の実運用経路、Derived knowledge、Discovery、Passive/Control Plane、Founder proof まで検証可能な順序で完成させる。タスクの正本は Beads であり、このファイルは順序付き index だけを持つ。

Claude Code Chronicle（`tsuzu-main-pb6.6.1`）と Web Chat Chronicle（`tsuzu-main-pb6.9.2`）は今回の対象外。一方、ChatGPT アプリから明示的に依頼する Apple Notes Clip 整理は対象に含む。既存 Beads を勝手に close/defer せず、Claude を除外した状態で完了を主張できない gate は明示的に保留する。

## Architecture decisions

- Canonical の mutable writer は Mac TSUZU Core/Python の A3 CaptureService → A4 SingleWriterWorker → A2/C1 の一本だけ。
- Tauri は app-local draft と Core receipt の表示に限定し、Codex は同じ Active Vault を解決する host adapter とする。
- Passive recall は explicit recall/A7/A8/C6 の境界を越えない。Derived output は Canonical へ自己昇格しない。
- Apple Notes と iOS は外部システム境界を明示し、fixture/test seam を本番統合の証拠と混同しない。
- Claude を含む未実施 gate を、Codex-only の検証で代替したことにしない。

## Ordered execution index

### 0. Cross-surface production path

1. `tsuzu-main-pb6.11` — Codex/Tauri の同一 Active Vault と A3/A4 ingress への収束。Codex hook の直接 `AtomicSourceWriter` 経路を廃止し、同一 writer・receipt・index を実証する。
2. `tsuzu-main-2fa` — signed/bundled Python Core sidecar、least-privilege 起動、draft/queued/committed receipt UI、install/launch/close-reopen smoke。`pb6.11` 完了後。

**Checkpoint 0:** Tauri draft と Codex prompt が同じ Vault に入り、Python 全テスト、Tauri test/build、実アプリの close/reopen smoke が通る。

### 1. Derived knowledge foundation（既存 Beads）

3. `tsuzu-main-pb6.6.2` — C4 Derived Processing Orchestrator の preflight、materialization、lease/retry/invalidation、fault coverage。
4. `tsuzu-main-pb6.6.3` — B2 Episode の C4 永続化、再現可能な segmentation、invalidation/golden coverage。
5. `tsuzu-main-pb6.6.4` → `pb6.6.5` — B3 Experience Candidate → B4 Decision Case / Assertions / Evidence。
6. `tsuzu-main-pb6.6.6` → `pb6.6.7` → `pb6.6.8` — B5 Reconciliation/Correction → B6 Experience/Outcome/Learning → B7 Promotion/Dependency。
7. `tsuzu-main-pb6.6.9` — Knowledge Integrity gate。モデル出力の USER_EXPLICIT 化、削除証拠の再利用、crash/retry/idempotency を全件検証する。B1 Claude はこの計画では実装しないため、gate の完了条件からは除外せず保留する。

### 2. Discovery and product events（既存 Beads）

8. `tsuzu-main-pb6.7.1` → `pb6.7.2` — B8 4 lanes/No-Aha → B9 A7/A8/A9 を通る bounded Discovery injection。
9. `tsuzu-main-pb6.7.3` — B10 immutable Product Proof events / denominators。
10. `tsuzu-main-pb6.7.4` → `pb6.7.5` — B11 technical golden cases → Slice B checkpoint。

### 3. Passive recall and control plane（既存 Beads）

11. `tsuzu-main-pb6.8.1` — R6 passive evaluation、single-use Trusted Intent、A7 per-candidate approval、PERSONAL-only egress。
12. `tsuzu-main-pb6.8.2` — C5 portable Canonical archive、schema/checksum、credential exclusion。
13. `tsuzu-main-pb6.8.3` → `pb6.8.4` — R7 thin control plane → Founder UX Safety gate（health、delete、export、recovery、capability truthfulness）。

### 4. Host verification（Claude 除外）

14. `tsuzu-main-pb6.9.1` — Codex/Cursor explicit read-only recall の capability report、live `tools/list`、scope/version downgrade、A7/A8 parity。既存の Codex-only/Cursor evidence を補完する。
15. `tsuzu-main-pb6.9.2` — Claude/Web Chat は今回の対象外。既存レコードは別スコープとして残し、未実施を完了扱いしない。

### 5. Founder proof and completion audit（既存 Beads）

16. `tsuzu-main-pb6.10.1` → `pb6.10.2` → `pb6.10.3` — R10 F0 internal instrumentation → F1 external Founder proof → F2 gate calibration。
17. `tsuzu-main-pb6.10.7` — MVP completion audit。全 P0 gate、manifest、focused/full checks、R8、そして対象とした Product Proof の証拠を照合する。Claude 除外による gate 未解決を隠さない。

### 6. 実システム統合の残課題（今回追加した Beads、P2）

18. `tsuzu-main-pb6.12` — Apple Notes の selected-note read-only bridge。既存の injected reader は test seam として残し、macOS 実ブリッジ・permission denied/cancel/idempotency を検証する。
19. `tsuzu-main-pb6.13` — R4 desktop verifier、paired-key registry/revocation、replay/expiry/tamper fail-closed、既存 outbox/A3/A4 への接続。
20. `tsuzu-main-pb6.14` — iOS Share Extension の Keychain/Secure Enclave-class key lifecycle と実機 round trip。現リポジトリ外の mobile deliverable を明示し、desktop verifier (`pb6.13`) の fixture/live evidence に依存する。

### 7. Codex デスクトップ Clip 整理（Web 版は対象外）

21. `tsuzu-main-pb6.15` — `tsuzu_clip_list` の25件超継続取得を可能にする。途中で処理済み receipt が増えても候補を飛ばさない。
22. `tsuzu-main-pb6.16` — Codex デスクトップのローカル MCP 登録、ツール発見、リンク先確認、下書き保存・重複防止を実ユーザー経路で検証する。Web 版とトンネルは対象外。

## Verification checkpoints

- 各 Bead は claim → focused test → full repository check → evidence を記録してから close する。
- Checkpoint 0 の後に C4/B2 を進め、Derived が不安定なまま Discovery/Passive を作らない。
- Phase 7 gate 前に R6/C5/R7 の fault/adversarial evidence を揃える。
- R10 F1 は technical PASS と Product GO を混同せず、Claude 除外の影響を明記する。

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Codex と Tauri が別 root を解決する | 二重 Vault / recall 欠落 | `pb6.11` で Active Vault Locator と A3/A4 経路を一本化し、同一 root の smoke を必須化 |
| Derived output が Canonical に自己昇格する | 証拠境界の破壊 | C4 preflight と C1 `DERIVED` storage、B3–B7 provenance を必須化 |
| Notes/iOS の test double を実統合と誤認する | Founder proof の虚偽 | `pb6.12`–`pb6.14` を別 P2 とし、fixture/live/device evidence を分離 |
| Claude 除外のまま MVP 完了を宣言する | gate の未解決を隠す | B1/R9 を close せず、`pb6.6.9`/`pb6.10.7` に未解決依存として残す |

## Scope boundary

今回の実装計画は Claude 対応を実装しない。Claude を含む gate の扱いを変更するには、別途明示的な scope decision を Beads に記録してから行う。
