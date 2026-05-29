# Phase 37 - Expanded Lenses Round 1

## Current Status

Step: 8 of 8
Branch: main
Started: 2026-05-29
Last session: 2026-05-29
Spec: `docs/specs/phase_37_expanded_lenses_round_1.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:4. Executor`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 37 opened after operator continuation resolved the prompt-content gate by authorizing agent-authored prompt bodies and planner prompt updates for this phase.

Next: operator acceptance of Phase 37. Do not start Phase 38 without explicit operator continuation.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add RED tests for the new executable lens contract boundary, prompt loader stage list, planner lens selection, executor call routing, and audit readback.
- [x] Step 2: Extend `LensName`, `LLMStage`, `PROMPT_STAGES`, and the lens taxonomy registry for `definition`, `citation`, `temporal`, and `quantity_with_unit`.
- [x] Step 3: Add approved executor prompt files for `definition`, `citation`, `temporal`, and `quantity_with_unit`.
- [x] Step 4: Update planner strategy and budget prompts so live planning can select and budget the new executable lenses.
- [x] Step 5: Run new lenses through existing executor materialization, normalization metadata, rejection, and audit paths.
- [x] Step 6: Add focused fixture or evaluation coverage for source-role-neutral recall improvement without fixture-specific source patches.
- [x] Step 7: Run final project, smoke, lint, prompt-change review, and evaluation gates.
- [x] Step 8: Fill the board summary and stop for operator acceptance.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Agent-authored prompt bodies and planner prompt updates are authorized for Phase 37. | Operator continuation resolved the prompt-content gate; the new lenses need prompts to be executable. |
| Q2 | Phase 37 implements only `definition`, `citation`, `temporal`, and `quantity_with_unit`. | These are lower-risk single-span roles; relation, obligation, condition, and exception need later cross-candidate semantics. |
| Q3 | The existing `ExtractedCandidatePayload` schema remains shared across executor lenses. | Keeps forced tool use and source reconstruction stable unless strict-tool tests prove a split schema is necessary. |

---

## Gate Interpretations

- Phase 37 may change prompt bodies under `prompts/` because the operator authorized agent-authored prompt text for this phase.
- Phase 37 may modify `planner.select_strategy` and `planner.allocate_budget` prompts to include the new executable lenses.
- Phase 37 must keep every LLM call routed through `src/extractor/llm/client.py`.
- Phase 37 must not make `relation`, `obligation`, `condition`, or `exception` executable.
- Phase 37 must not change dedup keys, conflict behavior, cross-document reconciliation, reporter formats, or architecture rules.
- New executable lenses must have prompt files, stage names, planner selection, budget validation, runtime routing, audit persistence, and tests before they are treated as executable.
- `git diff --exit-code -- prompts` is not a Phase 37 completion gate; the board must instead record every prompt file changed and why.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_37_expanded_lenses_round_1.md:1` | Approved Phase 37 spec and recorded prompt-content gate resolution. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_37_expanded_lenses_round_1.md:1` | Active Phase 37 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `tests/unit/test_phase_37_expanded_lenses.py:1` | Added RED/GREEN coverage for Phase 37 executable lens contracts, prompt stages, planner lens/budget models, planner prompt language, executor routing, and audit readback. | Steps 1-5 |
| `src/extractor/contracts/base.py:1` | Added Phase 37 round-one lenses to `LensName` and executor stages to `LLMStage`. | Step 2 |
| `src/extractor/contracts/lens_taxonomy.py:1` | Marked `definition`, `citation`, `temporal`, and `quantity_with_unit` executable while leaving relation/obligation/condition/exception contract-only. | Step 2 |
| `src/extractor/llm/prompts.py:1` | Added Phase 37 executor stages to prompt loading. | Step 2 |
| `prompts/executor/definition.md:1` | Added approved definition-lens executor prompt body. | Step 3 |
| `prompts/executor/citation.md:1` | Added approved citation-lens executor prompt body. | Step 3 |
| `prompts/executor/temporal.md:1` | Added approved temporal-lens executor prompt body. | Step 3 |
| `prompts/executor/quantity_with_unit.md:1` | Added approved quantity-with-unit executor prompt body. | Step 3 |
| `prompts/planner/select_strategy.md:1` | Updated strategy-selection prompt to describe and allow the Phase 37 executable lenses. | Step 4 |
| `prompts/planner/allocate_budget.md:1` | Updated budget prompt to budget Phase 37 executable lenses only when enabled. | Step 4 |
| `tests/unit/test_phase_36_lens_normalization_contracts.py:1` | Updated prior contract-boundary expectations so only remaining planned roles are contract-only after Phase 37. | Step 2 |
| `evals/fixtures/phase_37_lens_roles/source.txt:1` | Added source-role-neutral fixture text covering definition, citation, temporal, and quantity-with-unit spans. | Step 6 |
| `evals/fixtures/phase_37_lens_roles/expected.json:1` | Added strict expected data points with exact source and byte offsets for all four Phase 37 lens roles. | Step 6 |
| `evals/fixtures/phase_37_lens_roles/report.example.json:1` | Added checked-in passing report preserving exact provenance for the Phase 37 fixture. | Step 6 |
| `evals/suites/phase_37_expanded_lenses_round_1.json:1` | Added strict Phase 37 evaluation suite for the new source-role fixture. | Step 6 |
| `tests/unit/test_phase_37_eval_suite.py:1` | Added focused suite test asserting Phase 37 fixture, category, field, metric, and provenance coverage. | Step 6 |
| `prompts/planner/select_strategy.md:1` | Replaced a legal-pack-specific definition example with a source-neutral definition example after final source-neutrality testing. | Step 7 |

