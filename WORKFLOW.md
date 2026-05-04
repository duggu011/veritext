# Veritext Workflow

Board-first process for phased work on Veritext. This file defines how work gets opened, tracked, verified, committed, and handed off.

Where this file conflicts with `AGENTS.md` / `CLAUDE.md`, the agent rules win.

---

## Phase Lifecycle

```text
session start
  |
  v
read docs/boards/README.md
  |
  v
active board exists?
  |
  +-- no --> spec exists?
  |           |
  |           +-- no --> phase-doc mode: write spec from docs/PROJECT_OVERVIEW.md
  |           |
  |           +-- yes --> create board from docs/boards/README.md template
  |
  +-- yes --> implementation mode
                    |
                    v
              pick up next unchecked step
                    |
                    v
              make scoped change
                    |
                    v
              run relevant verification
                    |
                    v
              update board and PROGRESS.md
                    |
                    v
              commit completed step
                    |
                    v
              stop at phase gate and wait for explicit continue
```

---

## Session Start

Every session starts with these reads, in order:

1. `docs/boards/README.md`
2. the active board listed there, if it exists
3. the active phase spec listed by the board, if it exists
4. the relevant roadmap section in `docs/PROJECT_OVERVIEW.md`
5. any OPEN issues on the active board

Then report:

```text
Phase NN, Step K of N. Open issues: N. Next up: <description>. Ready?
```

No implementation work starts until the operator confirms.

If the active board does not exist yet, say that clearly, read this file, and open the phase through phase-doc mode or board creation mode. Do not invent scope from chat alone.

---

## Phase-Doc Mode

Use phase-doc mode when the roadmap identifies the next phase but no approved spec exists.

Output:

```text
docs/specs/phase_NN_<slug>.md
```

Read before writing a spec:

1. `docs/PROJECT_OVERVIEW.md`
2. `docs/boards/README.md`
3. latest completed board
4. `PROGRESS.md`
5. code files the spec will cite

A Veritext phase spec must cover:

- Goal and non-goals
- Domain-scope alignment with `docs/PROJECT_OVERVIEW.md`
- Stage or module boundaries
- Contract changes and Pydantic model changes
- Audit and provenance effects
- Invariant impact, especially I1-I9
- Configuration changes
- Prompt changes, if any
- Tests and evaluation gates
- Implementation order
- Open questions

The spec is not approved until the operator explicitly says it is approved.

---

## Board Creation

Create a board before implementation starts:

```text
docs/boards/phase_NN_<slug>.md
```

Use the template in `docs/boards/README.md`. Populate:

- Current status
- Implementation steps from the approved spec
- Open question resolutions
- Gate interpretations
- References
- Issues
- Tests
- Work log
- Deferred issues

Every issue, decision, and session handoff goes on the board. If it is not on the board, the next session cannot reliably reconstruct it.

---

## Implementation Mode

Before editing code, read:

1. active board
2. approved spec
3. `docs/PROJECT_OVERVIEW.md` domain-scope section if extraction behavior changes
4. every code file the step will touch
5. relevant tests

For each step:

1. Confirm the worktree state.
2. Write the narrowest relevant failing test when behavior changes.
3. Implement the minimal scoped change.
4. Run the narrowest relevant verification.
5. Update board references with changed files.
6. Update board tests with commands and results.
7. Update the board work log.
8. Update `PROGRESS.md` after the session or accepted phase.
9. Commit the completed step.

Do not merge unrelated cleanup into a phase step.

---

## Issue Tracking

Issues live on the active board.

Use this format:

```markdown
### ISS-001 - <short title>
**Status:** OPEN | **Severity:** high/medium/low | **Found:** Step K, YYYY-MM-DD
**Files:** `path/to/file.py:line`
**What is wrong:** <expected vs actual>
**How to reproduce:** <command or scenario>
**Root cause:** _(filled when diagnosed)_
**Resolution:** _(filled when fixed or deferred)_
**Resolved:** _(date + step, or "deferred to Phase NN")_
```

Severity guide:

- High: blocks the phase, threatens invariants, or means the spec may be wrong. Stop and ask.
- Medium: must be resolved before phase completion but does not block the current step.
- Low: non-blocking cleanup or clarity issue.

When an OPEN issue exists at session start, report it before continuing work.

---

## Test Protocol

Run the narrowest relevant tests during development.

Use these project-level commands before closing major work when feasible:

```bash
make test
make lint
make smoke
git diff --check
```

Evaluation work should also run the relevant fixture scorer and record precision, recall, F1, provenance recall, false positives, false negatives, and invariant violations.

No skipped tests are acceptable for final completion unless an approved phase explicitly changes that rule.

---

## Session End

Before ending a session:

1. Update the board Current Status.
2. Add a Work Log entry with what changed, verification, issues, and next step.
3. Update References for every file created or modified.
4. Update Tests with exact commands and results.
5. Update `PROGRESS.md` for the session or accepted phase.
6. Run `git status --short` and `git log --oneline -10`.
7. Commit completed board steps unless the operator explicitly says not to.
8. Tell the operator the next board step.

If a board marks a step DONE, a matching commit must exist or the work must be explicitly handed back as uncommitted.

---

## Commit Discipline

Prefer one commit per completed phase step.

Message format for board-tracked work:

```text
phase-NN(step-K): <short description>
```

Documentation-only bootstrap or design commits may use `docs:` if they are not a board implementation step. Do not force-push or rewrite shared history unless the operator explicitly asks.

---

## Source Of Truth

| Priority | Source | Purpose |
|---|---|---|
| 0 | `AGENTS.md` / `CLAUDE.md` | Agent operating rules. Must stay byte-identical. |
| 1 | `docs/boards/phase_NN_*.md` | Active phase state, issues, references, tests, and work log. |
| 2 | `docs/boards/README.md` | Active phase pointer, roadmap index, and board template. |
| 3 | `WORKFLOW.md` | Process manual. |
| 4 | `docs/PROJECT_OVERVIEW.md` | Roadmap, target domains, non-targets, and market scope. |
| 5 | `PROGRESS.md` | Historical accepted gate and session archive. |
| 6 | `config/default.yaml` | Canonical runtime configuration. |

---

## Roadmap Policy

Future phases are derived from `docs/PROJECT_OVERVIEW.md`, not improvised from individual fixtures or chat context.

Accuracy, generalization, and provenance phases come before deployment-economics phases unless the operator explicitly reorders them. Cost work is valid, but it must not weaken exact span matching, byte/character offsets, audit logging, forced tool use, Pydantic contracts, invariant enforcement, or no-silent-drop rejection accounting.

The current architecture rules ban adding a web UI, REST API, Docker, CI/CD, vector DBs, embeddings, fine-tuning hooks, and agent frameworks. Any future roadmap item that needs one of those capabilities must first amend `AGENTS.md` / `CLAUDE.md` through an explicit approved phase.

---

## Anti-Patterns

- Starting implementation without reading the active board.
- Treating `PROGRESS.md` as the active board.
- Marking a board step done without a matching commit or explicit handoff.
- Adding document-specific patches for one fixture.
- Weakening an invariant to improve a score.
- Making a prompt-body change outside an approved prompt phase.
- Adding runtime tuning values in source or tests.
- Losing provenance fields during transformation.
- Silently dropping rejected candidates.
