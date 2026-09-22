# TSUZU Implementation Rules v1.0

**Status:** Canonical Implementation Rule  
**Target:** TSUZU  
**Primary Stack:** Tauri v2 / React / Vite / TypeScript  
**Native Layer:** Rust  
**Purpose:** Local-first Knowledge ApplicationとしてOSアクセス能力を確保しながら、Rust依存と実装複雑性を最小化する。

---

# 1. 最重要方針

TSUZUでは、

**「Tauriで作る」≠「Rustで作る」**

と定義する。

基本構造：

```text
React
  ↓
TypeScript Application
  ↓
Domain
  ↓
Tauri Bridge
  ↓
Rust / Plugin
  ↓
OS
```

Application Logicの大部分はTypeScriptで実装する。

Rustは、

> OSへ到達するための薄い境界

として扱う。

---

# 2. Technology Boundary

TypeScriptで実現可能な処理をRustへ移動しない。

Rustを使用するのは主に、

- Filesystem
- OS integration
- Native capability
- 高負荷処理
- Security boundary
- TypeScriptでは不可能な処理

に限定する。

「Rustの方が高速」というだけでは移動理由にならない。

---

# 3. Project Structure

```text
src/
├─ app/
├─ features/
│  ├─ capture/
│  ├─ library/
│  ├─ retrieval/
│  ├─ connections/
│  ├─ backup/
│  └─ settings/
│
├─ domain/
├─ services/
├─ ingestion/
├─ storage/
├─ platform/
│  └─ tauri/
│      ├─ filesystem.ts
│      ├─ database.ts
│      ├─ shell.ts
│      └─ commands.ts
│
├─ components/
├─ types/
└─ utils/

src-tauri/
├─ capabilities/
├─ src/
│  ├─ lib.rs
│  └─ commands/
├─ Cargo.toml
└─ tauri.conf.json
```

Tauri公式でもJavaScript側とRust側を分離する構造を標準としている。

---

# 4. Tauri Bridge

Frontendから、

```ts
invoke(...)
```

を直接呼び散らさない。

禁止：

```text
Screen
 └→ invoke()

Component
 └→ invoke()

Hook
 └→ invoke()
```

原則：

```text
UI
↓
Service
↓
platform/tauri/*
↓
invoke
↓
Rust
```

とする。

これにより、Rust/Tauri依存を1箇所へ閉じ込める。

---

# 5. Rust Command

Rust Commandは、

- OS処理
- File IO
- Native処理

に限定する。

業務判断をRustへ入れない。

例えば、

```text
このKnowledgeを重要と判定する
```

はTypeScript Domain。

```text
このファイルを安全に読み込む
```

はRust/Tauri。

とする。

---

# 6. Command単位

`lib.rs`を巨大化させない。

Commandが増えた場合、

```text
commands/
├─ files.rs
├─ backup.rs
├─ import.rs
└─ system.rs
```

等へ責務別に分割する。

Tauri公式もcommandを別moduleへ分離可能としている。

---

# 7. Async

File IO、Network、重い処理はUI threadを塞がない。

Tauri公式では重い処理についてasync commandが推奨されているため、IO処理ではこれを基本とする。

---

# 8. Error Handling

User operationから到達するRustコードで、

```rust
unwrap()
expect()
panic!()
```

へ安易に依存しない。

回復可能なエラーは原則、

```rust
Result<T, E>
```

でFrontendへ返す。

Frontendでは、

```text
technical error
↓
application error
↓
user presentation
```

へ変換する。

Rust error messageをそのままユーザーに表示しない。

---

# 9. Tauri Event

Eventを通常のrequest/response代替として乱用しない。

基本：

```text
request → command
stream → channel
broadcast / event → event
```

とする。

Tauri公式でもeventは大容量・高throughput通信向けではなく、StreamingにはChannelが適しているとされている。

---

# 10. Capabilities / Permissions

Tauri Capabilityは**最小権限**で定義する。

禁止：

```text
とりあえず全filesystem許可
とりあえず全shell許可
```

必要な、

```text
window
command
path
operation
```

だけ許可する。

Capability変更はSecurity Changeとして扱う。

Tauri v2はCapability/PermissionによってWebViewから利用可能なCore/Plugin機能を制御できるため、これをSecurity Boundaryとして利用する。

---

# 11. Filesystem

TSUZUではFilesystemが重要だが、

**任意パスへ無制限アクセス可能にしない。**

アクセス対象は原則、

- App data directory
- TSUZU Vault
- ユーザーが明示的に選択した場所

に限定する。

Path traversalを前提に入力を検証する。

Frontendから渡されたpathを無条件で信用しない。

---

# 12. Shell

Shell executionはデフォルト禁止。

必要になった場合も、

```text
任意command
```

をFrontendから渡して実行してはならない。

許可された操作を個別Commandとして定義する。

例えば、

```text
openVaultInFinder()
```

は許容可能。

```text
runShell(command: string)
```

は原則禁止。

---

# 13. TSUZUのSoT

DatabaseとFilesystemで二重の正本を作らない。

Canonical設計で正本とされたデータをSoTとする。

Derived index、検索index、cache、embedding等は、

**必要なら再構築できるデータ**

として区別する。

