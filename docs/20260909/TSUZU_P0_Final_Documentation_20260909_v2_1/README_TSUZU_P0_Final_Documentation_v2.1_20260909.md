# TSUZU P0 Final Documentation v2.1 — README

- Date: 2026-09-09
- Status: **Current implementation-documentation package**
- Purpose: handoff package for implementation agents/humans. Product design is closed at P0 documentation level; code and Golden Case execution are not yet claimed.

---

# 1. Read this first

For any implementation task, minimum context is:

1. `TSUZU_P0_Contract_Index_v2.1_20260909.md`
2. the specific A/B/C/R Contract being implemented
3. `TSUZU_Canonical_Implementation_Closure_Addendum_v1.2.2_20260909.md`
4. `TSUZU_P0_Final_Implementation_Execution_Plan_v2.0_20260909.md`

Do **not** implement from one old A/B/R file in isolation when Contract Index says a Cross-cutting C Contract also applies.

---

# 2. Canonical read order

```text
Canonical Product Architecture v1.1
  -> Canonical Addendum v1.2
  -> Canonical Closing Addendum v1.2.1
  -> Canonical Implementation Closure Addendum v1.2.2
```

v1.2.2 has highest current implementation precedence but does not replace unchanged Product Constitution.

---

# 3. Current active Contract families

- `Slice_A/` — A1-A10: grounded local capture/recall core
- `Slice_B/` — B1-B11: Chronicle/Decision/Discovery/Product events
- `Cross_Cutting/` — C0-C6: shared persistence/deletion/materialization/runtime/export/capability mechanics
- `R_Contracts/` — R1-R10: Acquisition/mobile/recovery/passive/control/host/spike/Founder proof

Historical/superseded revisions are under `Historical/` and are **not current implementation authority**.

---

# 4. What changed from v2.0

The v2.0 review found cross-contract gaps even though individual Contracts were present.

v2.1 closes them through:

- C0 Active Vault Locator
- C1 Generic Persistent Object write mechanics / Canonical mutation
- C2 Effective Source Representation
- C3 Generic Deletion + purge boundary
- C4 Derived Processing Orchestrator
- C5 Canonical Export
- C6 Capability Registry/Router
- Canonical v1.2.2 closure
- active R1/R5/R6/R7/R8/R9/R10 revisions
- corrected implementation order
- real `MANIFEST.sha256`

---

# 5. Current P0 security decisions

- Content is data, never authority.
- Secret/credential material is not Knowledge.
- one active mutable Vault / shared writer authority.
- Last-write-wins prohibited.
- deletion truth is monotonic and generic across object types.
- SENSITIVE external egress is denied in P0; no one-time override implementation.
- credentialed generic Web fetch requires HTTPS.
- synced/shared iOS capture envelopes require paired-device authenticity verification before `IOS_SHARE_*` user-originated provenance.
- capability support does not equal permission/egress authorization.
- passive recall requires C6 verified capability + authentic R6 Trusted Intent + A7 candidate approval.
- normal active-store file deletion is attempted after logical delete, but forensic secure erase is not claimed.

---

# 6. Implementation entry point

Start at Phase 0 of:

`TSUZU_P0_Final_Implementation_Execution_Plan_v2.0_20260909.md`

Earliest dependency root:

```text
C0 -> A1 -> A2 -> C1 -> A3 -> A4
```

Do not start from B/R feature code before foundation gates unless the execution plan explicitly permits a spike.

---

# 7. Documentation vs implementation status

```text
P0 Product/Architecture documentation       CLOSED
A1-A10 implementation Contracts             CLOSED / READY
B1-B11 implementation Contracts             CLOSED / READY
C0-C6 cross-cutting Contracts               CLOSED / READY
R1-R10 Contracts                            CLOSED / READY or bounded Spike
Cross-document documentation audit           see v2.0 audit
Code implementation                          NOT CLAIMED
Golden Case runtime PASS                     NOT CLAIMED
Founder Product Proof                        NOT EXECUTED
```

---

# 8. Integrity

Run:

```bash
sha256sum -c MANIFEST.sha256
```

from this package root.

The manifest excludes itself and generated ZIP containers.

If a current file hash fails, treat the package as modified and re-run review before implementation.
