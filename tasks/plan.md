# TSUZU P0 v2.1 implementation plan

The verified documentation baseline is `docs/20260909/TSUZU_P0_Final_Documentation_20260909_v2_1/` (`MANIFEST.sha256`: PASS). Work is tracked only in Beads; this file is an ordered index, not a second task ledger.

Root epic: `tsuzu-main-pb6` — TSUZU P0 v2.1 implementation.

## Ordered execution index

| Phase | Epic | Work units and gate |
|---|---|---|
| 0 Storage authority | `tsuzu-main-pb6.1` | P0-0.0 `pb6.1.1`; C0 `pb6.1.2`; A1 `pb6.1.3`; A2 `pb6.1.4`; C1 `pb6.1.5`; F0-A `pb6.1.6` |
| 1 Capture/integrity | `tsuzu-main-pb6.2` | A3–A6/C3 `pb6.2.1`–`pb6.2.5`; F0-B `pb6.2.6` |
| 2 Explicit Recall | `tsuzu-main-pb6.3` | A7/A8/C6/A9 `pb6.3.1`–`pb6.3.4`; A10 `pb6.3.5` |
| 3 Acquisition/corpus | `tsuzu-main-pb6.4` | R1/C2/R2/R3/R4 `pb6.4.1`–`pb6.4.5`; Acquisition gate `pb6.4.6` |
| 4 Recovery | `tsuzu-main-pb6.5` | R5 `pb6.5.1`; Recovery gate `pb6.5.2` |
| 5 Chronicle/Derived | `tsuzu-main-pb6.6` | B1/C4/B2–B7 `pb6.6.1`–`pb6.6.8`; Knowledge Integrity `pb6.6.9` |
| 6 Discovery/events | `tsuzu-main-pb6.7` | B8–B11 `pb6.7.1`–`pb6.7.4`; Slice B gate `pb6.7.5` |
| 7 Passive/control plane | `tsuzu-main-pb6.8` | R6/C5/R7 `pb6.8.1`–`pb6.8.3`; UX Safety `pb6.8.4` |
| 8 Host/web spike | `tsuzu-main-pb6.9` | R8 `pb6.9.1`; R9 `pb6.9.2` |
| 9 Founder proof | `tsuzu-main-pb6.10` | R10 F0–F2 `pb6.10.1`–`pb6.10.3`; MVP completion audit `pb6.10.7` |

## Operating rules

- Implement only after claiming the Bead and reading its linked Contract plus C0–C6 requirements.
- Close a gate only with recorded deterministic PASS evidence; technical PASS is not Product GO.
- R10 F1 remains blocked until A10, B11, R5, R6, B10, R3, and the minimum R7 path pass.
- The MVP is complete only when `tsuzu-main-pb6.10.7` is closed with evidence. It requires R10 F2 plus the Phase 8 R8/R9 outcomes, every P0 gate PASS, the documentation manifest check, focused repository checks, and no unresolved blocking P0 risk.

## Risks and implementation-time decisions

The product contract deliberately defers the implementation stack, filesystem/concurrency APIs, current Host APIs, acquisition adapters, and model thresholds. `P0-0.0` selects and records these decisions before C0 work begins. No task may weaken the standing P0 invariants while resolving them.
