# Phase 37 - Expanded Lenses Round 1

## Current Status

Step: 1 of 8
Branch: main
Started: 2026-05-29
Last session: 2026-05-29
Spec: `docs/specs/phase_37_expanded_lenses_round_1.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:4. Executor`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 37 opened after operator continuation resolved the prompt-content gate by authorizing agent-authored prompt bodies and planner prompt updates for this phase.

Next: Step 1 - add RED tests for the expanded executable lens contract boundary, prompt loader stage list, planner lens selection, executor call routing, and audit readback.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [ ] Step 1: Add RED tests for the new executable lens contract boundary, prompt loader stage list, planner lens selection, executor call routing, and audit readback.
- [ ] Step 2: Extend `LensName`, `LLMStage`, `PROMPT_STAGES`, and the lens taxonomy registry for `definition`, `citation`, `temporal`, and `quantity_with_unit`.
- [ ] Step 3: Add approved executor prompt files for `definition`, `citation`, `temporal`, and `quantity_with_unit`.
- [ ] Step 4: Update planner strategy and budget prompts so live planning can select and budget the new executable lenses.
- [ ] Step 5: Run new lenses through existing executor materialization, normalization metadata, rejection, and audit paths.
- [ ] Step 6: Add focused fixture or evaluation coverage for source-role-neutral recall improvement without fixture-specific source patches.
- [ ] Step 7: Run final project, smoke, lint, prompt-change review, and evaluation gates.
- [ ] Step 8: Fill the board summary and stop for operator acceptance.

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

---

## Issues

_(No issues yet.)_

<!--
### ISS-001 - <short title>
**Status:** OPEN | **Severity:** high/medium/low | **Found:** Step K, 2026-05-29
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

### 2026-05-29 - Session 1

- Resumed from the Phase 37 spec draft after the prompt-content gate was resolved by operator continuation.
- Completed: approved the Phase 37 spec for implementation, opened this board, pinned gate interpretations, and updated active phase tracking.
- Issues found: none.
- Tests: board-opening verification passed as recorded above.
- Next: Step 1 - add RED tests for the expanded executable lens contract boundary, prompt loader stage list, planner lens selection, executor call routing, and audit readback.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: pending.
- Deferred: pending.
- Added beyond spec: pending.

### Lessons for downstream phases

- Pending.
