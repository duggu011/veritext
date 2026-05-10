# Phase 30 - Diverse Fixture Corpus Round 1

## Current Status

Step: 1 of 4
Branch: main
Started: 2026-05-10
Last session: 2026-05-10
Spec: `docs/specs/phase_30_diverse_fixture_corpus_round_1.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:13. Evaluation`; `docs/PROJECT_OVERVIEW.md:Target domains (ranked by fit)`; `docs/phase_26_plus_roadmap.md`

Step 1 complete. Next: Step 2 - add SEC, regulatory, standards, and procurement fixtures.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add corpus inventory validation and Phase 30 suite skeleton.
- [ ] Step 2: Add SEC, regulatory, standards, and procurement fixtures.
- [ ] Step 3: Add clinical, FDA-label, insurance, and scientific fixtures.
- [ ] Step 4: Add complete suite thresholds, prompt-neutrality verification, and final project verification.

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
| `docs/boards/phase_30_diverse_fixture_corpus_round_1.md:1` | Active Phase 30 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `tests/unit/test_eval_suites.py:208` | Added Phase 30 suite skeleton scoring and threshold-coverage validation. | Step 1 |
| `evals/suites/phase_30_diverse_corpus_round_1.json:1` | Added strict Phase 30 suite skeleton with `legal_contracts_core`. | Step 1 |

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

- Resumed after operator approved Phase 30 with `continue`.
- Completed: opened this board, pinned Phase 30 open-question resolutions, and updated active phase tracking.
- Completed Step 1: added Phase 30 suite skeleton validation, added `evals/suites/phase_30_diverse_corpus_round_1.json` with strict `legal_contracts_core` thresholds, and verified both Phase 29 and Phase 30 suite CLIs.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_30_diverse_fixture_corpus_round_1.md docs/boards/README.md docs/boards/phase_30_diverse_fixture_corpus_round_1.md` returned no matches; `rg -n "Phase 30|phase_30_diverse_fixture_corpus_round_1.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_30_diverse_fixture_corpus_round_1.md docs/boards/phase_30_diverse_fixture_corpus_round_1.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed.
- Tests for Step 1: `python3 -m pytest tests/unit/test_eval_suites.py::test_phase_30_diverse_corpus_suite_skeleton_scores_and_covers_thresholds -q` first failed with missing `phase_30_diverse_corpus_round_1.json`, then passed; `python3 -m pytest tests/unit/test_eval_suites.py -q` passed with 11 passed; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 9 expected/actual/true positive data points, precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, zero invariant violations, and zero threshold failures; `git diff --check` passed.
- Next: Step 2 - add SEC, regulatory, standards, and procurement fixtures.

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
