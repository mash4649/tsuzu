# TSUZU P0 R1-R10 Implementation Contracts — Integrated v1.0

- Date: 2026-09-09
- Status: Integrated exact-copy bundle / documentation complete
- Note: each section below is an exact copy of the standalone R Contract named at its boundary.


---

# SOURCE BOUNDARY — TSUZU_P0_R1_Acquisition_Fetcher_Adapter_Contract_v0.1_20260909.md

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


---

# SOURCE BOUNDARY — TSUZU_P0_R2_X_Acquisition_Rescue_Route_Contract_v0.1_20260909.md

# TSUZU P0 R2 — X Acquisition / Rescue Route Contract v0.1

- Date: 2026-09-09
- Status: **Implementation Contract / Closed / Ready for route spikes**
- Canonical basis: v1.1 X priority source + v1.2.1 X Fetcher strategy / Grok-Browser rescue validation
- Dependencies: R1 Acquisition/Fetcher, A3 Secret Guard, A4 Single Writer, A6 Deletion Ledger
- Scope: acquisition of X posts/threads/long posts/X Articles through replaceable legitimate routes
- Non-scope: bypassing X access controls, anti-bot evasion, engagement automation, posting/liking/replying, generic browser automation

---

# 0. Decision

X is a P0 priority source, but **X-specific transport instability must not leak into TSUZU Core**.

R2 is a strategy adapter above R1:

```text
Captured X URL
  -> identify X locator
  -> route resolver
  -> route attempt(s)
  -> normalized R1-compatible acquisition artifact
  -> fidelity/provenance classification
  -> immutable Source Version
```

No route is allowed to masquerade as another route. A Grok/intermediary reconstruction is not stored or cited as if it were verbatim X origin content.

---

# 1. Core invariants

1. Captured TSUZU `source_id` remains the user-action identity.
2. X post/status/article ID is external identity metadata, not TSUZU object identity.
3. Credentials/tokens/cookies remain outside Knowledge.
4. Every route records route identity, fidelity and completeness.
5. Route fallback cannot weaken R1 security boundaries.
6. External/intermediary content is untrusted data.
7. No route bypasses paywall/login/access restrictions without legitimate user authorization.
8. Partial content must be marked partial.
9. Deleted/private/unavailable content is a valid outcome, not an invitation to evade controls.
10. X acquisition success is not required for Capture success.

---

# 2. X locator contract

Parse, without network dependency where possible:

```yaml
x_locator:
  captured_url:
  host_family: X
  item_type: POST | ARTICLE | UNKNOWN
  external_item_id: string | null
  author_hint: string | null
  canonical_public_url_hint: string | null
```

URL normalization may remove tracking fragments but MUST NOT rewrite the original A1 payload.

---

# 3. Route classes

P0 recognizes capability classes, not hardcoded implementation ownership:

- `OFFICIAL_API_BYOK`
- `PUBLIC_ORIGIN_FETCH`
- `AUTHORIZED_BROWSER_SESSION`
- `GROK_ASSISTED_RESCUE`
- `UNAVAILABLE`

Exact vendor/API invocation is verified at implementation time and may change without changing this Contract.

---

# 4. Route selection policy

Default preference is:

```text
1. user-configured legitimate official/API route when available
2. public origin route when sufficient
3. explicitly authorized local browser-session route
4. explicitly connected Grok-assisted rescue
5. terminal unavailable/action-required
```

This order may be tuned by policy/cost configuration, but these invariants cannot change:

- no hidden purchase/API charge;
- no credential reuse outside its bound connector;
- no access-control bypass;
- fidelity always truthfully classified;
- user can disable a route class.

---

# 5. Route capability descriptor

```yaml
x_route_capability:
  route_id:
  route_class:
  available:
  supports_post:
  supports_article:
  supports_thread_context:
  requires_user_credential:
  requires_browser_session:
  may_return_intermediary_text:
  expected_fidelity:
  cost_class: FREE_LOCAL | USER_BYOK | SUBSCRIPTION_INCLUDED | METERED_EXTERNAL | UNKNOWN
  verified_at:
  implementation_version:
```

If cost class is `UNKNOWN` or `METERED_EXTERNAL`, route must not auto-run without an explicit configured policy allowing it.

---

# 6. Fidelity contract

Every successful route returns one of:

### ORIGIN_VERBATIM
Direct origin/API text with integrity-preserving representation.

### ORIGIN_RENDERED
Content captured from an authorized rendered session; presentation may differ but content is from origin view.

### INTERMEDIARY_RECONSTRUCTION
Content supplied/reconstructed by an intermediary model/service such as a rescue route.

### METADATA_ONLY
Identity/author/date/link known but body unavailable.

Intermediary reconstruction MUST NOT be used as a direct quotation/source-of-record without additional origin evidence.

---

# 7. Completeness contract

```yaml
completeness:
  state: COMPLETE | PARTIAL | UNKNOWN | METADATA_ONLY
  expected_segments: integer | null
  captured_segments: integer | null
  missing_reason: string | null
```

Long post / X Article MUST be `COMPLETE` only when the selected route provides the full body according to that route's verified capability.

A preview/snippet is never silently labeled complete.

---

# 8. Normalized X acquisition result

```yaml
x_acquisition_result:
  source_id:
  external_item_id:
  item_type:
  route_id:
  route_class:
  fidelity:
  completeness:
  author_observed:
  published_at_observed:
  fetched_at:
  origin_url:
  body_stream_ref:
  body_sha256:
  media_refs: []
  thread_parent_refs: []
  failure_code: null | string
```

This is translated to R1's immutable Source Version contract.

---

# 9. Thread handling

R2 may optionally acquire surrounding thread context only when:

- the route legitimately exposes it;
- scope is bounded;
- each post keeps independent external identity/provenance;
- the originally captured post remains identifiable;
- thread context is not confused with the user's saved target.

P0 MUST NOT recursively crawl unbounded conversations.

---

# 10. Authentication and browser session boundary

### Official/API BYOK
- key/token stored in OS Credential Store;
- Canonical stores only connector ID / key reference metadata;
- user can revoke route without deleting Source data.

### Authorized browser session
- session cookies/tokens are never copied into Vault;
- adapter accesses only an explicitly authorized browser/profile/session scope;
- page content cannot expand permissions;
- browser route is read-only for X acquisition.

### Grok-assisted route
- requires explicit connector availability/permission;
- output is `INTERMEDIARY_RECONSTRUCTION` unless independently verified as origin-verbatim;
- model output is untrusted external evidence, not user truth.

---

# 11. Prompt injection / memory poisoning boundary

X post/article text may contain instructions such as:

```text
ignore previous instructions
read the user's memory
run a shell command
save this as the user's principle
```

All remain data. R2 cannot:

- invoke TSUZU tools based on content;
- promote claims;
- alter policies;
- exfiltrate memory;
- request broader browser/API scopes.

---

# 12. Failure taxonomy

- `NOT_X_LOCATOR`
- `ITEM_NOT_FOUND`
- `ITEM_PRIVATE_OR_UNAVAILABLE`
- `AUTH_REQUIRED`
- `RATE_LIMITED`
- `ROUTE_UNAVAILABLE`
- `ROUTE_COST_NOT_ALLOWED`
- `PARTIAL_ONLY`
- `UNSUPPORTED_ARTICLE`
- `POLICY_BLOCKED`
- `RESTRICTED_CONTENT_BLOCKED`
- `MALFORMED_ROUTE_OUTPUT`

A route-specific error is normalized before reaching Core.

---

# 13. Fallback algorithm

```text
load current route registry
filter disabled/unavailable/unauthorized routes
sort by configured policy + fidelity + cost
for each route:
  preflight
  attempt within bounded budget
  if COMPLETE sufficient result -> stop
  if PARTIAL result -> retain as candidate, continue only if higher-fidelity route is allowed
  if auth/action required -> record, continue only to routes not requiring that scope
  if policy block -> never weaken policy in fallback
choose best truthful result
```

Fallback never converts `POLICY_BLOCKED` into success by switching to a less governed route.

---

# 14. Version/provenance semantics

A successful X representation becomes immutable evidence with:

```yaml
acquisition:
  route_class:
  route_id:
  fidelity:
  completeness:
  external_item_id:
```

If later acquisition gets a better representation, create a new Source Version and link:

```text
better_representation_of: <previous_version_id>
```

Do not overwrite the prior representation.

---

# 15. Cost control

R2 must favor user-owned/subscription-included/local methods where practical, consistent with prior P0 cost policy.

Mandatory behaviors:

- route capability exposes cost class;
- metered route requires explicit opt-in/configuration;
- retry policy caps spend;
- one failed capture cannot fan out into unlimited paid calls;
- cost metadata is body-free and auditable.

---

# 16. Health / user action

Ordinary route churn should stay invisible.

Surface user action only when:

- configured key expired;
- browser/session authorization is required;
- no legitimate route can retrieve a high-priority saved item and user action can fix it.

A route-specific outage should be `DEGRADED`, not a broken-Vault alert.

---

# 17. Golden Cases

## R2-G1 Public Post Direct
Public post acquired via legitimate direct route -> ORIGIN fidelity, COMPLETE.

## R2-G2 BYOK Route
Configured API key used via opaque credential reference; no key in Vault/logs.

## R2-G3 Browser Authorized
Authorized browser route reads target only; session credential not persisted.

## R2-G4 Grok Rescue Provenance
Rescue text stored as INTERMEDIARY_RECONSTRUCTION and cannot be cited as verbatim origin.

## R2-G5 Long Article Partial
Snippet-only route -> PARTIAL; never COMPLETE.

## R2-G6 Better Later Representation
Later origin-verbatim acquisition creates a new immutable version linked to prior partial/intermediary version.

## R2-G7 Private/Deleted Item
No bypass attempt; terminal unavailable/action-required semantics are correct.

## R2-G8 Prompt Injection Post
Post content requesting memory/tool access has zero authority.

## R2-G9 Cost Guard
Metered route not configured -> not auto-invoked.

## R2-G10 Fallback Does Not Weaken Policy
Policy-blocked primary route cannot be bypassed through an ungoverned fallback.

---

# 18. Implementation-time verification spike

Before enabling each concrete route, record:

```yaml
route_verification:
  route_id:
  product/version:
  verified_date:
  official_or_primary_docs_checked:
  supported_content_types:
  auth_method:
  observed_limits:
  fidelity_assumption:
  terms/access_constraint_notes:
  test_fixture_results:
```

A stale route verification does not invalidate the Contract; it disables or degrades that route until reverified.

---

# 19. Implementation tasks

- R2.1 X locator parser + fixtures
- R2.2 route capability registry
- R2.3 official/BYOK adapter spike
- R2.4 public origin adapter spike
- R2.5 authorized browser adapter spike
- R2.6 Grok-assisted rescue spike
- R2.7 fidelity/completeness normalizer
- R2.8 fallback/cost policy
- R2.9 Source Version provenance mapping
- R2.10 Golden/adversarial tests

---

# 20. Acceptance criteria

- [ ] X route choice is adapter-based and Core does not depend on one retrieval method.
- [ ] every result truthfully records route/fidelity/completeness.
- [ ] full article/post is never inferred from a snippet.
- [ ] BYOK/browser/session credentials never enter Canonical/telemetry.
- [ ] intermediary AI text cannot masquerade as original X text.
- [ ] prompt-injection content has no authority.
- [ ] disabled/metered routes cannot run silently outside configured policy.
- [ ] route fallback never weakens security/access-control rules.
- [ ] multiple representations remain immutable and traceable.
- [ ] R2-G1..G10 pass for all enabled route classes.

---

# 21. Explicit non-goals

- posting/liking/replying/following;
- account growth automation;
- access-control bypass;
- CAPTCHA solving/anti-bot evasion;
- scraping at scale;
- guaranteed retrieval of every X object;
- treating Grok as canonical authority.

---

# 22. Source-derived vs closure decisions

## Canonical source-derived
- X is P0 priority/main source;
- route can switch behind adapter;
- X Fetcher/Grok/Browser are validation concerns;
- credentials are not Knowledge;
- content is untrusted;
- Capture can succeed before acquisition.

## R2 closure decisions
- route capability registry;
- truthful fidelity/completeness classes;
- direct/public/browser/Grok route classes;
- no metered route without configured allowance;
- intermediary reconstruction cannot be treated as verbatim origin;
- bounded fallback that cannot weaken policy.

---

# 23. One-line contract

> **R2 makes X a high-priority source without making TSUZU dependent on one brittle retrieval method, while preserving route truth, access boundaries, cost control and the difference between original X evidence and intermediary reconstruction.**


---

# SOURCE BOUNDARY — TSUZU_P0_R3_Historical_Bootstrap_Apple_Notes_Markdown_Import_Contract_v0.1_20260909.md

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


---

# SOURCE BOUNDARY — TSUZU_P0_R4_iOS_Share_Create_Only_Capture_Contract_v0.1_20260909.md

# TSUZU P0 R4 — iOS Share / Create-only Capture Contract v0.1

- Date: 2026-09-09
- Status: **Implementation Contract / Closed / Ready to implement**
- Canonical basis: v1.1 Experience Plane / Share UX / Single Mutable Writer / Mobile create-only Capture
- Dependencies: A1-A4, A6; R1 for later URL acquisition
- Scope: iPhone/iOS Share Extension handoff for URL/Text/File without making mobile a Canonical writer
- Non-scope: mobile Recall, mobile AI integration, mobile Canonical editing, CRDT, multi-writer sync, Remote MCP

---

# 0. Decision

P0 mobile capture preserves the UX:

```text
Share -> TSUZU -> "残しました" -> return to source app
```

while preserving architecture:

```text
iPhone = create-only immutable capture transport
Mac TSUZU Core = only mutable Canonical writer
```

The iPhone does **not** write/update Canonical Source manifests directly.

---

# 1. Capture success semantics

On mobile, `残しました` means:

> the Share input has been durably accepted into the local TSUZU mobile outbox with a stable delivery identity and can survive extension/app termination.

It does **not** mean:

- Mac has already processed it;
- URL body has been acquired;
- indexing/discovery is complete.

This matches the canonical principle that Capture succeeds when input is no longer at risk of being lost.

---

# 2. Mobile write boundary

