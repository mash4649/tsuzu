# TSUZU 正本 v1.2.2 Implementation Closure Addendum
## Cross-cutting Persistence / Deletion / Materialization / Runtime / Portability Closure

- Version: v1.2.2 Implementation Closure Addendum
- Date: 2026-09-09
- Base: TSUZU 正本 v1.1 + v1.2 Addendum + v1.2.1 Closing Addendum
- Status: **P0 Implementation Contract Closure / Closed**
- Precedence:
  1. 本書 v1.2.2
  2. v1.2.1 Closing Addendum
  3. v1.2 Addendum
  4. v1.1 Canonical Product & Architecture Baseline
  5. それ以前のSavepoint
- Purpose: v2.0実装文書横断レビューで判明した「個別Contractは存在するがContract間の接続責務が未所有」の穴を閉じる。新しいProduct Scopeは追加しない。

---

# 0. 結論

v1.1 / v1.2 / v1.2.1のProduct Constitutionは維持する。

追加Product機能は定義しない。

今回、P0の実装責務を以下のCross-cutting Contractへ明示的に割り当てる。

1. C0 Active Vault Locator / Root Boundary
2. C1 Generic Persistent Object Persistence / Canonical Mutation
3. C2 Effective Source Representation / Materialization / Projection / Trace
4. C3 Generic Deletion Ledger / Purge / No-Resurrection
5. C4 Derived Processing Orchestrator / Job / Recompute
6. C5 Canonical Export / Portability
7. C6 Capability Registry / Router Interface

これにより、Sourceだけで閉じていたA2/A6と、Conversation/Decision/Discoveryへ拡張されたB系の間の責務断絶を解消する。

---

# 1. Cross-cutting Contract precedence rule

A/B/R Contractは廃止しない。

Cross-cutting Contractは、既存Contractの限定Scopeを以下のように一般化・接続する。

```text
Object-specific semantic Contract
  owns WHAT the object/action means

Cross-cutting C Contract
  owns HOW shared persistence/deletion/materialization/runtime boundary works
```

例:

- A2 owns SOURCE-specific atomic persistence details.
- C1 owns generic persistent-object mechanics across object types.
- A6 owns SOURCE deletion specialization.
- C3 owns generic deletion truth across object types.
- R1 owns acquisition.
- C2 owns how acquired bytes become the effective indexed/recallable representation.

下位ContractはC ContractのHard Invariantを弱められない。

---

# 2. Active Vault Locator is a foundation, not an R5-only detail

v1.2.1以前はactive Vault切替の必要性が主にRecovery文脈で現れたが、実装上はA2/A4/A5/A6/B/Rすべてが同じcurrent Vaultを参照しなければならない。

したがって:

- C0をA2等のwriter/index実装より前にFoundationとして実装する。
- 各moduleが独自にVault pathを保持することを禁止する。
- R5はC0のatomic cutoverを利用する。
- stale Vault handleからのcommitをgeneration checkで拒否する。

---

# 3. Generic Persistent Object persistence ownership

v1.2.1のCanonical Object Envelopeは、永続/追跡対象Object全体へ適用する。

A2がSOURCE専用であることを理由に、B1/B4/B5/R1等がprivate writerを作ってはならない。

Canonical persistent objectはC1を通る。

A2はSOURCE specializationとして維持する。

Derived persistent objectはC4のgeneration/materialization semanticsに従う。

---

# 4. Acquired Source materialization ownership

URL Captureのroot SOURCEと、R1/R2で取得したSOURCE_VERSIONは別Objectとして維持する。

ただしRecall/Indexがroot URL文字列だけを見続ける実装は禁止する。

C2を介し:

```text
SOURCE
+ eligible SOURCE_VERSION
-> Effective Representation
-> A5 index
-> A7 revalidation
-> A8 Context + Source Trace
```

とする。

Source identityはroot SOURCE、実際に利用したcontent bytesはrepresentationとして追跡する。HTML/PDF等のraw bytesを検索・excerptへ使う場合は、C2のversioned local deterministic text projectionをDerivedとして生成し、raw Canonical bytesを変更しない。

---

# 5. Generic deletion ownership

A6のSource-level Deletion LedgerはP0の最初のspecializationとして正しい。

