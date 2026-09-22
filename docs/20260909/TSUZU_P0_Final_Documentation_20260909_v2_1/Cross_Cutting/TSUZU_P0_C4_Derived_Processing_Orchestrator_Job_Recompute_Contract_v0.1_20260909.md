# TSUZU P0 C4 — Derived Processing Orchestrator / Job / Recompute Contract v0.1

- Date: 2026-09-09
- Status: **Cross-cutting Foundation Contract / Closed / Ready to implement**
- Canonical basis: v1.2 Realtime/Batch Processing + v1.2.1 dependency invalidation/recompute
- Depends on: C0, C1, C3, A3 Secret Guard, A7 policy library where external model egress is used
- Applies to: B2 Episode, B3 Candidate, B5 Reconciliation, B6 Learning, B7 invalidation/recompute, B8 precompute; acquisition-specific network jobs remain R1-owned
- Scope: durable local derived job scheduling, idempotency, input fingerprinting, stale generation, crash recovery, recompute/invalidation priority
- Non-scope: object-specific AI prompts, promotion policy, Acquisition network retry, Canonical user event invention, host recall transport

---

# 0. Decision

B contracts define what Derived processing means but not who owns the durable batch/job lifecycle.

C4 provides one orchestrator for derived work:

```text
Canonical event/change
  -> dependency trigger
  -> C4 job
  -> safe input snapshot/fingerprint
  -> model/algorithm
  -> validate output
  -> Derived materialization
  -> dependency edges/generation
```

At-least-once execution is allowed. Observable Derived effect must be idempotent/equivalent.

---

# 1. Job classes

Initial registered job types may include:

- `EPISODE_SEGMENT`
- `CANDIDATE_EXTRACT`
- `DECISION_RECONCILE`
- `EXPERIENCE_TRACE_RECOMPUTE`
- `DEPENDENCY_INVALIDATE`
- `PATTERN_RECOMPUTE`
- `DISCOVERY_PRECOMPUTE`
- `DERIVED_INDEX_REPROJECT`

Exact implementation can add internal job types only through a versioned registry. External content cannot register jobs.

---

# 2. Runtime job schema

Runtime durable state, not Canonical Knowledge:

```yaml
job_id:
job_type:
job_key_hash:
trigger_ref:
input_refs: []
input_fingerprint:
algorithm_version:
policy_version:
created_at:
attempt_count:
state: PENDING | RUNNING | RETRY_WAIT | SUCCEEDED | PERMANENT_FAILURE | BLOCKED_STALE | CANCELLED
next_attempt_at:
output_refs: []
last_failure_code:
```

Queue/body cache belongs outside synced Canonical truth and is excluded from R5 PROTECTED backup.

---

# 3. Idempotency identity

```text
job_key = H(
  job_type
  + normalized input object ids/revisions/content hashes
  + algorithm_version
  + policy_version
  + relevant scope
)
```

Same key:

- duplicate delivery -> one equivalent Derived generation;
- crash/retry -> no duplicate semantic outputs;
- algorithm/input revision change -> new key/generation.

---

# 4. Input safety gate

Before model/algorithm invocation:

1. resolve current C0 Vault;
2. re-read referenced persistent objects;
3. apply C3 deletion eligibility;
4. reject corrupt/unknown schema;
5. apply A3/current Secret Guard where body is processed;
6. enforce sensitivity/scope;
7. if external model is used, invoke the shared destination-aware **A7 Policy/Egress Decision Core** factored from A7 hard rules; C4 is only a caller and cannot define a weaker policy. SENSITIVE external default-deny remains;
8. mark all content as untrusted data.

A queued job created before deletion/sensitivity change must not process stale unsafe input later.

---

# 5. Canonical authority boundary

C4 cannot turn model output into Canonical fact by itself.

### Allowed

- persist Derived Episode/Candidate/Assessment/Pattern/Discovery generations;
- update Derived dependency metadata;
- request C1 persistence only for a Canonical event already authorized/defined by its owner Contract and produced from a trusted non-AI authority path.

### Forbidden

