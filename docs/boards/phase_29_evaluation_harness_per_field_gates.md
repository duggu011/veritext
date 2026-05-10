# Phase 29 - Evaluation Harness: Per-Field Gates

## Current Status

Step: 5 of 5
Branch: main
Started: 2026-05-10
Last session: 2026-05-10
Spec: `docs/specs/phase_29_evaluation_harness_per_field_gates.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:13. Evaluation`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 29 accepted by the operator on 2026-05-10. Matching commits exist through `0f3c3a1`. Phase 30 spec draft is opened; do not begin Phase 30 implementation until its spec is approved and a board is created.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add category and field metric breakdown contracts and scorer coverage.
- [x] Step 2: Add provenance and invariant breakdown grouping coverage.
- [x] Step 3: Add suite manifest contracts, loader, and core suite artifact.
- [x] Step 4: Add suite scoring, threshold failure reporting, and CLI output.
- [x] Step 5: Add prompt-neutrality verification and final project verification.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Add suite scoring as `veritext-eval --suite <manifest>` rather than a second console script. | Keeps the existing public eval entry point intact while adding a backwards-compatible suite mode. |
| Q2 | Keep grouped thresholds only in suite manifests for Phase 29. | Avoids expanding individual fixture contracts and keeps evaluation gates centralized for suite-level enforcement. |
| Q3 | Limit the first suite to fixtures with checked-in `report.example.json` files. | Suite scoring must be portable, deterministic, and independent of live LLM extraction or local `.veritext` state. |
| Q4 | Include full missing and unexpected ID lists by default in JSON output. | Phase 29 prioritizes auditability and no-silent-drop reporting over terse output. |

---

## Gate Interpretations

