# TSUZU P0 C0 — Active Vault Locator / Root Boundary Contract v0.1

- Date: 2026-09-09
- Status: **Cross-cutting Foundation Contract / Closed / Ready to implement**
- Canonical basis: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1
- Applies to: A2, A4, A5, A6, B1-B7 where persistent state is resolved, R1-R7, especially R5 cutover
- Scope: active Vault identity, root resolution, generation-safe handles, filesystem capability preflight, atomic locator cutover
- Non-scope: backup contents, schema migration semantics, multi-writer consensus, sync conflict merge, cloud discovery

---

# 0. Decision

P0では、各moduleがVault pathを個別設定・hard-code・自動探索してはならない。

すべてのpersistent/read-write componentは、**1つのlocal Active Vault Locator**を通じて現在のVaultを解決する。

```text
component
  -> C0 resolveActiveVault()
  -> vault_id + root + generation + capabilities
  -> operation
```

R5 Restore / MigrationによるVault切替は、directory内容をlive pathへ上書きするのではなく、検証済みcandidate Vaultへ**locatorをatomicに切り替える**。

---

# 1. Hard invariants

1. Active Vaultはpath文字列だけではなく`vault_id`で識別する。
2. LocatorはActive Vaultの内部に置かない。
3. Locatorがmissing/corrupt/ambiguousならfail closedし、近傍directoryを勝手に探索しない。
4. すべてのwriterは操作開始時にlocator generationを取得する。
5. long-running writeのcommit前にgenerationが変化していないことを確認する。
6. R5 cutoverはexpected generation付きCAS相当で行う。
7. old Vaultとnew Vaultを同時にmutable writerとして公開しない。
8. Vault rootはuser-controlled filenameやremote contentから決めない。
9. symlink/reparse/path traversalにより許可root外へ書かない。
10. filesystem capabilityが不明ならCanonical writeを開始しない。
11. Locator recordへcredential/body/contentを保存しない。
12. locator changeはbody-free audit/receiptを残す。

---

# 2. Locator record

概念Schema:

```yaml
locator_schema_version: "1.0.0"
locator_revision: 7

active:
  vault_id: uuid
  root_ref: platform_path_or_bookmark_reference
  root_fingerprint: sha256
  volume_identity: opaque_platform_identity
  generation: 12

capabilities:
  local_read: true
  local_write: true
  same_volume_staging: true
  atomic_rename: true
  no_clobber_publish: true
  coordinated_access: SUPPORTED | NOT_REQUIRED | UNSUPPORTED

updated_at:
updated_by_operation_id:
```

`root_ref`をHost Context / telemetry / external modelへ送らない。

---

# 3. Storage location

LocatorはVault外のTSUZU-managed local application stateに置く。

概念例:

```text
~/Library/Application Support/TSUZU/control/active-vault.json
```

実際のplatform pathは実装stackで確定してよいが、以下は必須。

- synced Canonical Vault内部ではない
- credential storeではない
- user content storageではない
- atomic replace可能
- OS account protection下

---

# 4. Public interface

```text
resolve_active_vault() -> VaultHandle
preflight_vault(root_ref) -> VaultCapabilityReport
compare_generation(handle) -> CURRENT | STALE
switch_active_vault(expected_generation, candidate_handle, operation_id) -> SwitchResult
inspect_locator() -> body-free LocatorHealth
```

### VaultHandle

```yaml
vault_id:
root_ref:
generation:
capability_report_hash:
resolved_at:
```

Handleはauthority tokenではない。write permissionはA2/C1 Single Writer Boundaryが別途判定する。

---

# 5. Filesystem capability preflight

最低限確認する。

- readable/writable
- stagingとCanonicalを同一volumeに置ける
- atomic rename/replace
- no-clobber create semantics
- directory/file fsync相当の利用可否
- symlink escape防止
- File Provider/iCloudの場合のcoordination strategy

安全なCanonical atomicityを実現できないfilesystemはP0 Vaultとしてunsupported。

Network share / arbitrary SMB/NFSをP0 supported rootとしない。

---

# 6. Generation binding

以下のraceを禁止する。

```text
worker resolves old Vault A
R5 switches to Vault B
worker commits into old Vault A
```

write operationは:

```text
resolve generation G
  -> compute/stage
  -> before publish verify locator generation == G
  -> if changed: abort/requeue against new Vault
```

R5 maintenance barrier中はnew Canonical mutationをboundedに停止/queueできる。

---

# 7. R5 cutover

R5 candidateがREADYになった後のみ:

```text
1. verify maintenance lock
2. expected_generation = current G
3. verify candidate vault_id != current vault_id
4. atomic locator replace G -> G+1
5. read-back locator
6. health smoke test through newly resolved handle
7. if failure before maintenance release:
     rollback locator G+1 -> G+2 pointing old Vault
8. release maintenance lock
```

Rollbackでもgenerationは単調増加させる。古いhandleの再利用を防ぐため。

---

# 8. Failure behavior

| Failure | Required behavior |
|---|---|
| locator missing | RED / fail closed; no arbitrary directory scan |
| locator corrupt | RED / recovery action required |
| root unavailable | read/write denied; health degraded |
| generation changes mid-write | abort publish / retry against current Vault |
| candidate cutover CAS mismatch | do not switch; re-evaluate |
| filesystem lacks no-clobber | unsupported as mutable Canonical Vault |
| path resolves outside approved root | deny |
| old Vault still mounted | not an authority; locator decides current Vault |

---

# 9. Golden cases

1. **Single resolution** — A2/A5/R1 resolve identical active vault_id/generation.
2. **Mid-write cutover** — staged write against old generation cannot publish after R5 switch.
3. **Corrupt locator** — system fails closed rather than choosing newest-looking directory.
4. **Cutover rollback** — post-switch health failure restores old Vault through a new generation.
5. **Symlink escape** — Canonical write outside root is denied.
6. **Unsupported filesystem** — preflight blocks initialization before first Canonical write.
7. **Old handle reuse** — stale handle is rejected after generation advance.

---

# 10. Implementation tasks

- C0.1 locator schema + codec
- C0.2 platform root reference abstraction
- C0.3 filesystem capability preflight
- C0.4 generation-aware VaultHandle
- C0.5 atomic CAS cutover + rollback
- C0.6 health projection + body-free receipt
- C0.7 Golden/fault tests

---

# 11. Acceptance criteria

- [ ] every persistent subsystem can resolve Vault only through C0.
- [ ] no writer hard-codes a live Vault root.
- [ ] locator corruption fails closed.
- [ ] generation change prevents stale commits.
- [ ] R5 can switch and rollback without mutating two active Vaults concurrently.
- [ ] capability preflight blocks unsupported storage.
- [ ] locator telemetry contains no user content/credential.

---

# 12. One-line contract

> **C0 makes “which Vault is current” a single generation-safe local authority so restore/migration can switch state without stale writers continuing to mutate the wrong Vault.**
