# Phase 37 - Expanded Lenses Round 1

Status: draft pending prompt-content gate.

Date drafted: 2026-05-29
Date approved: not approved.

Roadmap sources: `docs/PROJECT_OVERVIEW.md` section `4. Executor`,
`docs/PROJECT_OVERVIEW.md` highest-leverage item 4, `docs/phase_26_plus_roadmap.md`,
`docs/boards/README.md`, `PROGRESS.md`, and Phase 36 board/spec/commits through
`6277eae`.

## Goal

Implement the first expansion from four executable executor lenses to eight
executable lenses by adding:

- `definition`
- `citation`
- `temporal`
- `quantity_with_unit`

These four roles are lower-risk than obligation, condition, exception, and
relation extraction because they can remain tied to a single exact source span
without cross-candidate reasoning. Phase 37 should make the roles executable
only when their prompt bodies, LLM stages, planner selection, budget allocation,
runtime validation, audit payloads, and tests all agree.

The central outcome is increased recall for source-backed defined terms,
cross-references, dates/durations, and quantities-with-units while preserving
exact source spans, `value_verbatim`, optional canonical metadata, rejection
accounting, and all existing Phase 29-31 evaluation gates.

## Prompt-Content Gate

Phase 37 cannot be approved or opened for implementation until the operator
resolves this gate:

1. Provide human-authored prompt body text for the new executor prompts and any
   planner prompt changes, or explicitly authorize agent-authored prompt text
   for this phase.
2. Confirm that prompt changes should include `planner.select_strategy` and
   `planner.allocate_budget` updates so the planner can select and budget the
   new lenses in live runs.

Reason: `AGENTS.md` says prompt bodies must remain unfilled until a human fills
them. The code work is straightforward, but making these lenses useful requires
new or modified prompt bodies under `prompts/`.

## Non-Goals

- Do not implement `relation`, `obligation`, `condition`, or `exception`
  extraction in Phase 37.
- Do not change dedup keys, canonical-value dedup behavior, conflict
  preservation, cluster preservation, or cross-document reconciliation.
- Do not route normalization through an LLM.
- Do not add new provider integrations, embeddings, vector databases, REST API,
  web UI, Docker, CI/CD, fine-tuning hooks, or agent frameworks.
- Do not tune behavior for one fixture, document, proper noun, market sector,
  or evaluation answer.
- Do not weaken exact span matching, byte offsets, character offsets, source
  hashes, Pydantic contracts, audit logging, forced tool use, or no-silent-drop
  rejection accounting.

## Domain-Scope Alignment

The four Phase 37 lenses are domain-neutral primitives:

- `definition`: legal definitions, standards terminology, clinical endpoint
  definitions, insurance terms, procurement definitions, and regulatory terms.
- `citation`: contract section references, regulatory citations, standards
  clauses, statute references, table/figure references, and document
  cross-references.
- `temporal`: effective dates, deadlines, review periods, durations, reporting
  periods, trial windows, and policy periods.
- `quantity_with_unit`: monetary amounts, percentages with scope, measured
  quantities, dosage amounts, time intervals, rates, counts, capacity, and
  units.

Domain packs may later specialize field roles and default lens choices, but
Phase 37 must keep the extraction kernel domain-neutral.

## Current State

Phase 36 added `LensTaxonomyName` definitions for all planned roles but kept
only `entity`, `event`, `claim`, and `number` executable.

Current executable surfaces that must change together when a new lens becomes
runtime-supported:

- `src/extractor/contracts/base.py` defines `LensName` and `LLMStage`.
- `src/extractor/contracts/models.py` uses `LensName` in `LensBudget`,
  `ExtractionPlan.enabled_lenses`, and `LensCandidate.lens`.
- `src/extractor/contracts/lens_taxonomy.py` marks planned roles as
  `contract_only`.
- `src/extractor/planner/models.py` emits `StrategySelection.enabled_lenses`.
- `prompts/planner/select_strategy.md` currently says enabled lenses must
  contain only `entity`, `event`, `claim`, and `number`.
- `prompts/planner/allocate_budget.md` budgets one call per chunk per enabled
  lens.
- `src/extractor/llm/prompts.py` lists prompt stages in `PROMPT_STAGES`.
- `prompts/executor/` has prompt files for the current four executor stages.
- `src/extractor/executor/service.py` builds executor stage names from
  `executor.{lens}` and routes all calls through `src/extractor/llm/client.py`.
- `src/extractor/executor/models.py` keeps the LLM payload schema shared across
  lenses: `category`, `field_name`, `value`, `source_length`, `start_char`, and
  `confidence`.
- Server-side materialization reconstructs exact spans and Phase 36
  normalization metadata from the chunk and payload.

## Lens Semantics

### definition

Extract source spans that define a term, label, role, requirement, metric,
control, endpoint, or category. A valid definition candidate must include the
term or a source phrase that unambiguously carries the term role, plus the
definition text required by the approved field.

Do not extract background descriptions that are not definitional in the source.

### citation

Extract source spans that cite or reference another authority, section, table,
figure, exhibit, regulation, statute, standard control, policy clause, docket,
or document artifact.

Do not resolve the referenced target beyond the source text in Phase 37. Target
resolution and relation semantics remain later work.

### temporal

Extract source spans for dates, periods, deadlines, durations, effective times,
reporting windows, and time-based conditions when those spans directly support
an approved field.