```text
assistant/model says user decided X
-> C4 writes USER_EXPLICIT Decision Assertion
```

User Correction Event must be committed through B5+C1 before C4 recompute.

---

# 6. Derived storage/generation

Persistent Derived objects inherit Canonical Object Envelope fields required by v1.2.1 for traceability, but remain explicitly `DERIVED`.

Conceptual identity:

```yaml
object_id:
object_type:
storage_class: DERIVED
derivation:
  generation_id:
  input_fingerprint:
  algorithm_version:
  created_at:
  stale: false
```

New recompute does not rewrite the historical inputs.

Current eligibility resolves to the newest valid non-stale generation under owner policy.

---

# 7. Invalidation priority

Deletion/Correction/Sensitivity invalidation has higher priority than quality/enrichment work.

On C3 deletion or B5 Correction:

```text
1. synchronously mark known dependent current views ineligible/stale where possible
2. enqueue dependency invalidation/recompute
3. A7/B8 eligibility checks must also revalidate persistent truth and not rely solely on queue completion
```

Queue outage cannot make stale Derived knowledge authoritative.

---

# 8. Concurrency

Compute can run concurrently where safe, but:

- Canonical mutation still serializes through C1 shared writer.
- output commit uses deterministic/idempotent generation identity.
- two workers claiming same job use atomic claim/lease.
- lease expiration supports crash recovery.
- no unbounded worker spawning.

P0 may begin with one derived worker process for simplicity.

---

# 9. Retry classes

### Retryable

- temporary model/adapter outage
- transient I/O
- worker crash/lease expiration
- bounded rate limit

### Permanent/input-blocked

- invalid schema
- deleted input
- policy-denied external egress where no local path exists
- unsupported object version
- deterministic invalid model output after bounded retry

`PERMANENT_FAILURE` never changes Canonical evidence.

---

# 10. Failure behavior

| Failure | Behavior |
|---|---|
| crash after claim | lease expires/retry |
| crash after output temp write | no half published Derived object |
| input changed mid-compute | output fingerprint stale -> discard/requeue |
| input deleted mid-compute | no eligible output commit |
| invalidation queue unavailable | current dependent marked stale/ineligible; health degraded |
| external model denied by policy | no egress; retry only if policy/path changes |
| model output violates schema | reject; never coerce to Canonical |

---

# 11. Golden cases

1. **B2 crash retry** — one Episode generation after worker crash.
2. **Correction first** — Correction event persists; reconciliation crash cannot lose it.
3. **Deletion during compute** — output does not become eligible.
4. **Algorithm version bump** — new generation created; old inputs unchanged.
5. **Queue duplicate** — same job key converges.
6. **Invalidation queue failure** — stale Decision/Pattern is blocked before recompute finishes.
7. **Sensitive external processing** — default deny prevents body egress.
8. **Model hallucinated decision** — remains Derived Candidate, cannot become USER_EXPLICIT.

---

# 12. Implementation tasks

- C4.1 job type registry/schema
- C4.2 durable local queue + atomic claim/lease
- C4.3 input fingerprint builder
- C4.4 privacy/deletion preflight
- C4.5 Derived generation materializer
- C4.6 invalidation priority dispatcher
- C4.7 retry/health/receipts
- C4.8 Golden/fault tests

---

# 13. Acceptance criteria

- [ ] B2/B5/B7 background work has a single explicit lifecycle owner.
- [ ] job retries are idempotent.
- [ ] deletion/correction cannot be delayed into unsafe eligibility by queue outage.
- [ ] external model processing uses the shared **A7 Policy/Egress Decision Core** and observes Secret/Sensitivity policy; C4 has no independent allow path.
- [ ] model output cannot self-promote to Canonical user truth.
- [ ] input/algorithm change produces a new traceable generation.
- [ ] runtime queue is rebuildable/non-authoritative.

---

# 14. One-line contract

> **C4 owns the messy reality between “a Canonical event happened” and “Derived knowledge is safely recomputed,” making background AI work retryable, traceable and incapable of outranking Canonical truth.**
