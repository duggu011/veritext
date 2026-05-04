# Veritext Board Index

This is where agents look first every session. Find the active phase, then read the board or create it through `WORKFLOW.md` if it does not exist yet.

---

## Active Phase

**Phase 26 - Domain Packs, Schema Registry, and Schema-Fit Refusal** | Status: NOT STARTED | Spec: _(not opened)_ | Board: _(not opened)_ | Roadmap source: [`docs/PROJECT_OVERVIEW.md`](../PROJECT_OVERVIEW.md)

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
| 26 - Domain Packs, Schema Registry, and Schema-Fit Refusal | _(not opened)_ | _(not opened)_ | ACTIVE NEXT |
| 27 - Diverse Evaluation Fixture Suite | _(not opened)_ | _(not opened)_ | PLANNED |
| 28 - Boundary-Preserving PDF, DOCX, and Email Ingestion | _(not opened)_ | _(not opened)_ | PLANNED |
| 29 - Expanded Lenses and Normalization Policy | _(not opened)_ | _(not opened)_ | PLANNED |
| 30 - Provenance Viewer, Run Diffs, and Signed Reports | _(not opened)_ | _(not opened)_ | PLANNED; requires explicit architecture-rule review before any UI work |
| 31 - Cost Observability and Stage Model Comparison | _(not opened)_ | _(not opened)_ | PLANNED |
| 32+ - Deployment-Economics Track | _(not opened)_ | _(not opened)_ | PLANNED |

---

## Roadmap Source

Future phases are derived from `docs/PROJECT_OVERVIEW.md`:

- Phase 26 maps to highest-leverage item 1 and the Planner roadmap.
- Phase 27 maps to highest-leverage item 2 and the Evaluation roadmap.
- Phase 28 maps to highest-leverage item 3 and the Ingestion roadmap.
- Phase 29 maps to highest-leverage item 4 plus Executor, Dedup, and Reconciler roadmap items.
- Phase 30 maps to highest-leverage item 5 plus Reporter and Audit roadmap items.
- Phase 31 maps to the Cost Observability prerequisite and the per-stage model-comparison caution.
- Phase 32+ maps to the deployment-economics playbook after cost observability exists.

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
