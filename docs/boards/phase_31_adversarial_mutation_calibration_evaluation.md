# Phase 31 - Adversarial, Mutation, and Calibration Evaluation

## Current Status

Step: 1 of 6
Branch: main
Started: 2026-05-10
Last session: 2026-05-10
Spec: `docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:13. Evaluation`; `docs/PROJECT_OVERVIEW.md:Target domains (ranked by fit)`; `docs/phase_26_plus_roadmap.md`

Step 1 complete. Next: Step 2 - add adversarial fixture variants and strict suite gates.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add adversarial manifest contracts, loader validation, and suite skeleton.
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
| `src/extractor/evals/robustness.py:1` | Added adversarial manifest contracts, repo-relative loader validation, report/case validation, duplicate-pair rejection, mode validation, and copied-offset detection. | Step 1 |
| `src/extractor/evals/__init__.py:1` | Exported adversarial manifest contracts and loader. | Step 1 |
| `evals/suites/phase_31_adversarial.json:1` | Added empty Phase 31 adversarial suite skeleton for Step 2 fixture pairs. | Step 1 |
| `tests/unit/test_eval_robustness.py:1` | Added adversarial manifest loader, skeleton, path, mode, duplicate, and copied-offset validation coverage. | Step 1 |
| `docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md:1` | Marked Step 1 complete and recorded verification. | Step 1 |
| `PROGRESS.md:1` | Recorded Phase 31 Step 1 completion and next step. | Step 1 |

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
| 1 | `python3 -m pytest tests/unit/test_eval_robustness.py -q` first failed with missing `extractor.evals.robustness`, then passed with 4 passed; `python3 -m pytest tests/unit/test_eval_robustness.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json`; `make lint`; `git diff --check` | PASS | 2026-05-10 |

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
- Completed Step 1: added adversarial manifest contracts, loader validation, an empty Phase 31 adversarial suite skeleton, and test coverage for duplicate pair IDs, bad paths, unsupported modes, and copied offsets with changed variant text.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|O[p]en Questions|\\?\\?" docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md docs/boards/README.md docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md` returned no matches; `rg -n "Phase 31|phase_31_adversarial_mutation_calibration_evaluation.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed.
- Tests for Step 1: `python3 -m pytest tests/unit/test_eval_robustness.py -q` first failed with missing `extractor.evals.robustness`, then passed with 4 passed; `python3 -m pytest tests/unit/test_eval_robustness.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q` passed with 29 passed; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `make lint` passed; `git diff --check` passed.
- Next: Step 2 - add adversarial fixture variants and strict suite gates.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: _(phase in progress; see Work Log)_
- Deferred: _(phase in progress)_
- Added beyond spec: _(phase in progress)_

### Lessons for downstream phases

- Robustness and calibration work should stay in evaluation artifacts and code until a later approved phase changes runtime behavior.