---

## Issues

### ISS-001 - Planner prompt contained legal-pack identifier in example
**Status:** RESOLVED | **Severity:** medium | **Found:** Step 7, 2026-05-29
**Files:** `prompts/planner/select_strategy.md:50`
**What is wrong:** `make test` failed the Phase 28 source-neutrality guard because the Phase 37 planner example used `ContractDefinition`, a legal-pack runtime-forbidden identifier.
**How to reproduce:** `python3 -m pytest tests/unit/test_phase28_source_neutrality.py -q`
**Root cause:** The Phase 37 prompt update used a domain-pack-specific schema category as a planner example instead of a source-role-neutral definition category.
**Resolution:** Replaced the example with `DefinedTerm.definition_text or GlossaryEntry.meaning needs definition` and reran source-neutrality and prompt tests.
**Resolved:** 2026-05-29, Step 7

<!--
### ISS-NNN - <short title>
**Status:** <OPEN|RESOLVED|DEFERRED> | **Severity:** high/medium/low | **Found:** Step K, 2026-05-29
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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_37_expanded_lenses_round_1.md docs/boards/README.md docs/boards/phase_37_expanded_lenses_round_1.md` returned no matches; `rg -n "Phase 37|phase_37_expanded_lenses_round_1.md|BOARD OPEN|Step 1|approved|prompt-content gate|Agent-authored" docs/boards/README.md PROGRESS.md docs/specs/phase_37_expanded_lenses_round_1.md docs/boards/phase_37_expanded_lenses_round_1.md`. | PASS | 2026-05-29 |
| 1 | `python3 -m pytest tests/unit/test_phase_37_expanded_lenses.py -q` failed RED with 5 failures covering missing executable lens registry entries, missing prompt stages/files, planner model rejection of new lenses, missing planner prompt language, and executor plan validation rejection for new lenses. | RED verified | 2026-05-29 |
| 2-5 | `python3 -m pytest tests/unit/test_phase_37_expanded_lenses.py -q` passed with 5 passed; `python3 -m pytest tests/unit/test_phase_37_expanded_lenses.py tests/unit/test_phase_36_lens_normalization_contracts.py tests/unit/test_llm_client.py tests/unit/test_prompt_schema_quality.py tests/unit/test_executor.py tests/unit/test_audit_inspection.py tests/unit/test_contracts.py tests/unit/test_planner.py -q` first failed because Phase 36 tests still expected `definition` to be contract-only, then passed with 95 passed after updating those expectations; `make lint` passed; `git diff --check` passed; `wc -l tests/unit/test_phase_37_expanded_lenses.py src/extractor/contracts/base.py src/extractor/contracts/lens_taxonomy.py src/extractor/llm/prompts.py prompts/executor/definition.md prompts/executor/citation.md prompts/executor/temporal.md prompts/executor/quantity_with_unit.md prompts/planner/select_strategy.md prompts/planner/allocate_budget.md` reported 277, 76, 186, 121, 59, 59, 59, 62, 63, and 41 lines. | PASS | 2026-05-29 |
| 6 | `python3 -m pytest tests/unit/test_eval_suites.py -q` failed RED with missing Phase 37 suite manifest; `python3 -m pytest tests/unit/test_phase_37_eval_suite.py tests/unit/test_eval_suites.py tests/unit/test_evals.py -q` passed with 26 passed; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_37_expanded_lenses_round_1.json` passed with 4 expected/actual data points, 4 exact provenance matches, and zero invariant violations; `wc -l tests/unit/test_phase_37_eval_suite.py tests/unit/test_eval_suites.py evals/fixtures/phase_37_lens_roles/source.txt evals/fixtures/phase_37_lens_roles/expected.json evals/fixtures/phase_37_lens_roles/report.example.json evals/suites/phase_37_expanded_lenses_round_1.json` reported 46, 361, 5, 57, 136, and 108 lines. | PASS | 2026-05-29 |
| 7-8 | `make test` first failed on `tests/unit/test_phase28_source_neutrality.py` because `prompts/planner/select_strategy.md` contained `ContractDefinition`; `python3 -m pytest tests/unit/test_phase28_source_neutrality.py -q` reproduced the failure, then passed with 1 passed after the source-neutral prompt fix; `python3 -m pytest tests/unit/test_phase_37_expanded_lenses.py tests/unit/test_prompt_schema_quality.py -q` passed with 16 passed; `make test` passed with 337 passed and 2 skipped; `make lint` passed; `make smoke` passed with 1 passed; `git diff --check` passed; prompt review listed `prompts/executor/citation.md`, `prompts/executor/definition.md`, `prompts/executor/quantity_with_unit.md`, `prompts/executor/temporal.md`, `prompts/planner/allocate_budget.md`, and `prompts/planner/select_strategy.md`; Phase 29, Phase 30, Phase 31 adversarial, Phase 31 mutation, Phase 31 calibration, and Phase 37 eval gates passed. | PASS | 2026-05-29 |

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