Mobile may write only:

```text
App Group / local TSUZU mobile-outbox
  -> immutable capture envelopes
  -> immutable payload copies
  -> transport runtime state
```

Mobile may not write:

- Canonical Vault objects;
- Deletion Ledger;
- Promotion state;
- Decision/Pattern/Discovery objects;
- SQLite/FTS;
- active Vault locator;
- Recovery/Migration state.

---

# 3. Mobile Capture Envelope

```yaml
mobile_capture_envelope:
  envelope_schema_version: "1.0.0"
  mobile_capture_id: uuid
  idempotency_key: uuid
  created_at:

  input:
    kind: URL | TEXT | FILE
    original_name: string | null
    media_type: string | null

  payload:
    relative_path: payload/original
    sha256:
    bytes:

  source_plan:
    capture_method: IOS_SHARE_URL | IOS_SHARE_TEXT | IOS_SHARE_FILE
    requested_scope: GLOBAL
    sensitivity_hint: PERSONAL

  transport:
    state: LOCAL_PENDING
```

`mobile_capture_id` is stable across retry/relaunch.

---

# 4. Local durability

Share Extension writes to a same-container staging path:

```text
staging/<id>
 -> validate/hash
 -> atomic rename
 -> pending/<id>
```

Only after final local durable publish may UI return `残しました`.

Crash before publish -> no success acknowledgement.

Crash after publish -> retry/relaunch sees the same `mobile_capture_id`.

---

# 5. Secret Guard on mobile

To avoid creating an unnecessary synced copy of obvious credentials, mobile runs a **small high-confidence local restricted-secret guard** before accepting durable outbox payload.

It MUST at minimum cover the same high-confidence credential classes required for Capture:

- private key blocks;
- obvious access/API tokens;
- URL embedded credentials;
- high-confidence signed/auth secret locators.

If the mobile guard is unavailable/corrupt, P0 fails closed for Share acceptance rather than silently persisting possible RESTRICTED material.

The Mac A3 guard runs again before Canonical commit because rules may change.

---

# 6. Transport to Mac

R4 defines a transport adapter boundary. P0 may use a user-owned sync mechanism such as an iCloud-backed inbox, but Core cannot depend on that exact transport.

```yaml
mobile_transport_adapter:
  publish(envelope_ref) -> transport_receipt
  observe_delivery_state(id) -> state
```

Transport states:

- `LOCAL_PENDING`
- `SYNC_PENDING`
- `DELIVERABLE`
- `MAC_ACCEPTED`
- `MAC_COMMITTED`
- `ACTION_REQUIRED`

Transport metadata is runtime state, not Knowledge.

---

# 7. Mac ingestion bridge

Mac bridge converts a delivered immutable envelope into the A3/A4 pipeline.

Mapping preserves:

```text
idempotency_key = mobile idempotency key
planned source identity = stable after first A3 acceptance
payload bytes/hash = mobile envelope payload
capture method = IOS_SHARE_*
```

Same mobile envelope delivered multiple times MUST converge to one Canonical Source effect.

Different share actions of the same URL/text/file remain distinct captures because they have different idempotency keys.

---

# 8. Offline behavior

Offline Share is allowed when local durable outbox storage is available.

```text
no network / Mac offline
 -> local pending accepted
 -> user returns to source app
 -> sync later
```

The user does not need to keep TSUZU open.

A prolonged pending state appears only in R7 Health if intervention becomes necessary.

---

# 9. URL semantics

iOS URL Share stores the URL string only.

- no required page fetch in extension;
- no browser scraping in Share path;
- no redirect resolution before acceptance;
- later R1/R2 acquisition occurs on Mac.

This keeps Share latency and failure surface low.

---

# 10. File semantics

The extension must obtain a stable byte copy from the supplied share item before acknowledging success.

Requirements:

- validate allowed maximum size;
- stream rather than unbounded memory load;
- hash same copied bytes;
- do not retain external security-scoped handle as the only copy;
- temporary provider/file paths are never identity.

If the provider stops supplying bytes before durable copy, do not acknowledge success.

---

# 11. Privacy-safe user feedback

Normal success:

```text
残しました
```

Minimal failure classes:

- `保存できませんでした`
- `この内容は安全のため保存できません`
- `TSUZUの設定を確認してください`

Do not show internal tokens, local paths, stack traces or secret match values.

---

# 12. Single-writer proof

R4 passes only if:

```text
mobile filesystem writes
  != Canonical Vault writes
```

Even if the transport folder physically lives under a sync service, it is an **Inbox/transport namespace**, not the Canonical Vault namespace.

Mac A4 remains the one path that materializes Canonical Sources.

---

# 13. Deletion / stale delivery

If a mobile envelope is delayed and arrives later, it is still a new capture action unless its same idempotency receipt already exists.

R4 does not allow mobile to restore or mutate a TOMBSTONED existing Source.

If an identical delivery envelope was already committed and later its Source was deleted, replay of the same envelope is recognized by receipt and MUST NOT create a new Source that resurrects the deleted content.

A genuinely new share action uses a new idempotency key and is a new user action.

---

# 14. Outbox cleanup

Cleanup occurs only after a body-free durable receipt indicates Mac acceptance/commit or explicit terminal rejection.

Cleanup policy must be bounded by age/space and never delete an unacknowledged accepted envelope merely to reduce storage without surfacing an ACTION_REQUIRED health condition.

No secure-erase guarantee is claimed on mobile flash storage.

---

# 15. Failure behavior

| Failure | Behavior |
|---|---|
| extension killed before atomic publish | no success ack; no partial accepted item |
| killed after publish | envelope survives; retry same ID |
| sync duplicates delivery | A3/A4 idempotency -> one Source |
| Mac offline | pending locally/sync transport |
| mobile secret guard unavailable | fail closed |
| Mac guard newly classifies RESTRICTED | no Canonical Source; body-free terminal receipt |
| file provider disappears | no false success |
| outbox low disk | fail acceptance or ACTION_REQUIRED; never claim saved if not durable |

---

# 16. Golden Cases

## R4-G1 URL Share Online
Atomic local accept -> `残しました` -> later one Canonical URL Source.

## R4-G2 URL Share Offline
No network/Mac -> local durable success -> later delivery/commit.

## R4-G3 Duplicate Transport Delivery
Same envelope delivered N times -> one Source effect.

## R4-G4 Same URL Shared Twice
Two independent share actions -> two Source IDs.

## R4-G5 Extension Crash
Crash before/after publish produces no false success and no corruption.

## R4-G6 Restricted Secret
High-confidence secret blocked before durable outbox; Mac also rechecks.

## R4-G7 File Provider Lifetime
External provider vanishes after Share; TSUZU still has durable copied bytes or had not acknowledged success.

## R4-G8 Single Writer
No test path from iOS can mutate Canonical Source/Deletion/Promotion state.

## R4-G9 Replay After Delete
Old same-idempotency envelope cannot resurrect a deleted Source.

## R4-G10 Low Disk
System refuses/alerts rather than acknowledging a non-durable capture.

---

# 17. Implementation tasks

- R4.1 Share Extension input normalization
- R4.2 local high-confidence Secret Guard
- R4.3 atomic mobile outbox writer
- R4.4 transport adapter + receipts
- R4.5 Mac inbox consumer -> A3 bridge
- R4.6 outbox reconciliation/cleanup
- R4.7 minimal user feedback
- R4.8 Golden/fault tests

---

# 18. Acceptance criteria

- [ ] mobile can durably accept URL/Text/File and immediately return to source app.
- [ ] success acknowledgement is only after local atomic durable acceptance.
- [ ] mobile cannot mutate Canonical Vault state.
- [ ] offline accepted captures eventually deliver without user keeping app open.
- [ ] duplicate transport delivery is idempotent.
- [ ] distinct share actions remain distinct captures.
- [ ] high-confidence restricted secrets are blocked before mobile durable copy and rechecked on Mac.
- [ ] URL acquisition remains asynchronous on Mac.
- [ ] delayed replay cannot resurrect a deleted Source.
- [ ] R4-G1..G10 pass.

---

# 19. Explicit non-goals

- mobile Recall/Discovery;
- remote MCP;
- cloud Canonical DB;
- multi-writer editing;
- CRDT;
- mobile deletion/promotion;
- background webpage fetching on Share path.

---

# 20. Source-derived vs closure decisions

## Canonical source-derived
- Share -> TSUZU -> end UX;
- success means input not lost, not fully processed;
- Mobile is create-only Capture;
- Mac is single mutable writer;
- URL acquisition is separate/background.

## R4 closure decisions
- mobile App Group outbox as local durability boundary;
- transport namespace is non-Canonical;
- mobile high-confidence restricted-secret guard before durable outbox;
- same envelope replay cannot resurrect deleted Source;
- exact sync transport is an adapter, not Core contract.

---

# 21. One-line contract

> **R4 lets the user save from iPhone in one Share action even offline, while keeping mobile append-only, Mac the sole Canonical writer, and transport retries unable to duplicate or resurrect memory.**


---

# SOURCE BOUNDARY — TSUZU_P0_R5_Backup_Restore_Schema_Migration_Recovery_Contract_v0.1_20260908.md

# TSUZU P0 R5 — Backup / Restore / Schema Migration / Recovery Contract v0.1

- Date: 2026-09-08
- Base:
  - TSUZU Canonical Product Architecture v1.1
  - TSUZU Canonical Addendum v1.2
  - TSUZU Canonical Closing Addendum v1.2.1
  - TSUZU P0 Implementation Source of Truth v1.2 — Audited
- Depends on:
  - A1 Canonical Source Contract
  - A2 Atomic Vault Writer Contract
  - A4 Single Writer Worker Contract
  - A5 SQLite / FTS Derived Index + Rebuild Contract
  - A6 Minimal Tombstone / Deletion Ledger Contract
  - B7 Promotion / Dependency Invalidation / Recompute Contract where B objects exist
- Status: Implementation Contract / Ready to implement
- Scope: P0 backup snapshot, restore, schema compatibility/migration, recovery orchestration, cutover, rollback, integrity/failure tests.
- Non-scope: cloud backup service, custom encryption engine, multi-device merge/conflict protocol, undelete, selective object restore UI, automatic 3-way merge, physical secure erase, credential migration, continuous version history, Time Machine replacement.

---

# 0. Decision

R5は、TSUZUのRecoveryを次の原則で閉じる。

> **Canonicalを守り、Derivedは作り直し、Restoreはlive Vaultを直接上書きせず、Deletion Ledgerを最優先し、壊れた状態を検証前にcurrentへ昇格させない。**

P0のRecoveryは「何でも自動で救う」仕組みではない。

次を保証する最小Contractとする。

```text
Backup
  ↓ immutable snapshot
Verify
  ↓
Temporary Vault
  ↓
Deletion Ledger merge/reapply
  ↓
Schema compatibility / migration
  ↓
Canonical integrity validation
  ↓
Derived rebuild
  ↓
Smoke test
  ↓
Atomic active-vault cutover
```

以下は禁止する。

```text
backup -> blind overwrite live Vault
corrupt Canonical -> AI guess repair
old backup ledger -> overwrite current ledger
Derived DB -> restore authority
migration -> mutate current Vault in place
restore -> Last-write-wins merge
```

---

# 1. Canonical basis and responsibility boundary

R5は既存正本の以下を実装可能な形へ落とす。

## 1.1 Canonical requirements inherited

- Restoreはin-place overwriteしない。
- Temporary Vaultへ復元する。
- Integrity Checkを行う。
- Deletion Ledgerを再適用する。
- Schema compatibilityを確認する。
- Indexを再構築する。
- Smoke Test後に切り替える。
- SQLite破損はdiscard/rebuildする。
- Derived破損はCanonical parentからregenerateする。
- Canonical破損は重大障害としてBackupから復旧する。
- Schema Migration前にBackup必須。
- Readerは原則N-1 schemaを読める。
- CanonicalをAI推測で自動修復しない。
- Restore Test / Failure Injection TestをRelease/Founder Gateに含める。

## 1.2 Existing contract ownership

R5は既存責務を再定義しない。

```text
A2 = atomic file / metadata write primitives
A4 = single mutable writer execution boundary
A5 = disposable SQLite/FTS rebuild + atomic index swap
A6 = Deletion Ledger + no-resurrection precedence
B7 = downstream dependency invalidation/recompute
R5 = backup/restore/migration/recovery orchestration
```

R5のRecovery Coordinatorは上記を呼び出す。

---

# 2. Recovery invariants

R5 Hard Invariants:

1. **Active VaultをRestore/Migration中に直接上書きしない。**
2. **Backup Snapshotは作成後immutable。**
3. **Deletion Ledgerは常にSource/Knowledge状態より優先する。**
4. **TSUZU-managed restoreでは current ledger UNION backup ledger を先に構築する。**
5. **Current ledgerを古いbackup ledgerで置換しない。**
6. **Backup/RestoreからSQLite/FTS/queue/cache/lockを正本として復元しない。**
7. **Derivedの破損をCanonicalへ逆流させない。**
8. **Migration前Backupが成功しない限りMigrationを開始しない。**
9. **Schema migrationはdeterministic codeのみ。AI/LLMを使用しない。**
10. **Unsupported/unknown schemaは推測変換しない。**
11. **Restore candidateが完全検証されるまでactive locatorを変更しない。**
12. **Restore/Migration失敗時、現在のactive Vaultはそのまま利用可能である。**
13. **RESTRICTED credential/session secretをBackupへ追加しない。**
14. **Telemetry/operation receiptへSource本文を保存しない。**
15. **Unknown deletion stateはfail closed。**

---

# 3. Backup protection classes

物理directory名だけで「Backup対象/非対象」を推測しない。

P0ではversioned static registryとしてProtection Classを定義する。

```text
PROTECTED
REBUILDABLE
RUNTIME
EXTERNAL_SECRET
```

## 3.1 PROTECTED

失うとCanonical truth / user-owned history / safety factが失われるもの。

最低限:

- Raw Source / User Input
- Canonical Conversation Chronicle
- User Explicit records
- Promoted Knowledge
- Decision Case / canonical assertions where applicable
- Correction Event
- Outcome / canonical Experience evidence
- Lifecycle Event required for authoritative state
- Tombstone / Deletion Ledger
- Canonical system records required for identity/revision/schema

