# TSUZU P0 C5 — Canonical Export / Portability Contract v0.1

- Date: 2026-09-09
- Status: **Cross-cutting User Ownership Contract / Closed / Ready to implement**
- Canonical basis: v1.1 User Ownership, Data Management, Export; Vault-first / portability principle
- Depends on: C0, C1, C3, R5 integrity classification; invoked by R7 Control Plane
- Scope: user-triggered portable export of authoritative TSUZU state with checksums/schema inventory and deletion history protection
- Non-scope: cloud sync, automatic import/reimport, custom encrypted archive format, team sharing, public API/SDK

---

# 0. Decision

“User-owned” must be operational, not branding.

P0 provides one deterministic **Portable Canonical Archive** export that can be inspected/copied by the user and does not depend on TSUZU's disposable index/runtime state.

```text
R7 explicit Export
 -> C5 coherent read snapshot
 -> Portable Archive staging
 -> validate/checksum
 -> atomic finalization
```

---

# 1. Included by default

- LIVE Canonical Sources and payloads
- immutable eligible Source Versions
- Canonical Conversation records in supported scope
- Canonical Decision Assertions/Evidence/Correction Events/Experience records as defined by owner Contracts
- superseded but still LIVE history required to preserve Judgment Evolution
- generic C3 Deletion Ledger records (body-free)
- schema inventory and object registry version
- export manifest/checksums

The archive preserves provenance/history but does not revive tombstoned bodies.

---

# 2. Excluded by default

- SQLite/FTS/embeddings/indexes
- runtime queues/leases/cache
- temporary staging
- telemetry bodies (none should exist)
- OS Keychain credentials/tokens/cookies/private keys
- transient model prompts/responses not otherwise part of a defined persistent object
- tombstoned payload bytes

Derived objects are excluded from the required P0 portable archive because they are rebuildable and not authority. A future optional Derived export may be additive.

---

# 3. Restricted/secret anomaly behavior

Credential material must not be Canonical Knowledge. If export preflight detects high-confidence RESTRICTED material in a location that should be exported:

```text
EXPORT_BLOCKED_RESTRICTED
```

Do not silently omit a Canonical object and claim complete export.
Do not automatically include the secret.
Surface remediation through R7.

---

# 4. Export manifest

```yaml
export_format: TSUZU_PORTABLE_CANONICAL_ARCHIVE
export_format_version: "1.0.0"
export_id:
created_at:
source_vault_id:
source_locator_generation:

schema_inventory:
object_counts_by_type:
ledger_record_count:

files_manifest:
  - relative_path:
    sha256:
    bytes:

excluded_classes:
  - DERIVED_REBUILDABLE
  - RUNTIME
  - CREDENTIAL
```

Manifest itself contains no user content body.

---

# 5. Coherent snapshot boundary

P0 favors correctness over zero-pause export.

Options allowed:

- reuse R5 coherent maintenance/read barrier; or
- create a validated immutable temporary snapshot through a filesystem-safe mechanism.

Required property:

> Export must not combine half of object revision N and half of revision N+1.

Capture can queue during a short barrier according to existing durable capture semantics.

---

# 6. Deletion semantics

Before archive finalization:

- C3 generic ledger is read/validated.
- tombstoned object payload is excluded.
- deletion records are included so another TSUZU-aware future importer cannot naïvely resurrect stale material from mixed archives.

C5 is not a backup replacement: R5 remains the supported recovery Contract.

---

# 7. Privacy / UX

R7 must warn that the archive can contain PERSONAL/SENSITIVE user content.

P0 does not implement a proprietary encryption engine. User can choose a protected destination using OS/filesystem tools.

Export operation requires explicit user action and destination choice.

No automatic external upload.

---

# 8. Atomic finalization

```text
1. preflight destination capacity/write permission
2. resolve C0 generation
3. coherent snapshot/barrier
4. export to unique staging directory/file
5. calculate checksums
6. verify manifest/object coverage
7. recheck source generation/revision boundary as required
8. mark archive COMPLETE
9. atomic move/rename to chosen final destination where supported
10. body-free export receipt
```

Partial staging is never presented as a valid complete archive.

---

# 9. Failure behavior

| Failure | Behavior |
|---|---|
| destination full | fail; no valid final archive |
| Canonical corruption | fail complete export; surface recovery |
| C3 ledger unavailable | fail closed |
| RESTRICTED anomaly | block export pending remediation |
| file changes outside coherent snapshot | retry/new snapshot |
| checksum mismatch | archive invalid; do not mark complete |
| destination is external sync service | user-controlled destination only; TSUZU does not grant connector authority |

---

# 10. Golden cases

1. **Portable core** — export contains Canonical content and no SQLite/queue.
2. **Credential exclusion** — OS Keychain secret absent.
3. **Tombstone** — deleted body absent, deletion record present.
4. **Sensitive data** — exported locally with explicit privacy warning, not auto-uploaded.
5. **Interrupted export** — no COMPLETE archive.
6. **Corrupt source** — fail rather than silently skip.
7. **Superseded history** — retained when LIVE.
8. **Manifest verification** — every exported file checksum matches.

---

# 11. Acceptance criteria

- [ ] R7 Export invokes C5 rather than ad-hoc file copy.
- [ ] archive is complete/validated or clearly failed.
- [ ] Canonical history is portable without Derived/runtime dependencies.
- [ ] credentials and tombstoned bodies are absent.
- [ ] deletion ledger is preserved body-free.
- [ ] no automatic external upload occurs.
- [ ] export does not claim to be R5 recovery backup.

---

# 12. One-line contract

> **C5 turns user ownership into a testable feature: the authoritative record can leave TSUZU in a coherent, checksummed, credential-free archive without dragging along disposable indexes or deleted bodies.**