Temporal canonicalization may use Phase 36 metadata only when deterministic.
Ambiguous dates or locale-sensitive forms must remain verbatim or be rejected
according to policy.

### quantity_with_unit

Extract source spans that include a quantity and its unit, denominator, scope,
or role when the approved field requires more than a bare number.

This lens complements `number`; it should not replace existing number behavior
for bare numeric fields. It is intended for values where the unit/scope is part
of the field meaning, such as `5 mg/kg`, `1.85 gigawatt-hours`, `30 days`,
`99.9% uptime`, or `$2 million per year`.

## Contract Changes

Expected additive changes after the prompt-content gate is resolved:

- Extend `LensName` with `definition`, `citation`, `temporal`, and
  `quantity_with_unit`.
- Extend `LLMStage` with `executor.definition`, `executor.citation`,
  `executor.temporal`, and `executor.quantity_with_unit`.
- Mark those four lens definitions executable in the Phase 36 taxonomy
  registry.
- Extend prompt loading stage lists and prompt-file tests for the new executor
  prompt files.
- Preserve the existing `ExtractedCandidatePayload` schema for all executor
  lenses unless provider strict-tool tests prove a split schema is necessary.
- Preserve `LensCandidate` and `DataPoint` normalization fields unchanged.
- Add no new required fields to existing audit payloads.

## Runtime Boundaries

Allowed:

- Add new executor stage prompt files after prompt-content gate resolution.
- Let planner strategy selection choose the new lenses when approved fields
  require them.
- Allocate budget entries for the new lenses using the existing one call per
  chunk per enabled lens runtime model.
- Run each new lens through the existing executor service, validation,
  source-resolution, materialization, rejection, and audit-store paths.
- Add deterministic candidate validation helpers only where a lens needs
  source-role checks that can be tested without fixture-specific tokens.

Forbidden:

- Do not make contract-only lenses executable unless prompt, stage, budget,
  runtime, audit, and tests all exist.
- Do not add lens-specific loose dictionaries at stage boundaries.
- Do not make canonical values claim source spans.
- Do not silently fall back when a new lens prompt or budget is missing.
- Do not change dedup or reconciler semantics to make Phase 37 fixtures pass.

## Audit and Provenance Effects

- Every new lens candidate must remain a normal `LensCandidate` with an exact
  `SourceSpan`.
- Audit storage should record new lens candidates using existing candidate JSON
  payload storage.
- Existing audit payloads from old runs must remain readable.
- Rejections from new lenses must use existing explicit rejection trails.
- Compact audit inspection should show the new lens names without special-case
  formatting.

## Configuration Changes

No new runtime tuning keys are planned for Phase 37.

If tests show that lens enablement needs configuration, it must be typed,
defaulted, and stored under `config/default.yaml`; it must not be hardcoded in
source or tests.

## Prompt Changes

Prompt changes are required but gated:

- New executor prompt files:
  - `prompts/executor/definition.md`
  - `prompts/executor/citation.md`
  - `prompts/executor/temporal.md`
  - `prompts/executor/quantity_with_unit.md`
- Planner prompt updates:
  - `prompts/planner/select_strategy.md`
  - `prompts/planner/allocate_budget.md`

Each prompt must keep the required sections: Intent, Typed Inputs, Output Tool
Schema, Failure Modes, and Prompt.

## Tests and Evaluation Gates

Narrow tests:

- Contract tests proving new lens names are executable only after the full
  runtime surface exists.
- Prompt loader tests proving all new executor prompt files load and document
  required sections.
- Planner model and prompt tests proving strategy selection can emit the new
  lenses and still rejects duplicates.
- Executor tests proving the new lenses run through existing structured LLM
  requests, source resolution, materialization, normalization metadata, and
  audit recording.
- Audit inspection tests proving new lens candidates remain readable.

Regression and final gates:

- Existing unit tests for contracts, planner, executor, audit store, audit
  inspection, orchestrator, reporter, and prompt schema quality.
- `git diff --exit-code -- prompts` is not expected to pass after prompt work;
  instead the board must list each prompt file changed and why.
- `make test`
- `make lint`
- `make smoke`
- `git diff --check`
- Phase 29 and Phase 30 evaluation suites.
- Phase 31 adversarial, mutation, and calibration suites.

Evaluation acceptance:

- No regression in Phase 29 or Phase 30 precision, recall, F1, provenance
  recall, false positives, false negatives, or invariant violations.
- Any new fixture added for Phase 37 must improve recall for one of the new
  roles without lowering exact provenance or increasing false positives.

## Implementation Order

1. Resolve the prompt-content gate before board opening.
2. Add RED tests for the new executable lens contract boundary, prompt loader
   stage list, planner lens selection, executor call routing, and audit
   readback.
3. Extend `LensName`, `LLMStage`, `PROMPT_STAGES`, and the Phase 36 lens
   registry in one contract-focused change.
4. Add approved prompt changes for planner selection/budgeting and the four new
   executor lenses.
5. Run new lenses through existing executor materialization and audit paths.
6. Add focused fixture/evaluation coverage only if it is source-role-neutral
   and not tailored to one document string.
7. Run final project, smoke, lint, prompt-change review, and evaluation gates.
8. Fill the Phase 37 board summary and stop for operator acceptance.

## Open Questions Before Approval

1. Should the operator provide human-authored prompt bodies for the four new
   executor prompts and planner prompt changes, or explicitly authorize
   agent-authored prompt text for Phase 37?