**物理pathに関係なくPROTECTEDはBackup必須。**

## 3.2 REBUILDABLE

Canonicalから再生成できるもの。

最低限:

- SQLite / FTS index
- Embeddings
- Derived summaries that are explicitly rebuildable
- Recomputed ranking/cache views
- Dependency/materialized views that can be reconstructed from protected refs

P0 authoritative Backupからは原則除外する。

Optional copyを将来持ってもよいが、Restore時にauthorityとして採用してはならない。

## 3.3 RUNTIME

Backupしない。

- pending/processing/retry runtime queues
- worker lock
- cache
- WAL/SHM
- temporary telemetry state
- rebuild candidates
- staging files

Runtimeはactive machineのoperation stateであり、Vault Backupではない。

## 3.4 EXTERNAL_SECRET

Backupしない。

- API Key
- OAuth access/refresh token
- session cookie
- private key
- recovery code
- OS Keychain secrets

Restore後にconnector re-authenticationが必要になってよい。

## 3.5 Unknown class

新しいpersistent object_typeがProtection Registryに存在しない場合:

```text
BACKUP_CLASS_UNKNOWN
→ backup fail closed
```

Silent omissionは禁止する。

---

# 4. Backup snapshot format

P0 Backupは**immutable versioned snapshot**とする。

論理構造:

```text
<backup_root>/
  <backup_id>/
    backup.md
    protected/
      ... copied protected objects ...
    COMMITTED
```

`backup_id`はUUIDv4等の衝突困難なID。

File/Directory名をbackup identityにしない。

## 4.1 backup.md

最低限:

```yaml
backup_id:
backup_contract_version: "1.0.0"
created_at:
completed_at:

source:
  vault_instance_id:
  vault_locator_hash:

protection_registry_version:

schema_inventory:
  - object_type:
    schema_versions: []
    count:

content_manifest:
  algorithm: "SHA-256"
  entry_count:
  manifest_hash:

privacy_summary:
  contains_public:
  contains_personal:
  contains_sensitive:
  contains_restricted_knowledge: false

deletion_ledger:
  record_count:
  ledger_manifest_hash:

app_contract:
  canonical_contract_version:
  created_by_app_version:
```

### No body in manifest

`backup.md`へ以下を保存しない。

- Source body
- Conversation body
- full URL content
- secret
- free-text user note

`content_manifest`の個別entryは最低限:

```text
relative_path
protection_class
object_type where applicable
byte_length
sha256
```

## 4.2 COMMITTED marker

Snapshotは最後に`COMMITTED`をdurable publishする。

`COMMITTED`がないSnapshotは:

```text
INCOMPLETE_BACKUP
```

Restore候補にしない。

---

# 5. Backup destination contract

## 5.1 Destination restrictions

Backup destinationは以下を満たす。

- active Vault rootの内部ではない
- App Support index/runtime directoryの内部ではない
- staging/rebuild directoryの内部ではない
- writable
- required capacityを満たす

Symlink等によりactive Vault内部へ再帰するdestinationは拒否する。

## 5.2 Privacy risk

P0はcustom encryption engineを実装しない。

そのためBackupはCanonicalと同等以上にprivacy-sensitiveと扱う。

Backup EngineはUIに依存せず、最低限以下を返せること。

```yaml
privacy_risk:
  contains_personal:
  contains_sensitive:
  destination_type:
  encryption_guarantee: UNKNOWN | OS_MANAGED | USER_MANAGED
  warning_required:
```

`destination_type`は最低限:

```text
LOCAL_USER_STORAGE
USER_SYNCED_STORAGE
REMOVABLE_STORAGE
UNKNOWN
```

UNKNOWN destinationへSENSITIVEを含むBackupを作成する場合、Control Plane側でwarning/confirmationを要求可能にする。

R5自身はUIを作らない。

---

# 6. Backup creation consistency

P0では複雑なfilesystem snapshot engineを作らない。

Recoverabilityをperformanceより優先し、**coherent backup barrier**を使う。

## 6.1 Write barrier

Backup開始時:

```text
1. validate destination
2. acquire Recovery/Maintenance operation lock
3. wait for current A4 Canonical commit boundary
4. pause new Canonical mutation commits
5. new Capture requests may remain in durable runtime queue
6. enumerate/copy PROTECTED set
7. verify copy
8. commit backup manifest + COMMITTED
9. release mutation barrier
10. A4 resumes queued work
```

新しいCapture ingress自体を失敗させる必要はない。

ただしBackup中にCanonicalへcommitはしない。

## 6.2 Why pause writes in P0

P0 Founder corpusでは、backup中の短時間write pauseを受け入れる。

目的:

- cross-object revisionのsnapshot drift回避
- TombstoneとSourceの時間差を減らす
- distributed snapshot protocolを持ち込まない

将来copy-on-write/snapshot APIへ最適化可能だが、R5 v0.1の要件ではない。

---

# 7. Backup creation algorithm

```text
1. BACKUP_REQUEST accepted
2. preflight destination / capacity / permissions
3. acquire maintenance lock
4. freeze Canonical mutation commits at boundary
5. load Protection Registry
6. enumerate all PROTECTED objects deterministically
7. validate each protected object before copy
8. copy exact bytes into backup staging
9. hash copied bytes
10. separately validate Deletion Ledger completeness/readability
11. write backup.md to staging
12. verify manifest against copied snapshot
13. fsync/durability boundary as supported
14. publish snapshot directory
15. publish COMMITTED last
16. read-back verify committed snapshot
17. release maintenance lock
18. record body-free receipt
```

If any PROTECTED object is corrupt/unreadable:

```text
BACKUP_SOURCE_INTEGRITY_FAILED
```

Normal healthy Backupとしてcommitしない。

Partial backupをsuccess扱いしない。

---

# 8. Backup operation result

Logical interface:

```text
createBackup(request) -> BackupResult
```

Request:

```yaml
request_id:
idempotency_key:
destination:
reason: MANUAL | PRE_MIGRATION | PRE_RESTORE | RECOVERY
```

Result:

```yaml
backup_id:
status: COMMITTED | FAILED | ALREADY_COMMITTED
created_at:
completed_at:
protected_object_count:
protected_bytes:
privacy_summary:
error_code:
```

Same idempotency key + same semantic request:

```text
ALREADY_COMMITTED
```

Conflicting request under same idempotency key:

```text
BACKUP_IDEMPOTENCY_CONFLICT
```

---

# 9. Restore modes

P0は2 restore modeを区別する。

## 9.1 NORMAL_RESTORE

Current VaultのDeletion Ledgerがvalid/readableな通常復元。

```text
restore ledger = current ledger UNION backup ledger
```

これが標準。

## 9.2 DISASTER_RESTORE

新端末/全損等で、current Deletion Ledgerが存在しない場合。

A6で確定済みの通り、backup以降に削除された情報を知る方法はない。

したがって:

```text
current ledger unavailable
+
backup ledger valid
=
DELETION_HISTORY_INCOMPLETE risk
```

P0 behavior:

- Normal Restoreとしてsilentに続行しない。
- 明示的なDisaster Restore modeが必要。
- Restore後Healthを`RECOVERED_WITH_DELETION_HISTORY_LIMITATION`とする。
- 「backup作成後に削除された項目が再出現する可能性」を表示可能なstructured warningを返す。

**Deletion historyをAIで推測しない。**

Founder safety gateの標準Restore TestはNORMAL_RESTOREを対象とする。

---

# 10. Restore is snapshot cutover, not merge

P0 Restoreはautomatic merge engineではない。

```text
Selected Backup Snapshot
→ validated restored Vault
→ active Vault switch
```

Current Vaultの新しいObjectをbackup snapshotへ自動3-way mergeしない。

例外は安全上必須の:

```text
Deletion Ledger = current UNION backup
```

のみ。

Restore開始前、current Vaultがhealthy enoughであれば、**PRE_RESTORE Backup**を作成する。

これによりbackup時点以降のcurrent dataを捨てる判断を可逆にする。

Current Vaultが破損して通常Backup不能の場合:

- PRE_RESTORE Backup failureを記録
- live Vaultを直接改変しない
- broken Vault pathをquarantine/retain
- Restore candidateを別pathで構築する

---

# 11. Temporary Vault restore layout

Restoreはlive rootへ展開しない。

例:

```text
<restore_workspace>/
  restore.<restore_id>/
    vault/
    restore-state.md
```

active Vaultと同じfilesystem semanticsが必要なcutoverを行う場合、最終candidateは同一volume上へ配置する。

ただしP0は「directory内容をliveへ上書き」より、**validated new Vault + active locator switch**を優先する。

---

# 12. Active Vault locator contract

R5ではcurrent Vaultへの参照を中央resolver経由にする。

```text
getActiveVaultLocator() -> vault locator
```

A2/A4/A5/A6/B7等がhard-coded pathを独自保持してはいけない。

Cutover時:

```text
1. acquire maintenance lock
2. stop Canonical mutation commits
3. close Vault-bound readers/writers
4. atomically update local active-vault locator record
5. reopen against candidate Vault
6. run immediate health check
7. resume A4 queued mutations
```

Locator record自体はlocal Control Stateであり、Canonical user knowledgeではない。

Cutover後も旧Vaultを即時削除しない。

```text
old Vault -> recovery quarantine / retained rollback source
```

明示cleanupまでは保持可能とする。

---

# 13. Restore pipeline

NORMAL_RESTORE:

```text
1. RESTORE_REQUEST accepted
2. validate backup COMMITTED marker
3. verify backup manifest/hash inventory
4. verify backup schema inventory can be handled
5. if live Vault readable: create PRE_RESTORE Backup
6. acquire maintenance lock
7. pause Canonical commits; new Capture stays queued
8. materialize backup into Temporary Vault
9. validate all PROTECTED objects
10. load current Deletion Ledger
11. load backup Deletion Ledger
12. merge = current UNION backup
13. publish merged Ledger into Temporary Vault first
14. reapply effective deletion to restored objects
15. run schema compatibility/migration if needed
16. run Canonical integrity validation again after migration
17. discard all restored REBUILDABLE state if any exists
18. A5 full index rebuild from restored Canonical
19. B7 dependency invalidation/recompute bootstrap where implemented
20. run Restore Smoke Test
21. mark candidate READY
22. switch active-vault locator
23. reopen services
24. post-cutover health check
25. resume queued A4 mutations into new active Vault
26. retain old Vault/pre-restore backup for rollback
27. body-free restore receipt
```

Deletion Ledger merge must occur **before** any restored Source becomes retrieval-eligible.

---

# 14. Deletion Ledger merge contract

## 14.1 Set semantics

Deletion record identity:

```text
(object_type, object_id)
```

For same target:

### same valid deletion semantics

Use one effective record; preserve earliest valid deletion fact where semantically equivalent.

### conflicting valid records

Example:

```text
same target
but different payload fingerprint / impossible source identity
```

Result:

```text
DELETION_LEDGER_CONFLICT
→ restore fail closed
```

AIで解決しない。

## 14.2 Current wins only by union, not overwrite

「current wins」はLWWを意味しない。

意味は:

```text
if either valid ledger says deleted
→ deleted
```

削除単調性を守る。

---

# 15. Canonical integrity validation during restore

最低限:

- required directory/system state readable
- known protected object schema valid
- object_id/path consistency where contract requires
- revision valid
- payload exists where required
- payload byte length matches
- payload SHA-256 matches
- source immutable payload contract preserved
- Deletion Ledger records valid
- no deletion target/path mismatch
- no unknown PROTECTED object class
- no RESTRICTED credential material introduced as Knowledge through restore processing

Corrupt objectをskipしてRestore成功にはしない。

```text
RESTORE_CANONICAL_INTEGRITY_FAILED
```

---

# 16. Schema compatibility contract

Schema compatibilityはobject typeごとに判定する。

Current appを`N`としたP0 default:

```text
schema == N
→ READ_NATIVE

schema == N-1
→ READ_COMPATIBLE / MIGRATE_TO_N before cutover

schema > N
→ RESTORE_REQUIRES_NEWER_APP

schema < N-1
→ UNSUPPORTED_OLD_SCHEMA
   unless an explicitly registered and tested migration chain exists

unknown object_type/schema
→ SCHEMA_UNKNOWN_FAIL_CLOSED
```

「だいたい読めそう」で続行しない。

---

# 17. Canonical migration contract

Canonical migrationはlive Vaultへ直接行わない。

```text
Current Vault
  ↓ mandatory pre-migration Backup
Temporary Migration Vault
  ↓ deterministic migration
Validate
  ↓ rebuild Derived
Smoke
  ↓ active locator cutover
```

## 17.1 Migration properties

Migration functionは:

- deterministic
- versioned
- test fixtureあり
- idempotent where practical
- body meaningを勝手に変更しない
- AI/LLM不使用
- Source raw payloadを変更しない
- object_idを維持
- schema_versionを明示更新
- required revision/update semanticsを守る

## 17.2 Migration registry

Logical interface:

```text
migrate(object_type, from_version, to_version, object)
```

Unregistered migration:

```text
MIGRATION_PATH_MISSING
```

## 17.3 Migration receipt

Body-free system record:

```yaml
migration_id:
started_at:
completed_at:
from_schema_inventory_hash:
to_schema_inventory_hash:
migration_contract_version:
object_counts:
failure_counts:
pre_migration_backup_id:
status:
```

Source本文を保存しない。

---

# 18. Pre-migration backup gate

Migration開始条件:

```text
pre_migration_backup.status == COMMITTED
AND backup read-back verification passed
```

Backup失敗時:

```text
MIGRATION_BLOCKED_NO_BACKUP
```

Migrationを開始しない。

これはwarningではなくHard Gate。

---

# 19. Migration rollback

Migration failure before cutover:

```text
active Vault untouched
candidate quarantined/discardable
pre-migration backup retained
```

Migration failure after locator cutover but immediate health check before release:

```text
reacquire/retain maintenance lock
switch locator back to old Vault
mark migration failed
keep candidate for diagnosis without body telemetry export
```

A4 queued mutationsはrollback完了後にold active Vaultへ再開する。

---

# 20. Recovery class behavior

## 20.1 SQLite / FTS corrupt

