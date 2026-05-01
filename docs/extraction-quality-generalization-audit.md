# Extraction quality generalization audit

Run audited: `medium-research-debug-20260502-003044`

This report treats the medium research fixture as a diagnostic specimen, not as
the product target. The goal is to convert the observed failures into
document-agnostic pipeline behavior and tests.

## Baseline result

- Expected data points: 53
- Actual data points: 57
- True positives: 35
- False negatives: 18
- False positives: 22
- Precision: 0.614
- Recall: 0.660
- F1: 0.636
- Provenance recall: 0.660
- Exact-provenance matches: 35
- Provenance mismatches among true positives: 0
- Invariant violations: 0

The span-width annotation problem is no longer the blocking issue. Remaining
work is extraction scope, schema role naming, candidate value normalization,
statement coverage, and correction discipline.

## Important distinction

An eval false positive is not automatically a bad product extraction. Some
unexpected data points are source-backed facts that the fixture did not choose
to expect. The current default product policy is comprehensive source-backed
extraction; see `docs/output-scope-policy.md`.

For future product modes, the system may support:

- comprehensive extraction: emit all material source-backed facts approved by
  the planner;
- task-scoped extraction: emit only facts that match an operator-provided or
  benchmark schema;
- hybrid extraction: emit all facts, but label which facts are core,
  supporting, or contextual.

Without holding that distinction, prompt edits can improve this fixture while
making the general application worse.

## Failure classes

### 1. Planner semantic-role mismatch

Evidence:

- Expected fields not approved by the plan:
  - `FinancialMetric.notable_qualifier`
  - `ForwardGuidance.condition`
  - `ForwardGuidance.speaker`
  - `ForwardGuidance.target_date`
- Plan fields not expected by the fixture:
  - `FinancialMetric.summary`
  - `ForwardGuidance.change_type`
  - `ForwardGuidance.conditions`
  - `ForwardGuidance.period`
  - `ForwardGuidance.person`
  - `ForwardGuidance.role`
  - `OperationalMetric.event_date`
  - `OperationalMetric.period`
  - `PersonnelChange.parties`
  - `RegulatoryRisk.period`

General diagnosis:

The planner often sees the right facts but names their roles generically or
structurally rather than relationally. For example, a person in a guidance
sentence is not just `person`; in that relation the person is the `speaker`.
A future deadline in guidance is not just a `period`; it is a target date when
the sentence says the target must be reached by that date.

Likely owner:

- Planner prompt and planner prompt regression tests.

General fix shape:

- Prefer field names that encode the source relation when that relation is
  explicit: `speaker`, `target_date`, `condition`, `notable_qualifier`.
- Avoid replacing semantic roles with generic fields such as `person`, `role`,
  `period`, or `summary` when the source relation is more specific.
- Keep this as a general naming principle, not a fixture field whitelist.

### 2. Executor role-qualifier contamination

Evidence:

- `forecast_value` emitted `$88.0 million forecast` instead of `$88.0 million`.
- `target_value` emitted `29.0% target` instead of `29.0%`.
- `facility` emitted `Atacama-1 in Chile` instead of the bare facility name.
- `metric_name` emitted `Q1 2026 revenue` instead of `revenue`.

General diagnosis:

The executor includes role words, period words, or location qualifiers in
atomic values even when the field name already carries that role. This creates
valid-looking source spans but unstable values.

Likely owner:

- Executor prompts first.
- Executor/value-validation logic if prompt-only fixes are not reliable.

General fix shape:

- For atomic fields, emit the bare value unless the field name requires the
  qualifier.
- Field names such as `forecast_value`, `target_value`, `facility`,
  `metric_name`, `prior_rate`, and `new_rate` should guide value trimming.
- Add synthetic unit tests with neutral source snippets, not fixture names.

### 3. Label normalization gaps

Evidence:

- Source phrase `commenced operation` did not produce
  `CorporateEvent.event_type = Facility commencement`.
- Source phrase `approved acquiring` did not produce
  `CorporateEvent.event_type = Acquisition approval`.
- Source word `appointed` produced `PersonnelChange.change_type = appointed`
  instead of the normalized label `appointment`.

General diagnosis:

Label fields are controlled semantic labels. The source may use verbs while the
field value should be a noun-form event or change label. The executor currently
leans toward verbatim source text for these labels.

Likely owner:

- Executor prompts.
- Possibly typed label-normalization helpers later, if the product defines
  stable controlled vocabularies.

General fix shape:

- Allow label/category fields to use noun-form normalization when every content
  word traces to the selected source phrase.
- Preserve source provenance over the source phrase, not the normalized label.
- Do not invent labels whose content words are not traceable to the source.

### 4. Statement and clause coverage gaps

