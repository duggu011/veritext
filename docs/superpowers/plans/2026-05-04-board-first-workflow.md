# Board-First Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install a Veritext-native board-first workflow and make future roadmap tracking explicit.

**Architecture:** Documentation-only workflow bootstrap. `AGENTS.md` and `CLAUDE.md` become byte-identical operating rules; `WORKFLOW.md` defines the process; `docs/boards/README.md` points at the active board; `docs/boards/phase_25_workflow_and_roadmap_tracking.md` tracks this bootstrap and the next handoff.

**Tech Stack:** Markdown documentation, existing git workflow, no source-code changes.

---

## File Structure

- Modify: `AGENTS.md` and `CLAUDE.md` with identical board-first agent rules.
- Create: `WORKFLOW.md` with Veritext-specific phase, board, issue, test, and commit process.
- Create: `docs/boards/README.md` with active phase, roadmap index, and reusable board template.
- Create: `docs/boards/phase_25_workflow_and_roadmap_tracking.md` with Phase 25 status, steps, references, tests, and work log.
- Modify: `PROGRESS.md` with a new current-gate entry for workflow bootstrap.

## Task 1: Install Workflow Docs

**Files:**
- Create: `WORKFLOW.md`
- Create: `docs/boards/README.md`
- Create: `docs/boards/phase_25_workflow_and_roadmap_tracking.md`

- [x] **Step 1: Write workflow docs**

Add Veritext-specific board-first docs. Required content:

```text
WORKFLOW.md:
- phase lifecycle
- session start
- session end
- board creation
- issue tracking
- test protocol
- commit discipline
- source-of-truth hierarchy
- roadmap source in docs/PROJECT_OVERVIEW.md

docs/boards/README.md:
- exactly one active phase
- future roadmap index derived from docs/PROJECT_OVERVIEW.md
- board template

docs/boards/phase_25_workflow_and_roadmap_tracking.md:
- active status for Phase 25
- implementation checklist
- references to workflow files
- tests and verification checklist
- current work log
```

- [x] **Step 2: Verify links and required references**

Run:

```bash
test -f WORKFLOW.md
test -f docs/boards/README.md
test -f docs/boards/phase_25_workflow_and_roadmap_tracking.md
rg -n "phase_25_workflow_and_roadmap_tracking.md|PROJECT_OVERVIEW.md|WORKFLOW.md" docs/boards/README.md docs/boards/phase_25_workflow_and_roadmap_tracking.md
```

Expected: all files exist and `rg` returns references to the active board, roadmap source, and workflow manual.

## Task 2: Align Agent Rules

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

- [x] **Step 1: Replace both files with identical rules**

Rules must include:

```text
- AGENTS.md and CLAUDE.md must stay byte-identical.
- Read docs/boards/README.md, active board, and active spec/roadmap source at session start.
- Report phase, step, open issues, and next action before work.
- Update board, references, tests, work log, git status, and progress at session end.
- Preserve Veritext mission, domain scope, architecture rules, invariants, configuration, prompt rules, testing, and auditability.
```

- [x] **Step 2: Verify byte identity**

Run:

```bash
cmp -s AGENTS.md CLAUDE.md
```

Expected: exit code `0`.

## Task 3: Update Progress Log

**Files:**
- Modify: `PROGRESS.md`

- [x] **Step 1: Add workflow bootstrap current gate and session log**

Update the top of `PROGRESS.md` to make Phase 25 board tracking the current gate while preserving historical entries.

Required content:

```text
Last completed phase: LLM provider adapter boundary
Current phase: Phase 25 - Workflow and Roadmap Tracking
Current status: board-first workflow bootstrap in progress
Next required work: use docs/boards/README.md and the active board for future sessions
```

- [x] **Step 2: Verify progress references**

Run:

```bash
sed -n '1,40p' PROGRESS.md
```

Expected: top gate mentions Phase 25 and board-first tracking.

## Task 4: Final Verification And Commit

**Files:**
- Verify all changed documentation files.

- [x] **Step 1: Run verification**

Run:

```bash
cmp -s AGENTS.md CLAUDE.md
test -f WORKFLOW.md
test -f docs/boards/README.md
test -f docs/boards/phase_25_workflow_and_roadmap_tracking.md
rg -n "Phase 25|Workflow and Roadmap Tracking|docs/PROJECT_OVERVIEW.md" docs/boards/README.md docs/boards/phase_25_workflow_and_roadmap_tracking.md PROGRESS.md
git diff --check
```

Expected: all commands pass.

- [x] **Step 2: Commit workflow bootstrap**

Run:

```bash
git add AGENTS.md CLAUDE.md WORKFLOW.md docs/boards/README.md docs/boards/phase_25_workflow_and_roadmap_tracking.md PROGRESS.md docs/superpowers/plans/2026-05-04-board-first-workflow.md
git commit -m "phase-25(step-4): add board-first workflow tracking"
```

Expected: commit succeeds with only documentation changes.