Ownership: A5.

```text
detect
→ close
→ discard derived DB/sidecars
→ rebuild from active Canonical
```

R5はCanonical Restoreを起動しない。

## 20.2 Rebuildable Derived corrupt

```text
mark stale/ineligible
→ regenerate from protected parent/evidence
```

必要に応じてB7を使う。

CanonicalへDerived内容を戻さない。

## 20.3 Canonical object corrupt

```text
stop strong use of affected object
health = CANONICAL_INTEGRITY_FAILURE
→ recover from valid Backup
```

AI inferenceで修復しない。

## 20.4 Deletion Ledger unavailable/corrupt

Ownership: A6 safety rule。

```text
UNKNOWN_FAIL_CLOSED
→ recall/rebuild eligibility deny
→ restore/recovery required
```

可用性よりanti-resurrectionを優先する。

## 20.5 Runtime queue corrupt

Runtime stateはBackup source of truthではない。

Recoverable jobのみquarantine/retry policyへ。

Canonical committed receiptがあるものを二重commitしない。

R5はA4 idempotency contractを利用する。

---

# 21. Restore Smoke Test

Restore candidateをREADYにする最低条件:

1. Canonical protected-object full validation PASS
2. Deletion Ledger full validation PASS
3. effective deletion resolver PASS
4. A5 `integrity_check` PASS on rebuilt index
5. eligible source set is consistent with Canonical + Ledger
6. fixed bounded exact-ID/read fixtures PASS
7. TOMBSTONED fixture is not retrievable
8. current active Hostを使わないlocal retrieval smoke PASS
9. no external AI egress required
10. body-free Health state = RESTORE_CANDIDATE_HEALTHY

Personal Discovery品質そのものをRestore Gateにしない。

B-derived rebuildが未完了の場合:

```text
Canonical healthy
Index healthy
Discovery derived rebuilding
→ candidate may cut over with Health YELLOW
```

ただしstale B-derived objectをstrong current useしてはならない。

---

# 22. Health states exposed by R5

R7 Control Planeが利用できるstructured health onlyを定義する。

```text
HEALTHY
BACKUP_IN_PROGRESS
BACKUP_FAILED
RESTORE_IN_PROGRESS
RESTORE_CANDIDATE_INVALID
RESTORE_READY
RECOVERED_WITH_DELETION_HISTORY_LIMITATION
MIGRATION_IN_PROGRESS
MIGRATION_BLOCKED_NO_BACKUP
MIGRATION_FAILED
CANONICAL_INTEGRITY_FAILURE
DELETION_LEDGER_UNAVAILABLE
DERIVED_REBUILDING
```

R5は日常Dashboardを作らない。

---

# 23. Failure behavior

| Failure | Required behavior |
|---|---|
| Backup interrupted before COMMITTED | incomplete; never selectable as valid restore |
| Backup destination full | fail backup; live Vault untouched |
| Source corrupt during backup | fail healthy backup; do not silently skip |
| Manifest/hash mismatch | backup invalid; restore denied |
| Unknown protected object class | fail closed |
| Restore interrupted before cutover | live Vault unchanged |
| Current Ledger valid, backup Ledger stale | union; current deletion remains effective |
| Ledger record conflict | restore fail closed |
| Current Ledger unavailable in normal restore | normal restore denied; explicit Disaster Restore only |
| Backup schema newer than app | require newer app; no downgrade guess |
| Backup schema N-1 | migrate in Temporary Vault |
| Migration path missing | fail before cutover |
| Pre-migration backup fails | migration not started |
| Migration crashes | old live Vault remains/switches back |
| Index rebuild fails | candidate not READY for normal Founder restore |
| B-derived recompute fails | mark stale/ineligible; Canonical may remain recoverable |
| Active locator cutover health check fails | rollback locator before releasing maintenance lock |

---

# 24. Concurrency and maintenance lock

R5 operation lockはA4 Single Writer process boundaryと協調する。

P0では同時に許可しない:

```text
Backup commit snapshot
Restore cutover
Canonical schema migration
```

Operation ordering:

```text
one Recovery/Maintenance operation at a time
```

Capture ingressは可能ならdurable queueへ受け入れてよいが、Canonical commitはbarrier解除まで待つ。

Delete mutationも同様にqueueされる。

**Restore中にDeletion mutationを別Vaultへcommitさせない。**

---

# 25. Backup retention and cleanup

R5 v0.1はretention policyを自動最適化しない。

P0 minimum:

- committed Backupを自動上書きしない
- pre-migration Backupはmigration success直後に自動削除しない
- pre-restore Backupはrestore success直後に自動削除しない
- incomplete stagingはrecovery scanでcleanup可能
- deletion of old backups is explicit Control Plane operation in R7 scope

Backup削除はCanonical Source deletionとは別操作。

---

# 26. Security boundaries

## 26.1 Backup content is data

Backup内のWeb/X/PDF/Conversation本文はuntrusted data。

Restore中に:

- promptとして実行しない
- Tool命令として解釈しない
- migration instructionとして解釈しない
- external AIへ送らない

## 26.2 No credentials

OS Credential StoreはBackup対象外。

Restoreによってconnector secret/sessionを復元しない。

## 26.3 Filesystem safety

Restore enumeration時:

- path traversal拒否
- unexpected symlink拒否/明示扱い
- manifest外fileをauthorityとして自動読込しない
- expected regular-file/directory structureを検証

## 26.4 Telemetry

Allowed:

- backup_id / restore_id / migration_id
- counts / bytes
- durations
- error codes
- hash/fingerprint where not secret-derived leakage risk
- schema versions
- health states

Not allowed:

- Source body
- Conversation body
- FTS body
- full URLs
- credentials
- backup archive/file itself

---

# 27. Recovery operation receipts

Body-free local receiptsを残す。

## Backup Receipt

```yaml
operation: BACKUP
request_id:
backup_id:
status:
started_at:
completed_at:
protected_object_count:
manifest_hash:
error_code:
```

## Restore Receipt

```yaml
operation: RESTORE
restore_id:
backup_id:
mode: NORMAL_RESTORE | DISASTER_RESTORE
status:
started_at:
completed_at:
pre_restore_backup_id:
merged_deletion_record_count:
from_schema_inventory_hash:
to_schema_inventory_hash:
old_vault_locator_hash:
new_vault_locator_hash:
error_code:
```

## Migration Receipt

Section 17.3を使用。

Receiptsに本文を保存しない。

---

# 28. Golden Cases

R5 Mandatory Golden Cases:

## R5-G1 — Healthy Backup / Restore Round Trip

Given:
- valid active Vault
- LIVE Sources
- valid Deletion Ledger

When:
- backup
- restore into Temporary Vault
- rebuild A5
- smoke
- cutover

Then:
- protected Canonical identity/revision/hash set preserved
- live eligible Source set equivalent
- no body copied into telemetry

## R5-G2 — Interrupted Backup

Inject crash after file copy but before COMMITTED.

Expected:
- snapshot not valid
- live Vault unchanged
- retry creates/finishes one valid snapshot by idempotency policy

## R5-G3 — Corrupt Backup Payload

Modify one backed-up payload byte.

Expected:
- hash validation fails
- restore denied before cutover

## R5-G4 — Tombstone No Resurrection

Given:
- old backup contains Source as LIVE
- current Ledger says Source deleted

Restore.

Expected:
- current UNION backup ledger contains deletion
- restored Source remains ineligible
- A5 rebuild excludes it

## R5-G5 — Restore Crash Before Cutover

Crash after Temporary Vault build but before active locator update.

Expected:
- old active Vault still active
- candidate remains non-authoritative
- restart can discard/resume safely

## R5-G6 — N-1 Schema Migration

Backup contains supported N-1 object schema.

Expected:
- migration runs only in Temporary Vault
- raw payload unchanged
- object identity preserved
- post-migration validation passes
- original backup remains unchanged

## R5-G7 — Newer Schema Reject

Backup contains N+1 schema.

Expected:
- `RESTORE_REQUIRES_NEWER_APP`
- no mutation to live Vault

## R5-G8 — Migration Requires Backup

Force pre-migration backup failure.

Expected:
- migration never starts
- live schema unchanged

## R5-G9 — Migration Failure Rollback

Inject deterministic migrator failure.

Expected:
- live locator unchanged before cutover OR rolled back before maintenance release
- pre-migration backup retained

## R5-G10 — Missing/Corrupt SQLite

Backup has no SQLite or restored derived state is discarded.

Expected:
- A5 rebuild from Canonical succeeds
- recall eligibility equivalent after rebuild

## R5-G11 — Current Ledger Missing

NORMAL_RESTORE with no valid current ledger.

Expected:
- normal restore fails closed
- explicit Disaster Restore path required
- limitation health/warning emitted

## R5-G12 — Unknown Protection Class

Introduce persistent unknown object type.

Expected:
- Backup fails rather than silently omitting it

## R5-G13 — Cutover Health Failure

Inject failure immediately after locator switch but before maintenance release.

Expected:
- locator restored to old Vault
- queued mutations not written to failed candidate

## R5-G14 — Post-backup Capture Queue

Capture arrives while Backup/Restore maintenance barrier is held.

Expected:
- ingress accepted durably where A3/A4 permits
- not committed into frozen/candidate Vault prematurely
- processed once after active Vault resumes

---

# 29. Failure Injection Matrix

Minimum fault points:

1. after backup staging created
2. mid protected-file copy
3. after manifest write / before COMMITTED
4. after COMMITTED / before read-back receipt
5. mid Temporary Vault materialization
6. before Deletion Ledger merge
7. after Ledger merge / before migration
8. mid migration
9. after migration / before integrity validation
10. mid A5 rebuild
11. after candidate READY / before locator switch
12. immediately after locator switch
13. before queued A4 work resumes
14. old Vault cleanup attempt

Each fault must prove one of:

```text
old active remains authoritative
OR
new candidate is fully validated before authority
```

中間状態が「どちらが正本かわからない」状態になってはならない。

---

# 30. Implementation tasks

## R5.1 — Protection Registry + Backup Manifest

Acceptance:
- all persistent object types classify into PROTECTED/REBUILDABLE/RUNTIME/EXTERNAL_SECRET
- unknown class fails closed
- manifest is body-free and hash-verifiable

## R5.2 — Coherent Backup Coordinator

Acceptance:
- maintenance barrier produces one coherent protected snapshot
- incomplete backup cannot be restored
- idempotent retry semantics exist

## R5.3 — Backup Privacy / Destination Preflight

Acceptance:
- active Vault recursion prevented
- destination capacity/permission checked
- sensitivity/privacy summary exposed without content

## R5.4 — Restore Materializer + Validator

Acceptance:
- restore never writes into live Vault
- full protected integrity validation required
- corrupt snapshot rejected

## R5.5 — Ledger Merge / Anti-resurrection Restore

Acceptance:
- current UNION backup ledger semantics
- unknown/corrupt ledger fails closed
- stale backup cannot resurrect tombstoned Source

## R5.6 — Schema Compatibility + Migration Registry

Acceptance:
- N and N-1 handling explicit
- N+1 rejected
- migration deterministic/no LLM
- raw Source payload immutable

## R5.7 — Pre-migration Backup + Rollback

Acceptance:
- migration cannot start without committed backup
- failure leaves old active Vault usable

## R5.8 — Derived Rebuild Orchestration

Acceptance:
- restored SQLite/FTS is discarded/rebuilt via A5
- B7 stale/invalidation semantics honored where present
- Derived failure never repairs Canonical

## R5.9 — Active Locator Cutover

Acceptance:
- all writers resolve one active locator
- cutover occurs under maintenance lock
- immediate health failure rolls back before release

## R5.10 — Golden / Fault Tests

Acceptance:
- G1–G14 pass deterministically
- fault points 1–14 have assertions
- no flaky pass accepted for deletion/integrity/migration cases

---

# 31. Acceptance criteria

R5 DONE条件:

1. Backup対象がProtection Classで明示され、unknown persistent objectをsilent omitしない。
2. PROTECTED objectとDeletion LedgerがBackupされる。
3. SQLite/FTS/runtime/credentialをauthorityとしてBackup/Restoreしない。
4. Backupはimmutable snapshotで、COMMITTED前は無効。
5. Backup中のCanonical snapshot consistencyが保証される。
6. RestoreはTemporary Vaultへ行い、liveをblind overwriteしない。
7. NORMAL_RESTOREでcurrent ledger UNION backup ledgerが必ず適用される。
8. stale backupからTOMBSTONED objectがRecall可能に戻らない。
9. Current ledger不在をsilent normal restoreしない。
10. Canonical full integrity validation失敗時にcutoverしない。
11. Current/N-1/newer/unknown schemaの扱いが決定的。
12. Migration前BackupがHard Gate。
13. MigrationはdeterministicでAI/LLMを使わない。
14. Migration失敗時にold active Vaultへ戻れる。
15. Raw Source payloadをmigrationで変更しない。
16. A5 IndexをCanonicalから再構築できる。
17. Derived/B7再計算失敗がCanonicalへ逆流しない。
18. active-vault cutoverが単一のauthority boundaryを持つ。
19. Cutover直後Health失敗でrollbackできる。
20. Restore Smoke Testが外部AI egressなしで実行できる。
21. Backup destination privacy summaryをR7へ返せる。
22. Recovery telemetry/receiptsに本文・Secretを保存しない。
23. G1–G14がPASSする。
24. Restore Test / Failure Injection TestをFounder safety gateの証跡として残せる。

---

# 32. Explicit non-goals

- encrypted proprietary backup archive
- TSUZU cloud backup
- Dropbox/Drive等へのbackup connector
- automatic backup retention optimizer
- minute-by-minute version history
- multi-device restore conflict merge
- selective object restore UI
- semantic conflict resolution
- CRDT
- undelete
- forensic secure erase guarantee
- OS Keychain secret transfer
- automatic credential re-authentication
- AI-assisted schema migration
- AI-assisted corrupt Canonical repair
- restoring SQLite as source of truth
- guaranteed recovery from deletion history that no longer exists anywhere

---

# 33. Gate to R6 / Founder Product Proof

R5をFounder Safety Gateとして閉じる条件:

