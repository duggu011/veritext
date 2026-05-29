# Phase 42 - Static Provenance Artifact

## Current Status

Step: 0 of 8
Branch: main
Started: 2026-05-30
Last session: 2026-05-30
Spec: `docs/specs/phase_42_static_provenance_artifact.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:9. Reporter`; `docs/PROJECT_OVERVIEW.md` highest-leverage item 5; `docs/phase_26_plus_roadmap.md`

Phase 42 opened after operator approval to begin spec work and operator-trust
readiness checks found no open questions, unfinished-work markers, prompt changes, or
scope conflicts with the Phase 41 static-artifact allowance.

Next: Step 1 - add static provenance view contracts and source-context
validation tests.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [ ] Step 1: Add static provenance view contracts and source-context validation tests.
- [ ] Step 2: Implement typed artifact construction from `ExtractionReport`, optional `SignedReportManifest`, optional `RunDiffReport`, and optional audited `Document`/rejections.
- [ ] Step 3: Add deterministic HTML rendering and escaping tests.
- [ ] Step 4: Implement static HTML writing with output hash and byte-length reporting.
- [ ] Step 5: Extend `veritext-report` with the provenance command and CLI tests.
- [ ] Step 6: Add source-neutral acceptance coverage.
- [ ] Step 7: Run final phase gates.
- [ ] Step 8: Fill the Phase 42 summary and stop for operator acceptance.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Scope Phase 42 to deterministic local static provenance artifacts for `report.v2`. | This consumes the Phase 41 allowance without introducing a web UI, server, browser app, REST API, or extraction behavior change. |
| Q2 | Defer refusal and cross-document static artifacts unless the implementation can support them through the same renderer without broadening scope. | Single-document `report.v2` is the highest-value exact-span review surface and avoids mixing multiple report semantics into the first artifact. |
| Q3 | Allow optional inline JavaScript only for deterministic local navigation/toggling, with no data fetching, persistence, network access, or fact computation. | The artifact remains static and auditable while preserving room for basic reviewer ergonomics if useful. |

---

## Gate Interpretations

- Phase 42 may add reporter-side contracts, rendering, file-writing, and CLI support for deterministic static local artifacts.
- Phase 42 must not add a web UI, web server, REST API, dynamic browser app, client-side data fetching, persistent browser/local state, Docker, deployment packaging, vector DB, embeddings, fine-tuning behavior, local model serving, external service, or agent framework.
- Phase 42 must not change prompt bodies, LLM calls, extraction behavior, schema-fit policy, critic/verifier/reconciler behavior, or evaluation thresholds.
- Missing or mismatched provenance must be rendered as explicit warnings, not silently repaired.
- Optional trail inputs such as signed manifests and run diffs must be rendered as present or absent explicitly.
- Evaluation gates are required only if extraction behavior changes, which Phase 42 should avoid.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_42_static_provenance_artifact.md:1` | Approved the Phase 42 spec and recorded static-artifact scope, contracts, gates, and implementation order. | Opening |
| `docs/boards/phase_42_static_provenance_artifact.md:1` | Active Phase 42 board, decisions, gates, references, tests, and handoff tracking. | Opening |
| `docs/boards/README.md:1` | Updated active Phase 42 pointer from pre-board state to approved board/spec. | Opening |
| `PROGRESS.md:1` | Updated current gate and session log for Phase 42 opening. | Opening |

---

## Issues

_(No issues yet.)_

<!--
### ISS-NNN - <short title>
**Status:** <OPEN|RESOLVED|DEFERRED> | **Severity:** high/medium/low | **Found:** Step K, 2026-05-30
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
| Opening | `rg -n "T[B]D\|T[O]DO\|i[m]plement later\|f[i]ll in\|place[h]older\|\\?\\?" docs/specs/phase_42_static_provenance_artifact.md docs/boards/phase_42_static_provenance_artifact.md` returned no matches; `rg -n "Status: dr[a]ft\|Date approved: _\\(\|SPEC DR[A]FT" docs/specs/phase_42_static_provenance_artifact.md docs/boards/phase_42_static_provenance_artifact.md docs/boards/README.md` returned no matches; `git diff --check`; `git diff --exit-code -- prompts`; `wc -l docs/specs/phase_42_static_provenance_artifact.md docs/boards/phase_42_static_provenance_artifact.md docs/boards/README.md PROGRESS.md` reported 314, 142, 192, and 3364 lines. | PASS | 2026-05-30 |

### Final Gate

- [ ] Narrow relevant tests pass
- [ ] `make test` passes when feasible
- [ ] `make lint` passes
- [ ] `make smoke` passes when feasible
- [ ] `git diff --check` passes
- [ ] `git diff --exit-code -- prompts` passes
- [ ] Evaluation gates pass if extraction behavior changes
- [ ] All OPEN issues are resolved or explicitly deferred
- [ ] Phase Summary filled in
- [ ] `PROGRESS.md` updated

---

## Work Log

Reverse chronological. Log every session.

### 2026-05-30 - Opening

- Resumed from Phase 42 not-opened state after operator approval to begin spec work.
- Completed: drafted and approved the Phase 42 spec under operator-trust readiness rules, opened the board, and updated active tracking.
- Issues found: none.
- Tests: opening readiness checks passed as recorded above.
- Next: Step 1 - add static provenance view contracts and source-context validation tests.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: _(pending)_
- Deferred: _(pending)_
- Added beyond spec: _(pending)_

### Lessons for downstream phases

- _(pending)_
