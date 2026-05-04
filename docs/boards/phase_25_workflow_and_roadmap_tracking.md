# Phase 25 - Workflow and Roadmap Tracking

## Current Status

Step: 4 of 4 complete
Branch: main
Started: 2026-05-04
Last session: 2026-05-04
Spec: `docs/superpowers/specs/2026-05-04-board-first-workflow-design.md`
Plan: `docs/superpowers/plans/2026-05-04-board-first-workflow.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md`

Phase 25 installed the board-first workflow and made future roadmap tracking explicit. Next active phase is Phase 26, but its spec and board are not opened yet.

---

## Implementation Steps

- [x] Step 1: Write and commit the approved board-first workflow design spec.
- [x] Step 2: Add Veritext-specific `WORKFLOW.md`, `docs/boards/README.md`, and this Phase 25 board.
- [x] Step 3: Make `AGENTS.md` and `CLAUDE.md` byte-identical and board-aware.
- [x] Step 4: Update `PROGRESS.md`, verify links/identity/diff hygiene, and commit the workflow bootstrap.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Keep `PROGRESS.md` as history and make boards primary for active/future tracking. | Preserves the existing accepted phase log while giving future sessions a concise active-state source. |
| Q2 | Make `AGENTS.md` and `CLAUDE.md` byte-identical. | Prevents agent-rule drift across Codex and Claude workflows. |
| Q3 | Derive the future roadmap from `docs/PROJECT_OVERVIEW.md`. | Keeps tracking grounded in the approved overview instead of one-off chat context. |
| Q4 | Renumber workflow bootstrap from Phase 19 to Phase 25. | `PROGRESS.md` already contains historical Phases 19-24, so the board system must start at the next unused phase number. |

---

## Gate Interpretations

No ambiguous gates. This phase is documentation-only.

---

## References

| File | Change | Step |
|---|---|---|
| `docs/superpowers/specs/2026-05-04-board-first-workflow-design.md` | Approved design spec for the board-first workflow. | Step 1 |
| `docs/superpowers/plans/2026-05-04-board-first-workflow.md` | Implementation plan for the workflow bootstrap. | Step 2 |
| `WORKFLOW.md` | Veritext-specific phase, board, issue, test, commit, and session process. | Step 2 |
| `docs/boards/README.md` | Active phase pointer, roadmap index, and board template. | Step 2 |
| `docs/boards/phase_25_workflow_and_roadmap_tracking.md` | Active board for the workflow bootstrap. | Step 2 |
| `AGENTS.md` | Replaced with board-first rules shared with `CLAUDE.md`. | Step 3 |
| `CLAUDE.md` | Replaced with byte-identical board-first rules shared with `AGENTS.md`. | Step 3 |
| `PROGRESS.md` | Updated current gate and added Phase 25 session log. | Step 4 |

---

## Issues

_(No issues.)_

---

## Tests

### Per-Step Results

| Step | Tests | Result | Date |
|---|---|---|---|
| 1 | `rg -n "TBD|TODO|implement later|fill in|placeholder|\\?\\?" docs/superpowers/specs/2026-05-04-board-first-workflow-design.md`; `git diff --check` | PASS | 2026-05-04 |
| 2 | `test -f WORKFLOW.md`; `test -f docs/boards/README.md`; `test -f docs/boards/phase_25_workflow_and_roadmap_tracking.md`; `rg -n "phase_25_workflow_and_roadmap_tracking.md|PROJECT_OVERVIEW.md|WORKFLOW.md" docs/boards/README.md docs/boards/phase_25_workflow_and_roadmap_tracking.md` | PASS | 2026-05-04 |
| 3 | `cmp -s AGENTS.md CLAUDE.md` | PASS | 2026-05-04 |
| 4 | Final verification checklist below. | PASS | 2026-05-04 |

### Final Gate

- [x] `AGENTS.md` and `CLAUDE.md` are byte-identical.
- [x] Active phase and Phase 25 board are linked from `docs/boards/README.md`.
- [x] Phase 25 board references `WORKFLOW.md`, `docs/boards/README.md`, `AGENTS.md`, `CLAUDE.md`, `PROGRESS.md`, and `docs/PROJECT_OVERVIEW.md`.
- [x] `git diff --check` passes.
- [x] `PROGRESS.md` updated.
- [x] No source behavior, prompt, config, or test behavior changed.

---

## Work Log

### 2026-05-04 - Session 1

- Resumed after operator approved the board-first workflow design and said `continue`.
- Completed: workflow design spec, implementation plan, `WORKFLOW.md`, board index, Phase 25 board, byte-identical agent rules, progress log update, and phase-number amendment.
- Issues found: none.
- Tests: documentation verification commands listed above.
- Next: Phase 26 spec and board creation after explicit operator `continue`.

---

## Deferred Issues

_(None.)_

---

## Phase Summary

### What shipped vs spec

- Built as specified: board-first workflow, board index, Phase 25 board, byte-identical agent rules, and progress log handoff.
- Deferred: Phase 26 spec and board creation.
- Added beyond spec: implementation plan file under `docs/superpowers/plans/` per the planning workflow.

### Lessons for downstream phases

- `PROGRESS.md` is now the historical archive; active work starts at `docs/boards/README.md`.
- Phase 26 should open from `docs/PROJECT_OVERVIEW.md` highest-leverage item 1 and the Planner roadmap.
- Any future HTML provenance viewer work requires an explicit architecture-rule review before implementation because current agent rules still prohibit adding a web UI.