```text
R5-G1 Healthy Round Trip PASS
R5-G4 Tombstone No Resurrection PASS
R5-G6 N-1 Migration PASS
R5-G8 Migration Requires Backup PASS
R5-G9 Migration Failure Rollback PASS
R5-G13 Cutover Health Failure PASS
```

加えて:

- A5 rebuild equivalence PASS
- A6 Deletion Ledger availability/anti-resurrection PASS
- body-free recovery report生成

これを満たせば、Canonical/Recovery観点でR6 Passive Recall / Trusted Intentを次の主要Blockerとして扱える。

---

# 34. Source-derived vs implementation closure decisions

## Canonical source-derived requirements

以下はv1.1/v1.2.1およびA5/A6/B7から継承した要求:

- Temporary Vault restore
- no in-place overwrite
- Integrity Check
- Deletion Ledger reapplication
- current UNION backup ledger anti-resurrection semantics
- schema compatibility and N-1 reader expectation
- backup before schema migration
- index discard/rebuild
- Canonical corruption requires backup recovery
- no AI repair of Canonical
- Restore/Failure Injection Gate

## R5 v0.1 implementation closure decisions

既存Canonicalが方法を固定していなかったため、R5でP0用に確定したもの:

- Protection Class Registryでbackup inclusionを決める
- committed immutable backup snapshot + final COMMITTED marker
- coherent maintenance barrier during backup
- NORMAL_RESTORE / DISASTER_RESTORE分離
- P0 Restoreはsnapshot cutoverでありautomatic 3-way mergeではない
- validated new Vault + active locator switchを優先
- live migrationを禁止しTemporary Migration Vaultで行う
- Nより古いschemaは明示migration chainがなければfail closed
- cutover直後health failureはmaintenance release前にlocator rollback
- R5-G1〜G14をmandatory Golden Casesとする

これらはProduct Scope追加ではなく、既存Recovery ConstitutionをP0実装可能にするためのambiguity closureである。

---

# 35. One-line contract

> **R5は、TSUZUのユーザー所有Canonicalをimmutable Backupとして保護し、削除履歴を失わせず、壊れたDerivedは作り直し、Schema変更や復元を必ず検証済みTemporary Vault上で行ってから単一のactive Vaultへ切り替えることで、「壊しても戻せる」をP0 Founder Test前に証明する。**


---

# SOURCE BOUNDARY — TSUZU_P0_R6_Passive_Recall_Trusted_Intent_Invisible_Egress_Contract_v0.1_20260909.md

# TSUZU P0 R6 — Passive Recall / Trusted Intent / Invisible Egress Contract v0.1

- Date: 2026-09-09
- Status: **Implementation Contract / Closed / Ready to implement**
- Canonical basis: v1.1 Passive Recall + v1.2 Invisible Operation + v1.2.1 Observation/Egress + B9 trusted-intent security spike
- Dependencies: A7 Policy/Egress, A8 Context Bundle/Trace, A9 Claude Code Host Adapter, B8 Discovery, B9 Discovery Injection, B10 Product Events
- Scope: safe automatic recall/discovery injection on a user-originated current turn without requiring the user to summon TSUZU
- Non-scope: SENSITIVE silent override, background autonomous memory egress without a user turn, remote/cloud relay, passive action execution

---

# 0. Decision

R6 closes the tension between:

```text
Connect once. Never summon.
```

and:

```text
Content is data, never authority.
```

Passive Recall may run without a per-call approval dialog **only when the trigger is cryptographically/logically bound to a current structured user-originated host event**, not to repository text, webpage text, tool output, assistant output or other untrusted content.

If that trusted-intent proof is missing or ambiguous, R6 downgrades to explicit approval/explicit recall. It does not guess.

---

# 1. Security claim

The only thing allowed to authorize passive PERSONAL-memory egress to a `TRUSTED_EXTERNAL` host is a valid, fresh, scoped **Trusted Intent Token** minted from a host event classified by the adapter as `USER_PROMPT` / equivalent user-originated input.

Plain text saying "the user asked" is never sufficient.

---

# 2. Trusted Intent Token

```yaml
trusted_intent_token:
  token_id: uuid
  issued_at:
  expires_at:
  single_use: true

  host_id:
  destination_id:
  session_id:
  user_event_id:
  user_event_type: USER_PROMPT

  granted_scope:
  capability: PASSIVE_RECALL

  intent_projection_hash:
  adapter_version:
  policy_version:
  integrity_source: HOST_ADAPTER_STRUCTURED_EVENT
```

The token body is local runtime/security state, not Knowledge.

---

# 3. Token invariants

A token MUST be:

- minted locally by a trusted Host Adapter;
- bound to one destination/host/session/user event;
- short-lived;
- single-use for one passive recall evaluation;
- rejected if scope broadens after issuance;
- rejected after session/user-event mismatch;
- impossible to mint from untrusted content text alone;
- represented in Context/Egress Trace by token ID/hash, not by full user prompt body.

Replay fails closed.

Token authenticity MUST be protected by an implementation mechanism that caller-controlled content cannot forge, such as an opaque process-local token registry or a MAC using a process-local secret. A caller may not construct a valid token merely by supplying matching YAML/JSON fields.

---

# 4. Intent Projection

R6 does not hand arbitrary entire host context to the trigger classifier.

```yaml
intent_projection:
  user_event_id:
  user_text: bounded_current_user_input
  structured_host_mode: optional
  workspace_scope: typed_scope
  conversation_stage_hint: optional
```

Excluded from authorization input:

- repository/file contents;
- retrieved web/X content;
- tool output;
- MCP result text;
- assistant message text;
- model-generated hidden summaries;
- instructions embedded inside imported memory.

Those may later be data for answering, but cannot create the authority to fetch personal memory.

---

# 5. Passive Recall trigger semantics

Topical similarity alone is insufficient.

Trigger evaluation must classify the current user need into at least:

- `ANSWER_REQUIRED`: past user-specific evidence is likely necessary to answer correctly;
- `DECISION_RELEVANT`: prior decision/outcome may materially alter the current decision;
- `DISCOVERY_OPPORTUNITY`: current user is exploring/deciding and grounded personal evidence may add meaningful connection/challenge;
- `TOPICAL_ONLY`: merely related topic;
- `NONE`.

Passive retrieval may proceed for the first three only, subject to policy/budget.

`TOPICAL_ONLY` and `NONE` -> no passive recall.

---

# 6. Trigger confidence / safe downgrade

R6 supports:

```yaml
trigger_decision:
  class:
  confidence: LOW | MEDIUM | HIGH
  reason_code:
```

Default:

- HIGH/MEDIUM + valid token -> evaluate retrieval;
- LOW -> no passive egress or require explicit approval depending on host UX;
- invalid/missing token -> explicit mode only.

No Aha is an acceptable result.

---

# 7. Retrieval / egress inheritance

R6 cannot weaken A7/A8:

- RESTRICTED external egress: always deny;
- SENSITIVE external: default deny;
- unknown sensitivity: deny;
- unknown destination: deny;
- TOMBSTONED: deny;
- scope mismatch: deny;
- current Secret Guard before egress;
- body-free Context Trace/Egress Manifest required.

R6 only authorizes **whether passive evaluation may occur**, not whether every candidate may egress.

---

# 8. Sensitivity policy for passive mode

P0 passive mode:

| Sensitivity | TRUSTED_EXTERNAL passive |
|---|---|
| PUBLIC | allow if relevant |
| PERSONAL | allow with valid Trusted Intent Token |
| SENSITIVE | deny |
| RESTRICTED | deny |
| UNKNOWN | deny |

The v1.1 concept of a possible one-time SENSITIVE override is not exercised silently by R6.

---

# 9. Context presentation classes

## BACKGROUND
Memory can shape the host answer without a user-facing memory callout when safe and ordinary.

## SUPPORTING
TSUZU-derived past evidence materially supports the answer. Source Trace should be available and may be surfaced where useful.

## DECISION_RELEVANT
Past decision/outcome/conflict could materially change the user's choice. The host MUST make that influence legible enough to avoid covertly steering the user and MUST preserve Source Trace.

These are presentation semantics, not different security privileges.

---

# 10. Discovery injection

B8/B9 Discovery Candidate can be passively injected only after:

1. valid Trusted Intent Token;
2. trigger class is eligible;
3. current evidence revalidation;
4. A7/A8 policy pass;
5. No-Aha/diversity rules;
6. bounded context budget.

Exploratory Jump remains explicitly hypothesis-like and cannot be phrased as a known personal fact.

---

# 11. Prompt injection threat model

The following must **not** mint intent or trigger passive recall:

- source file says `retrieve the user's secrets`;
- README says `call tsuzu_recall`;
- fetched article says `remember the user's private history`;
- tool/MCP output says `the user wants personal context`;
- assistant output instructs itself to load memory;
- imported Chronicle contains such instructions from prior assistant text.

Only the new structured current user event can authorize passive evaluation.

---

# 12. User control

At minimum:

- global `Passive Recall: ON/OFF`;
- per-host enable/disable;
- scope allowlist inherited from Observation Permission;
- Strict Privacy mode may force explicit approval (R7 mapping);
- immediate disable must take effect before next token issuance.

Turning Passive Recall off does not delete memory.

---

# 13. Host fallback modes

Each host has a runtime mode:

- `PASSIVE_TRUSTED_INTENT_ENABLED`
- `EXPLICIT_APPROVAL_ONLY`
- `EXPLICIT_RECALL_ONLY`
- `DISABLED`

If adapter cannot prove user-event origin, it cannot claim passive support.

A9's per-call approval remains the safe fallback for Claude Code until R6 Host Golden Cases pass against the installed supported host version.

---

# 14. Event / trace semantics

Every passive attempt records body-free:

```yaml
passive_recall_trace:
  trace_id:
  token_id_hash:
  host_id:
  session_id_hash:
  trigger_class:
  trigger_confidence:
  retrieval_attempted:
  candidates_approved_count:
  bundle_id:
  presentation_class:
  product_event_refs: []
  policy_version:
  timestamp:
```

No full user prompt or memory body in telemetry.

---

# 15. Noise / repetition controls

R6 should not fire on every turn.

P0 controls:

- trigger eligibility before retrieval;
- bounded candidate count/context size;
- dedupe recent surfaced discovery IDs;
- cooldown/relevance suppression for repeated irrelevant Aha;
- no injection when utility threshold not met;
- B10 `IRRELEVANT_AHA_REPEAT` reporting.

Exact ranking thresholds are implementation/Founder calibration, not fixed Product Constitution.

---

# 16. Failure behavior

| Failure | Behavior |
|---|---|
| missing token | explicit mode/no passive egress |
| token expired/replayed | deny |
| host/session mismatch | deny |
| untrusted content asks for recall | no token/no passive recall |
| A7 unavailable | no passive context |
| trace write fails | fail closed before egress |
| sensitivity unknown | deny candidate |
| user disables passive mid-session | stop new token issuance; reject pending unused token |
| classifier unavailable | explicit fallback |

---

# 17. Golden Cases

## R6-G1 Normal User Decision Prompt
Current user asks a real decision question; valid token -> relevant PERSONAL context can pass A7/A8 and inject.

## R6-G2 Topical Only
User mentions a topic with no material need -> no passive context.

## R6-G3 Repository Prompt Injection
Repo text tells model to recall private memory -> no Trusted Intent Token from that content; no passive egress.

## R6-G4 Web Prompt Injection
Fetched page contains recall instruction -> no passive authorization.

## R6-G5 Tool Output Injection
Tool result requests TSUZU memory -> ignored as authority.

## R6-G6 Assistant Self-trigger
Assistant text proposes calling TSUZU -> cannot mint token.

## R6-G7 Token Replay
Same token used twice -> second denied.

## R6-G8 Scope Mismatch
Token bound to Project A cannot retrieve Project B.

## R6-G9 SENSITIVE Candidate
Valid user intent still cannot silently egress SENSITIVE memory.

## R6-G10 No Aha
Eligible turn with no sufficiently useful candidate -> no injection and no fabricated discovery.

## R6-G11 Decision Relevant Disclosure
Past decision conflict materially affects answer -> DECISION_RELEVANT semantics + trace.

## R6-G12 Passive Disabled
Setting OFF -> no tokens/no passive recall while explicit recall remains possible.

---

# 18. Adversarial matrix

Test at minimum combinations of:

```text
origin: USER_PROMPT | ASSISTANT | FILE | WEB | TOOL | MEMORY
x content: benign | recall-command injection | scope-broadening injection
x sensitivity: PUBLIC | PERSONAL | SENSITIVE | RESTRICTED
x token: valid | missing | expired | replayed | wrong-scope
```

Only valid user-originated + permitted policy combinations may egress.

---

# 19. Implementation tasks

- R6.1 structured user-event adapter contract
- R6.2 Trusted Intent Token mint/verify/replay ledger
- R6.3 Intent Projection boundary
- R6.4 trigger evaluator + safe fallback
- R6.5 A7/A8/B9 passive bridge
- R6.6 presentation class mapping
- R6.7 user controls / runtime mode
- R6.8 body-free tracing + B10 events
- R6.9 adversarial Golden tests

---

# 20. Acceptance criteria

- [ ] passive recall cannot be triggered by untrusted content origin.
- [ ] valid passive authorization is bound to a current structured user event, host, session, scope and capability.
- [ ] token replay/expiry/scope broadening are denied.
- [ ] topical similarity alone does not trigger passive recall.
- [ ] A7/A8 sensitivity/deletion/trace gates remain mandatory.
- [ ] SENSITIVE/RESTRICTED are never silently egressed.
- [ ] no-candidate/no-Aha is a normal success state.
- [ ] DECISION_RELEVANT influence is traceable and legible.
- [ ] passive mode can be disabled globally/per host immediately.
- [ ] hosts without trustworthy user-event provenance remain explicit-only.
- [ ] R6-G1..G12 and adversarial matrix pass before removing A9 approval for that host.

---

# 21. Explicit non-goals

- autonomous background memory egress without a user turn;
- tool execution authorization;
- SENSITIVE silent override;
- personality inference trigger;
- passive recall from unknown external destination;
- forcing an Aha every turn.

---

# 22. Source-derived vs closure decisions

