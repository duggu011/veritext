# Veritext Board Index

This is where agents look first every session. Find the active phase, then read the board or create it through `WORKFLOW.md` if it does not exist yet.

---

## Active Phase

**Phase 31 - Adversarial, Mutation, and Calibration Evaluation** | Status: SPEC DRAFT | Spec: [draft](../specs/phase_31_adversarial_mutation_calibration_evaluation.md) | Board: _(not opened)_ | Roadmap source: [`docs/PROJECT_OVERVIEW.md`](../PROJECT_OVERVIEW.md), [`docs/phase_26_plus_roadmap.md`](../phase_26_plus_roadmap.md)

Exactly one phase is active. Completed phases live in the Phase Index below.

---

## Phase Index

| Phase | Spec | Board | Status |
|---|---|---|---|
| 0-18 - Core Extraction Kernel | historical | historical | COMPLETE (see `PROGRESS.md`) |
| 19 - Anthropic Prompt Caching | historical | historical | COMPLETE (see `PROGRESS.md`) |
| 20 - Compact LLM-Boundary View Models | historical | historical | COMPLETE (see `PROGRESS.md`) |
| 21 - Compact Critic / Verifier Output Schema | historical | historical | COMPLETE (see `PROGRESS.md`) |
| 22 - Pre-Critic Candidate Deduplication | historical | historical | COMPLETE (see `PROGRESS.md`) |
| 23 - Reconciler Input Slim | historical | historical | COMPLETE (see `PROGRESS.md`) |
| 24 - Batch-Size Tuning and Observability | historical | historical | COMPLETE (see `PROGRESS.md`) |
| 25 - Workflow and Roadmap Tracking | [design](../superpowers/specs/2026-05-04-board-first-workflow-design.md) | [board](phase_25_workflow_and_roadmap_tracking.md) | COMPLETE (2026-05-04) |
| 26 - Domain Pack and Schema Registry Foundation | [approved](../specs/phase_26_domain_pack_and_schema_registry_foundation.md) | [board](phase_26_domain_pack_and_schema_registry_foundation.md) | COMPLETE (2026-05-05) |
| 27 - Planner Schema Reuse and Schema-Fit Refusal | [approved](../specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md) | [board](phase_27_planner_schema_reuse_and_schema_fit_refusal.md) | COMPLETE (2026-05-09) |
| 28 - Legal Contracts Domain Pack v1 | [approved](../specs/phase_28_legal_contracts_domain_pack_v1.md) | [board](phase_28_legal_contracts_domain_pack_v1.md) | COMPLETE (2026-05-10) |
| 29 - Evaluation Harness: Per-Field Gates | [approved](../specs/phase_29_evaluation_harness_per_field_gates.md) | [board](phase_29_evaluation_harness_per_field_gates.md) | COMPLETE (2026-05-10) |
| 30 - Diverse Fixture Corpus Round 1 | [approved](../specs/phase_30_diverse_fixture_corpus_round_1.md) | [board](phase_30_diverse_fixture_corpus_round_1.md) | COMPLETE (2026-05-10) |
| 31 - Adversarial, Mutation, and Calibration Evaluation | [draft](../specs/phase_31_adversarial_mutation_calibration_evaluation.md) | _(not opened)_ | ACTIVE - SPEC DRAFT |
| 32 - Boundary-Preserving Ingestion Model | _(not opened)_ | _(not opened)_ | PLANNED |
| 33 - PDF and Table Ingestion | _(not opened)_ | _(not opened)_ | PLANNED |
| 34 - DOCX, HTML, and Email Ingestion | _(not opened)_ | _(not opened)_ | PLANNED |
| 35 - Layout-Aware Chunking | _(not opened)_ | _(not opened)_ | PLANNED |
| 36 - Lens Taxonomy and Normalization Contracts | _(not opened)_ | _(not opened)_ | PLANNED |
| 37 - Expanded Lenses Round 1 | _(not opened)_ | _(not opened)_ | PLANNED |
| 38 - Dedup, Canonical Values, and Conflict Preservation | _(not opened)_ | _(not opened)_ | PLANNED |
| 39 - Cross-Document Reconciliation | _(not opened)_ | _(not opened)_ | PLANNED |
| 40 - Signed Reports and Run Diffs | _(not opened)_ | _(not opened)_ | PLANNED |
| 41 - Architecture Rule Amendment for Viewer, Governance, and CI | _(not opened)_ | _(not opened)_ | PLANNED; required before any UI or CI work |
| 42 - HTML Provenance Viewer, If Approved | _(not opened)_ | _(not opened)_ | PLANNED; gated by Phase 41 |
| 43 - Cost Observability and Cost-per-Correct-Fact | _(not opened)_ | _(not opened)_ | PLANNED |
| 44 - Stage Model Comparison | _(not opened)_ | _(not opened)_ | PLANNED |
| 45 - Deployment-Economics Cost Cuts | _(not opened)_ | _(not opened)_ | PLANNED |

