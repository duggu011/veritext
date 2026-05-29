# Phase 36 - Lens Taxonomy and Normalization Contracts

## Current Status

Step: 1 of 6
Branch: main
Started: 2026-05-29
Last session: 2026-05-29
Spec: `docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:4. Executor`; `docs/PROJECT_OVERVIEW.md:5. Dedup`; `docs/PROJECT_OVERVIEW.md:8. Reconciler`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 36 opened under operator-trust resume mode after spec-readiness checks found no open questions, unresolved draft markers outside board-template text, architecture-rule changes, invariant risk, or unclear gate interpretations.

Next: Step 1 - Add lens taxonomy and normalization contract tests, including legacy audit payload readability and executable-vs-contract-only lens validation.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [ ] Step 1: Add lens taxonomy and normalization contract tests, including legacy audit payload readability and executable-vs-contract-only lens validation.
- [ ] Step 2: Add focused Pydantic taxonomy and normalization modules plus public exports.
- [ ] Step 3: Extend `LensCandidate` and `DataPoint` additively with verbatim/canonical value metadata and validation.
- [ ] Step 4: Populate candidate normalization metadata during server-side materialization without changing executor prompt bodies or tool payload requirements.
- [ ] Step 5: Carry normalization metadata through reconciler materialization, audit readback, and compact inspection output while preserving ID-only reconciler behavior.
- [ ] Step 6: Run final project, smoke, lint, prompt-neutrality, and evaluation gates; fill the board summary and stop for operator acceptance.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Planned lens roles are contract-only in Phase 36 unless already executable. | Prevents prompt/stage expansion before Phase 37 while making future roles auditable. |
| Q2 | Existing `value` remains a compatibility field. | Keeps old audit payloads and downstream consumers readable while adding verbatim/canonical fields. |
| Q3 | Verbatim and canonical values are separate. | Auditors need source-facing values; downstream tooling needs canonical comparison values. |
| Q4 | Canonical values are metadata and do not create source spans. | Preserves exact span provenance and prevents normalized strings from claiming source bytes. |
| Q5 | Unsupported normalization fails explicitly. | Prevents silent invention of canonical values and preserves no-silent-drop behavior. |

---

## Gate Interpretations

- Phase 36 may add focused contract modules under `src/extractor/contracts/` and optional metadata fields on schema/domain-pack contracts.
- Phase 36 may extend `LensCandidate` and `DataPoint` additively with defaults or compatibility validators.
- Phase 36 must preserve the existing four executable lenses and must not schedule planned-only lenses through executor runtime.
- Phase 36 must not change executor prompt bodies, add new executor prompt files, or require the LLM to emit new candidate payload fields.
- Phase 36 must not change dedup keys, conflict behavior, cross-document reconciliation, reporter formats, or architecture rules.
- Existing audit payload JSON for candidates and data points must remain readable.
- Prompt-neutrality verification is required before Phase 36 completion.
- If normalization metadata changes report JSON or audit inspection output, record before/after payload shape and extraction metrics on this board.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md:1` | Approved Phase 36 spec. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_36_lens_taxonomy_and_normalization_contracts.md:1` | Active Phase 36 board. | Board opening |
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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md docs/boards/README.md docs/boards/phase_36_lens_taxonomy_and_normalization_contracts.md`; `rg -n "Phase 36|phase_36_lens_taxonomy_and_normalization_contracts.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md docs/boards/phase_36_lens_taxonomy_and_normalization_contracts.md`; `cmp -s AGENTS.md CLAUDE.md` returned `1` because of pre-existing local `AGENTS.md` drift unrelated to this phase. | PASS with noted unrelated drift | 2026-05-29 |

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

- Resumed from the Phase 36 spec draft under operator-trust resume mode.
- Completed: approved the Phase 36 spec for implementation, opened this board, pinned gate interpretations, and updated active phase tracking.
- Issues found: none for board opening.
- Tests: board-opening verification passed as recorded above, with the known unrelated `AGENTS.md`/`CLAUDE.md` drift preserved outside this phase.
- Next: Step 1 - add lens taxonomy and normalization contract tests, including legacy audit payload readability and executable-vs-contract-only lens validation.

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
