# TSUZU P0 R3 — Historical Bootstrap / Apple Notes / Markdown Import Contract v0.1

- Date: 2026-09-09
- Status: **Implementation Contract / Closed / Ready to implement**
- Canonical basis: v1.1 Small Historical Bootstrap + v1.2/v1.2.1 Apple Notes / local source roadmap
- Dependencies: A1-A4, A6, R1 only for imported URL follow-up acquisition
- Scope: bounded one-way historical bootstrap from Apple Notes and Markdown/local folders
- Non-scope: full migration, continuous two-way sync, editing source apps, conflict merge with Apple Notes/Obsidian, Drive/Notion production connectors

---

# 0. Decision

R3 exists to solve cold start without making users migrate their life into TSUZU.

Default product behavior is a **small, bounded, one-way import** of recent user-selected history, approximately the 30–100 item range described by the canonical bootstrap concept.

Imported items enter the same A3/A4 safety/materialization path as direct Capture wherever possible.

---

# 1. Core invariants

1. Import is optional; TSUZU remains useful without full migration.
2. Source systems are read-only from R3.
3. Import does not modify/delete/reorganize Apple Notes/Markdown.
4. Each imported snapshot is immutable after Canonical commit.
5. Restricted secret material is not newly copied into TSUZU Knowledge.
6. Import provenance must say where/when the snapshot came from.
7. Import retry is idempotent; cancellation leaves committed items valid.
8. A repeat import must not silently duplicate an already imported identical external snapshot.
9. Changed external content is not overwritten into an old Source payload.
10. Coverage is explicitly recorded; unimported history is not treated as nonexistent.

---

# 2. Connector interface

```yaml
historical_source_adapter:
  adapter_id:
  source_type: APPLE_NOTES | MARKDOWN_FOLDER
  capabilities:
    enumerate: true
    read_item: true
    write_back: false
    delete_source: false
    continuous_watch: false
```

```yaml
historical_item_descriptor:
  external_item_key:
  title_hint:
  created_at_observed:
  modified_at_observed:
  container_hint:
  media_type:
  size_hint:
```

Connector-specific API details remain implementation-time verified.

---

# 3. Bootstrap selection

P0 selection supports at least:

- most recent N eligible items;
- optional date window;
- optional explicitly selected folder/container where adapter supports it.

Default UI should favor a small recent sample rather than `Import everything`.

The 30–100 range is a bootstrap target, not a hard technical limit. The exact default is configurable and must be recorded in the import session.

---

# 4. Import Session

```yaml
import_session:
  import_session_id:
  adapter_id:
  started_at:
  completed_at:
  selection:
    mode: RECENT_N | DATE_WINDOW | CONTAINER
    recent_n: integer | null
    from: timestamp | null
    to: timestamp | null
    container_ref: string | null
  enumerated_count:
  eligible_count:
  committed_count:
  skipped_count:
  blocked_count:
  failed_count:
  cancelled: boolean
```

No imported body is stored in session telemetry.

---

# 5. Imported item identity / idempotency

R3 distinguishes:

- TSUZU `source_id`: Canonical identity of the imported snapshot;
- `external_item_key`: connector-local identity/locator;
- `external_snapshot_fingerprint`: material snapshot fingerprint.

```text
external_snapshot_fingerprint =
SHA256(adapter_id + external_item_key + body_sha256 + observed_modified_at)
```

A body-free Import Receipt maps fingerprint -> source_id.

### Same item, same snapshot
Return `ALREADY_IMPORTED`; do not create another Source due to retry/re-run.

### Same item, changed body
Create a new immutable imported Source snapshot and link:

```text
previous_snapshot_ref: <source_id>
```

Do not mutate the old payload.

### Independent direct user Capture
A later explicit Share/Capture remains a distinct user action under A1/A3 semantics even if bytes match an imported snapshot.

---

# 6. Imported Canonical Source extension

R3 extends capture provenance/capture method with implementation values:

```text
IMPORT_APPLE_NOTES
IMPORT_MARKDOWN
```

Canonical Source stores:

```yaml
provenance:
  origin: IMPORTED
  actor: USER
  explicitness: IMPORT_REQUESTED

import:
  adapter_id:
  external_item_key_hash:
  external_modified_at_observed:
  import_session_id:
  previous_snapshot_ref: null | uuid
```

Raw external item IDs/paths that reveal sensitive filesystem structure should be minimized; use hashed/body-free references where sufficient.

---

# 7. Apple Notes boundary

R3 Apple Notes adapter is one-way snapshot import.

Requirements:

- explicit OS/user permission;
- read only the selection scope;
- no deletion/editing/re-foldering;
- rich content may be normalized into a preserved export representation, but fidelity must be declared;
- attachments are imported only within configured size/type boundaries;
- unsupported attachment remains represented as `SKIPPED_ATTACHMENT` metadata, not silently lost.

Exact Notes API/bridge mechanism is implementation-time validated and must not be baked into Core.

---

# 8. Markdown folder boundary

Markdown import:

- reads user-selected local folder/files;
- never edits source files;
- copies bytes into TSUZU Canonical Source snapshots;
- symlinks are not followed outside the selected root by default;
- path traversal is rejected;
- hidden/system files are not implicitly imported unless selected policy allows;
- `.git`, build caches, dependency directories and obvious runtime directories are excluded by default for folder bootstrap.

R3 is not an Obsidian sync engine.

---

