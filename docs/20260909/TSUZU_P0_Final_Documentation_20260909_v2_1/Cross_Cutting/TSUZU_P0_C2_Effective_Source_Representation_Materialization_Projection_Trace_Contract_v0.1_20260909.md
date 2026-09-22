# TSUZU P0 C2 — Effective Source Representation / Materialization / Projection / Trace Contract v0.1

- Date: 2026-09-09
- Status: **Cross-cutting Integration Contract / Closed / Ready to implement**
- Canonical basis: Capture/Acquisition separation, immutable Source Versions, Source Trace, Canonical/Derived separation
- Depends on: A1, A5, A6, A7, A8, C1, C3, R1; R2 specializes acquired fidelity
- Scope: deterministic selection of raw content representation, safe rebuildable text projection for index/context, and trace linkage back to user capture
- Non-scope: network fetching, semantic extraction algorithm, Discovery ranking, remote refresh policy

---

# 0. Problem closed by C2

A1 URL Source preserves the **user capture action and locator**. R1 stores fetched remote bytes as immutable `SOURCE_VERSION`.

Without C2, A5/A7 can keep indexing only the URL locator while the acquired page body exists but is never recallable.

C2 defines one explicit bridge:

```text
Root SOURCE (user action)
    + eligible SOURCE_VERSION (content evidence)
        -> Effective Source Representation
        -> A5 projection
        -> A7 revalidation
        -> A8 body + Source Trace
```

Root Source identity is never replaced by a fetched version.

---

# 1. Concepts

## Root Source

A1 `SOURCE`. Represents what the user captured/saved.

## Representation

Bytes/text eligible to represent that Source for a purpose.

- direct TEXT/FILE payload from Root Source
- acquired remote `SOURCE_VERSION` from R1/R2
- locator-only metadata when body is unavailable

## Effective Representation

The deterministic representation selected at query/index time under current deletion/sensitivity/scope/integrity state.

---

# 2. Hard invariants

1. `source_id` remains the primary user-action identity.
2. SOURCE_VERSION never overwrites Root Source payload.
3. A5 must not assume Root Source payload is always the best content body.
4. A7/A8 must re-resolve/revalidate representation from persistent truth; FTS snippet is not authority.
5. C3 deletion of Root Source makes every child representation ineligible.
6. C3 deletion of one Source Version removes only that version; root may remain locator-only or use another eligible version.
7. effective sensitivity can only stay equal or become stricter than the Root Source.
8. child representation cannot widen Root Source scope.
9. unknown/corrupt representation fails closed for body usage.
10. Source Trace records both user capture root and actual representation used.
11. External content remains `UNTRUSTED_DATA` regardless of fidelity.
12. No summary/extraction is promoted to Canonical remote bytes.

---

# 3. Resolver interface

```text
resolve_effective_representation(source_id, purpose, as_of?)
  -> EffectiveRepresentation
```

P0 purposes:

- `INDEX_CURRENT`
- `RETRIEVAL_CURRENT`
- `CONTEXT_CURRENT`
- `TRACE_ONLY`

Historical time-travel UI is not P0, but immutable versions must not block future `as_of` support.

---

# 4. Selection rules

## TEXT / direct note

```text
valid LIVE Root Source payload
-> representation = ROOT_PAYLOAD
```

## FILE

If supported textual payload is directly indexable:

```text
ROOT_PAYLOAD
```

Otherwise metadata-only until a separate extractor Contract produces Derived text. C2 does not invent OCR/parser semantics.

## URL

Candidate Source Versions must satisfy:

- parent_source_id == source_id
- integrity valid
- effective deletion == LIVE
- acquisition status success
- sensitivity known
- representation version supported

For P0 `CURRENT` purpose, select deterministic newest eligible acquired version by:

```text
acquired_at DESC
then object_id deterministic tie-break
```

If none exists:

```text
LOCATOR_ONLY
```

Because R1 does not auto-refresh in P0, most URL Sources have zero or one acquired version initially.

---

# 5. Effective policy fields

### Sensitivity

```text
effective_sensitivity = stricter(root.sensitivity, representation.sensitivity)
```

If either side is unknown -> UNKNOWN -> external fail closed.

### Scope

Representation may narrow but never widen Root scope.

```text
effective_scope = intersection(root_scope, representation_scope_constraints)
```

If no valid intersection -> ineligible.

### Temporal

Expired/current-fact rules from Canonical apply to both root and child.

---

# 6. EffectiveRepresentation schema

Runtime/Derived projection descriptor:

```yaml
root_source_id:
representation_kind: ROOT_PAYLOAD | SOURCE_VERSION | LOCATOR_ONLY
representation_ref:
  object_type: SOURCE | SOURCE_VERSION
  object_id:
content_sha256: null | sha256
content_bytes: null | integer
media_type:
fidelity: DIRECT_USER | ORIGIN_RESPONSE | RESCUE_VERBATIM | RESCUE_RECONSTRUCTED | LOCATOR_ONLY

effective_scope:
effective_sensitivity:
resolved_at:
resolver_version:
```

This descriptor is not a new Canonical truth.

---

# 7. Indexable text projection

Raw Canonical bytes are not automatically indexable text. C2 therefore owns the semantic boundary of a **rebuildable text projection**. Execution/retry may use C4.

```text
Canonical raw representation
 -> media-type-specific local deterministic extractor
 -> Derived Text Projection
 -> A5 FTS / A8 excerpt
```

