# Phase 31 - Adversarial, Mutation, and Calibration Evaluation

## Current Status

Step: 5 of 6
Branch: main
Started: 2026-05-10
Last session: 2026-05-10
Spec: `docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:13. Evaluation`; `docs/PROJECT_OVERVIEW.md:Target domains (ranked by fit)`; `docs/phase_26_plus_roadmap.md`

Step 5 complete. Next: Step 6 - add prompt-neutrality verification and final project verification.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add adversarial manifest contracts, loader validation, and suite skeleton.
- [x] Step 2: Add adversarial fixture variants and strict suite gates.
- [x] Step 3: Add mutation manifest contracts, source-sensitivity scoring, and suite skeleton.
- [x] Step 4: Add mutation fixtures and strict source-sensitivity gates.
- [x] Step 5: Add calibration report generation and CLI JSON output.
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
| `evals/fixtures/sec_market_disclosure_adversarial_distractors/source.txt:1` | Added SEC disclosure distractor-insertion adversarial variant source. | Step 2 |
| `evals/fixtures/sec_market_disclosure_adversarial_distractors/expected.json:1` | Added SEC adversarial variant expected spans copied from the source-backed base facts. | Step 2 |
| `evals/fixtures/sec_market_disclosure_adversarial_distractors/report.example.json:1` | Added SEC adversarial variant static report example. | Step 2 |
| `evals/fixtures/regulatory_order_compliance_adversarial_distractors/source.txt:1` | Added regulatory-order distractor-insertion adversarial variant source. | Step 2 |
| `evals/fixtures/regulatory_order_compliance_adversarial_distractors/expected.json:1` | Added regulatory adversarial variant expected spans copied from the source-backed base facts. | Step 2 |
| `evals/fixtures/regulatory_order_compliance_adversarial_distractors/report.example.json:1` | Added regulatory adversarial variant static report example. | Step 2 |
| `evals/fixtures/insurance_policy_coverage_adversarial_distractors/source.txt:1` | Added insurance-policy distractor-insertion adversarial variant source. | Step 2 |
| `evals/fixtures/insurance_policy_coverage_adversarial_distractors/expected.json:1` | Added insurance adversarial variant expected spans copied from the source-backed base facts. | Step 2 |
| `evals/fixtures/insurance_policy_coverage_adversarial_distractors/report.example.json:1` | Added insurance adversarial variant static report example. | Step 2 |
| `evals/fixtures/procurement_rfp_requirements_adversarial_distractors/source.txt:1` | Added procurement-RFP distractor-insertion adversarial variant source. | Step 2 |
| `evals/fixtures/procurement_rfp_requirements_adversarial_distractors/expected.json:1` | Added procurement adversarial variant expected spans copied from the source-backed base facts. | Step 2 |
| `evals/fixtures/procurement_rfp_requirements_adversarial_distractors/report.example.json:1` | Added procurement adversarial variant static report example. | Step 2 |
| `evals/suites/phase_31_adversarial.json:1` | Added four distractor-insertion adversarial fixture pairs. | Step 2 |
| `tests/unit/test_eval_robustness.py:1` | Added adversarial manifest coverage and strict variant report scoring assertions. | Step 2 |
| `docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md:1` | Marked Step 2 complete and recorded verification. | Step 2 |
| `PROGRESS.md:1` | Recorded Phase 31 Step 2 completion and next step. | Step 2 |
| `src/extractor/evals/mutation.py:1` | Added mutation manifest contracts, repo-relative loader validation, declared-change validation, source-sensitivity result models, and mutation source-sensitivity scoring. | Step 3 |
| `src/extractor/evals/robustness.py:1` | Re-exported mutation contracts and scorer from the Phase 31 robustness surface while preserving adversarial manifest behavior. | Step 3 |
| `src/extractor/evals/__init__.py:1` | Exported mutation manifest contracts, result models, loader, and scorer. | Step 3 |
| `evals/suites/phase_31_mutation.json:1` | Added empty Phase 31 mutation suite skeleton for Step 4 fixture mutations. | Step 3 |
| `tests/unit/test_eval_robustness.py:1` | Added mutation manifest skeleton, duplicate ID, path, empty-change, absent-retired-value, and source-sensitivity failure coverage. | Step 3 |
| `docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md:1` | Marked Step 3 complete and recorded verification. | Step 3 |
| `PROGRESS.md:1` | Recorded Phase 31 Step 3 completion and next step. | Step 3 |
| `evals/fixtures/sec_market_disclosure_mutated_revenue/source.txt:1` | Added SEC disclosure source mutation for revenue and growth-rate sensitivity. | Step 4 |
| `evals/fixtures/sec_market_disclosure_mutated_revenue/expected.json:1` | Added SEC mutation expected spans with unchanged offsets and updated source-backed value. | Step 4 |
| `evals/fixtures/sec_market_disclosure_mutated_revenue/report.example.json:1` | Added SEC mutation static report example. | Step 4 |
| `evals/fixtures/regulatory_order_compliance_mutated_penalty/source.txt:1` | Added regulatory-order source mutation for civil-penalty sensitivity. | Step 4 |
| `evals/fixtures/regulatory_order_compliance_mutated_penalty/expected.json:1` | Added regulatory mutation expected spans with unchanged offsets and updated source-backed value. | Step 4 |
| `evals/fixtures/regulatory_order_compliance_mutated_penalty/report.example.json:1` | Added regulatory mutation static report example. | Step 4 |
| `evals/fixtures/insurance_policy_coverage_mutated_limit/source.txt:1` | Added insurance-policy source mutation for coverage-limit sensitivity. | Step 4 |
| `evals/fixtures/insurance_policy_coverage_mutated_limit/expected.json:1` | Added insurance mutation expected spans with unchanged offsets and updated source-backed value. | Step 4 |
| `evals/fixtures/insurance_policy_coverage_mutated_limit/report.example.json:1` | Added insurance mutation static report example. | Step 4 |
| `evals/fixtures/procurement_rfp_requirements_mutated_weight/source.txt:1` | Added procurement-RFP source mutation for evaluation-weight sensitivity. | Step 4 |
| `evals/fixtures/procurement_rfp_requirements_mutated_weight/expected.json:1` | Added procurement mutation expected spans with unchanged offsets and updated source-backed value. | Step 4 |
| `evals/fixtures/procurement_rfp_requirements_mutated_weight/report.example.json:1` | Added procurement mutation static report example. | Step 4 |
| `evals/suites/phase_31_mutation.json:1` | Added four declared mutation entries with retired and introduced source values. | Step 4 |
| `tests/unit/test_eval_robustness.py:1` | Added strict checked-in mutation manifest scoring and source-sensitivity assertions. | Step 4 |
| `docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md:1` | Marked Step 4 complete and recorded verification. | Step 4 |
| `PROGRESS.md:1` | Recorded Phase 31 Step 4 completion and next step. | Step 4 |
| `src/extractor/evals/calibration.py:1` | Added deterministic calibration report contracts, default confidence bins, suite report loading, matched/unmatched counting, and ECE/provenance ECE calculation. | Step 5 |
| `src/extractor/evals/cli.py:1` | Added `--adversarial-suite`, `--mutation-suite`, and `--calibration-suite` JSON output modes. | Step 5 |
| `src/extractor/evals/robustness.py:1` | Added adversarial suite result contracts and scorer for public CLI output. | Step 5 |
| `src/extractor/evals/__init__.py:1` | Exported calibration contracts, report generator, and adversarial suite result/scorer. | Step 5 |
| `tests/unit/test_eval_calibration.py:1` | Added calibration determinism, unmatched actual point, and Phase 31 CLI mode coverage. | Step 5 |
| `tests/unit/test_eval_robustness.py:1` | Consolidated robustness test imports and formatting to keep the file below the 400-line limit. | Step 5 |
| `docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md:1` | Marked Step 5 complete and recorded verification. | Step 5 |
| `PROGRESS.md:1` | Recorded Phase 31 Step 5 completion and next step. | Step 5 |

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
| 2 | `python3 -m pytest tests/unit/test_eval_robustness.py::test_phase_31_adversarial_manifest_covers_variant_domains_and_scores -q` first failed with no variant pairs; `python3 -m pytest tests/unit/test_eval_robustness.py -q`; `python3 -m pytest tests/unit/test_eval_robustness.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json`; `make lint`; `git diff --check` | PASS | 2026-05-10 |
| 3 | `python3 -m pytest tests/unit/test_eval_robustness.py::test_phase_31_mutation_manifest_loads tests/unit/test_eval_robustness.py::test_load_mutation_manifest_rejects_duplicate_ids_bad_paths_empty_changes_and_absent_retired_value tests/unit/test_eval_robustness.py::test_evaluate_mutation_manifest_reports_source_sensitivity tests/unit/test_eval_robustness.py::test_evaluate_mutation_manifest_fails_when_report_keeps_retired_value -q` first failed with missing mutation loader/scorer, then passed with 4 passed; `python3 -m pytest tests/unit/test_eval_robustness.py -q`; `python3 -m pytest tests/unit/test_eval_robustness.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json`; `make lint`; `git diff --check` | PASS | 2026-05-10 |
| 4 | `python3 -m pytest tests/unit/test_eval_robustness.py::test_phase_31_mutation_manifest_covers_mutated_domains_and_scores -q` first failed with no checked-in mutation entries, then passed; `python3 -m pytest tests/unit/test_eval_robustness.py -q`; `python3 -m pytest tests/unit/test_eval_robustness.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json`; `make lint`; `git diff --check` | PASS | 2026-05-10 |
| 5 | `python3 -m pytest tests/unit/test_eval_calibration.py -q` first failed with missing `extractor.evals.calibration` and missing Phase 31 CLI flags, then passed with 3 passed; `python3 -m pytest tests/unit/test_eval_calibration.py tests/unit/test_eval_robustness.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json`; `PYTHONPATH=src python3 -m extractor.evals --adversarial-suite evals/suites/phase_31_adversarial.json`; `PYTHONPATH=src python3 -m extractor.evals --mutation-suite evals/suites/phase_31_mutation.json`; `PYTHONPATH=src python3 -m extractor.evals --calibration-suite evals/suites/phase_30_diverse_corpus_round_1.json`; `make lint`; `git diff --check` | PASS | 2026-05-10 |

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
- Completed Step 2: added SEC disclosure, regulatory order, insurance policy, and procurement RFP distractor-insertion adversarial variants; updated the adversarial manifest with four pairs; and added strict static report scoring assertions for every variant.
- Completed Step 3: added mutation manifest contracts, an empty mutation suite skeleton, declared-change validation, mutation result models, source-sensitivity scoring, and tests for retained retired values and missing introduced values.
- Completed Step 4: added SEC disclosure, regulatory order, insurance policy, and procurement RFP mutation fixtures; updated the mutation manifest with retired and introduced source values; and added strict source-sensitivity scoring assertions for every mutation.
- Completed Step 5: added deterministic calibration report generation, default confidence bins, public JSON CLI modes for adversarial, mutation, and calibration suites, and calibration tests for deterministic bins and unmatched actual points.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|O[p]en Questions|\\?\\?" docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md docs/boards/README.md docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md` returned no matches; `rg -n "Phase 31|phase_31_adversarial_mutation_calibration_evaluation.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_31_adversarial_mutation_calibration_evaluation.md docs/boards/phase_31_adversarial_mutation_calibration_evaluation.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed.
- Tests for Step 1: `python3 -m pytest tests/unit/test_eval_robustness.py -q` first failed with missing `extractor.evals.robustness`, then passed with 4 passed; `python3 -m pytest tests/unit/test_eval_robustness.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q` passed with 29 passed; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `make lint` passed; `git diff --check` passed.
- Tests for Step 2: `python3 -m pytest tests/unit/test_eval_robustness.py::test_phase_31_adversarial_manifest_covers_variant_domains_and_scores -q` first failed with no variant pairs, then passed; `python3 -m pytest tests/unit/test_eval_robustness.py -q` passed with 5 passed; `python3 -m pytest tests/unit/test_eval_robustness.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q` passed with 30 passed; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; Phase 31 adversarial summary reported 4 pairs and each variant had 5 expected data points with precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, and zero invariant violations; `make lint` passed; `git diff --check` passed.
- Tests for Step 3: `python3 -m pytest tests/unit/test_eval_robustness.py::test_phase_31_mutation_manifest_loads tests/unit/test_eval_robustness.py::test_load_mutation_manifest_rejects_duplicate_ids_bad_paths_empty_changes_and_absent_retired_value tests/unit/test_eval_robustness.py::test_evaluate_mutation_manifest_reports_source_sensitivity tests/unit/test_eval_robustness.py::test_evaluate_mutation_manifest_fails_when_report_keeps_retired_value -q` first failed with missing mutation loader/scorer, then passed with 4 passed; `python3 -m pytest tests/unit/test_eval_robustness.py -q` passed with 9 passed; `python3 -m pytest tests/unit/test_eval_robustness.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q` passed with 34 passed; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `make lint` passed; `git diff --check` passed.
- Tests for Step 4: `python3 -m pytest tests/unit/test_eval_robustness.py::test_phase_31_mutation_manifest_covers_mutated_domains_and_scores -q` first failed with no checked-in mutation entries, then passed; `python3 -m pytest tests/unit/test_eval_robustness.py -q` passed with 10 passed; `python3 -m pytest tests/unit/test_eval_robustness.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q` passed with 35 passed; Phase 31 mutation summary reported 4 mutations, source-sensitivity 1.0, each mutation with 5 expected data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero source-sensitivity failures; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `make lint` passed; `git diff --check` passed.
- Tests for Step 5: `python3 -m pytest tests/unit/test_eval_calibration.py -q` first failed with missing `extractor.evals.calibration` and missing Phase 31 CLI flags, then passed with 3 passed; `python3 -m pytest tests/unit/test_eval_calibration.py tests/unit/test_eval_robustness.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q` passed with 38 passed; `PYTHONPATH=src python3 -m extractor.evals --adversarial-suite evals/suites/phase_31_adversarial.json` passed with 4 pairs; `PYTHONPATH=src python3 -m extractor.evals --mutation-suite evals/suites/phase_31_mutation.json` passed with 4 mutations and source-sensitivity 1.0; `PYTHONPATH=src python3 -m extractor.evals --calibration-suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 total data points, 49 matched data points, 0 unmatched data points, expected calibration error 0.048979591836734754, and provenance calibration error 0.048979591836734754; Phase 29 and Phase 30 suites remained passing with zero invariant violations and zero threshold failures; `make lint` passed; `git diff --check` passed.
- Next: Step 6 - add prompt-neutrality verification and final project verification.

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
