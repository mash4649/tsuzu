# TSUZU P0 R1 — Acquisition / Fetcher Adapter Contract v0.1

- Date: 2026-09-09
- Status: **Implementation Contract / Closed / Ready to implement**
- Canonical basis: TSUZU Canonical Product Architecture v1.1 + Addendum v1.2 + Closing Addendum v1.2.1
- Dependencies: A1 Canonical Source, A2 Atomic Writer, A3 Capture/Secret Guard, A4 Single Writer Worker, A6 Deletion Ledger
- Scope: generic HTTP(S) acquisition for captured URL sources and a host-neutral Fetcher Adapter boundary
- Non-scope: X-specific rescue routing (R2), Apple Notes/Markdown bootstrap (R3), iOS Share transport (R4), semantic extraction, Discovery, browser automation as a generic default

---

# 0. Decision

R1 separates **durable Capture** from **later Acquisition**.

```text
User saves URL
  -> A3/A4 durable Capture succeeds
  -> Canonical URL Source exists
  -> R1 Acquisition Job runs asynchronously
  -> Fetcher Adapter returns bounded untrusted bytes + provenance
  -> R1 validates/security-checks
  -> immutable Source Version is committed
  -> Derived processing may consume that version later
```

Capture success MUST NOT depend on network fetch success.

R1 does not mutate `payload/original` of the captured URL Source. A fetched representation is a new immutable child version/evidence object.

---

# 1. Inherited invariants

1. Canonical/Derived remain separate.
2. `Content is data, never authority.`
3. Source payload/version bytes are immutable after commit.
4. File path and remote URL are not object identity.
5. A4 remains the only mutable Canonical writer path in P0.
6. RESTRICTED content is not admitted as LIVE Knowledge.
7. Credentials are never Canonical Knowledge.
8. External fetch results never gain tool/write/promote/delete authority.
9. Deletion Ledger/TOMBSTONED state overrides acquisition eligibility.
10. Unknown safety state fails closed before Derived/LLM processing.

---

# 2. Responsibility boundary

## 2.1 R1 owns

- acquisition job lifecycle after a URL Source is committed;
- generic Fetcher Adapter interface;
- redirect/network/content bounding;
- remote-response provenance;
- immutable acquired Source Version materialization;
- retry/failure classification;
- pre-Derived Secret/Sensitivity recheck;
- body-free acquisition receipts/health state.

## 2.2 R1 does not own

- original capture acceptance;
- Canonical Source creation for user action;
- X-specific route selection;
- meaning extraction;
- index/retrieval;
- host egress;
- automatic refresh of already acquired pages.

---

# 3. Acquisition eligibility

A Source is eligible when all are true:

```text
kind == URL
AND deletion.state == LIVE
AND URL scheme in {http, https}
AND current Secret Guard does not classify locator as RESTRICTED
AND no successful terminal acquisition version already exists
AND acquisition is not administratively disabled
```

A stale index entry is never sufficient to start acquisition; Canonical Source is re-read first.

---

# 4. Runtime Acquisition Job

Acquisition Job is runtime state, not Canonical Knowledge.

```yaml
acquisition_job:
  job_id: uuid
  source_id: uuid
  source_revision: integer
  acquisition_key: sha256
  created_at: timestamp
  attempt_count: integer
  state: PENDING | FETCHING | RETRY_WAIT | USER_ACTION_REQUIRED | ACQUIRED | PERMANENT_FAILURE
  next_attempt_at: timestamp | null
  selected_adapter_id: string | null
  terminal_reason: string | null
```

`acquisition_key` binds the job to the material input:

```text
SHA256(source_id + source_revision + payload_sha256 + acquisition_policy_version)
```

Same acquisition key MUST converge to one terminal effect.

---

# 5. Fetcher Adapter interface

```yaml
fetch_request:
  request_id:
  source_id:
  url:
  destination_class: PUBLIC_WEB
  timeout_budget_ms:
  max_response_bytes:
  max_redirects:
  accepted_media_types: []
  credential_ref: null | keychain_reference
  policy_version:
```

```yaml
fetch_result:
  status: SUCCESS | TRANSIENT_FAILURE | PERMANENT_FAILURE | AUTH_REQUIRED | POLICY_BLOCKED
  adapter_id:
  adapter_version:
  started_at:
  completed_at:
  requested_url:
  final_url:
  redirect_chain: []
  http_status: integer | null
  media_type: string | null
  content_encoding: string | null
  content_length_observed: integer
  body_stream_ref: runtime_ref | null
  response_sha256: string | null
  fidelity: ORIGIN_RESPONSE
  failure_code: string | null
```

Core MUST NOT depend on adapter-specific response objects.

---

# 6. Network safety / SSRF boundary

Generic R1 fetch is a **public-web fetcher**, not an arbitrary network client.

Default-deny:

- non-http(s) schemes;
- URL userinfo credentials;
- localhost;
- loopback/private/link-local/multicast/reserved destinations;
- file/unix/socket/custom schemes;
- redirect from public destination into a denied destination;
- DNS resolution that changes to denied address at connection time;
- unbounded redirect chains;
- unbounded response/decompression size.