Evidence:

- Missing full-sentence `CorporateEvent.summary` candidates.
- Missing full-sentence or clause-level `CorporateEvent.asset_detail`
  candidates.
- Missing full regulatory action `RegulatoryRisk.summary`.
- Near misses truncated leading dates, trailing values, or sentence punctuation.

General diagnosis:

For statement-like fields, the executor tends to emit the event core rather
than the whole sentence or full clause. That is useful for atomic fields but
wrong for `summary`, `statement`, `description`, `condition`, and similar
free-text fields.

Likely owner:

- Executor prompts.
- Potentially field-type metadata if prompt-only behavior stays inconsistent.

General fix shape:

- Treat statement fields as sentence/clause fields.
- For a statement field, value and span should preserve the full source
  sentence or standalone clause.
- For atomic fields in the same sentence, keep the tight atomic span.

### 5. Critic correction can drop source qualifiers

Evidence:

- Executor candidate value: `Approximately 18%`
- Candidate span text: `Approximately 18%`
- Critic accepted a corrected candidate with value `18%` and the same span.
- The final data point therefore failed eval matching even though provenance
  stayed exact.

General diagnosis:

This is not a reconciler mutation. The reconciler derives final data points
from accepted candidates. The value changed because the critic correction path
accepted a value that dropped the qualifier while retaining the original span.

Likely owner:

- Critic correction validation logic.
- Critic prompt secondarily.

General fix shape:

- A critic correction must not remove source qualifiers such as
  `approximately`, `at least`, `up`, `down`, `no more than`, or `subject to`
  when those words are part of the source span and field meaning.
- If normalized numeric values are desired, they should live in a separate
  normalized field, not replace the audited source-backed value.
- Add deterministic correction-validation tests before another live run.

### 6. Executor offset repair caught but did not recover one item

Evidence:

- `FinancialMetric.period = Q1 2026` had one matching candidate, but it was
  executor-rejected because the reported span text resolved to `eadline`.

General diagnosis:

The invariant enforcement worked: the bad offset did not leak into final
output. The recall gap remains because there was no alternate valid candidate
for that expected field.

Likely owner:

- Executor retry/correction behavior or executor prompt offset discipline.

General fix shape:

- Keep rejecting bad offsets.
- Improve retry feedback or candidate generation so a bad offset on a simple
  repeated value can be corrected to a unique valid span.

## False-positive buckets

The 22 unexpected data points split into reusable buckets:

- Source-backed but outside fixture scope:
  - acquirer/organization parties, guidance person and role, operational event
    date, regulatory period, personnel organization.
- Wrong granularity:
  - summary values that omit leading dates, prices, or punctuation;
  - asset detail values that include the operator verb or omit the desired
    clause width.
- Role-qualifier contamination:
  - `$88.0 million forecast`, `29.0% target`, `Atacama-1 in Chile`,
    `Q1 2026 revenue`.
- Label normalization mismatch:
  - `acquisition` instead of a source-backed event label for approval;
  - `appointed` instead of noun-form `appointment`.
- Critic correction drift:
  - `Approximately 18%` corrected to `18%`.

The first bucket requires a product/eval scope decision. The other buckets are
general extraction-quality defects.

## Recommended next implementation phases

### Phase A: policy and deterministic guardrails

No live LLM calls.

1. Decide whether default output is comprehensive, task-scoped, or hybrid.
2. Add tests proving critic corrections cannot drop meaningful source
   qualifiers.
3. Add tests proving reconciler uses accepted corrected candidates exactly and
   does not independently rewrite values.
4. Add tests for role-qualifier trimming in generic snippets.

### Phase B: planner role naming discipline

No live LLM calls until prompt tests pass.

1. Add prompt regression tests for relation-specific field naming:
   `speaker`, `target_date`, `condition`, `notable_qualifier`.
2. Patch planner prompts to prefer semantic role names over generic
   `person`, `role`, `period`, and catch-all `summary` when the source
   relation is explicit.

### Phase C: executor value and statement discipline

No live LLM calls until prompt tests pass.

1. Add executor prompt tests for noun-form labels from source verbs.
2. Add executor prompt tests for atomic value trimming.
3. Add executor prompt tests for statement fields requiring full
   sentence/clause spans.
4. Patch executor prompts only in those general terms.

### Phase D: local test sweep, then one paid live run

1. Run focused unit tests.
2. Run `make lint`.
3. Run `make smoke` if feasible.
4. Only then run one new live extraction to measure actual behavior.

## Non-goals

- Do not hardcode this fixture's company, asset, person, or regulator names.
- Do not add a fixture-specific schema registry.
- Do not relax provenance matching.
- Do not suppress all extra source-backed facts until the output scope policy
  is explicit.