# 9. Secret / sensitivity behavior

Each item is streamed through local Secret/Sensitivity Guard before durable Canonical copy.

High-confidence RESTRICTED item:

```text
no TSUZU body copy
body-free blocked receipt
item counts as BLOCKED, not FAILED
```

SENSITIVE may be stored locally under Canonical policy but remains external-egress default deny.

A blocked item does not abort the whole import session.

---

# 10. Imported URL handling

If an Apple Note/Markdown item contains URLs, R3 does not automatically explode every URL into separate Sources.

The note itself is the imported Source.

Only explicit extraction rules added later may create URL Candidates. If the imported item itself is a pure URL source and adapter can unambiguously represent that, R3 may map it to `kind: URL`, after which R1 acquisition applies.

This prevents uncontrolled fan-out during bootstrap.

---

# 11. Cancellation / crash semantics

Import commits one item at a time through A3/A4.

- cancellation stops new item admission;
- already committed Sources remain valid;
- active item either commits atomically or leaves no partial Canonical Source;
- resume uses Import Receipts to skip already identical snapshots;
- adapter enumeration may be rerun; Source IDs are not regenerated for already committed fingerprints.

---

# 12. Coverage marker

Because bootstrap is partial, R3 writes body-free coverage metadata:

```yaml
history_coverage:
  source_type:
  import_session_id:
  selection_mode:
  observed_oldest_item_at:
  observed_newest_item_at:
  enumerated_count:
  committed_count:
  incomplete_reasons: []
```

Discovery/Pattern systems may use this only to qualify statements such as:

> "TSUZUが観測できた範囲では"

Coverage never implies that non-imported history does not exist.

---

# 13. Failure behavior

| Failure | Behavior |
|---|---|
| permission denied | no import; ACTION_REQUIRED |
| item disappears during read | skip/re-enumerate; no partial Source |
| file changed while reading | retry from new snapshot; do not commit inconsistent bytes |
| secret scanner unavailable | fail closed for new body copy |
| single item corrupt/unsupported | skip item with reason; continue session |
| whole adapter unavailable | DEGRADED/ACTION_REQUIRED, committed items retained |
| cancel | stop admissions; preserve committed items |
| duplicate receipt mismatch | hard conflict; do not overwrite mapping |

---

# 14. Golden Cases

## R3-G1 Recent Bootstrap
Recent N eligible Notes produce bounded independent Sources with IMPORTED provenance.

## R3-G2 No Full Migration Requirement
User can complete onboarding with a small selection; no requirement to import all history.

## R3-G3 Same Snapshot Re-run
Same import repeated -> ALREADY_IMPORTED, no duplicate Source.

## R3-G4 Changed Note Snapshot
Changed source item -> new immutable Source linked to previous snapshot.

## R3-G5 Independent Direct Capture
Same content later explicitly shared -> separate Source because user action is distinct.

## R3-G6 Restricted Historical Item
Secret-bearing item creates no new TSUZU body copy and session continues.

## R3-G7 Cancel/Resume
Cancel midway then resume -> committed items preserved, no duplicates.

## R3-G8 Markdown Symlink Escape
Symlink/path traversal outside selected root is not imported.

## R3-G9 Partial Attachment Support
Unsupported attachment is visibly marked in metadata/coverage, not silently treated as complete.

## R3-G10 Observation Bias Marker
Discovery downstream can identify that only bounded history was imported.

---

# 15. Implementation tasks

- R3.1 historical adapter interface
- R3.2 bounded selection/session schema
- R3.3 Apple Notes read-only spike
- R3.4 Markdown safe enumerator
- R3.5 import fingerprint/receipt ledger
- R3.6 A3/A4 import bridge
- R3.7 coverage marker
- R3.8 cancel/resume and health
- R3.9 Golden/adversarial tests

---

# 16. Acceptance criteria

- [ ] user can bootstrap recent history without full migration.
- [ ] Apple Notes/Markdown adapters are read-only.
- [ ] same imported snapshot does not duplicate on retry/re-run.
- [ ] changed external content creates a new immutable snapshot rather than overwrite.
- [ ] direct user Capture semantics remain distinct from import idempotency.
- [ ] Secret/Sensitivity Guard runs before new Canonical body copy.
- [ ] import can cancel/resume without corrupting/duplicating committed Sources.
- [ ] partial coverage is recorded and downstream can avoid overclaiming.
- [ ] no uncontrolled URL/attachment fan-out.
- [ ] R3-G1..G10 pass.

---

# 17. Explicit non-goals

- continuous sync;
- two-way editing;
- full Notes migration;
- Obsidian replacement;
- Drive/Notion connector;
- AI classification required during import;
- background import of unselected entire filesystem.

---

# 18. Source-derived vs closure decisions

## Canonical source-derived
- Small Historical Bootstrap;
- recent roughly 30–100 items concept;
- Apple Notes/Markdown as bootstrap sources;
- no forced full migration;
- Canonical/Derived + Secret rules.

## R3 closure decisions
- one-way snapshot import;
- stable import fingerprint/receipt idempotency;
- changed item -> new immutable snapshot;
- coverage marker to preserve observation limits;
- no automatic URL fan-out;
- safe Markdown root/symlink boundary.

---

# 19. One-line contract

> **R3 gives TSUZU enough real personal history to produce an early Aha without demanding migration, by importing a small read-only snapshot of existing Notes/Markdown safely, idempotently and with explicit coverage limits.**