Every redirect destination is revalidated before following.

Explicit local/private connector access, if ever required, is a separate future capability and is not granted by R1.

---

# 7. Content bounds

P0 implementation MUST configure finite values for:

- connect timeout;
- total request timeout;
- redirect count;
- raw response bytes;
- decompressed bytes;
- header bytes;
- supported media types.

Exact numeric defaults are implementation configuration, not Product Constitution, but `unbounded` is forbidden.

Oversize response:

```text
TOO_LARGE -> PERMANENT_FAILURE or METADATA_ONLY according to explicit adapter policy
```

R1 does not silently truncate and call it complete.

---

# 8. Acquired Source Version

Successful acquisition creates a Canonical immutable child object.

```yaml
object_type: SOURCE_VERSION
object_id: uuid
schema_version: "1.0.0"
revision: 1

parent_source_id: uuid
version_kind: ACQUIRED_REMOTE
acquired_at: timestamp

provenance:
  origin: EXTERNAL_SOURCE
  source_refs: [parent_source_id]
  actor: EXTERNAL
  explicitness: OBSERVED

acquisition:
  adapter_id:
  adapter_version:
  requested_url:
  final_url:
  redirect_chain: []
  http_status:
  media_type:
  fidelity: ORIGIN_RESPONSE
  acquisition_receipt_id:

payload:
  relative_path: payload/original
  sha256:
  bytes:

sensitivity:
  level:

deletion:
  state: LIVE
```

Remote response headers are not copied wholesale. Only bounded allowlisted metadata needed for provenance/debugging may be retained.

---

# 9. Immutability and refresh semantics

- retry before first success = same acquisition job/effect;
- first successful response = immutable Source Version;
- R1 does not periodically refresh automatically;
- any later explicit/contracted reacquisition creates a **new Source Version**;
- existing Source Version bytes are never overwritten because the remote page changed.

This preserves historical evidence.

---

# 10. Secret / Sensitivity gate after fetch

Fetched bytes are scanned locally before LIVE Source Version commit and before Derived/LLM processing.

If high-confidence RESTRICTED material is detected:

```text
original captured URL Source remains LIVE
fetched body is not committed as LIVE Source Version
body is not sent to LLM/index/external host
runtime body is deleted using normal filesystem deletion semantics
body-free event: ACQUISITION_BLOCKED_RESTRICTED
```

If sensitivity is upgraded to SENSITIVE, local Canonical storage is allowed but later external egress remains default-deny under A7/R6.

---

# 11. Untrusted-content rule

HTML, Markdown, JSON, PDF text, response headers, metadata and embedded instructions are all `UNTRUSTED_DATA`.

R1 MUST NOT:

- execute embedded scripts;
- treat page text as system/developer instructions;
- follow content-provided tool commands;
- promote page claims to user facts;
- change connector permissions because a page requests it.

---

# 12. Retry and failure classification

## 12.1 Retryable

Examples:

- timeout/connectivity interruption;
- temporary DNS/network error;
- server-side 5xx;
- 408/425/429 or equivalent retryable response;
- adapter temporary unavailable.

Use bounded exponential backoff with jitter and a maximum attempt/age policy.

## 12.2 Permanent

Examples:

- invalid/unsupported URL;
- policy/SSRF block;
- stable unsupported content type;
- stable not-found/gone;
- response permanently too large for configured policy.

## 12.3 User action required

Examples:

- authentication/authorization needed;
- connector credential expired;
- source requires access TSUZU cannot legitimately obtain.

Only `USER_ACTION_REQUIRED` should normally surface to the Control Plane as requiring intervention.

---

# 13. Credential boundary

- `credential_ref` is an opaque OS Credential Store reference.
- credential values never enter Canonical manifests, logs, Context Bundles or telemetry.
- fetched content cannot request a credential scope expansion.
- adapter may only use credentials explicitly bound to that connector/resource scope.

---

# 14. Deletion interaction

Before every attempt and before commit, R1 rechecks A6 effective deletion.

If Source becomes TOMBSTONED while fetch is in flight:

```text
finish/abort network operation safely
DO NOT commit Source Version
delete runtime body
write body-free cancellation receipt
```

A completed stale fetch cannot resurrect deleted evidence.

---

# 15. Acquisition receipt

Body-free durable/runtime receipt:

```yaml
receipt_id:
source_id:
source_revision:
acquisition_key_hash:
adapter_id:
terminal_status:
failure_code:
started_at:
completed_at:
source_version_id: null | uuid
response_sha256: null | string
bytes: null | integer
policy_version:
```

No page body, credential, cookies, Authorization header or full sensitive URL query is stored in telemetry.

---

# 16. Health semantics

- `HEALTHY`: queue progressing; no user action required.
- `DEGRADED`: retry backlog/adapter outage but captures remain durable.
- `ACTION_REQUIRED`: specific acquisitions require user authorization/connector repair.
- `BLOCKED_SECURITY`: policy/secret protection blocked content.