v1.2.1で追加されたConversation / Evidence / Decision等についても、Deletion truthを同じ原則へ拡張する。

Generic key:

```text
(object_type, object_id)
```

C3 ledgerが有効なら、object manifestがLIVEでもdeletedが勝つ。

TOMBSTONEDは全Promotion/Derived/Recall状態より優先する。

---

# 6. Physical purge guarantee boundary

v1.1の「Forget後にPhysical Purgeする」とA6の「physical secure eraseはNon-scope」は以下で統一する。

## P0で行う

- logical deletionを即時有効化
- index/cache/Derived利用を除外
- active TSUZU-managed storageから対象payload/fileを通常filesystem deletionでbest-effort purge
- purge失敗をHealthへ残す

## P0で保証しない

- SSD/APFSのforensic secure erase
- OS snapshot / Time Machineの強制消去
- 外部backup provider内部の保持削除保証
- iCloud内部複製の即時物理消去保証

したがって「通常のactive-store purge」はP0、**secure erase guarantee**はP0外とする。

---

# 7. Derived Processing Orchestrator ownership

B2/B5/B7等の`queue/retry/recompute`を各featureが独自実装しない。

C4が以下を共通所有する。

- durable local Derived job lifecycle
- at-least-once execution + idempotent result
- input fingerprint/generation
- deletion/correction invalidation priority
- crash recovery
- external model利用時のSecret/Sensitivity policy適用。外部Derived処理もA7で確定したHard Policy/Egress Decision Coreを再利用し、C4独自のallow経路を作らない

C4はAI outputをCanonical USER_EXPLICIT truthへ昇格させる権限を持たない。

---

# 8. SENSITIVE one-time override P0 decision

v1.1では将来の外部SENSITIVE one-time overrideを許容可能な設計として記載した。

Slice A/R6では安全のため実装していない。

P0 Product Proofでは以下に固定する。

> **SENSITIVE external one-time overrideは実装しない。外部送信はdefault denyのまま。**

理由:

- Founder Proofに必須ではない。
- Passive Recall / Trusted Intentとの組み合わせで誤操作面積が増える。
- Security invariantを先に証明する方がProduct Proof上重要。

将来必要性が実測された場合、resource × destination × purpose × one-time confirmationを独立Contractとして追加する。

これはv1.1の将来Optionを削除するのではなく、P0 Scopeから明示延期する決定である。

---

# 9. R1 credential transport hardening

Generic public-web fetcher R1はHTTP/HTTPSを扱えるが、credential付きrequestについて以下をHard Ruleとする。

```text
credential_ref != null
=> HTTPS required
=> HTTP downgrade redirect forbidden
```

Plain HTTPはunauthenticated public fetchに限定する。

CredentialをHTTPへ送らない。

---

# 10. Mobile capture transport authenticity

R4のcreate-only mobile architectureは維持するが、iOS outboxがiCloud等のshared/synced transportを通る場合、payload hashだけでは「内容が変わっていない」ことしか証明できず、「paired user deviceから来た」ことは証明できない。

P0では以下をHard Ruleとする。

```text
shared/synced mobile envelope
-> paired-device authenticity verification
-> payload/hash/schema verification
-> only then IOS_SHARE_* user-originated provenance
```

- device private signing materialはiOS Keychain / Secure Enclave-class storageから出さない。
- Macは明示Pairingされたpublic verification identityのみを信頼する。
- signatureはimmutable envelope identityとpayload hash/bytesをcoverする。
- unknown / revoked key、signature failure、hash mismatch、malformed canonicalizationはfail closed。
- signatureはreplay protectionではない。replay convergenceはA3/A4 idempotencyが所有する。
- untrusted contentやtransport上のmetadataから新しいtrusted keyを登録してはならない。

Exact platform API / signing algorithmはimplementation-time verificationとするが、shared/synced transport利用時のauthenticity boundary自体はP0必須とする。

---

# 11. Export ownership

v1.1でData Management / ExportはP0 Control Plane責務に含まれる。

R7 UIだけではportable exportのintegrity semanticsが不足するため、C5を追加する。

P0 exportは:

- Canonical authoritative state
- deletion history
- schema/checksum manifest

を含むportable archiveとし、Derived/index/runtime/credentialをauthorityとして持ち出さない。