```text
Canonical Data
≠
Index
≠
Cache
```

を維持する。

---

# 14. Migration

Schema変更は必ずversion管理する。

禁止：

- App起動時の無条件破壊変更
- MigrationなしのSchema変更
- Backupなしの不可逆変更

Migrationは最低限、

```text
old
↓
migrate
↓
new
↓
read/write
```

をテストする。

Backup / Restore / Recovery契約と矛盾しないことを確認する。

---

# 15. Backup

Backup処理はApplication dataを単純copyするだけではなく、

Canonical Backup Contractに従う。

最低限、

```text
backup
restore
restart
read
```

まで確認する。

「Backup fileを作れた」だけでは成功としない。

---

# 16. React

ReactはUIレイヤーとして扱う。

Componentから、

- File IO
- DB migration
- Parsing
- Knowledge extraction
- Backup
- Tauri invoke

を直接実行しない。

ReactのEffectは外部システムとの同期に限定する。

---

# 17. TypeScript

Application LogicはTypeScriptを中心に置く。

`strict: true`。

`any`禁止を原則とする。

RustとのIPC boundaryでは特に、

- Request type
- Response type
- Error type

を定義する。

例えば、

```text
readVaultFile()
```

ならFrontend側でも戻り値の型を持つ。

---

# 18. Ingestion

URL、YouTube、Markdown、外部ファイル等の取り込みは、

```text
Fetch
↓
Parse
↓
Normalize
↓
Extract
↓
Persist
```

へ分離する。

1関数で全部処理しない。

Parserは可能な限りPure Functionとしてテスト可能にする。

---

# 19. External Content

外部データは信用しない。

- HTML
- Markdown
- JSON
- File
- Imported metadata

はすべてuntrusted inputとして扱う。

読み込んだ内容から自動でShell Commandを実行しない。

---

# 20. Dependency

Frontend dependencyとRust crateの両方を最小限にする。

追加前に、

```text
既存APIで可能か
公式Pluginがあるか
自前の小さい実装で十分か
保守されているか
Security surfaceを増やさないか
```

を確認する。

Rust crateをAI判断だけで追加しない。

---

# 21. Native / Rust複雑化防止

以下は禁止。

- Business LogicのRust移植
- Rust独自Domain Modelの二重管理
- 複雑なMacro
- 不要なTrait abstraction
- 過剰なGeneric
- 独自async runtime
- 独自Pluginの早期開発

Rustは「賢く」書くより「単純に」書く。

---

# 22. Desktop First

TSUZUの初期実装ではDesktopを第一対象とする。

Tauri v2がmobileをサポートすることを理由に、

```text
desktop + iOS + Android
```

を同時最適化しない。

Mobile要件が確定した時点で追加検証する。

---

# 23. Testing

## TypeScript

- Domain
- Parser
- Normalization
- Migration orchestration
- Backup orchestration

## Rust

- File operations
- Path validation
- Command error
- Boundary handling

## Integration

最低限、

```text
Create
↓
Save
↓
Close
↓
Restart
↓
Read
```

を検証する。

Backupについては、

```text
Backup
↓
Delete/alter
↓
Restore
↓
Restart
↓
Read
```

まで確認する。

---

# 24. Security Change

以下は通常Featureと分けてレビューする。

- Capability追加
- Filesystem scope拡張
- Shell permission
- External URL handling
- Credential handling
- Auto update
- Plugin追加

---

# 25. AI禁止事項

AIは独断で、

- RustへLogicを移動しない
- Capabilityを広げない
- Shell accessを追加しない
- New crateを大量追加しない
- Databaseを正本化しない
- Vault構造を変更しない
- Backup形式を変更しない
- Schemaを破壊変更しない
- Native mobile codeを追加しない
- Tauri Pluginを自作しない

---

# 26. 変更原則

一つの変更は一つの目的。

Feature追加時に、

```text
Rust refactor
+
React refactor
+
DB migration
+
Dependency update
```

をまとめて行わない。

必要なら段階的に行う。

---

# 27. 完了条件

```text
[ ] TypeScript check
[ ] frontend test
[ ] Rust compile
[ ] Rust test
[ ] Tauri dev起動
[ ] Capability確認
[ ] File access確認
[ ] Failure path確認
[ ] Restart確認
[ ] 既存Data互換性確認
```

Migration / Backup変更時：

```text
[ ] migration test
[ ] backup test
[ ] restore test
[ ] recovery test
```

---

# 28. AIの報告形式

```text
変更内容:
TypeScript変更:
Rust変更:
Tauri Capability変更:
Storage変更:
Schema変更:
追加dependency/crate:
Security影響:
検証結果:
残存リスク:
```

RustまたはCapabilityに変更がなかった場合も、

```text
Rust変更: なし
Capability変更: なし
```

と明記する。

---

# 29. TSUZU最重要原則

> TypeScriptをApplicationの中心にする。

> RustはOS Boundaryに閉じ込める。

> invokeをFrontend全体へ漏らさない。

> 最小権限を守る。

> DB・Index・CacheとCanonical Dataを混同しない。

> Backupは「作成」ではなく「復元できた」までを成功とする。

> AIが理解しやすい高度なArchitectureより、人間が追える単純なArchitectureを優先する。