- The Phase 29 core suite is the authoritative first suite and must use repo-relative case and report paths.
- Suite thresholds default to zero allowed invariant violations unless a manifest entry explicitly declares a non-zero allowance with a documented test rationale.
- Category and field metric keys must include category for field metrics so same-named fields in different categories cannot collide.
- Suite mode must not change existing `veritext-eval <case> <report>` behavior.
- JSON output must carry enough detail to identify failing suite, fixture, category, or field gates without relying on external logs.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_29_evaluation_harness_per_field_gates.md:1` | Approved Phase 29 spec. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_29_evaluation_harness_per_field_gates.md:1` | Active Phase 29 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `src/extractor/evals/models.py:107` | Added category and field metric breakdown contracts and additive `EvaluationResult` fields. | Step 1 |
| `src/extractor/evals/scoring.py:70` | Added deterministic category and field metric aggregation to `evaluate_report(...)`. | Step 1 |
| `src/extractor/evals/__init__.py:3` | Exported new eval breakdown model contracts. | Step 1 |
| `tests/unit/test_evals.py:28` | Added category and field metric coverage for passing fixtures and grouped false positives/false negatives. | Step 1 |
| `src/extractor/evals/scoring.py:84` | Grouped invariant violations by violated report data point category and field. | Step 2 |
| `tests/unit/test_evals.py:192` | Added shifted-span provenance recall and invariant grouping assertions for category and field metrics. | Step 2 |
| `src/extractor/evals/models.py:132` | Added suite manifest threshold contracts, suite result contracts, and threshold failure contracts. | Step 3, Step 4 |
| `src/extractor/evals/suites.py:1` | Added repo-local JSON manifest loader, suite scoring, aggregate metric merging, and threshold failure reporting. | Step 3, Step 4 |
| `src/extractor/evals/__init__.py:27` | Exported suite manifest contracts and loader. | Step 3 |
| `evals/suites/phase_29_core.json:1` | Added the Phase 29 static fixture suite manifest with strict global, category, and field thresholds. | Step 3 |
| `tests/unit/test_eval_suites.py:1` | Added suite manifest loader validation coverage for valid manifests, duplicate IDs, bad paths, duplicate thresholds, invalid thresholds, invariant allowance rationale, and the core suite artifact. | Step 3 |
| `src/extractor/evals/cli.py:13` | Added `veritext-eval --suite <manifest>` while preserving single-fixture positional mode. | Step 4 |
| `tests/unit/test_eval_suites.py:206` | Added suite scoring, field-threshold failure, and suite CLI JSON tests. | Step 4 |
| `tests/unit/test_evals.py:274` | Extended single-fixture CLI JSON assertions for category/field breakdown output and ID lists. | Step 4 |
| `docs/boards/README.md:1` | Marked Phase 29 final-gate-ready. | Step 5 |
| `docs/boards/phase_29_evaluation_harness_per_field_gates.md:1` | Recorded final verification, final gate status, and phase summary. | Step 5 |
| `PROGRESS.md:1` | Recorded Phase 29 final verification handoff. | Step 5 |
| `docs/specs/phase_30_diverse_fixture_corpus_round_1.md:1` | Opened draft Phase 30 spec after operator acceptance. | Acceptance |
| `docs/boards/README.md:1` | Marked Phase 29 complete and Phase 30 active in spec-draft state. | Acceptance |
| `PROGRESS.md:1` | Recorded Phase 29 acceptance and Phase 30 spec-draft handoff. | Acceptance |

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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/README.md docs/boards/phase_29_evaluation_harness_per_field_gates.md`; `rg -n "Phase 29|phase_29_evaluation_harness_per_field_gates.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/phase_29_evaluation_harness_per_field_gates.md`; `cmp -s AGENTS.md CLAUDE.md` | PASS | 2026-05-10 |
| 1 | `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_includes_category_and_field_metrics_for_passing_fixture -q` first failed with missing `EvaluationResult.category_metrics`; `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_includes_category_and_field_metrics_for_passing_fixture -q`; `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_groups_false_positive_and_false_negative_metrics -q`; `python3 -m pytest tests/unit/test_evals.py -q`; `python3 -m pytest tests/unit/test_evals.py tests/integration/test_recall_baseline.py -q`; `git diff --check`; `make lint` | PASS | 2026-05-10 |
| 2 | `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_flags_source_span_invariant_breaks -q` first failed with grouped invariant count `0 != 2`; `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_flags_source_span_invariant_breaks -q`; `python3 -m pytest tests/unit/test_evals.py tests/integration/test_recall_baseline.py -q`; `git diff --check`; `make lint` | PASS | 2026-05-10 |
| 3 | `python3 -m pytest tests/unit/test_eval_suites.py::test_load_suite_manifest_accepts_valid_manifest -q` first failed with missing `extractor.evals.suites`; `python3 -m pytest tests/unit/test_eval_suites.py -q`; `python3 -m pytest tests/unit/test_eval_suites.py tests/unit/test_evals.py tests/integration/test_recall_baseline.py -q`; `git diff --check`; `make lint` | PASS | 2026-05-10 |
| 4 | `python3 -m pytest tests/unit/test_eval_suites.py::test_evaluate_suite_manifest_scores_static_core_suite -q` first failed with missing `evaluate_suite_manifest`; `python3 -m pytest tests/unit/test_eval_suites.py -q`; `python3 -m pytest tests/unit/test_eval_suites.py tests/unit/test_evals.py tests/integration/test_recall_baseline.py -q`; `git diff --check`; `make lint` | PASS | 2026-05-10 |
| 5 | `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json`; `make test`; `make lint`; `make smoke`; `git diff --check`; `git diff --exit-code -- prompts` | PASS | 2026-05-10 |
| Acceptance | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_30_diverse_fixture_corpus_round_1.md docs/boards/README.md docs/boards/phase_29_evaluation_harness_per_field_gates.md`; `rg -n "Phase 30|phase_30_diverse_fixture_corpus_round_1.md|SPEC DRAFT|COMPLETE \\(2026-05-10\\)" docs/boards/README.md PROGRESS.md docs/specs/phase_30_diverse_fixture_corpus_round_1.md docs/boards/phase_29_evaluation_harness_per_field_gates.md`; `cmp -s AGENTS.md CLAUDE.md` | PASS | 2026-05-10 |

### Final Gate

- [x] Narrow relevant tests pass
- [x] `make test` passes when feasible
- [x] `make lint` passes
- [x] `make smoke` passes when feasible
- [x] `git diff --check` passes
- [x] Evaluation gates pass, if this phase changes extraction behavior
- [x] All OPEN issues are resolved or explicitly deferred
- [x] Phase Summary filled in
- [x] `PROGRESS.md` updated

---

## Work Log

Reverse chronological. Log every session.

### 2026-05-10 - Session 2

- Resumed after operator accepted Phase 29 with `continue`.
- Completed: marked Phase 29 complete in the board index, opened the draft Phase 30 spec for Diverse Fixture Corpus Round 1, and updated `PROGRESS.md`.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_30_diverse_fixture_corpus_round_1.md docs/boards/README.md docs/boards/phase_29_evaluation_harness_per_field_gates.md` returned no matches; `rg -n "Phase 30|phase_30_diverse_fixture_corpus_round_1.md|SPEC DRAFT|COMPLETE \\(2026-05-10\\)" docs/boards/README.md PROGRESS.md docs/specs/phase_30_diverse_fixture_corpus_round_1.md docs/boards/phase_29_evaluation_harness_per_field_gates.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed.
- Next: operator review of `docs/specs/phase_30_diverse_fixture_corpus_round_1.md`. Phase 30 implementation must not begin until the spec is approved and a board is created.

### 2026-05-10 - Session 1

- Resumed after operator approved Phase 29 with `continue`.
- Completed: opened this board, pinned Phase 29 open-question resolutions, updated active phase tracking, added additive category and field metric contracts, added scorer aggregation for passing, false-positive, and false-negative grouped metrics, grouped exact provenance recall plus invariant violations by category and field, added suite manifest contracts, loader validation, and the Phase 29 core suite artifact, added suite scoring, threshold failure reporting, and CLI JSON output, and completed final verification.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/README.md docs/boards/phase_29_evaluation_harness_per_field_gates.md` returned no matches; `rg -n "Phase 29|phase_29_evaluation_harness_per_field_gates.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/phase_29_evaluation_harness_per_field_gates.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed; `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_includes_category_and_field_metrics_for_passing_fixture -q` first failed with missing `EvaluationResult.category_metrics`, then passed; `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_groups_false_positive_and_false_negative_metrics -q` passed; `python3 -m pytest tests/unit/test_evals.py -q` passed with 14 passed; `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_flags_source_span_invariant_breaks -q` first failed with grouped invariant count `0 != 2`, then passed; `python3 -m pytest tests/unit/test_eval_suites.py::test_load_suite_manifest_accepts_valid_manifest -q` first failed with missing `extractor.evals.suites`, then passed; `python3 -m pytest tests/unit/test_eval_suites.py -q` passed with 7 passed; `python3 -m pytest tests/unit/test_eval_suites.py::test_evaluate_suite_manifest_scores_static_core_suite -q` first failed with missing `evaluate_suite_manifest`, then passed; `python3 -m pytest tests/unit/test_eval_suites.py tests/unit/test_evals.py tests/integration/test_recall_baseline.py -q` passed with 26 passed and 2 skipped; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with suite metrics precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, 21 expected/actual/true positive data points, zero invariant violations, and zero threshold failures; `make test` passed with 264 passed and 2 skipped; `make lint` passed; `make smoke` passed with 1 passed; `git diff --check` passed; `git diff --exit-code -- prompts` passed.
- Next: operator review and acceptance of Phase 29. Phase 30 must not begin until the operator explicitly continues.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

### What shipped vs spec

- Built as specified: additive per-category and per-field metrics; grouped false positive, false negative, precision, recall, F1, exact provenance, provenance recall, and invariant counts; strict suite manifest contracts; checked-in Phase 29 core suite; suite scoring; threshold failure reporting; single-fixture and suite CLI JSON output; prompt-neutrality verification.
- Deferred: diverse cross-domain fixtures remain Phase 30; adversarial/mutation/calibration work remains Phase 31; CI/CD remains blocked until an architecture amendment phase.
- Added beyond spec: none.

### Lessons for downstream phases

- Phase 30 fixtures can enter through `evals/suites/*.json` without changing runtime extraction behavior.
- Category and field threshold failures now identify weak slices directly, so new corpus work should add strict thresholds as fixtures are introduced.
- Keep checked-in static reports for suite membership unless a later phase explicitly adds a deterministic report-generation step.
