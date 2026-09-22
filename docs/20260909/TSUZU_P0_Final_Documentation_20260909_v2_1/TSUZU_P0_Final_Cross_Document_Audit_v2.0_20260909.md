# TSUZU P0 Final Cross-Document Audit v2.0

- Date: 2026-09-09
- Status: **Documentation Audit / PASS — 100/100 against P0 documentation-closure rubric**
- Replaces: Audit v1.0 PASS claim and the subsequent v2.0 review `Request changes`
- Audited scope: Canonical v1.1/v1.2/v1.2.1/v1.2.2; A1-A10; B1-B11; C0-C6; active R1-R10; Contract Index v2.1; Execution Plan v2.0
- Important limitation: this is a **documentation/contract score**, not a claim that code, Golden Cases or Product Proof have passed.

---

# 0. Verdict

**PASS. Documentation-level P0 closure is restored after addressing the v2.0 review findings.**

The previous package correctly specified many individual components but overclaimed closure because several cross-contract mechanics had no single owner.

v2.1 fixes that structurally rather than by adding comments to isolated files.

Current result:

```text
Named P0 responsibility without owner                    0 found
Known cross-contract authority conflict                   0 found
Known lower-contract weakening of Security invariant      0 found
Known P0/ Post-proof scope ambiguity from prior review    0 found
Prior Critical findings unresolved                        0 / 3
Prior High findings unresolved                            0 / 6
Prior Medium findings unresolved                          0 / 3
```

---

# 1. Documentation closure score

| Axis | Weight | Score | Evidence |
|---|---:|---:|---|
| Requirement / semantic correctness | 20 | 20 | Canonical precedence + object-specific owners preserved |
| Responsibility ownership | 20 | 20 | C0-C6 close shared mechanics; Index v2.1 maps sole/primary owners |
| Security / trust boundaries | 20 | 20 | A7/R6/C6 separation, SENSITIVE P0 deny, HTTPS credentials, C3 fail-closed deletion |
| Integrity / recovery / deletion | 15 | 15 | C0/C1/C3 + R5 coherent restore/cutover/no-resurrection |
| Implementation dependency order | 10 | 10 | C0 before A2; C1 after A2; C3 after A6; C4 before B2; C5 before R7 |
| Verification / Golden coverage | 10 | 10 | A10/B11/R5/R6 + C0-C6 Golden cases and acceptance criteria |
| Packaging / agent usability | 5 | 5 | current/superseded separation, README, Index, manifest contract |
| **Total** | **100** | **100** | documentation-level only |

A score of 100 means “no known documentation defect against this rubric,” not “future implementation cannot reveal new facts.”

---

# 2. Resolution of the prior 12 review findings

| Previous finding | Severity | Resolution | Result |
|---|---|---|---|
| B Canonical object persistence had no generic owner | Critical | **C1** shared Persistent Write Core; A2 remains SOURCE specialization; C4 Derived semantics reuse safe primitives | CLOSED |
| R1 acquired body did not reach A5/A7/A8 | Critical | **C2** Effective Source Representation explicitly wires Root SOURCE + SOURCE_VERSION -> Index -> Retrieval -> Trace | CLOSED |
| Deletion Ledger was SOURCE-only | Critical | **C3** generic `(object_type, object_id)` deletion truth; A6 remains SOURCE specialization | CLOSED |
| B background/recompute queues had no owner | High | **C4** Derived Processing Orchestrator owns durable jobs, fingerprint, retry, invalidation priority | CLOSED |
| Physical purge semantics conflicted | High | v1.2.2 + C3: active-store best-effort file purge in P0; forensic secure erase guarantee not claimed | CLOSED |
| SENSITIVE one-time override ambiguous | High | v1.2.2: explicitly **deferred beyond P0**; P0 external SENSITIVE remains deny | CLOSED |
| Active Vault Locator introduced too late | High | **C0** Foundation; implemented before A2; R5 consumes C0 cutover | CLOSED |
| R7 Export under-specified | High | **C5** Portable Canonical Archive; R7 v0.2 invokes it | CLOSED |
| R1 credential/HTTP boundary weak | High | R1 v0.2: credentialed fetch HTTPS-only; credential-scope downgrade to HTTP denied | CLOSED |
| Capability Router owner missing | Medium | **C6** common capability registry/router; A9/R8/R9 provide Host-specific evidence | CLOSED |
| R10 did not depend on R7 | Medium | R10 v0.2: F0 internal may precede R7; F1 external requires minimum R7 Control Plane | CLOSED |
| MANIFEST.sha256 missing | Medium | v2.1 package includes/generated manifest and README verification rule | CLOSED at packaging gate |