### 2026-05-29 - Session 1

- Resumed from the Phase 37 spec draft after the prompt-content gate was resolved by operator continuation.
- Completed: approved the Phase 37 spec for implementation, opened this board, pinned gate interpretations, and updated active phase tracking.
- Completed Step 1: added RED tests for new executable lens contracts, prompt loading, planner lens selection/budgeting, planner prompt coverage, executor routing, and audit readback.
- Completed Step 2: extended executable lens and LLM stage contracts plus the taxonomy registry for definition, citation, temporal, and quantity-with-unit.
- Completed Step 3: added approved executor prompt files for the four new lenses.
- Completed Step 4: updated planner selection and budget prompts for the new executable lenses.
- Completed Step 5: verified the new lenses run through existing executor materialization, normalization metadata, rejection, and audit paths.
- Completed Step 6: added a focused Phase 37 evaluation fixture and suite covering definition, citation, temporal, and quantity-with-unit source roles with strict exact-provenance gates.
- Completed Step 7: ran final project, smoke, lint, prompt-change review, source-neutrality, and Phase 29-31 plus Phase 37 evaluation gates.
- Completed Step 8: filled the final gate and phase summary for operator acceptance.
- Issues found: ISS-001, resolved in Step 7.
- Tests: board-opening and Steps 1-8 verification passed as recorded above.
- Next: operator acceptance of Phase 37. Do not start Phase 38 without explicit operator continuation.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

### What shipped vs spec

- Built as specified: `definition`, `citation`, `temporal`, and `quantity_with_unit` are executable through typed contracts, prompt loading, planner strategy/budget prompts, executor routing, source-span materialization, normalization metadata, rejection paths, LLM audit logging, candidate audit readback, and tests.
- Built as specified: relation, obligation, condition, and exception remain contract-only.
- Built as specified: final Phase 29, Phase 30, Phase 31 adversarial/mutation/calibration, and Phase 37 evaluation gates passed without false positives, false negatives, provenance regressions, or invariant violations.
- Deferred: none for Phase 37.
- Added beyond spec: a dedicated Phase 37 source-role-neutral fixture and strict suite for the four new executable lens roles.

### Lessons for downstream phases

- Runtime prompts are covered by the Phase 28 source-neutrality guard; future prompt examples should prefer generic role names over domain-pack category names unless the prompt is explicitly domain-pack-scoped.
- The shared executor payload schema remained sufficient for the first lower-risk lens expansion, so later semantic lenses can start from the same materialization/audit path but should add their own cross-candidate tests before becoming executable.
