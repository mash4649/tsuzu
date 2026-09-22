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
