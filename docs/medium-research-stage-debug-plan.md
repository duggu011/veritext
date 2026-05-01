# Medium Research Stage Debug Plan

Source: `evals/fixtures/medium_research_brief/source.md`

Purpose: give the operator a source-derived checklist for validating each stage
without waiting until the full pipeline has finished. This is not a canonical
schema registry and should not be wired into production extraction. It is a
diagnostic target for the medium research fixture.

## Core Problem

The current full-chain run hides planner mistakes until the final eval. Recent
runs completed with zero invariant violations but weak scoring because the
planner generated semantically plausible names that drifted from stable labels:

- `Guidance` instead of `ForwardGuidance`
- `RegulatoryRateChange` instead of `RegulatoryRisk`
- `change_percentage` instead of `change_pct`
- `announcement_date` instead of `event_date`
- `forecast_value` under guidance instead of `guidance_value`

A step-by-step workflow should let us stop after each stage and ask: is this
stage producing the artifact we actually want before the next stage compounds
the mistake?

## Desired Manual Workflow

Long term, add a debug runner that can execute one stage at a time and persist a
reviewable artifact after each step:

```text
veritext-debug prepare <source> --run-id <id>
veritext-debug planner.classify --run-id <id>
veritext-debug planner.propose --run-id <id>
veritext-debug planner.critique --run-id <id>
veritext-debug planner.strategy --run-id <id>
veritext-debug planner.budget --run-id <id>
veritext-debug executor --run-id <id> --lens claim
veritext-debug executor --run-id <id> --lens number
veritext-debug executor --run-id <id> --lens event
veritext-debug executor --run-id <id> --lens entity
veritext-debug dedup --run-id <id>
veritext-debug critic --run-id <id>
veritext-debug verifier --run-id <id>
veritext-debug reconciler --run-id <id>
veritext-debug report --run-id <id>
```

Each command should:

- read only audited outputs from prior stages;
- write its own audited stage state;
- emit a JSON artifact suitable for review;
- fail cleanly if prior-stage output is missing or partial;
- allow the operator to edit prompts/config before continuing;
- never silently reuse stale artifacts from a different source hash.

Until that exists, use the existing audit CLI and SQLite queries to inspect
completed or failed runs:

```bash
PYTHONPATH=src python3 -m extractor.audit .veritext/audit.sqlite3 \
  --run-id medium-research-schema-quality-1 \
  --details
```

## Stage 1: Ingestion And Chunking

Expected source identity:

- title: `Helios Renewables - Q1 2026 Snapshot`
- format: markdown
- source byte length: `1775`
- document should fit in one chunk under the current default chunking policy
- distractor section must remain present so later stages can reject it

Expected sections:

- Headlines
- Operations
- Acquisition
- Guidance
- Risk
- Personnel
- Distractors - Do Not Extract

## Stage 2: Planner Classification

Expected classification should be close to:

```json
{
  "document_type": "corporate research snapshot",
  "domain_hints": [
    "finance",
    "earnings",
    "renewable_energy",
    "operations",
    "corporate_events",
    "guidance",
    "regulatory_risk",
    "personnel"
  ],
  "confidence": 0.9
}
```

Classification must not treat these as extractable subjects:

- Lila Okafor as a personnel change
- CleanTech Daily headline
- Northwind/Sunbelt draft term sheet

## Stage 3: Planner Schema

The planner should preserve stable reusable category and field names where they
fit naturally, while still keeping semantic roles. For this fixture, a good
approved schema should be structurally close to:

```text
FinancialMetric:
  metric_name, period, value, change_pct, prior_period_value,
  margin, forecast_value, notable_qualifier

OperationalMetric:
  metric_name, value, change_pct, prior_period_value,
  target_value, facility

CorporateEvent:
  event_type, summary, event_date, expected_close_date,
  parties, transaction_value, conditions, asset_detail

ForwardGuidance:
  speaker, guidance_date, metric_name, guidance_value,
  target_date, condition

RegulatoryRisk:
  summary, issuing_authority, prior_rate, new_rate,
  effective_date, exposure_pct

PersonnelChange:
  person, role, change_type, effective_date
```

Planner reject conditions:

- Reject `Guidance` when the facts are forward-looking commitments or revenue
  guidance; use `ForwardGuidance`.
- Reject `RegulatoryRateChange` when the source section frames the fact as risk
  and exposure; use `RegulatoryRisk`.
- Reject `change_percentage` when compact stable `change_pct` fits.
- Reject `announcement_date` when the field means the event date.
- Reject `guidance_period` if the source role is better captured by
  `target_date` or `guidance_date`.