R7はC5を呼ぶ。

---

# 12. Capability Router ownership

v1.1でP0 Interface OnlyとしたCapability Routerは、C6が共通interface ownerとなる。

- A9/R8/R9がHost-specific capability evidenceを作る。
- C6がversioned registry/routerを提供する。
- R6/A7がpermission/egressを別途判定する。

`capability supported` と `permission granted` は統合しない。

---

# 13. Founder Product Proof phase dependency

R10の依存を明確化する。

### F0 Instrument Validation

R7 full Control Plane UIは必須ではない。内部操作でinstrumentationを検証可能。

### F1 external Founder Product Proof

R7の最低限Control Planeを必須とする。

少なくとも:

- connection state
- privacy/permission
- health/action-required
- backup/recovery access
- delete/export access

がユーザーに提供されること。

Invisible UXは「UIがない」ことではなく「不要な日常操作を要求しない」ことである。

---

# 14. Updated P0 foundation order

実装依存順の最初を以下へ更新する。

```text
C0 Active Vault Locator
A1 Canonical Source Schema
A2 Source Atomic Writer
C1 Generic Persistent Object Persistence
A3 Capture/Secret Guard
A4 Single Writer Worker
A5 Index
A6 Source Deletion
C3 Generic Deletion
A7/A8/A9/A10
R1 Acquisition
C2 Effective Source Representation
...
C4 before B2/B5/B7 background processing
C5 before R7 Export completion
C6 before R8 multi-host expansion / R6 passive host routing completion
```

詳細な完全順序はFinal Implementation Execution Plan v2.0を正とする。

---

# 15. Documentation completion gate update

「P0 responsibility owner = 0 gaps」と宣言するために最低限以下を満たす。

- Canonical object persistence ownerが全object typeで明確
- Derived processing queue ownerが明確
- root Sourceとacquired contentのRecall bridgeが明確
- generic deletion ownerが明確
- active Vault locator ownerが明確
- export ownerが明確
- capability router ownerが明確
- P0-sensitive override decisionが明確
- cross-contract Golden Casesが存在

本書 + C0-C6で上記を閉じる。

---

# 16. Final Decision Ledger v1.2.2

## 【確定：Cross-cutting Foundation】

- C0 is sole active Vault locator authority.
- C1 is generic persistent-object write mechanics / Canonical mutation owner.
- C2 owns Source -> effective representation -> index/trace bridge.
- C3 owns generic deletion truth and practical purge boundary.
- C4 owns Derived batch/recompute job lifecycle.
- C5 owns portable Canonical export semantics.
- C6 owns common capability registry/router interface.

## 【確定：P0 Security】

- SENSITIVE external one-time override is deferred beyond P0.
- credentialed generic HTTP fetch is forbidden; HTTPS required.
- shared/synced mobile capture requires paired-device authenticity before user-originated provenance.
- external model Derived processing cannot bypass Secret/Sensitivity policy.
- generic deletion unknown/corrupt state fails closed.

## 【確定：P0 Product Proof】

- R7 minimal Control Plane required for external Founder F1.
- R7 may be omitted only for internal F0 instrumentation validation.

## 【未変更】

- Personal Discovery is core value.
- Past is evidence, not authority.
- Outcomes over archives.
- Invisible operation.
- Connect once. Never summon.
- User-owned Local/Vault-first architecture.
- Product Proof before scale.

---

# 17. 閉鎖判定

v2.0横断レビューで検出された以下は本書で責務を確定した。

- B系Canonical Object persistence gap
- acquired Source body -> Recall/index gap
- generic deletion gap
- Derived queue/orchestrator gap
- physical purge interpretation conflict
- SENSITIVE override ambiguity
- Vault Locator implementation-order gap
- Export contract gap
- credential over HTTP hardening gap
- Capability Router ownership gap
- R10/R7 phase dependency ambiguity
- package manifest requirement
- mobile synced-transport authenticity boundary
- raw acquired HTML/PDF -> safe local text projection boundary
- external-model Derived processing -> shared A7-class policy/egress decision boundary
- active Founder Product event/denominator continuity across managed restore

**これらを反映したv2.1 Documentation Bundleで再監査を行い、PASS時のみDocumentation-level closureを再宣言する。**