P0 rules:

- `text/plain` / Markdown-like text: bounded charset decode/normalization.
- HTML: no script execution; deterministic local parsing/sanitization/visible-text extraction.
- PDF: local deterministic text extractor adapter when supported; if extraction cannot be performed safely, record `EXTRACTION_UNAVAILABLE` and remain metadata-only rather than inventing text.
- Binary/unsupported media: metadata-only unless a separately registered safe extractor exists.
- No LLM summary is a substitute for raw-text extraction.
- extractor output is Derived/rebuildable and never overwrites raw SOURCE/SOURCE_VERSION bytes.

Conceptual projection descriptor:

```yaml
text_projection:
  projection_id:
  root_source_id:
  raw_representation_ref:
  raw_sha256:
  extractor_id:
  extractor_version:
  status: READY | METADATA_ONLY | EXTRACTION_UNAVAILABLE | FAILED
  text_sha256: null | sha256
  text_bytes: null | integer
  generated_at:
```

A5 indexes only a `READY` text projection or direct safe text representation. A8 may excerpt the same validated projection, and Source Trace includes raw representation + extractor version.

---

# 8. A5 index projection integration

A5 `source_index`/FTS projection must carry enough identity to prove what body was indexed.

Conceptual columns:

```text
root_source_id
representation_object_type
representation_object_id
representation_sha256
resolver_version
projection_version
scope/sensitivity snapshot
```

FTS body comes from the C2 validated text projection (or direct safe text representation), never automatically from raw binary/HTML bytes or `SOURCE.payload/original` alone.

Rebuild:

```text
Canonical Root Sources
+ eligible SOURCE_VERSION objects
+ C3 deletion truth
-> C2 resolve
-> A5 deterministic projection
```

A rebuilt index must select the same representation under identical inputs/policy versions.

---

# 9. A7 retrieval revalidation

An index hit is only a candidate.

A7 must:

1. re-read Root Source;
2. ask C3 effective deletion;
3. re-resolve C2 representation;
4. compare indexed representation identity/hash where needed;
5. re-evaluate current sensitivity/scope/destination policy;
6. drop stale index candidate if resolver result changed.

A stale index can never force use of a deleted/older representation.

---

# 10. A8 Context / Source Trace

A8 revalidates the selected raw representation after A7 approval, then uses the matching READY C2 text projection for excerpting when projection is required. It does not treat a stale FTS snippet as body authority.

Trace must distinguish:

```yaml
source_trace:
  root_source_id:
  representation:
    object_type:
    object_id:
    sha256:
    fidelity:
  text_projection:
    projection_id: optional
    extractor_id: optional
    extractor_version: optional
    text_sha256: optional
  acquisition_receipt_ref: optional
  excerpt_range_or_method:
```

User-facing trace can link to the original capture while diagnostic trace proves which version supplied the content.

---

# 11. Deletion and reacquisition

### Root deleted

All versions become ineligible immediately through C3, even if version files remain pending purge.

### Version deleted

Resolver selects next eligible version or LOCATOR_ONLY. It never resurrects the deleted version.

### New explicit reacquisition

New immutable Source Version may become `CURRENT` representation without overwriting history.

Index invalidation/reprojection is dispatched through C4/A5.

---

# 12. Failure behavior

| Failure | Behavior |
|---|---|
| root missing/corrupt | no representation / health error |
| selected version corrupt | exclude; fall back only to another independently valid eligible representation |
| deletion truth unavailable | fail closed |
| sensitivity unknown | external deny; index policy follows configured safe rule |
| stale FTS version ref | candidate discarded/reprojected |
| body unavailable | locator/metadata-only, not fabricated body |
| version-parent mismatch | quarantine version |

---

# 13. Golden cases

1. **URL body recall** — captured URL + R1 version indexes page body and A8 traces both IDs.
2. **No acquisition** — URL remains locator-only; system does not hallucinate page content.
3. **Reacquisition** — newer valid version becomes current; older remains historical.
4. **Version delete** — deleted current version is not used; next eligible/locator fallback.
5. **Root delete** — all child content disappears from retrieval despite stale FTS rows.
6. **Sensitive upgrade** — child SENSITIVE makes effective representation SENSITIVE.
7. **Stale index** — A7 detects mismatch and drops old representation.
8. **R2 reconstructed rescue** — fidelity stays reconstructed in trace and is never labeled origin response.
9. **HTML projection** — scripts are not executed; visible text projection rebuilds deterministically.
10. **PDF unavailable extractor** — metadata-only status, no fabricated text.

---

# 14. Acceptance criteria

- [ ] acquired Web/X body can reach A5/A7/A8 without mutating Root Source.
- [ ] every indexed body has a representation identity/hash.
- [ ] stale/deleted representation cannot survive Canonical revalidation.
- [ ] effective sensitivity/scope never weakens root restrictions.
- [ ] Source Trace names both capture root and content representation.
- [ ] rebuild produces equivalent representation selection.
- [ ] HTML/PDF/raw binary never becomes index text without a registered safe projection path.
- [ ] A8 trace can identify extractor/version for projected text.

---

# 15. One-line contract

> **C2 makes captured identity and acquired content coexist: TSUZU remembers what the user saved, indexes the best eligible immutable representation, and can always prove exactly which bytes informed recall.**