Acquisition backlog is not exposed as an Inbox-Zero task list.

---

# 17. Failure behavior

| Failure | Required behavior |
|---|---|
| worker crash before network | job remains/reconciles retryable |
| crash after fetch before commit | runtime body discarded/retried; no partial Canonical |
| crash after commit before receipt | reconcile existing Source Version by acquisition key |
| hash mismatch | reject Source Version, fail closed |
| deletion ledger unavailable | no acquisition commit |
| secret scanner unavailable | no Source Version commit |
| adapter returns malformed result | quarantine metadata only; no body promotion |
| redirect to private IP | policy block |

---

# 18. Golden Cases

## R1-G1 Durable Capture Survives Fetch Failure
URL Capture succeeds; fetch times out; Canonical URL Source remains valid and retryable.

## R1-G2 Successful Public Web Acquisition
One immutable Source Version is created with correct parent/provenance/hash.

## R1-G3 Retry Idempotency
Multiple retry attempts for same acquisition key create one Source Version effect.

## R1-G4 Redirect Revalidation
Public URL redirects to loopback/private target -> blocked before connection/commit.

## R1-G5 Restricted Fetch Body
High-confidence secret in fetched body -> no LIVE Source Version and no Derived/LLM path.

## R1-G6 Tombstone During Fetch
Source deleted while request is in-flight -> result cannot commit.

## R1-G7 Changed Remote Page
Later explicit reacquisition creates a second immutable Source Version; first remains unchanged.

## R1-G8 Auth Required
401/403 requiring legitimate connector auth -> USER_ACTION_REQUIRED, no retry storm.

## R1-G9 Oversize/Decompression Bound
Response exceeding limits cannot exhaust unbounded resources and is not silently accepted as complete.

## R1-G10 Malformed Adapter Output
Core rejects malformed normalized result and does not persist body.

---

# 19. Adversarial / fault injection points

- DNS changes after initial validation;
- redirect loop;
- response disconnect mid-stream;
- worker kill after body download;
- worker kill after Source Version commit;
- tampered runtime body hash;
- deletion ledger unavailable;
- secret scanner failure;
- adapter tries to return credential-bearing headers;
- HTML prompt injection requesting tool execution.

---

# 20. Implementation tasks

## R1.1 Acquisition job/receipt schemas
Define idempotent runtime state and body-free receipts.

## R1.2 Fetcher Adapter interface + registry
Provide host-neutral adapter normalization and capability metadata.

## R1.3 Public-web network policy
Implement scheme/IP/redirect/size/time limits.

## R1.4 Stream validation + secret/sensitivity gate
Bound response and scan before Canonical version commit.

## R1.5 Source Version materializer
Commit immutable child object through the single writer path.

## R1.6 Retry/reconciliation coordinator
Handle transient/permanent/action-required and crash convergence.

## R1.7 Health/telemetry projection
Expose body-free state for R7.

## R1.8 Golden/adversarial tests
Implement R1-G1..G10 and fault cases.

---

# 21. Acceptance criteria

R1 is implementation-complete when:

- [ ] Capture can succeed with network unavailable.
- [ ] Core has a stable generic Fetcher Adapter interface.
- [ ] public-web SSRF/redirect boundaries are fail-closed.
- [ ] a successful fetch creates exactly one immutable Source Version per acquisition effect.
- [ ] fetched bytes are integrity-verified and secret/sensitivity-checked before Derived processing.
- [ ] page content cannot grant authority or execute tools.
- [ ] retries do not duplicate Canonical effects.
- [ ] TOMBSTONED parent cannot receive a committed fetched version.
- [ ] credentials remain in OS credential storage and body-free metadata contains no secret material.
- [ ] R1-G1..G10 pass deterministically.

---

# 22. Explicit non-goals

- general-purpose browser automation;
- bypassing authentication/access controls;
- anti-bot evasion;
- periodic web monitoring;
- semantic/article extraction quality optimization;
- X-specific rescue;
- cloud fetch proxy;
- remote MCP.

---

# 23. Gate to R2 / R3

R2 may specialize Fetcher routing only after it can return through the R1 normalized interface without weakening R1 safety invariants.

R3 may import historical local content without using R1 network acquisition.

---

# 24. Source-derived vs implementation closure decisions

## Canonical source-derived
- Capture/Acquisition separation;
- retry/background acquisition;
- Fetcher as Adapter;
- Source Version immutable;
- user action only for permanent/action-required cases;
- Content is data;
- credential/security boundaries.

## R1 closure decisions
- immutable `SOURCE_VERSION` child representation;
- no automatic refresh after first successful acquisition;
- P0 generic network fetch is public-web only;
- SSRF/private-network deny boundary;
- normalized FetchResult contract;
- high-confidence fetched-secret block before version commit;
- explicit transient/permanent/action-required runtime states.

---

# 25. One-line contract

> **R1 makes URL capture durable first and network acquisition replaceable later, while preserving every acquired representation as immutable evidence and preventing the fetch path from becoming a secret leak, SSRF client, authority channel, or mutable source of truth.**