---

## Roadmap Source

Future phases are derived from `docs/PROJECT_OVERVIEW.md` and split in
`docs/phase_26_plus_roadmap.md`:

- Phases 26-28 map to highest-leverage item 1, the Planner roadmap, and the first-domain-pack proving ground.
- Phases 29-31 map to highest-leverage item 2 and the Evaluation roadmap.
- Phases 32-35 map to highest-leverage item 3 plus the Ingestion and Chunker roadmaps.
- Phases 36-39 map to highest-leverage item 4 plus the Executor, Dedup, and Reconciler roadmaps.
- Phases 40-42 map to highest-leverage item 5 plus Reporter, Audit, and governance roadmap items.
- Phases 43-45 map to the Cost Observability prerequisite, stage model-comparison caution, and deployment-economics playbook.

---

## Board Template

When starting implementation of a phase, create `docs/boards/phase_NN_<slug>.md` using this format.

```markdown
# Phase NN - <Name>

## Current Status

Step: 0 of N
Branch: <branch or main>
Started: YYYY-MM-DD
Last session: YYYY-MM-DD
Spec: `docs/specs/phase_NN_<slug>.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:<section>`

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [ ] Step 1: <description>
- [ ] Step 2: <description>
- [ ] Step 3: <description>

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | ... | ... |

---

## Gate Interpretations

Pin any gate whose measurement, time range, fixture set, or aggregation was ambiguous in the spec.

_(None yet.)_

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `path/to/file.py:line` | What changed | Step K |

---

## Issues

Log every issue when found.

_(No issues yet.)_

<!--
### ISS-001 - <short title>
**Status:** OPEN | **Severity:** high/medium/low | **Found:** Step K, YYYY-MM-DD
**Files:** `path/to/file.py:line`
**What is wrong:** <expected vs actual>
**How to reproduce:** <command or scenario>
**Root cause:** _(filled when diagnosed)_
**Resolution:** _(filled when fixed or deferred)_
**Resolved:** _(date + step, or "deferred to Phase NN")_
-->

---

## Tests

### Per-Step Results

| Step | Tests | Result | Date |
|---|---|---|---|
| 1 | <command> | PASS/FAIL | YYYY-MM-DD |

### Final Gate

- [ ] Narrow relevant tests pass
- [ ] `make test` passes when feasible
- [ ] `make lint` passes
- [ ] `make smoke` passes when feasible
- [ ] `git diff --check` passes
- [ ] Evaluation gates pass, if this phase changes extraction behavior
- [ ] All OPEN issues are resolved or explicitly deferred
- [ ] Phase Summary filled in
- [ ] `PROGRESS.md` updated

---

## Work Log

Reverse chronological. Log every session.

### YYYY-MM-DD - Session N

- Resumed at step K.
- Completed: <what changed>.
- Issues found: <ISS-NNN or none>.
- Tests: <commands and results>.
- Next: step K+1 - <description>.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: ...
- Deferred: ...
- Added beyond spec: ...

### Lessons for downstream phases

- ...
```