---

# 2.1 Second-pass hardening findings

After closing the original 12 findings, a second adversarial/security pass found four additional integration boundaries. They were fixed before final packaging rather than being deferred.

| Second-pass finding | Risk | Resolution | Result |
|---|---|---|---|
| Raw acquired HTML/PDF bytes were not guaranteed to become safe searchable text | Incorrect/unsafe materialization | **C2** now owns deterministic local Text Projection; HTML is locally parsed/sanitized without script execution, supported PDF text extraction is adapter-versioned, unsupported extraction is metadata-only and never fabricated | CLOSED |
| C4 external-model Derived processing could otherwise invent a weaker outbound policy path | Sensitive egress / policy divergence | **C4** must call the shared destination-aware A7 Policy/Egress Decision Core; it cannot create an independent weaker allow path | CLOSED |
| Synced/shared iOS outbox had integrity hash but no sender authenticity | Forged USER-originated capture provenance | **R4 v0.2** requires paired-device signature verification before `IOS_SHARE_*` provenance; unknown/revoked/invalid signatures fail closed | CLOSED |
| Restore could preserve Canonical data but silently lose an in-progress Founder experiment denominator/event record | Invalid Product Proof metrics after recovery | **R5 v0.2** protects body-free B10 Product Proof events/denominators and durable security/egress traces required by their owner contracts | CLOSED |

No second-pass item remains open.

---

# 3. Authority conflict audit

## 3.1 Persistent writes

Potential conflict:

- A2 says SOURCE Atomic Writer.
- B/R create other persistent objects.
- C4 materializes Derived outputs.

Resolution:

```text
C1 = shared persistent write mechanics / Canonical mutation authority
A2 = SOURCE specialization
C4 = Derived job/generation semantics, reusing C1 physical atomic primitives
```

No second writer lock or Last-write-wins path is authorized.

**PASS.**

---

## 3.2 Active Vault

Potential conflict:

- R5 needs to switch Vaults.
- A2/A4/A5/B/R need stable paths.

Resolution:

- C0 is sole locator authority.
- R5 owns restore decision/orchestration, not locator semantics.
- generation check blocks stale post-cutover commits.

**PASS.**

---

## 3.3 Source identity vs acquired content

Potential conflict:

- A1 preserves user-captured URL.
- R1/R2 preserve fetched bytes as child versions.
- A5 originally indexed Source.

Resolution:

- C2 keeps Root `source_id` as user-action identity.
- Effective representation can be ROOT payload / SOURCE_VERSION / locator-only.
- Canonical raw bytes remain immutable; C2 creates a rebuildable deterministic local Text Projection for supported text/HTML/PDF forms.
- HTML projection never executes source scripts; unsupported PDF/text extraction is metadata-only, not guessed or LLM-fabricated.
- A5 indexes the selected READY text projection/representation.
- A7 revalidates persistent root/representation/deletion/policy.
- A8 trace names both root and actual bytes used.

**PASS.**

---

## 3.4 Deletion

Potential conflict:

- A6 SOURCE deletion.
- B Decision/Conversation/Evidence deletion.
- R5 stale restore.
- B7 dependency invalidation.

Resolution:

```text
C3 = generic deletion truth
A6 = SOURCE specialization
C4/B7 = downstream stale/recompute
R5 = generic ledger union/reapply
```

C3 deletion truth wins before async recompute/purge.

**PASS.**

---

## 3.5 Egress / Passive Recall / Host capability

Potential conflict:

- C6 knows a Host can inject context.
- R6 knows a current user event can authorize passive evaluation.
- A7 knows whether particular data may leave.

Resolution:

```text
C6 technical support
AND R6 authentic Trusted Intent
AND A7 resource/destination policy allow
=> candidate may egress through A8/B9
```

Any deny/unknown fails closed.

**PASS.**

---

## 3.6 Control Plane / destructive operations

Potential conflict:

UI could implement its own delete/export/restore behavior.

Resolution:

- R7 is presentation/orchestration only.
- C3 owns delete.
- C5 owns export.
- R5 owns backup/restore.
- C6 owns capability truth.

**PASS.**

---

# 4. Canonical/Derived/Runtime truth audit

Current rule:

```text
Canonical factual/user/allowed observation records
  -> persistent under owner semantics + C1 safe mutation

Derived inference/segmentation/assessment/discovery
  -> C4 generation/materialization
  -> never authority merely because persisted

Runtime queue/cache/lease/index
  -> disposable/rebuildable
```

`Canonical Object Envelope` inheritance does not mean all objects are equally authoritative. Provenance/storage class/promotion remain separate.

Model output alone cannot create `USER_EXPLICIT` or silently rewrite Canonical evidence.

**PASS.**

---

# 5. Security hardening audit

## External content

- R1/R2/R9: untrusted content.
- C4: model/algorithm input revalidated; external processing MUST use the shared destination-aware A7 Policy/Egress Decision Core and cannot define a weaker allow path.
- no content-created capability/token/job registration.

## Credentials

- OS Credential Store references only.
- C5 export excludes credentials.
- R1 credentialed fetch requires HTTPS.
- R9 does not collect browser cookies/session tokens.
- R4 v0.2 authenticates synced/shared mobile envelopes against active paired-device public identity before accepting `IOS_SHARE_*` user-originated provenance; unknown/revoked/invalid signatures fail closed.

## Sensitive/Restricted

- RESTRICTED never normal Knowledge/egress.
- P0 SENSITIVE external override is explicitly not implemented.
- R6 silent path remains PERSONAL-only.
- unknown sensitivity/destination/deletion is fail closed.

## Prompt injection / passive authorization

- R6 token cannot be forged from YAML/JSON text; opaque registry/MAC-class authenticity required.
- C6 capability cannot be self-asserted by content.
- A7 remains final candidate egress gate.

**PASS.**

---

# 6. Recovery / deletion audit

- C0 gives a single generation-safe Vault authority.
- R5 never blind-overwrites live Vault.
- C3 generic deletion records are PROTECTED and unioned on managed restore.
- body-free B10 Product Proof event/denominator records for an active Founder experiment are PROTECTED so recovery does not silently invalidate metrics.
- A5/Derived are rebuilt rather than restored as authority.
- schema migration is deterministic and pre-backed-up.
- purge failure cannot resurrect deletion truth.
- forensic secure erase is not falsely promised.

**PASS.**

---

# 7. Implementation order audit

Execution Plan v2.0 corrects the prior dependency inversion.

Key gates:

```text
C0 -> A1 -> A2 -> C1 -> A3/A4
A6 -> C3
R1 -> C2 -> R2/R3/R4 v0.2
B1 -> C4 -> B2...
C6 -> R6/R8/R9
C5 -> R7 -> R10 F1
```

High-risk data-loss/security foundations are earlier than features that depend on them.

**PASS.**

---

# 8. Verification ownership audit

Deterministic technical gates exist at multiple layers:

- A10: core Capture/Recall/Secret/Delete/Rebuild.
- B11: Chronicle/Decision/Discovery technical Founder cases.
- R5: backup/restore/migration/failure injection.
- R6: token/prompt-injection/passive safety.
- R4 v0.2: paired-device mobile transport authenticity, revoked/forged envelope rejection and replay idempotency.
- C0-C6: cross-cutting Golden cases for locator/persistence/materialization/deletion/job/export/capability boundaries.
- R10: real human Product Proof protocol and denominator freeze.

Technical PASS cannot be mislabeled business GO.

**PASS.**

---

# 9. Intentionally unresolved by design

These remain legitimate Spike/implementation/measurement questions, not undefined responsibility:

- repository language/framework and exact filesystem APIs;
- network timeout/size constants;
- X current viable route;
- Apple Notes bridge mechanism;
- iOS transport;
- Claude/Codex/Cursor current APIs/versions;
- Web Chat capture method;
- model/prompt/threshold/ranking parameters;
- numeric GO/PIVOT/KILL gates after Founder evidence.

Each has a named Contract/phase that decides it.

---

# 10. What this audit does NOT approve

This audit does not claim:

- implementation exists;
- tests have run against code;
- current Claude/Codex/Cursor APIs have been verified;
- X acquisition works today;
- restore works on real filesystem yet;
- Personal Discovery produces Aha in real users;
- WTP/business GO.

Those remain implementation/Founder gates.

---

# 11. Final audit decision

**Documentation-level closure: PASS — 100/100 against the defined P0 documentation rubric.**

The correct next action is implementation from Execution Plan v2.0, not another broad design round.

If implementation exposes a contradiction, update the smallest owning Contract/ADR first rather than reopening the full Product Constitution.
