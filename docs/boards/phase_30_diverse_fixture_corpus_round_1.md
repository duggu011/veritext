# Phase 30 - Diverse Fixture Corpus Round 1

## Current Status

Step: 4 of 4
Branch: main
Started: 2026-05-10
Last session: 2026-05-10
Spec: `docs/specs/phase_30_diverse_fixture_corpus_round_1.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:13. Evaluation`; `docs/PROJECT_OVERVIEW.md:Target domains (ranked by fit)`; `docs/phase_26_plus_roadmap.md`

Phase 30 final gate ready. Awaiting operator acceptance; do not start Phase 31 without explicit `continue`.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add corpus inventory validation and Phase 30 suite skeleton.
- [x] Step 2: Add SEC, regulatory, standards, and procurement fixtures.
- [x] Step 3: Add clinical, FDA-label, insurance, and scientific fixtures.
- [x] Step 4: Add complete suite thresholds, prompt-neutrality verification, and final project verification.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Require at least eight new cross-domain fixtures in Round 1. | The Phase 30 gate exists to broaden coverage visibly; fewer fixtures would weaken the phase's generalization objective. |
| Q2 | Keep live LLM baseline reports optional operator-run evidence outside required tests. | Required gates must remain deterministic, portable, and independent of API keys, model availability, or local `.veritext` state. |
| Q3 | Add `annotation.md` only for fixtures with non-obvious span-width decisions. | `expected.json` plus `docs/annotation-conventions.md` is enough for straightforward fixtures; notes should clarify ambiguity, not add documentation churn. |
| Q4 | Keep new domain schemas embedded in static report metadata for Phase 30; defer domain-pack/schema-registry artifacts to later dedicated phases. | Phase 30 is corpus and evaluation coverage only, and should not expand runtime planner or schema registry behavior. |

---

## Gate Interpretations