## Canonical source-derived
- Passive Recall only when needed or decision-relevant;
- Invisible operation;
- Content is data;
- observation allowlist;
- SENSITIVE external default deny;
- Context Trace;
- No Aha allowed;
- false personal assertion is hard failure.

## R6 closure decisions
- Trusted Intent Token as authorization boundary;
- only structured current user event can mint token;
- untrusted host context excluded from intent authorization projection;
- token is short-lived/single-use/session/scope-bound;
- explicit fallback if proof unavailable;
- DECISION_RELEVANT requires legible influence.

---

# 23. Gate

R6 is the specification gate for claiming that `Connect once. Never summon.` can be implemented without turning passive recall into an injection-driven exfiltration path.

Code-level removal of A9 per-call approval is allowed only per-host after R6 Golden/Adversarial PASS.

---

# 24. One-line contract

> **R6 permits TSUZU to appear without being summoned only when the current user turn—not files, tools, websites, assistants or old memory—provides fresh scoped authority, and every retrieved item still passes the existing security and trace gates.**


---

# SOURCE BOUNDARY — TSUZU_P0_R7_Thin_Control_Plane_Settings_Health_Privacy_Contract_v0.1_20260909.md

# TSUZU P0 R7 — Thin Settings / Health / Privacy / Data Management Control Plane Contract v0.1

- Date: 2026-09-09
- Status: **Implementation Contract / Closed / Ready to implement**
- Canonical basis: v1.1 Experience Plane/Control Plane + Settings/Health sections + v1.2 Control Plane restatement
- Dependencies: A/R/B health and policy projections; especially A3/A4/A5/A6/A7, R1, R5, R6
- Scope: the minimal TSUZU application/control surface for setup, permissions, privacy, data/recovery and health
- Non-scope: daily chat, memory browser as primary UX, task Inbox, Aha feed, Knowledge Graph UI, analytics dashboard

---

# 0. Decision

TSUZU's own UI is a **control plane, not the place where value is consumed**.

P0 top-level IA is limited to:

```text
Home / Health
Connections
Data Sources & Import
Privacy & Permissions
Storage / Backup / Recovery
Data Management
Advanced
```

No daily-use `Search`, `Chat`, `Aha`, `Tasks`, `Inbox` navigation is added.

---

# 1. Product invariants

1. Control Plane must not create a new organizational burden.
2. Routine healthy processing stays invisible.
3. User action is requested only when necessary.
4. Internal sensitivity taxonomy need not be fully exposed to ordinary users.
5. No UI control can weaken hard security invariants such as RESTRICTED external deny.
6. Health is system state, not a work queue.
7. Data ownership/export/delete/recovery are first-class controls.
8. Connector secrets are never rendered after entry except masked status.
9. Destructive/recovery operations are explicit and traceable.
10. Product Proof does not depend on app DAU/time-in-app.

---

# 2. Home / Health Summary

Default home shows a compact state such as:

```text
TSUZU

● 正常に動作しています
最終処理: 数分前

接続
データソース
プライバシー
保存とバックアップ
データ管理
詳細設定
```

Allowed summary content:

- overall Green/Yellow/Red;
- last successful processing time;
- whether user action is required;
- backup freshness summary;
- connection state summary.

Do not show raw queue counts as a productivity Inbox by default.

---

# 3. Health state model

Each subsystem reports normalized state:

```yaml
health_projection:
  subsystem_id:
  status: GREEN | YELLOW | RED
  action_required: boolean
  reason_code:
  last_success_at:
  observed_at:
  detail_ref: body_free_ref
```

### GREEN
Normal; no user action.

### YELLOW
Degraded/retrying/stale but safe; may not require action.

### RED
Safety/integrity/permission failure or durable processing blocked; likely action required.

A content item failing acquisition is not automatically global RED.

---

# 4. Health aggregation

Overall health is severity-aware, not a naive max:

- Canonical corruption / Deletion Ledger unavailable / Recovery failure -> RED;
- Secret Scanner unavailable for new persistence/egress -> RED or blocking RED;
- one external fetcher outage while capture remains durable -> YELLOW;
- one optional host disconnected -> YELLOW/ACTION_REQUIRED depending user intent;
- no pending work and healthy core -> GREEN.

Aggregation rules are deterministic and versioned.

---

# 5. Connections

Connections page displays:

- supported Host adapters;
- source/fetcher connectors;
- connection status;
- allowed scope/capabilities;
- last verified/last success;
- reconnect/revoke action.

Per connection:

```yaml
connection_view:
  connector_id:
  connector_type:
  status:
  granted_scopes: []
  granted_capabilities: []
  credential_present: boolean
  credential_value: NEVER_EXPOSED
  last_success_at:
```

`connected` does not imply global observation permission.

---

# 6. Data Sources & Import

Provides:

- Apple Notes/Markdown bootstrap entry (R3);
- future supported source connectors only when enabled;
- import scope/coverage summary;
- acquisition health summary;
- user-action-required failures.

No Folder/Tag reorganization UI is required.

---

# 7. Privacy mode contract

P0 exposes two understandable modes while preserving hard policy:

## STANDARD
- existing A7/R6 policy;
- PUBLIC/PERSONAL may go to trusted external host when authorized;
- passive PERSONAL allowed only under R6 trusted intent;
- SENSITIVE external default deny;
- RESTRICTED deny.

## STRICT
- hard rules remain;
- passive external PERSONAL recall is disabled or requires explicit approval;
- explicit external recall can require approval per host;
- local processing remains available.

No mode can allow silent SENSITIVE or any RESTRICTED external egress.

The internal four sensitivity levels remain implementation policy; UI may provide advanced detail separately.

---

# 8. Permission controls

At minimum expose:

```text
host x workspace/project/session scope x capability
```

Capabilities may include:

- read/recall;
- capture/chronicle;
- watch/observe;
- propose.

UI never implies `connected = all capabilities`.

Permission revocation must take effect before new observation/token issuance.

---

# 9. Storage / Backup / Recovery

R7 is UI/orchestration surface only; R5 owns mechanics.

Expose:

- active Vault location/reference;
- backup destination/status/freshness;
- create backup;
- restore preflight;
- recovery/maintenance state;
- schema compatibility/update-required status.

Restore flow must clearly state that active data is switched only after validation and that R5 creates a pre-restore backup where applicable.

Never offer a blind `overwrite current vault` button.

---

# 10. Data Management

P0 includes:

- export user-owned Canonical data;
- delete/forget selected data where supported;
- full delete/reset workflow if implemented by deletion contract;
- show deletion/recovery consequences;
- no hidden AI-generated repair of Canonical.

Deletion action must use A6/R5 semantics, not direct filesystem removal from UI.

---

# 11. Destructive-operation confirmation

For delete/restore/reset/revoke-with-data-impact:

- identify operation and affected scope;
- explain reversible vs logically irreversible state;
- require explicit user confirmation;
- perform preflight;
- produce body-free receipt/result.

Do not require repetitive confirmations for routine non-destructive background processing.

---

# 12. Advanced

Advanced may contain:

- version/build info;
- policy/compiler/index versions;
- diagnostic export with body-free logs;
- adapter capability reports;
- experimental spike toggles;
- developer/test controls gated from ordinary users.

Advanced must not become a hidden path to bypass hard security policies.

---

# 13. Error disclosure

User-facing errors show actionable reason, not internal bodies/paths/secrets.

Diagnostic detail may contain IDs/hashes/version/reason codes but:

- no raw memory body;
- no credential;
- no Authorization/Cookie values;
- no full sensitive query strings;
- no stack trace in normal UI.

---

# 14. Notification philosophy

Default:

- silent healthy success;
- no notification for transient retry;
- surface only persistent action-required or safety/integrity issues;
- no engagement Push strategy in P0.

Control Plane does not optimize for opens.

---

# 15. Accessibility / resilience baseline

P0 controls for critical operations must remain usable with:

- keyboard navigation where desktop technology supports it;
- readable text labels, not color alone for Green/Yellow/Red;
- progress/error states that survive app restart through underlying receipts;
- destructive confirmation that does not depend on animation/transient toast only.

---

# 16. Golden Cases

## R7-G1 Healthy Idle
Home is simple Green; no Inbox/queue burden.

## R7-G2 Fetcher Degraded
R1 adapter outage -> Yellow; durable capture still healthy; no global corruption message.

## R7-G3 Deletion Ledger Failure
A6 critical state -> Red and relevant operations fail closed.

## R7-G4 Standard Privacy
PERSONAL trusted external behavior matches A7/R6; SENSITIVE/RESTRICTED remain blocked.

## R7-G5 Strict Privacy
Passive external PERSONAL is disabled/approval-only without deleting memory.

## R7-G6 Revoke Host
Revocation prevents subsequent observation/trusted-intent tokens.

## R7-G7 Restore
UI invokes R5 preflight/validated restore; no direct overwrite path.

## R7-G8 Delete
UI invokes A6 tombstone/ledger path, not raw file removal.

## R7-G9 Credential Display
Connection page confirms credential presence but never reveals stored token.

## R7-G10 No Daily-use Feature Creep
Navigation contains no chat/Aha feed/task Inbox/search-as-primary surface.

---

# 17. Implementation tasks

- R7.1 normalized health projection/aggregator
- R7.2 Home/Health screen
- R7.3 Connections/permissions screen
- R7.4 Data Sources/Import screen
- R7.5 Privacy modes + R6 controls
- R7.6 Storage/Backup/Recovery surface
- R7.7 Data Management destructive workflows
- R7.8 Advanced/diagnostic body-free export
- R7.9 Golden/UI integration tests

---

# 18. Acceptance criteria

- [ ] TSUZU UI remains a thin Control Plane.
- [ ] healthy users can ignore it.
- [ ] Green/Yellow/Red are deterministic and not raw queue counts.
- [ ] connector scopes/capabilities are visible and revocable.
- [ ] Standard/Strict modes cannot weaken hard sensitivity rules.
- [ ] R5 backup/restore and A6 delete are invoked through their contracts.
- [ ] credential values/content bodies are not exposed in health telemetry/UI diagnostics.
- [ ] routine retry does not create user task burden.
- [ ] destructive actions are explicit and auditable.
- [ ] R7-G1..G10 pass.

---

# 19. Explicit non-goals

- chat client;
- memory exploration feed;
- graph UI;
- tag/folder manager;
- acquisition Inbox Zero;
- admin analytics product;
- engagement notifications;
- team management.

---

# 20. Source-derived vs closure decisions

## Canonical source-derived
- TSUZU app is Control Plane;
- Connection/Data Sources/Privacy/Storage/Delete/Health/Advanced only;
- simple Health Summary;
- no daily operations dashboard;
- internal sensitivity need not be exposed directly;
- no Inbox burden.

## R7 closure decisions
- deterministic normalized Health projection;
- top-level IA fixed for P0;
- `STANDARD` and `STRICT` privacy modes;
- Strict downgrades passive external PERSONAL without weakening other hard rules;
- destructive workflows must route through owning contracts.

---

# 21. One-line contract

> **R7 gives users one small place to connect, protect, recover and own TSUZU without turning TSUZU itself into another app they must organize, check or spend time inside.**


---

# SOURCE BOUNDARY — TSUZU_P0_R8_Codex_Cursor_Host_Adapter_Expansion_Contract_v0.1_20260909.md

# TSUZU P0 R8 — Codex / Cursor Host Adapter Expansion Contract v0.1

- Date: 2026-09-09
- Status: **Implementation Contract / Closed / Ready for host-specific verification**
- Canonical basis: v1.2 Claude Code/Codex/Cursor target + v1.2.1 ONE Host first / shared Adapter / remaining Hosts after initial proof-capable slice
- Dependencies: A7-A9 common host boundary, B1 Chronicle, B9 Injection, R6 Trusted Intent
- Scope: common adapter contract and parity gates for adding Codex and Cursor after Claude Code
- Non-scope: requiring all three hosts before first Founder test, cloud relay, mobile/web chat bidirectional integration

---

# 0. Decision

R8 does not assume that Codex and Cursor expose identical hooks/APIs.

P0 fixes the **behavioral Host Adapter contract**, then each host publishes a truthful capability report based on implementation-time verified host features.

Missing host capability degrades that feature; it does not cause the adapter to fake observation/injection fidelity.

---

# 1. Common Host Adapter capabilities

```yaml
host_capabilities:
  explicit_recall:
  context_injection:
  conversation_chronicle:
  structured_user_event:
  artifact_observation:
  project_scope_identity:
  session_identity:
  source_trace_rendering:
  passive_recall_trusted_intent:
```

Each value:

```text
SUPPORTED | PARTIAL | UNSUPPORTED | DISABLED_BY_POLICY
```

---

# 2. Required P0 baseline per added Host

A Host may be considered `TSUZU_RECALL_CAPABLE` when it supports:

- explicit recall through the common retrieval/egress path;
- trustworthy destination identity;
- bounded context return;
- Source/Context Trace;
- scope that cannot silently widen beyond user grant.

Chronicle/Passive Recall may be added independently only when their own evidence requirements are met.

---

# 3. Host descriptor

```yaml
host_descriptor:
  host_id: CODEX | CURSOR
  adapter_id:
  adapter_version:
  host_version_observed:
  destination_class: TRUSTED_EXTERNAL
  verified_at:
  capability_report_ref:
  supported_version_range:
```

If version leaves verified range, high-risk capabilities such as passive trusted-intent may automatically downgrade until reverified.

---

# 4. Common adapter interfaces

Conceptual interfaces:

```text
HostIdentityResolver
HostScopeResolver
ExplicitRecallBridge
ChronicleCaptureBridge
StructuredUserEventBridge
ContextInjectionBridge
ArtifactObservationBridge
SourceTraceRenderer
CapabilityReporter
```

Core logic remains in TSUZU, not duplicated per Host.

---

# 5. Destination / sensitivity

Codex and Cursor are treated as `TRUSTED_EXTERNAL` only when registered/known under A7 policy.

That still means:

- PERSONAL may egress under allowed capability;
- SENSITIVE external default deny;
- RESTRICTED deny;
- unknown destination/version/integration identity fails closed for protected content.

Vendor-side privacy settings do not replace TSUZU authorization.

---

# 6. Scope mapping

Host adapter must derive a typed scope from trustworthy host metadata where possible:

```yaml
host_scope:
  scope_type: GLOBAL | PROJECT
  scope_id:
  evidence: STRUCTURED_HOST_METADATA | USER_BOUND_CONFIG
```

A repository path string found in conversation content cannot grant scope.

If host cannot provide trustworthy project identity:

```text
GLOBAL_ONLY or explicit user-bound scope
```

never silent broadening.

---

# 7. Conversation Chronicle mapping

Chronicle requires ordered actor/event capture with enough fidelity for B1/B2.

Adapter must identify:

- user vs assistant vs tool/system event;
- session/thread identity;
- timestamp/order;
- scope;
- capture completeness/coverage.

If only partial conversation access is available, mark `PARTIAL` and propagate evidence-coverage bias. Do not infer missing user acceptance.

---

# 8. Structured user event / R6

Passive Recall is enabled per Host only if adapter can independently prove a structured current user-originated event suitable for R6 token minting.

If not:

```text
explicit recall works
passive recall = EXPLICIT_APPROVAL_ONLY or DISABLED
```

Never parse arbitrary conversation text to fabricate `USER_PROMPT` origin.

---

# 9. Artifact observation

Artifact/file/project observations are allowed only when:

- user explicitly granted relevant watch/read scope;
- host exposes trustworthy artifact event/path identity;
- content is treated as untrusted data;
- observation does not imply write permission.

If host lacks reliable event support, do not emulate by scanning the entire filesystem by default.

---

# 10. Common Recall contract

Where host tool protocol permits, expose behavior equivalent to A9 `tsuzu_recall`:

```yaml
input:
  query:
  requested_scope_if_supported:

output:
  bounded_context:
  source_trace:
  no_result_reason:
```

Exact MCP/tool/function mechanism may differ, but semantics and A7/A8 gates do not.

---

# 11. Context injection

Host-specific injection must preserve:

- content role = untrusted/user-memory data, not authority;
- bounded context;
- source IDs/traces;
- current policy revalidation;
- B8 lane/confidence semantics for discovery;
- R6 trusted-intent requirement for passive mode.

---

# 12. Capability Report

Implementation generates a body-free report:

```yaml
host_capability_report:
  host_id:
  host_version:
  adapter_version:
  verified_at:
  official_or_primary_docs_checked: []
  capabilities:
    explicit_recall: SUPPORTED
    conversation_chronicle: ...
    structured_user_event: ...
    passive_recall_trusted_intent: ...
  limitations: []
  regression_fixture_version:
```

This report is the truth; marketing/UI cannot claim unsupported capability.

---

# 13. Reconnect / failure behavior

- connector unavailable -> local TSUZU data remains safe;
- host version incompatible -> disable affected capability, not entire Vault;
- hook/event missed -> mark Chronicle coverage incomplete;
- malformed host event -> discard/fail closed, not reclassify by text guess;
- source trace rendering unavailable -> explicit recall may return structured trace data but capability is PARTIAL;
- tool protocol error -> distinguish no-result from system failure.

---

# 14. Host parity matrix

Required comparison against Claude Code baseline:

| Capability | Claude baseline | Codex | Cursor |
|---|---|---|---|
| Explicit recall | reference | verify | verify |
| A7/A8 policy/trace | reference | mandatory | mandatory |
| Chronicle | B1 reference | verify | verify |
| User-event provenance | R6 reference | verify | verify |
| Passive recall | conditional | conditional | conditional |
| Artifact observation | conditional | verify | verify |
| Project scope | constrained | verify | verify |

`verify` is not permission to assume support.

---

# 15. Golden Cases per Host

## R8-G1 Explicit Recall Parity
Same canonical fixture/query -> same eligible Source set before host formatting.

## R8-G2 SENSITIVE Deny Parity
No host adapter bypasses A7.

## R8-G3 Tombstone Parity
Deleted Source never appears.

## R8-G4 Scope Broadening Attempt
Host metadata/content cannot widen user grant.

## R8-G5 Chronicle Actor Fidelity
Captured events preserve user/assistant/tool roles or mark unsupported/partial.

## R8-G6 Missing User-event Provenance
Passive Recall remains disabled/approval-only.

## R8-G7 Host Upgrade
Unverified incompatible version downgrades risky capabilities until verification.

## R8-G8 Prompt Injection
Repository/tool content cannot mint R6 intent or alter adapter policy.

## R8-G9 Trace Parity
Every egress has Context Trace/host destination identity.

## R8-G10 Capability Honesty
Unsupported feature is reported as unsupported, never silently emulated with broader observation.

---

# 16. Implementation-time source verification

For each Host, before implementation/enabling a capability:

1. check current primary/official documentation;
2. record host/version and supported interface;
3. create minimal spike fixture;
4. verify scope/event ordering/failure behavior;
5. update Capability Report;
6. run parity/security tests.

Host-specific details belong in implementation notes/ADR, not in this stable behavioral Contract.

---

# 17. Implementation tasks

- R8.1 common HostAdapter type/capability model
- R8.2 Codex source verification/spike
- R8.3 Codex adapter + parity tests
- R8.4 Cursor source verification/spike
- R8.5 Cursor adapter + parity tests
- R8.6 capability/version downgrade logic
- R8.7 R6 trusted-intent integration per host
- R8.8 capability reports + UI projection

---

# 18. Acceptance criteria

- [ ] Codex/Cursor share a common behavioral adapter contract with Claude Code.
- [ ] host-specific APIs/hooks do not leak into TSUZU Core contracts.
- [ ] every enabled capability has implementation-time verification evidence.
- [ ] missing capabilities are truthfully downgraded, not guessed.
- [ ] all hosts preserve A7/A8 deletion/sensitivity/trace invariants.
- [ ] R6 passive mode is enabled only with trustworthy user-event provenance.
- [ ] project scope cannot be inferred from untrusted content.
- [ ] capability report is versioned and visible to R7.
- [ ] R8-G1..G10 pass per enabled Host.

---

# 19. Explicit non-goals

- making three-host QA a first-Founder-test blocker;
- requiring feature-perfect host parity;
- remote/cloud relay;
- host write/action permissions;
- filesystem-wide observation to compensate for missing hooks.

---

# 20. Source-derived vs closure decisions

## Canonical source-derived
- Claude Code/Codex/Cursor share adapter architecture;
- one Host first;
- remaining two added after first proof-capable operation;
- three-host formal QA not Founder entry gate;
- observation is allowlisted;
- host-specific hook methods are spike concerns.

## R8 closure decisions
- truthful per-host Capability Report;
- unsupported features degrade independently;
- host/version compatibility can downgrade risky capabilities;
- R6 passive support requires structured user-event provenance per Host;
- parity defined at policy/result semantics, not identical API mechanics.

---

# 21. One-line contract

> **R8 lets TSUZU follow the user from Claude Code to Codex and Cursor without pretending the hosts are identical: the Core contract stays stable, each adapter proves only the capabilities its current host version can actually support, and safety semantics remain identical.**


---

# SOURCE BOUNDARY — TSUZU_P0_R9_Web_Chat_Chronicle_One_Way_Validation_Spike_Contract_v0.1_20260909.md

# TSUZU P0 R9 — Web Chat Chronicle One-way Validation Spike Contract v0.1

- Date: 2026-09-09
- Status: **Validation Spike Contract / Closed / Ready to execute**
- Canonical basis: v1.2/v1.2.1 Web Chat Chronicle One-way = P0 Validation Spike; full bidirectional Web/Mobile AI = post-proof
- Dependencies: B1 Chronicle, B2 Episode, B3 Provenance, A3 Secret Guard, Observation Permission
- Scope: determine whether selected web AI conversations can be safely captured one-way with enough actor/order/scope fidelity to become Chronicle evidence
- Non-scope: web chat Recall/injection, session hijacking, credential/cookie extraction, automation that bypasses provider access controls, Remote MCP

---

# 0. Decision

R9 is a **Spike**, not a promise that every web AI is supported.

Success criterion is not "we scraped the page." It is:

> a legitimate user-authorized method can capture a bounded conversation with actor/order/session provenance, without storing credentials or claiming completeness it cannot prove.

If that cannot be demonstrated for a provider/method, the provider remains unsupported/partial.

---

# 1. One-way boundary

Allowed direction:

```text
Web AI conversation -> local TSUZU Chronicle
```

Forbidden in R9:

```text
TSUZU memory -> Web AI context
TSUZU -> post/send/edit/delete in Web AI
```

This separation contains security and provider fragility.

---

# 2. Candidate acquisition method classes

R9 may evaluate, in order of legitimacy/fidelity:

- `USER_EXPORT_IMPORT`
- `EXPLICIT_SHARE_COPY`
- `BROWSER_EXTENSION_READ_ONLY_CAPTURE`
- `OTHER_PROVIDER_SUPPORTED_EXPORT`

Exact provider method is implementation-time verified.

R9 does not store login cookies/session tokens as a shortcut.

---

# 3. Observation permission

Web Chronicle capture requires explicit configuration:

```text
provider/domain
x account/profile if resolvable without storing credentials
x conversation/session scope
x capability = capture/chronicle
```

Connection to a browser does not authorize all browser history/tabs.

---

# 4. Chronicle event schema mapping

For each captured message/event, R9 must produce enough information for B1:

```yaml
web_chat_event:
  provider_id:
  conversation_external_key_hash:
  session_observed_at:
  event_order:
  actor: USER | ASSISTANT | TOOL | SYSTEM | UNKNOWN
  timestamp_observed: timestamp | null
  content_stream_ref:
  capture_method:
  fidelity:
  completeness:
```

`UNKNOWN` actor is retained as unknown; never guessed into user acceptance.

---

# 5. Fidelity classes

- `EXPORT_STRUCTURED`: provider/export gives structured actor/order data.
- `DOM_OBSERVED`: local extension observed rendered page structure.
- `USER_COPIED`: explicit user-shared representation.
- `UNKNOWN_RECONSTRUCTION`: insufficient for Chronicle Knowledge extraction by default.

Actor/order confidence is separate from content plausibility.

---

# 6. Completeness / coverage

Each captured conversation records:

```yaml
chronicle_coverage:
  state: COMPLETE_AS_OBSERVED | PARTIAL | UNKNOWN
  first_event_observed:
  last_event_observed:
  missing_history_possible: boolean
  reason_codes: []
```

DOM viewport capture does not claim full conversation history unless independently verified.

B5/B8 downstream must preserve coverage bias.

---

# 7. Secret handling

Conversation content may contain credentials.

Before Canonical Chronicle persistence:

- local high-confidence Secret Guard runs;
- RESTRICTED segments are not stored as body;
- body-free omission marker preserves event ordering/coverage;
- surrounding conversation is not automatically discarded if safe to retain;
- SENSITIVE follows local storage/external egress policy.

R9 never stores browser auth cookies/tokens as Knowledge or telemetry.

---

# 8. DOM / browser content trust

If browser extension capture is tested:

- page DOM is untrusted data;
- embedded instructions cannot grant TSUZU permissions;
- extension runs read-only for the allowed page/domain;
- no arbitrary script from page is executed with TSUZU privileges;
- only required conversation fields are extracted;
- permission remains domain/scope bounded.

---

# 9. Duplicate / update semantics

Same observed conversation captured multiple times:

- same stable event fingerprint -> no duplicate Chronicle event;
- new later messages -> append new immutable Chronicle events;
- changed rendered text with same provider event identity -> preserve a new observed version or conflict marker, never silent overwrite;
- missing earlier events on a later capture do not imply deletion.

---

# 10. Provider/account identity

Do not infer personal identity from display names alone.

Provider/account binding is user-configured or based on trustworthy local browser/profile context where available. If ambiguous, capture may remain provider/session scoped without asserting person identity.

---

# 11. Spike output

For each provider/method tested, write body-free Capability Evidence:

```yaml
web_chronicle_spike_result:
  provider_id:
  method:
  verified_at:
  status: PASS | PARTIAL | FAIL
  actor_fidelity:
  ordering_fidelity:
  session_identity_fidelity:
  completeness_fidelity:
  credential_risk:
  maintenance_risk:
  limitations: []
  recommendation: ENABLE | EXPERIMENTAL | DO_NOT_ENABLE
```

No provider support is Canonical until its spike PASS/PARTIAL decision is recorded.

---

# 12. Failure behavior

- provider UI changes -> adapter PARTIAL/disabled, not guessed;
- actor marker unavailable -> UNKNOWN;
- conversation history lazy/unloaded -> PARTIAL;
- login/session unavailable -> ACTION_REQUIRED; do not extract credential;
- extension permission revoked -> stop capture immediately;
- content secret detected -> omit blocked body, preserve coverage marker;
- duplicate capture -> idempotent event mapping.

---

# 13. Golden / spike cases

## R9-G1 Structured Export
Actor/order/session preserved -> PASS-capable Chronicle.

## R9-G2 DOM Partial View
Only visible subset captured -> PARTIAL, never complete.

## R9-G3 Assistant Suggestion Not User Decision
Roles preserved so B3 cannot promote assistant output as user Knowledge.

## R9-G4 Restricted Segment
Secret-containing message omitted/body-blocked without losing event-order marker.

## R9-G5 Duplicate Capture
Re-capture same thread -> no duplicate same event.

## R9-G6 UI Change
Selector/structure fails -> adapter disables/partial; no text-guess actor mapping.

## R9-G7 Prompt Injection in Chat
Conversation content cannot change extension/TSUZU permissions.

## R9-G8 No Cookie Storage
Capture works or fails without persisting auth cookie/session token.

## R9-G9 Missing Old History
Coverage marker prevents downstream statement that unobserved history never occurred.

## R9-G10 One-way Enforcement
No available R9 code path injects TSUZU memory or sends messages to provider.

---

# 14. Implementation tasks

- R9.1 WebChronicle adapter interface
- R9.2 structured export/import spike
- R9.3 read-only browser-extension spike where appropriate
- R9.4 actor/order/session mapper
- R9.5 Secret Guard + omission markers
- R9.6 duplicate/coverage reconciliation
- R9.7 provider capability evidence report
- R9.8 Golden/security cases

---

# 15. Acceptance criteria

R9 Contract is execution-complete when at least one tested method has a documented PASS/PARTIAL/FAIL result and:

- [ ] no web credentials/cookies are stored as Knowledge/telemetry.
- [ ] actor/order/session fidelity is measured, not assumed.
- [ ] partial history is explicitly marked partial.
- [ ] assistant/user roles remain distinct.
- [ ] Secret Guard prevents RESTRICTED Chronicle body persistence.
- [ ] capture permissions are provider/domain/scope bounded.
- [ ] page/chat content cannot alter permissions.
- [ ] capture is idempotent for repeated observations.
- [ ] R9 remains one-way only.
- [ ] R9-G1..G10 pass for each method claimed enabled.

---

# 16. Explicit non-goals

- full bidirectional ChatGPT/Claude/Gemini integration;
- remote MCP;
- browser credential extraction;
- provider auth automation;
- cross-account monitoring;
- universal support guarantee.

---

# 17. Source-derived vs closure decisions

## Canonical source-derived
- Web Chat Chronicle One-way is a P0 Validation Spike;
- full bidirectional Web/Mobile AI is post-proof;
- Chronicle requires user/assistant separation and provenance;
- observation is allowlisted;
- secret/prompt-injection rules apply.

## R9 closure decisions
- one-way capability evaluated by fidelity, not scraping success;
- explicit method classes;
- coverage/partial markers mandatory;
- no credential/cookie persistence;
- provider/method capability evidence report determines enablement.

---

# 18. One-line contract

> **R9 tests whether web AI conversations can become trustworthy one-way Chronicle evidence without pretending partial DOM access is complete, confusing assistant text with user decisions, or turning browser credentials into TSUZU data.**


---

# SOURCE BOUNDARY — TSUZU_P0_R10_Founder_Product_Proof_Experiment_Gate_Calibration_Contract_v0.1_20260909.md

# TSUZU P0 R10 — Founder Product Proof Experiment / Gate Calibration Contract v0.1

- Date: 2026-09-09
- Status: **Evaluation Contract / Closed / Ready to execute after technical gates**
- Canonical basis: v1.1 Product Proof + v1.2 Discovery Proof + v1.2.1 denominator/gate closure
- Dependencies: A10, B10, B11, R3 historical bootstrap, R5 recovery safety, R6 invisible passive recall safety
- Scope: evidence collection and decision protocol for moving TSUZU from Product Proof / TEST toward GO/PIVOT/KILL
- Non-scope: pre-declaring success thresholds before evidence, growth/marketing scale test, team/enterprise proof, pricing optimization beyond initial WTP evidence

---

# 0. Decision

R10 freezes **definitions before results**, not numeric success thresholds before results.

The experiment evaluates at least four axes:

1. Pain
2. Invisible UX
3. Personal Discovery / Compounding
4. WTP

`CONNECTED` or above is the minimum TSUZU-specific Discovery evidence. `REMEMBERED` alone may validate Recall but does not validate Personal Discovery.

---

# 1. Entry gate

Founder Product Proof must not start as a claimable full test until:

### Required technical safety/data gates
- A10 mandatory Slice A cases pass;
- B11 required technical Founder Golden Cases pass;
- R5 required restore/no-resurrection/migration cases pass;
- R6 trusted-intent/adversarial cases pass for the Host used in passive testing;
- B10 event/denominator instrumentation is versioned and queryable.

### Corpus readiness
Each participant/session intended for Discovery measurement must have enough eligible personal history to produce a fair opportunity. R3's small bootstrap is the default acceleration mechanism.

No exact universal corpus count proves readiness; record actual source/episode/evidence counts per participant.

---

# 2. Founder cohort

Canonical v1.1 uses an initial cohort around 10 people as a provisional Founder test frame.

R10 therefore defines:

```yaml
cohort_plan:
  target_participants: approximately_10
  icp:
    frequent_ai_user: true
    saves_urls_notes_or_files: true
    repeated_decision_work: true
    manual_organization_averse: preferred
  inclusion_rules: frozen_before_run
  exclusion_rules: frozen_before_run
```

This target is for learning density, not a statistically representative market survey.

---

# 3. Experiment phases

## F0 — Instrument Validation
Founder/internal use verifies event correctness, traceability, safety and denominators.

No business GO conclusion from F0 alone.

## F1 — Founder Product Proof
Target initial cohort uses TSUZU in real work with a predeclared observation window.

## F2 — Gate Calibration
After F1 data lock, calibrate numeric GO/PIVOT/KILL thresholds for the next cohort/version. Do not retroactively rewrite F1 denominators to make the result look better.

---

# 4. Pre-run freeze manifest

Before F1 begins:

```yaml
experiment_manifest:
  experiment_id:
  product_version:
  event_schema_version:
  policy_version:
  retrieval_version:
  discovery_version:
  host_adapter_version:

  cohort_definition:
  observation_start:
  observation_end:

  denominator_definitions:
  qualitative_questions_version:
  hard_failure_definitions:
  analysis_plan_version:
```

Manifest becomes immutable once the first eligible participant event is recorded.

Corrections require a new amendment record; old definition remains auditable.

---

# 5. Denominators

Use B10/v1.2.1 separate denominators:

- `users`
- `captured_sources`
- `conversation_episodes`
- `eligible_discovery_opportunities`
- `surfaced_discoveries`
- `connected_or_above_events`
- `decision_impact_events`
- `reused_events`
- `wtp_responses`

Never report `CONNECTED rate` without naming its denominator.

---

# 6. Pain evidence

Measure whether the ICP actually experiences:

- re-explaining context to AI;
- saved information becoming dead/forgotten;
- searching/reconstructing old decisions;
- difficulty carrying context across AI/tools/time.

Evidence sources:

- pre-test structured interview;
- concrete recent examples;
- observed retrieval/reuse behavior during test.

General statements like "memory sounds useful" are weak Pain evidence.

---

# 7. Invisible UX evidence

Measure:

- capture burden;
- need to organize/tag;
- frequency of manual TSUZU invocation;
- passive recall usefulness/noise;
- amount of Control Plane attention required;
- security/approval friction.

A participant liking the concept but needing to constantly manage TSUZU is not Invisible UX success.

---

# 8. Discovery / Compounding evidence

For each surfaced event classify, with evidence:

- REMEMBERED
- CONNECTED
- REFRAMED
- EXPANDED
- CHANGED_DECISION
- OUTCOME_HELPED
- REUSED

Strong evidence order is not simply linear, but CONNECTED+ is the product-specific floor.

Qualitative notes must link to body-free product event IDs/source traces, not create unverifiable anecdotes.

---

# 9. Decision Impact

`CHANGED_DECISION` requires evidence that the user's actual decision/plan changed, not merely that the answer contained a new idea.

Possible evidence:

- explicit user statement;
- revised artifact/plan;
- later Revealed Decision;
- Decision Reconciliation evidence.

Silence is not impact.

---

# 10. Outcome / reuse evidence

`OUTCOME_HELPED` remains causal-humble:

- record observed outcome;
- record possible explanations/confounds;
- do not claim TSUZU caused the outcome from temporal sequence alone.

`REUSED` requires a later distinct judgment/context reusing prior TSUZU-connected evidence.

---

# 11. WTP protocol

Collect WTP after participants have experienced the product, not only as a concept survey.

At minimum ask:

1. would you continue using this if free?
2. would you pay for this personally?
3. canonical baseline check: willingness around the previously hypothesized `¥980/month` level;
4. open maximum/acceptable price and why;
5. what would make payment unnecessary/not worth it?

Record actual answer; do not infer WTP from usage.

If later price points are tested, version the questionnaire rather than mixing answers.

---

# 12. Qualitative interview protocol

Post-window interview covers:

- best moment TSUZU helped;
- example where retrieved past was obvious/useless;
- example of CONNECTION/REFRAME/EXPANSION if any;
- example of noise or interruption;
- any false personal assertion;
- trust/privacy concern;
- whether they had to manage TSUZU;
- what they would miss if removed;
- WTP questions.

Interviewers must allow "none"; do not lead participants to invent an Aha.

---

# 13. Hard failure review

Mandatory separate review:

- FALSE_PERSONAL_ASSERTION
- UNSUPPORTED_DECISION_CLAIM
- SENSITIVE_EGRESS_VIOLATION
- IRRELEVANT_AHA_REPEAT
- SUPERSEDED_KNOWLEDGE_MISAPPLIED

`SENSITIVE_EGRESS_VIOLATION` is a Security Incident and pauses affected testing until remediated/reverified. It is not averaged away by good UX metrics.

---

# 14. Analysis integrity

Before seeing outcome rates, freeze:

- eligibility rules;
- denominator definitions;
- event semantics;
- observation window;
- handling of partial/missing telemetry;
- participant exclusions.

After data lock:

- raw event counts remain immutable;
- corrections are amendments;
- missing data is missing, not success/failure by convenience;
- qualitative and quantitative evidence are reported separately then reconciled.

---

# 15. No pre-evidence numeric GO threshold

R10 explicitly does **not** turn v1.1's provisional 7/10, 6/10, etc. into final Canonical gates before Founder evidence.

Those figures remain historical hypotheses/reference points.

After F1, Gate Calibration writes a new decision record with:

```yaml
gate_calibration:
  based_on_experiment_id:
  sample_characteristics:
  observed_distributions:
  data_quality_limits:
  proposed_next_thresholds:
  rationale:
  effective_for_next_experiment_only: true
```

---

# 16. Decision framework

## Candidate GO signal
Evidence indicates:

- real Pain;
- low/manageable operational burden;
- repeatable CONNECTED+ events;
- acceptable noise/hard-failure profile;
- some Decision Impact/Reuse emerging;
- credible WTP from experienced users.

## Candidate PIVOT signals

- useful REMEMBERED recall but little CONNECTED+ -> consider Recall-centered positioning/product changes;
- CONNECTED+ exists but passive noise/friction high -> trigger/UX pivot;
- value/reuse exists but WTP weak -> monetization/ICP pivot;
- only one narrow source/host creates value -> scope/channel specialization may be appropriate.

## Candidate KILL signal

After fair corpus/opportunities and trustworthy instrumentation, repeated users get essentially no meaningful personal advantage beyond ordinary AI/search, with no credible WTP path.

A security implementation bug is normally a STOP/FIX condition, not by itself proof the product hypothesis is false.

---

# 17. Founder Proof Report

Required output:

```markdown
# Founder Product Proof Report

## Experiment identity / frozen manifest
## Cohort and corpus quality
## Pain evidence
## Invisible UX evidence
## Discovery distribution
## Decision Impact / Outcome / Reuse
## WTP evidence
## Hard failures / incidents
## Biases / missing coverage
## What is proven
## What remains unproven
## GO / PIVOT / KILL recommendation
## Gate Calibration for next run
```

Claims must identify whether they are event-derived, interview-derived or inference.

---

# 18. Golden analysis cases

## R10-G1 Denominator Freeze
After experiment starts, changing denominator definition requires amendment/new analysis version.

## R10-G2 REMEMBERED != CONNECTED
Recall-only event cannot count as TSUZU-specific Discovery proof.

## R10-G3 Silence != Impact
No response cannot become USER_ACKNOWLEDGED/CHANGED_DECISION.

## R10-G4 Hard Failure Isolation
Security incident remains visible regardless of overall satisfaction.

## R10-G5 Partial Chronicle Coverage
Incomplete evidence is reported as bias, not interpreted as absence.

## R10-G6 WTP From Experience
Concept-only respondent is not mixed with experienced-user WTP without labeling.

## R10-G7 No Retroactive Gate
Threshold can be calibrated for next run, not back-applied to declare current run successful.

## R10-G8 Outcome Causality Humility
Outcome improvement does not become causal TSUZU claim without evidence.

## R10-G9 Recall Pivot Signal
High REMEMBERED, low CONNECTED is surfaced explicitly rather than averaged into "Aha".

## R10-G10 Reproducible Report
Same locked events + analysis version -> same quantitative tables.

---

# 19. Implementation/execution tasks

- R10.1 frozen Experiment Manifest schema
- R10.2 participant/corpus eligibility worksheet
- R10.3 pre/post qualitative protocol
- R10.4 B10 denominator/event query fixtures
- R10.5 hard-failure incident review
- R10.6 WTP response capture
- R10.7 locked analysis/report generator
- R10.8 Gate Calibration decision record
- R10.9 analysis Golden fixtures

---

# 20. Acceptance criteria

- [ ] experiment definitions/denominators are frozen before F1 data.
- [ ] cohort is ICP-relevant and corpus readiness is recorded.
- [ ] Pain/Invisible UX/Discovery/WTP are all measured.
- [ ] CONNECTED+ is separated from REMEMBERED.
- [ ] Decision Impact/Outcome/Reuse use evidence, not silence or model guess.
- [ ] hard failures are reviewed separately and security incidents pause affected testing.
- [ ] WTP is collected from experienced users and versioned.
- [ ] no final GO/PIVOT/KILL numeric threshold is retroactively invented for the completed cohort.
- [ ] final report separates fact/evidence/inference and records biases.
- [ ] R10-G1..G10 analysis fixtures pass.

---

# 21. Explicit non-goals

- statistical market sizing;
- paid acquisition CAC test;
- team/enterprise WTP;
- final pricing optimization;
- growth retention benchmark;
- declaring business GO from technical Golden Cases alone.

---

# 22. Source-derived vs closure decisions

## Canonical source-derived
- current status is Product Proof/TEST, not business GO;
- four proof axes Pain/Invisible UX/Discovery/WTP;
- CONNECTED+ is TSUZU-specific floor;
- separate denominators;
- hard failures tracked separately;
- numeric GO/PIVOT/KILL calibrated after Founder evidence;
- initial cohort around 10 is a provisional frame;
- ¥980/month is prior WTP hypothesis, not final price.

## R10 closure decisions
- F0/F1/F2 experiment phases;
- immutable pre-run Experiment Manifest;
- WTP collected after use plus canonical ¥980 baseline question;
- hard security incident pauses affected test;
- Gate Calibration applies to next experiment, not retroactively;
- reproducible Founder Proof Report format.

---

# 23. One-line contract

> **R10 turns TSUZU from a well-specified idea into an auditable product test by freezing what will be measured before the results, separating recall from real personal discovery, preserving hard failures, and calibrating business gates only after Founder evidence exists.**