- Reject `forecast_value` under forward guidance when the role is the guided
  value; use `guidance_value`.

## Stage 4: Planner Strategy And Budget

Expected lenses:

```text
entity, event, claim, number
```

Reason:

- `number`: amounts, percentages, rates, dates, quantities
- `entity`: people, organizations, facilities, authorities, counterparties
- `event`: acquisition approval, facility commencement, appointments, retirement
- `claim`: full source-backed statements, conditions, risk/exposure summaries

For a one-chunk source, budgets should allow one call per enabled lens plus
normal retry allowance from `execution.max_llm_attempts`.

## Stage 5: Executor Targets

Executor output should over-generate enough source-backed candidates for later
review, but only against approved schema names. The following final datapoints
are the source-derived target set.

### FinancialMetric

| Field | Value | Source Span |
| --- | --- | --- |
| `period` | `Q1 2026` | `Q1 2026 revenue $482.3 million, up 17.4% versus $410.8 million in Q1 2025.` |
| `metric_name` | `Revenue` | `Q1 2026 revenue $482.3 million, up 17.4% versus $410.8 million in Q1 2025.` |
| `value` | `$482.3 million` | `$482.3 million` |
| `change_pct` | `up 17.4%` | `up 17.4%` |
| `prior_period_value` | `$410.8 million in Q1 2025` | `$410.8 million in Q1 2025` |
| `metric_name` | `Adjusted EBITDA` | `Adjusted EBITDA $94.1 million at 19.5% margin, beating the $88.0 million forecast.` |
| `value` | `$94.1 million` | `$94.1 million` |
| `margin` | `19.5%` | `19.5% margin` |
| `forecast_value` | `$88.0 million` | `$88.0 million forecast` |
| `metric_name` | `Free cash flow` | `Free cash flow positive at $12.6 million for the first time in eight quarters.` |
| `value` | `$12.6 million` | `$12.6 million` |
| `notable_qualifier` | `for the first time in eight quarters` | `for the first time in eight quarters` |

### OperationalMetric

| Field | Value | Source Span |
| --- | --- | --- |
| `metric_name` | `Fleet generation` | `Fleet generation 7,318 gigawatt-hours, up 11.2% from 6,581 in Q1 2025.` |
| `value` | `7,318 gigawatt-hours` | `7,318 gigawatt-hours` |
| `change_pct` | `up 11.2%` | `up 11.2%` |
| `prior_period_value` | `6,581 in Q1 2025` | `6,581 in Q1 2025` |
| `metric_name` | `Solar capacity factor` | `Solar capacity factor 28.4% versus 29.0% target.` |
| `value` | `28.4%` | `Solar capacity factor 28.4% versus 29.0% target.` |
| `target_value` | `29.0% target` | `29.0% target` |
| `facility` | `Atacama-1` | `Atacama-1` |
| `value` | `312 gigawatt-hours` | `312 gigawatt-hours` |

### CorporateEvent

| Field | Value | Source Span |
| --- | --- | --- |
| `event_type` | `Facility commencement` | `Atacama-1 in Chile commenced operation January 22, 2026, contributing 312 gigawatt-hours.` |
| `summary` | `Atacama-1 in Chile commenced operation January 22, 2026, contributing 312 gigawatt-hours.` | `Atacama-1 in Chile commenced operation January 22, 2026, contributing 312 gigawatt-hours.` |
| `asset_detail` | `Atacama-1 in Chile, contributing 312 gigawatt-hours` | `Atacama-1 in Chile commenced operation January 22, 2026, contributing 312 gigawatt-hours.` |
| `event_type` | `Acquisition approval` | `On March 28, 2026, the board approved acquiring Northwind Storage, a Reno, Nevada battery operator, for $1.24 billion.` |
| `event_date` | `March 28, 2026` | `March 28, 2026` |
| `summary` | `Board approved acquiring Northwind Storage, a Reno, Nevada battery operator, for $1.24 billion` | `the board approved acquiring Northwind Storage, a Reno, Nevada battery operator, for $1.24 billion.` |
| `parties` | `Northwind Storage` | `Northwind Storage` |
| `transaction_value` | `$1.24 billion` | `$1.24 billion` |
| `expected_close_date` | `September 30, 2026` | `September 30, 2026` |
| `conditions` | `subject to FERC and CFIUS review` | `subject to FERC and CFIUS review` |
| `asset_detail` | `1.85 gigawatt-hours across seven U.S. states` | `1.85 gigawatt-hours across seven U.S. states` |

### ForwardGuidance

