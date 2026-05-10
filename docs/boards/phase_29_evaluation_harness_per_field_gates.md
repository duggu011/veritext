# Phase 29 - Evaluation Harness: Per-Field Gates

## Current Status

Step: 0 of 5
Branch: main
Started: 2026-05-10
Last session: 2026-05-10
Spec: `docs/specs/phase_29_evaluation_harness_per_field_gates.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:13. Evaluation`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 29 approved by the operator on 2026-05-10. Board opened; Step 1 is next after the board-opening commit.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [ ] Step 1: Add category and field metric breakdown contracts and scorer coverage.
- [ ] Step 2: Add provenance and invariant breakdown grouping coverage.
- [ ] Step 3: Add suite manifest contracts, loader, and core suite artifact.
- [ ] Step 4: Add suite scoring, threshold failure reporting, and CLI output.
- [ ] Step 5: Add prompt-neutrality verification and final project verification.

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

- Resumed after operator approved Phase 29 with `continue`.
- Completed: opened this board, pinned Phase 29 open-question resolutions, and updated active phase tracking.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/README.md docs/boards/phase_29_evaluation_harness_per_field_gates.md` returned no matches; `rg -n "Phase 29|phase_29_evaluation_harness_per_field_gates.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/phase_29_evaluation_harness_per_field_gates.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed.
- Next: Step 1 - add category and field metric breakdown contracts and scorer coverage.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: not yet started.
- Deferred: not yet determined.
- Added beyond spec: not yet determined.

### Lessons for downstream phases

- Not yet determined.
