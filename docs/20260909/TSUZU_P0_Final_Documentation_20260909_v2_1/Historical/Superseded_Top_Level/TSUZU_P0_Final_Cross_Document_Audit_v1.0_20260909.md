# TSUZU P0 Final Cross-Document Audit v1.0

- Date: 2026-09-09
- Status: **Documentation Audit / PASS with implementation-time spikes explicitly bounded**
- Audited sources: Canonical v1.1, v1.2, v1.2.1; Slice A A1-A10; Slice B B1-B11; R1-R10
- Audit objective: detect missing P0 responsibilities, conflicting ownership, weakened invariants, hidden scope expansion and untestable contracts.

---

# 0. Conclusion

**Documentation-level closure passes.**

No currently known P0 Product/Architecture responsibility remains without a named implementation/evaluation Contract.

The remaining uncertainty is intentionally located in implementation-time verification or Founder measurement, not in undefined ownership.

This audit does **not** claim that code works. All code and Golden Case results remain pending.

---

# 1. Canonical requirement coverage

## 1.1 Product / UX

| Canonical requirement | Coverage | Result |
|---|---|---|
| TSUZU is Control Plane, not daily-use app | R7 | PASS |
| Share -> TSUZU -> end | A3 + R4 | PASS |
| Explicit Recall in existing AI | A9 | PASS |
| Passive Recall without summoning | R6 | PASS at spec level |
| First Aha/Personal Discovery in existing AI | B8/B9 | PASS |
| no forced organization | A3/R3/R7 | PASS |
| Small Historical Bootstrap | R3 | PASS |

## 1.2 Data / Integrity

| Requirement | Coverage | Result |
|---|---|---|
| Canonical user-owned Vault | A1/A2 | PASS |
| Raw/Canonical vs Derived separation | A1/A5/B* | PASS |
| Single Mutable Writer | A4 + R4 boundary | PASS |
| immutable Source Versions | A1 + R1/R2/R3 | PASS |
| revision/no last-write-wins | A2 | PASS |
| Tombstone/no resurrection | A6 + R4/R5 | PASS |
| rebuildable index | A5 | PASS |
| backup/restore/migration | R5 | PASS |

## 1.3 Acquisition / Sources

| Requirement | Coverage | Result |
|---|---|---|
| Capture separated from Acquisition | A3/A4 + R1 | PASS |
| Fetcher adapter abstraction | R1 | PASS |
| X main source/rescue strategies | R2 | PASS |
| Apple Notes/Markdown bootstrap | R3 | PASS |
| mobile Share create-only | R4 | PASS |
| local files | A1/R3 | PASS |
| AI Conversation Chronicle | B1 | PASS |
| Web Chat one-way spike | R9 | PASS |

## 1.4 Knowledge / Decision / Discovery

| Requirement | Coverage | Result |
|---|---|---|
| assistant-generated not user truth | B3/B4/B7 | PASS |
| Stated vs Revealed | B4/B5 | PASS |
| silence not acceptance | B4/B5/B10/R10 | PASS |
| correction canonical, derived recompute | B5/B7 | PASS |
| outcomes without causal overclaim | B6/R10 | PASS |
| Pattern contradiction/exception | B8 | PASS |
| 4 Discovery lanes | B8 | PASS |
| No Aha allowed | B8/B9/R6 | PASS |
| False Personal Assertion hard failure | B10/B11/R10 | PASS |

## 1.5 Security / Egress

| Requirement | Coverage | Result |
|---|---|---|
| Content is data | A7/R1/R2/R6/R9 | PASS |
| Secret Detector before LLM/Derived | A3/R1/R3/R4/R9 | PASS |
| Credential not Knowledge | R1/R2/R7/R9 | PASS |
| RESTRICTED deny | A3/A7/R6 | PASS |
| SENSITIVE external default deny | A7/R6/R7 | PASS |
| unknown sensitivity/destination fail closed | A7 | PASS |
| observation allowlist | B1/R6/R7/R8/R9 | PASS |
| Context Trace/Egress Manifest | A7/A8/R6/R8 | PASS |
| prompt-injection does not trigger authority | A7/R1/R2/R6/R9 | PASS |
| Passive trusted intent | R6 | PASS at spec level |

## 1.6 Host scope

| Requirement | Coverage | Result |
|---|---|---|
| first Host only for first E2E | A9 | PASS |
| shared multi-host adapter architecture | A9/R8 | PASS |
| Codex/Cursor later expansion | R8 | PASS |
| host capability differences remain truthful | R8 | PASS |
| web chat bidirectional deferred | R9 | PASS |

## 1.7 Product Proof

| Requirement | Coverage | Result |
|---|---|---|
| stable product event semantics | B10 | PASS |
| separate denominators | B10/R10 | PASS |
| CONNECTED+ minimum | B10/R10 | PASS |
| Pain/Invisible/Discovery/WTP | R10 | PASS |
| hard failures separate | B10/R10 | PASS |
| numeric gate after Founder evidence | R10 | PASS |

---

# 2. Ownership conflict audit

## 2.1 Deletion

Potential conflict: R5 restore, R4 replay and B7 invalidation all touch deleted data.

Resolution:

- **A6 exclusively owns effective deletion truth.**
- R5 unions/reapplies ledger; it does not redefine deletion.
- R4 same-envelope replay must honor receipt/tombstone and cannot create resurrection.
- B7 only invalidates/recomputes derived dependents.

Result: PASS.

## 2.2 Egress

Potential conflict: R6 passive recall appears to authorize memory use while A7 owns egress.

Resolution:

- **R6 owns authorization to start a passive evaluation from current user intent.**
- **A7 owns whether each candidate is allowed to egress.**
- A8 owns body/bundle/trace.