| Field | Value | Source Span |
| --- | --- | --- |
| `guidance_date` | `April 9, 2026` | `April 9, 2026 earnings call` |
| `speaker` | `Marcus Bell` | `CEO Marcus Bell` |
| `guidance_value` | `at least 4.2 gigawatts` | `at least 4.2 gigawatts of new solar capacity` |
| `target_date` | `December 31, 2027` | `December 31, 2027` |
| `condition` | `at least 60% under long-term offtake at signing` | `at least 60% under long-term offtake at signing` |
| `metric_name` | `Full-year 2026 revenue` | `Full-year 2026 revenue` |
| `guidance_value` | `$2.10 to $2.25 billion` | `$2.10 to $2.25 billion` |

### RegulatoryRisk

| Field | Value | Source Span |
| --- | --- | --- |
| `summary` | `U.S. Department of Commerce raised module countervailing duties from 15.0% to 26.5% on March 6, 2026` | `U.S. Department of Commerce raised module countervailing duties from 15.0% to 26.5% on March 6, 2026` |
| `issuing_authority` | `U.S. Department of Commerce` | `U.S. Department of Commerce` |
| `prior_rate` | `15.0%` | `from 15.0%` |
| `new_rate` | `26.5%` | `to 26.5%` |
| `effective_date` | `March 6, 2026` | `March 6, 2026` |
| `exposure_pct` | `approximately 18%` | `Approximately 18% of the 2026 module pipeline is exposed.` |

### PersonnelChange

| Field | Value | Source Span |
| --- | --- | --- |
| `change_type` | `appointment` | `Dr. Anya Kowalski appointed Chief Sustainability Officer on February 2, 2026.` |
| `person` | `Dr. Anya Kowalski` | `Dr. Anya Kowalski appointed Chief Sustainability Officer on February 2, 2026.` |
| `role` | `Chief Sustainability Officer` | `appointed Chief Sustainability Officer` |
| `effective_date` | `February 2, 2026` | `February 2, 2026` |
| `change_type` | `retirement` | `announced retirement effective at the June 18, 2026 Annual Meeting.` |
| `person` | `Hiroshi Tanaka` | `Hiroshi Tanaka` |
| `role` | `Director` | `Director Hiroshi Tanaka` |
| `effective_date` | `June 18, 2026 Annual Meeting` | `June 18, 2026 Annual Meeting` |

## Stage 6: Critic Checks

The critic should reject:

- any candidate about `Lila Okafor` as a personnel change;
- `CleanTech Daily` or `10 GW deployment by 2027`;
- `Northwind/Sunbelt draft term sheet`;
- bare values that lose the field role, such as `19.5%` for margin when the
  selected span should include `margin`;
- `15.0%` and `26.5%` when their spans omit `from` or `to` for prior/new roles;
- any category/field not approved by planner schema.

The critic may correct:

- source span boundaries;
- field names that are approved and clearly source-backed;
- values that are concise but still supported by the selected source span.

The critic must not correct by inventing a category or field outside the
approved planner schema.

## Stage 7: Verifier Checks

Verifier should be mechanical and strict:

- source span slice must match audited chunk text;
- category and field must be in the approved schema;
- selected span must support both value and field meaning;
- reject accepted critic reports that still have wrong label alignment;
- do not infer from neighboring sentences if the selected span is insufficient.

High-risk provenance spans for this fixture:

- `$88.0 million forecast`
- `19.5% margin`
- `from 15.0%`
- `to 26.5%`
- `CEO Marcus Bell`
- `appointed Chief Sustainability Officer`
- full event sentences for `event_type` and `change_type`

## Stage 8: Reconciler Checks

The reconciler should merge duplicate candidates into exactly one final data
point per distinct category/field/value/source role. It should not merge:

- current facts with distractor facts;
- prior values with current values;
- prior rates with new rates;
- target values with actual values;
- guidance values with conditions;
- personnel roles with people.

For this fixture, a high-quality final report should be close to 53 data points
with zero invariant violations.

## Suggested Debug Artifacts

When implementing one-stage-at-a-time debugging, write these files under a run
directory such as `.veritext/debug/<run_id>/`:

```text
00_document.json
01_chunks.json
02_classification.json
03_schema_proposal.json
04_schema_critique.json
05_plan.json
06_executor_entity.json
07_executor_event.json
08_executor_claim.json
09_executor_number.json
10_dedup.json
11_critic.json
12_verifier.json
13_reconciler.json
14_report.json
15_eval.json
```

Each artifact should include:

- input pointers: source hash, run id, prior stage artifact hash;
- output payload exactly as validated by Pydantic;
- rejected items and reasons;
- LLM call id and prompt hash when applicable;
- a short operator checklist for pass/fail review.
