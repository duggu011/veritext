# Phase 31 - Adversarial, Mutation, and Calibration Evaluation

## Current Status

Step: 0 of 6
Branch: main
Started: 2026-05-10
Last session: 2026-05-10
Spec: `docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:13. Evaluation`; `docs/PROJECT_OVERVIEW.md:Target domains (ranked by fit)`; `docs/phase_26_plus_roadmap.md`

Phase 31 approved for implementation after operator continuation with `continue`. Board open. Next: Step 1 - add adversarial manifest contracts, loader validation, and suite skeleton.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [ ] Step 1: Add adversarial manifest contracts, loader validation, and suite skeleton.
- [ ] Step 2: Add adversarial fixture variants and strict suite gates.
- [ ] Step 3: Add mutation manifest contracts, source-sensitivity scoring, and suite skeleton.
- [ ] Step 4: Add mutation fixtures and strict source-sensitivity gates.
- [ ] Step 5: Add calibration report generation and CLI JSON output.
- [ ] Step 6: Add prompt-neutrality verification and final project verification.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Require at least four adversarial variants and four mutation fixtures across at least four Phase 30 target domains. | The phase exists to measure robustness across the diverse corpus; fewer domains would weaken the source-sensitivity goal. |
| Q2 | Keep live LLM robustness baselines optional operator-run evidence outside required tests. | Required gates must remain deterministic, portable, and independent of API keys, model availability, or local `.veritext` state. |
| Q3 | Keep calibration output as deterministic JSON reliability tables without plotting dependencies. | The current architecture does not need a plotting stack, viewer, or generated image artifact to enforce calibration contracts. |
| Q4 | Add evaluation-only robustness contracts rather than changing runtime report, data point, planner, or audit contracts. | Phase 31 is measurement work and must not change runtime extraction behavior or weaken provenance invariants. |

---

## Gate Interpretations

- Phase 31 robustness manifests are separate evaluation-only Pydantic contracts in `src/extractor/evals/robustness.py`; do not extend or change existing `EvaluationSuiteManifest` semantics for Phase 29 and Phase 30.
- The adversarial manifest path is `evals/suites/phase_31_adversarial.json`.
- The mutation manifest path is `evals/suites/phase_31_mutation.json`.
- Public CLI modes for Phase 31 are `--adversarial-suite`, `--mutation-suite`, and `--calibration-suite`.
- Step 1 covers adversarial manifest contracts, loader validation, and the adversarial suite skeleton only; adversarial fixture variants and strict suite gates belong to Step 2.
- Phase 31 must not change runtime extraction stages, prompt bodies, runtime config, domain-pack runtime behavior, or architecture rules.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md:1` | Approved Phase 31 spec. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md:1` | Active Phase 31 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |

---

## Issues

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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|O[p]en Questions|\\?\\?" docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md docs/boards/README.md docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md`; `rg -n "Phase 31|phase_31_adversarial_mutation_calibration_evaluation.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md`; `cmp -s AGENTS.md CLAUDE.md` | PASS | 2026-05-10 |

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

### 2026-05-10 - Session 1

- Resumed after operator approved Phase 31 with `continue`.
- Completed: approved the Phase 31 spec for implementation, opened this board, pinned Phase 31 open-question resolutions, and updated active phase tracking.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|O[p]en Questions|\\?\\?" docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md docs/boards/README.md docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md` returned no matches; `rg -n "Phase 31|phase_31_adversarial_mutation_calibration_evaluation.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed.
- Next: Step 1 - add adversarial manifest contracts, loader validation, and suite skeleton.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: board opened and Phase 31 implementation decisions pinned.
- Deferred: implementation steps remain open.
- Added beyond spec: none.

### Lessons for downstream phases

- Robustness and calibration work should stay in evaluation artifacts and code until a later approved phase changes runtime behavior.
