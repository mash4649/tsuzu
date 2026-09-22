# TSUZU P0 R2 — X Acquisition / Rescue Route Contract v0.2

- Date: 2026-09-09
- Status: **Implementation Contract / Closed / Ready for route spikes**
- Canonical basis: v1.1 X priority source + v1.2.1 X Fetcher strategy / Grok-Browser rescue validation + v1.2.2 cross-cutting closure
- Dependencies: R1 Acquisition/Fetcher v0.2, C2 Effective Source Representation, C3 Generic Deletion, A3 Secret Guard, A4 Single Writer
- Scope: acquisition of X posts/threads/long posts/X Articles through replaceable legitimate routes
- Non-scope: bypassing X access controls, anti-bot evasion, engagement automation, posting/liking/replying, generic browser automation

## v0.2 cross-cutting closure

R2 route output is persisted through R1/C1 and becomes recallable only through C2 representation resolution. Source Version deletion/Root deletion obey C3. Fidelity metadata is mandatory input to C2/A8 trace and must not be upgraded by the router.


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