R6 cannot turn an A7 deny into allow.

Result: PASS.

## 2.3 Canonical writes

Potential conflict: R1 acquired versions, R3 imports and R4 mobile capture create new information.

Resolution:

- R4 writes transport only.
- R3/R1 materialize Canonical via the A2/A4 single-writer path.
- no secondary mutable writer is introduced.

Result: PASS.

## 2.4 Control Plane

Potential conflict: R7 could bypass underlying contracts through UI operations.

Resolution:

- R7 is orchestration/presentation only.
- deletion calls A6;
- backup/restore calls R5;
- egress/privacy uses A7/R6;
- connector secrets use OS Credential Store.

Result: PASS.

## 2.5 Product Proof

Potential conflict: B11 technical Golden Cases vs R10 real Founder evidence.

Resolution:

- B11 = deterministic technical Slice B exit.
- R10 = human/evidence Product Proof.
- technical PASS cannot be called business GO.

Result: PASS.

---

# 3. Cross-version conflict resolutions retained

The following interpretations remain current:

1. v1.1 `ACTIVE/DEPRECATED` are not new axes; v1.2.1 maps them to `PROMOTED/SUPERSEDED + LIVE`.
2. Exact same payload from distinct direct user captures remains separate Source IDs; same delivery/idempotency retry converges to one effect.
3. SQLite/FTS is outside synced Canonical Vault and rebuildable.
4. v1.1 future one-time SENSITIVE override is not exercised by Slice A/R6 passive mode.
5. A7 can model project scope, but A9 Slice A is narrowed to its validated host scope behavior.
6. A9 per-call approval was temporary safe mode; R6 defines the proof required to remove it per host.
7. Web Chat remains one-way validation only in R9.
8. 3-host formal QA remains non-blocking for first Founder run.

---

# 4. Adversarial review of new R decisions

Cross-model review was **not invoked** because this run is executing the user's explicit autonomous "finish everything" instruction and external CLI invocation would require separate authorization. The following is a degraded in-session adversarial review.

## 4.1 R1 SOURCE_VERSION child object

Challenge: is this new Product Scope?

Assessment: acceptable implementation closure. v1.1 already states Source Version is immutable and Acquisition is P0 Required. A child Source Version is the minimal representation that preserves captured URL identity and remote historical bytes without mutating A1 raw payload.

## 4.2 R1 public-web SSRF restriction

Challenge: canonical did not explicitly say SSRF.

Assessment: required security closure for a generic URL fetcher. It narrows capability; it does not add product behavior. Future private/local connector must be separate.

## 4.3 R3 repeated import idempotency

Challenge: A1 says same payload captured twice can be two Sources.

Assessment: no conflict. R3 repeat of the same external snapshot is delivery/import reconciliation, while a later direct user Share is explicitly preserved as a distinct action.

## 4.4 R4 mobile pre-outbox secret guard

Challenge: A3 runs on Mac; mobile guard duplicates logic.

Assessment: justified as defense-in-depth before new mobile/sync persistence. Mac A3 remains authoritative and runs again. Mobile guard may only be same/narrower high-confidence deny; it cannot downgrade A3.

## 4.5 R6 Trusted Intent Token

Challenge: a token may become a new authorization system and itself be forgeable.

Actionable hardening: token authenticity must be protected by an opaque local registry or MAC/process secret and cannot be self-asserted by caller-provided fields. This requirement is added to final R6 revision.

## 4.6 R7 Standard/Strict labels

Challenge: canonical only gave them as examples.

Assessment: valid implementation closure, not Product Constitution. The modes cannot weaken hard rules and can be renamed later without schema/architecture impact.

## 4.7 R8 current host capability uncertainty

Challenge: APIs change.

Assessment: contract deliberately refuses to freeze current API names. Capability Report + implementation-time primary-source verification handles this correctly.

## 4.8 R9 browser-extension fragility

Challenge: DOM capture is brittle and privacy-sensitive.

Assessment: it is only a candidate spike method, with PARTIAL/FAIL allowed. R9 does not require browser-extension success.

## 4.9 R10 cohort/price assumptions

Challenge: approximately 10 users and ¥980 could become fake final thresholds.

Assessment: both are inherited historical hypotheses; R10 explicitly prevents them from becoming final GO thresholds and requires post-evidence calibration.

---

# 5. Action from audit

One non-trivial hardening issue was found and **patched before final packaging**:

**R6 token authenticity** now explicitly requires an unforgeable local token mechanism (opaque registry or MAC/process-local key) and denies caller-supplied self-asserted token fields.

After this patch, no documentation-level blocker remains.

---

# 6. Intentionally open implementation decisions

These remain open by design, with owners:

| Open decision | Owner / closure point |
|---|---|
| concrete fetch library/network budgets | R1 implementation + tests |
| X routes currently available/legal/cost | R2 route verification |
| Apple Notes bridge mechanism | R3 adapter spike |
| mobile transport mechanism | R4 transport adapter |
| model/prompt/ranking thresholds | B8/B9 + R10 evidence |
| Codex/Cursor current host APIs | R8 source verification |
| Web Chat provider capture method | R9 spike |
| numeric business gates | R10 F2 |

Open does not mean unowned.

---

# 7. Final documentation gate

PASS conditions:

- [x] every P0 required concern has a named owner Contract;
- [x] every R Contract has Scope/Non-scope/Invariants/Failure/Golden/Tasks/Acceptance;
- [x] no R Contract weakens hard canonical security/deletion ownership;
- [x] future/spike decisions remain explicitly non-Canonical until verified;
- [x] human Product Proof remains separate from technical tests;
- [x] final precedence and ownership are documented;
- [x] implementation order can be followed without reading project chat history.

**Result: PASS after R6 authenticity patch.**