- The Phase 30 suite manifest is `evals/suites/phase_30_diverse_corpus_round_1.json`.
- The Phase 30 suite must include `legal_contracts_core` plus the new cross-domain fixtures; the Phase 29 core suite remains a separate regression gate.
- Every new category and `(category, field_name)` introduced by Phase 30 fixtures must have strict suite thresholds.
- Static `report.example.json` files prove fixture validity and scorer gates; they are not evidence that live extraction generalizes.
- Fixture sources must be synthetic or repo-safe, UTF-8 text/Markdown, and supported by the current static eval tooling.
- Phase 30 must not change runtime extraction code, prompt bodies, runtime config, or domain-pack runtime behavior.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_30_diverse_fixture_corpus_round_1.md:1` | Approved Phase 30 spec. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/README.md:9` | Marked Phase 30 final gate ready. | Step 4 |
| `docs/boards/phase_30_diverse_fixture_corpus_round_1.md:1` | Active Phase 30 board. | Board opening |
| `docs/boards/phase_30_diverse_fixture_corpus_round_1.md:1` | Marked Step 4 complete, recorded final verification, and filled the phase summary. | Step 4 |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `PROGRESS.md:1` | Recorded Phase 30 final verification and next operator acceptance gate. | Step 4 |
| `tests/unit/test_eval_suites.py:206` | Added Phase 30 suite scoring, required-fixture, and threshold-coverage validation. | Steps 1-3 |
| `evals/suites/phase_30_diverse_corpus_round_1.json:1` | Added strict Phase 30 suite skeleton with `legal_contracts_core`. | Step 1 |
| `evals/suites/phase_30_diverse_corpus_round_1.json:1` | Expanded Phase 30 suite with SEC, regulatory, standards, and procurement fixtures plus strict thresholds for introduced categories and fields. | Step 2 |
| `evals/suites/phase_30_diverse_corpus_round_1.json:1` | Expanded Phase 30 suite with clinical, FDA-label, insurance, and scientific fixtures plus strict thresholds for introduced categories and fields. | Step 3 |
| `evals/fixtures/sec_market_disclosure/source.txt:1` | Added synthetic SEC market-disclosure fixture source. | Step 2 |
| `evals/fixtures/sec_market_disclosure/expected.json:1` | Added expected exact-span annotations for SEC market disclosure. | Step 2 |
| `evals/fixtures/sec_market_disclosure/report.example.json:1` | Added static report example for SEC market disclosure. | Step 2 |
| `evals/fixtures/regulatory_order_compliance/source.txt:1` | Added synthetic regulatory-order fixture source. | Step 2 |
| `evals/fixtures/regulatory_order_compliance/expected.json:1` | Added expected exact-span annotations for regulatory order compliance. | Step 2 |
| `evals/fixtures/regulatory_order_compliance/report.example.json:1` | Added static report example for regulatory order compliance. | Step 2 |
| `evals/fixtures/standards_security_controls/source.txt:1` | Added synthetic standards-control fixture source. | Step 2 |
| `evals/fixtures/standards_security_controls/expected.json:1` | Added expected exact-span annotations for standards security controls. | Step 2 |
| `evals/fixtures/standards_security_controls/report.example.json:1` | Added static report example for standards security controls. | Step 2 |
| `evals/fixtures/procurement_rfp_requirements/source.txt:1` | Added synthetic procurement-RFP fixture source. | Step 2 |
| `evals/fixtures/procurement_rfp_requirements/expected.json:1` | Added expected exact-span annotations for procurement RFP requirements. | Step 2 |
| `evals/fixtures/procurement_rfp_requirements/report.example.json:1` | Added static report example for procurement RFP requirements. | Step 2 |
| `evals/fixtures/clinical_trial_protocol/source.txt:1` | Added synthetic clinical-trial protocol fixture source. | Step 3 |
| `evals/fixtures/clinical_trial_protocol/expected.json:1` | Added expected exact-span annotations for clinical trial protocol. | Step 3 |
| `evals/fixtures/clinical_trial_protocol/report.example.json:1` | Added static report example for clinical trial protocol. | Step 3 |
| `evals/fixtures/fda_label_safety/source.txt:1` | Added synthetic regulated drug-label safety fixture source. | Step 3 |
| `evals/fixtures/fda_label_safety/expected.json:1` | Added expected exact-span annotations for FDA-label safety. | Step 3 |
| `evals/fixtures/fda_label_safety/report.example.json:1` | Added static report example for FDA-label safety. | Step 3 |
| `evals/fixtures/insurance_policy_coverage/source.txt:1` | Added synthetic insurance-policy coverage fixture source. | Step 3 |
| `evals/fixtures/insurance_policy_coverage/expected.json:1` | Added expected exact-span annotations for insurance policy coverage. | Step 3 |
| `evals/fixtures/insurance_policy_coverage/report.example.json:1` | Added static report example for insurance policy coverage. | Step 3 |
| `evals/fixtures/scientific_review_paper/source.txt:1` | Added synthetic scientific-review paper fixture source. | Step 3 |
| `evals/fixtures/scientific_review_paper/expected.json:1` | Added expected exact-span annotations for scientific review paper. | Step 3 |
| `evals/fixtures/scientific_review_paper/report.example.json:1` | Added static report example for scientific review paper. | Step 3 |

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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_30_diverse_fixture_corpus_round_1.md docs/boards/README.md docs/boards/phase_30_diverse_fixture_corpus_round_1.md`; `rg -n "Phase 30|phase_30_diverse_fixture_corpus_round_1.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_30_diverse_fixture_corpus_round_1.md docs/boards/phase_30_diverse_fixture_corpus_round_1.md`; `cmp -s AGENTS.md CLAUDE.md` | PASS | 2026-05-10 |
| 1 | `python3 -m pytest tests/unit/test_eval_suites.py::test_phase_30_diverse_corpus_suite_skeleton_scores_and_covers_thresholds -q` first failed with missing `phase_30_diverse_corpus_round_1.json`; `python3 -m pytest tests/unit/test_eval_suites.py::test_phase_30_diverse_corpus_suite_skeleton_scores_and_covers_thresholds -q`; `python3 -m pytest tests/unit/test_eval_suites.py -q`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json`; `git diff --check` | PASS | 2026-05-10 |
| 2 | `python3 -m pytest tests/unit/test_eval_suites.py::test_phase_30_diverse_corpus_suite_skeleton_scores_and_covers_thresholds -q` first failed with missing Step 2 fixture IDs; `python3 -m pytest tests/unit/test_eval_suites.py::test_phase_30_diverse_corpus_suite_skeleton_scores_and_covers_thresholds -q`; `python3 -m pytest tests/unit/test_eval_suites.py tests/unit/test_evals.py -q`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json`; `git diff --check` | PASS | 2026-05-10 |
| 3 | `python3 -m pytest tests/unit/test_eval_suites.py::test_phase_30_diverse_corpus_suite_skeleton_scores_and_covers_thresholds -q` first failed with missing Step 3 fixture IDs; `python3 -m pytest tests/unit/test_eval_suites.py::test_phase_30_diverse_corpus_suite_skeleton_scores_and_covers_thresholds -q`; `python3 -m pytest tests/unit/test_eval_suites.py tests/unit/test_evals.py -q`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json`; `git diff --check` | PASS | 2026-05-10 |
| 4 | `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json`; `make test`; `make lint`; `make smoke`; `git diff --check`; `git diff --exit-code -- prompts` | PASS | 2026-05-10 |

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

### 2026-05-10 - Session 1

- Resumed after operator approved Phase 30 with `continue`.
- Completed: opened this board, pinned Phase 30 open-question resolutions, and updated active phase tracking.
- Completed Step 1: added Phase 30 suite skeleton validation, added `evals/suites/phase_30_diverse_corpus_round_1.json` with strict `legal_contracts_core` thresholds, and verified both Phase 29 and Phase 30 suite CLIs.
- Completed Step 2: added synthetic SEC disclosure, regulatory order, standards security-control, and procurement RFP fixtures with exact expected spans and static report examples.
- Completed Step 3: added synthetic clinical-trial protocol, regulated drug-label safety, insurance policy coverage, and scientific review paper fixtures with exact expected spans and static report examples.
- Expanded the Phase 30 suite to include the Step 2 fixtures and strict thresholds for every introduced category and field.
- Expanded the Phase 30 suite to include the Step 3 fixtures and strict thresholds for every introduced category and field.
- Completed Step 4: verified complete Phase 30 suite thresholds, prompt neutrality, Phase 29 regression suite behavior, project tests, lint, smoke, and whitespace.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_30_diverse_fixture_corpus_round_1.md docs/boards/README.md docs/boards/phase_30_diverse_fixture_corpus_round_1.md` returned no matches; `rg -n "Phase 30|phase_30_diverse_fixture_corpus_round_1.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_30_diverse_fixture_corpus_round_1.md docs/boards/phase_30_diverse_fixture_corpus_round_1.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed.
- Tests for Step 1: `python3 -m pytest tests/unit/test_eval_suites.py::test_phase_30_diverse_corpus_suite_skeleton_scores_and_covers_thresholds -q` first failed with missing `phase_30_diverse_corpus_round_1.json`, then passed; `python3 -m pytest tests/unit/test_eval_suites.py -q` passed with 11 passed; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 9 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `git diff --check` passed.
- Tests for Step 2: `python3 -m pytest tests/unit/test_eval_suites.py::test_phase_30_diverse_corpus_suite_skeleton_scores_and_covers_thresholds -q` first failed with missing Step 2 fixture IDs, then passed; `python3 -m pytest tests/unit/test_eval_suites.py tests/unit/test_evals.py -q` passed with 25 passed; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 29 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with zero threshold failures; `git diff --check` passed.
- Tests for Step 3: `python3 -m pytest tests/unit/test_eval_suites.py::test_phase_30_diverse_corpus_suite_skeleton_scores_and_covers_thresholds -q` first failed with missing Step 3 fixture IDs, then passed; `python3 -m pytest tests/unit/test_eval_suites.py tests/unit/test_evals.py -q` passed with 25 passed; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `git diff --check` passed.
- Tests for Step 4: `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `make test` passed with 265 passed and 2 skipped; `make lint` passed; `make smoke` passed with 1 passed; `git diff --check` passed; `git diff --exit-code -- prompts` passed.
- Next: operator acceptance of Phase 30, then Phase 31 spec opening after explicit `continue`.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

Phase 30 is final-gate-ready as of 2026-05-10.

### What shipped vs spec

- Built as specified: a checked-in static diverse corpus with eight new cross-domain fixtures plus the `legal_contracts_core` baseline, strict global/category/field thresholds, exact source spans, static report examples, prompt-neutrality verification, and full final-gate verification.
- Deferred: live LLM baseline reports remain optional operator-run evidence outside required tests.
- Added beyond spec: none.

### Lessons for downstream phases

- Static mirror reports prove fixture and scorer validity, not live extraction generalization; Phase 31 should use this corpus for adversarial, mutation, and calibration evaluation without tuning prompts or runtime behavior around fixture-specific answers.
