# Phase 27 - Planner Schema Reuse and Schema-Fit Refusal

## Current Status

Step: 1 of 7
Branch: main
Started: 2026-05-05
Last session: 2026-05-05
Spec: `docs/specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:Improvement Roadmap - Accuracy, Generalization, and Provenance`; `docs/PROJECT_OVERVIEW.md:Planner`; `docs/phase_26_plus_roadmap.md`

Step 1 complete. Schema registry, selection policy, fit assessment, and refusal contracts are in place and verified. Next up: Step 2 - add config surface for schema registry policy and coverage threshold.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add schema registry, selection policy, fit assessment, and refusal contracts.
- [ ] Step 2: Add config surface for schema registry policy and coverage threshold.
- [ ] Step 3: Add schema registry loader validation and hash enforcement.
- [ ] Step 4: Add planner approved-schema candidate matching and reuse path.
- [ ] Step 5: Add planner schema-fit refusal and fallback policy.
- [ ] Step 6: Propagate refusal through orchestrator, audit, resume, reporter, and CLI.
- [ ] Step 7: Run final verification, update board and `PROGRESS.md`, and commit/handoff cleanly.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Treat the Phase 27 registry as read-only approved input; do not write planner-generated schemas as proposed artifacts. | Automatic writeback changes governance and approval semantics. Proposed-schema queues can be added in a later governance phase. |
| Q2 | Default `require_approved_schema` to `false`; strict refusal only activates when explicitly configured. | Preserves existing local and smoke behavior unless a test or operator enables approved-schema policy. |
| Q3 | Use a separate strict refusal report contract while leaving successful extraction reports at `report.v2` unless implementation proves a union is cleaner. | Avoids unnecessary churn in successful report consumers while keeping refusal machine-readable. |
| Q4 | Keep full reusable approved schemas in the schema registry for Phase 27; do not extend domain-pack templates to carry full categories yet. | Phase 28 can prove domain-pack category templates with a legal pack after registry reuse/refusal is stable. |

---

## Gate Interpretations

- "Terminal refusal" means a strict audited outcome distinct from `failed` and `completed`; the preferred implementation is a `refused` run status unless audit migration constraints require an equivalent strict outcome model.
- "Approved schema reuse" means the `ExtractionPlan.approved_categories` are materialized from a validated registry artifact without planner mutation of category or field semantics.
- "Fallback remains decision-equivalent" means with `require_approved_schema: false` and no matching registry artifact, existing planner propose/critique, strategy, budget, executor, critic, verifier, reconciler, and reporter decisions remain equivalent except for added policy metadata.
- "Coverage threshold" applies only to schema-fit assessment; it must not relax source-span validation, candidate category validation, or data-point provenance rules.
- "Invalid registry artifacts fail explicitly" applies before extraction stages beyond startup validation. A missing optional registry directory must not break default local runs.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md:1` | Approved Phase 27 spec. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_27_planner_schema_reuse_and_schema_fit_refusal.md:1` | Active Phase 27 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `src/extractor/contracts/schema_registry.py:1` | Added strict approved-schema artifact, selection policy, coverage estimate, fit assessment, schema selection, and planning-refusal contracts. | Step 1 |
| `src/extractor/contracts/schema_metadata.py:1` | Added `schema_registry` to schema source kinds for approved registry artifacts. | Step 1 |
| `src/extractor/contracts/__init__.py:1` | Exported Phase 27 schema registry/refusal contracts from the public contracts package. | Step 1 |
| `tests/unit/test_schema_registry_contracts.py:1` | Added TDD coverage for registry artifact hash validation, strict policy bounds, fit-assessment reason requirements, schema selection consistency, and refusal consistency. | Step 1 |

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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md docs/boards/phase_27_planner_schema_reuse_and_schema_fit_refusal.md`; `rg -n "phase_27_planner_schema_reuse_and_schema_fit_refusal.md|approved|BOARD OPEN" docs/boards/README.md PROGRESS.md docs/specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md`; `cmp -s AGENTS.md CLAUDE.md` | PASS | 2026-05-05 |
| 1 | `python3 -m pytest tests/unit/test_schema_registry_contracts.py -q` first failed with `ImportError: cannot import name 'ApprovedSchemaArtifact'`; `python3 -m pytest tests/unit/test_schema_registry_contracts.py -q`; `python3 -m pytest tests/unit/test_schema_registry_contracts.py tests/unit/test_schema_metadata.py tests/unit/test_contracts.py -q`; `python3 -m py_compile src/extractor/contracts/__init__.py src/extractor/contracts/base.py src/extractor/contracts/models.py src/extractor/contracts/schema_metadata.py src/extractor/contracts/schema_registry.py`; `python3 -m pytest tests/unit/test_planner.py tests/unit/test_domain_pack_loader.py -q`; `git diff --check` | PASS | 2026-05-05 |

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

### 2026-05-05 - Session 2

- Resumed at Step 1 after operator confirmation.
- Completed: added strict Phase 27 contracts for approved schema registry artifacts, schema selection policy, schema coverage estimates, schema-fit assessments, schema selection records, and planner refusal records; added `schema_registry` as a schema source kind; exported the new contracts.
- Issues found: none.
- Tests: `python3 -m pytest tests/unit/test_schema_registry_contracts.py -q` first failed with `ImportError: cannot import name 'ApprovedSchemaArtifact'`; `python3 -m pytest tests/unit/test_schema_registry_contracts.py -q` passed; `python3 -m pytest tests/unit/test_schema_registry_contracts.py tests/unit/test_schema_metadata.py tests/unit/test_contracts.py -q` passed; `python3 -m py_compile src/extractor/contracts/__init__.py src/extractor/contracts/base.py src/extractor/contracts/models.py src/extractor/contracts/schema_metadata.py src/extractor/contracts/schema_registry.py` passed; `python3 -m pytest tests/unit/test_planner.py tests/unit/test_domain_pack_loader.py -q` passed; `git diff --check` passed.
- Next: Step 2 - add config surface for schema registry policy and coverage threshold.

### 2026-05-05 - Session 1

- Resumed after operator approved the Phase 27 spec.
- Completed: opened this board, pinned Phase 27 implementation open-question resolutions, and updated tracking references.
- Issues found: none.
- Tests: board-opening documentation checks listed above.
- Next: Step 1 - add schema registry, selection policy, fit assessment, and refusal contracts.

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
