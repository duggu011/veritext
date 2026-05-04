# Board-First Workflow Design

## Goal

Create a Veritext-native board-first workflow, modeled on the Emergence project but adapted to Veritext's extraction, audit, invariant, and roadmap discipline.

## Context

Veritext currently tracks historical work in `PROGRESS.md` and agent rules in `AGENTS.md` / `CLAUDE.md`. Future planning lives in `docs/PROJECT_OVERVIEW.md`, especially the accuracy, generalization, provenance, target-domain, and cost-reduction sections.

Emergence uses a stronger operational loop:

- `WORKFLOW.md` defines the process.
- `docs/boards/README.md` identifies the active phase and board template.
- `docs/boards/phase_NN.md` tracks current status, issues, references, tests, and work logs.
- `AGENTS.md` and `CLAUDE.md` stay byte-identical so agents follow the same rules.

## Source Of Truth

Veritext will use this hierarchy:

| Priority | Source | Purpose |
|---|---|---|
| 0 | `AGENTS.md` / `CLAUDE.md` | Agent operating rules; must stay byte-identical. |
| 1 | `docs/boards/phase_NN_*.md` | Active phase state, issues, references, test log, session log. |
| 2 | `docs/boards/README.md` | Active phase pointer, roadmap index, board template. |
| 3 | `WORKFLOW.md` | Process for creating specs, boards, implementation steps, and session handoff. |
| 4 | `docs/PROJECT_OVERVIEW.md` | Product/roadmap source for future phases and domain scope. |
| 5 | `PROGRESS.md` | Historical phase/session log and accepted gate archive. |
| 6 | `config/default.yaml` | Canonical runtime configuration. |

## Workflow Shape

Every session starts by reading:

1. `docs/boards/README.md`
2. the active board listed there
3. the active spec or roadmap source referenced by the board
4. any OPEN issues on the active board

Agents then report the current phase, current step, number of open issues, and next action before starting work. Work should not begin until the user confirms.

Every session ends by updating the active board:

- Current status
- Work log
- References for changed files
- Test/verification results
- Issues and deferred work

If a board marks a step as done, a matching commit should exist before the session is closed unless the user explicitly asks not to commit.

## Board System

Add:

- `WORKFLOW.md`
- `docs/boards/README.md`
- `docs/boards/phase_19_workflow_and_roadmap_tracking.md`

Phase 19 is a bootstrap phase that installs the board-first workflow itself. Future phases should be opened one at a time from the roadmap index.

## Future Roadmap Mapping

The roadmap index should preserve Phases 0-18 as implemented historical work and start future tracking at Phase 19:

| Phase | Name | Source |
|---|---|---|
| 19 | Workflow and Roadmap Tracking | Current workflow bootstrap. |
| 20 | Domain Packs, Schema Registry, and Schema-Fit Refusal | `docs/PROJECT_OVERVIEW.md` highest-leverage item 1 and Planner roadmap. |
| 21 | Diverse Evaluation Fixture Suite | Highest-leverage item 2 and Evaluation roadmap. |
| 22 | Boundary-Preserving PDF, DOCX, and Email Ingestion | Highest-leverage item 3 and Ingestion roadmap. |
| 23 | Expanded Lenses and Normalization Policy | Highest-leverage item 4, Executor, Dedup, and Reconciler roadmap. |
| 24 | Provenance Viewer, Run Diffs, and Signed Reports | Highest-leverage item 5 and Reporter/Audit roadmap. |
| 25 | Cost Observability and Stage Model Comparison | Cost observability prerequisite and tiered-model caution. |
| 26+ | Deployment-Economics Track | Batch APIs, confidence-gated critic, sampled verifier, provider routing, and local models. |

## Constraints

- Do not weaken extraction invariants I1-I9.
- Do not make workflow rules Emergence-specific.
- Keep `PROGRESS.md` as history; do not bulk-migrate it into boards.
- Keep future phase descriptions grounded in `docs/PROJECT_OVERVIEW.md`.
- Keep source files and workflow docs concise enough for agents to read at session start.

## Implementation Scope

The implementation should be documentation-only:

- Rewrite `AGENTS.md` and `CLAUDE.md` to be byte-identical and board-aware.
- Add `WORKFLOW.md`.
- Add `docs/boards/README.md`.
- Open the Phase 19 board.
- Update `PROGRESS.md` with the workflow-bootstrap session.

No source behavior, prompts, configs, tests, or extraction logic should change in this phase.

## Verification

Verification should confirm:

- `AGENTS.md` and `CLAUDE.md` are byte-identical.
- The active board link in `docs/boards/README.md` points to an existing file.
- The Phase 19 board references `WORKFLOW.md`, `docs/boards/README.md`, `AGENTS.md`, `CLAUDE.md`, `PROGRESS.md`, and `docs/PROJECT_OVERVIEW.md`.
- `git diff --check` passes.
