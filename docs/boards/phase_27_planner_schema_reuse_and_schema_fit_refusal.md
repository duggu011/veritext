# Phase 27 - Planner Schema Reuse and Schema-Fit Refusal

## Current Status

Step: 5 of 7
Branch: main
Started: 2026-05-05
Last session: 2026-05-09
Spec: `docs/specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:Improvement Roadmap - Accuracy, Generalization, and Provenance`; `docs/PROJECT_OVERVIEW.md:Planner`; `docs/phase_26_plus_roadmap.md`

Step 5 complete. Planner now applies a typed schema-selection policy, produces structured `PlanningRefusal` payloads for strict no-candidate or below-threshold schema fit, and preserves planner-generated fallback when policy allows it. Next up: Step 6 - propagate refusal through orchestrator, audit, resume, reporter, and CLI.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add schema registry, selection policy, fit assessment, and refusal contracts.
- [x] Step 2: Add config surface for schema registry policy and coverage threshold.
- [x] Step 3: Add schema registry loader validation and hash enforcement.
- [x] Step 4: Add planner approved-schema candidate matching and reuse path.
- [x] Step 5: Add planner schema-fit refusal and fallback policy.
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
- Step 5 schema-fit assessment uses a deterministic coverage proxy from planner document-class confidence rather than adding a new LLM prompt body; this keeps prompt governance unchanged while making strict policy behavior typed and testable. Step 6 may persist this decision or replace it with an audited forced-tool stage if a human-filled prompt is approved.

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
| `src/extractor/config/models.py:1` | Added typed schema-registry policy and minimum coverage threshold config fields. | Step 2 |
| `src/extractor/config/__init__.py:1` | Exported schema coverage threshold type from the config package. | Step 2 |
| `config/default.yaml:1` | Added canonical defaults for schema-registry policy and coverage threshold. | Step 2 |
| `tests/unit/test_config.py:1` | Added config loader, environment override, and strict validation coverage for schema-registry policy fields. | Step 2 |
| `src/extractor/planner/schema_registry.py:1` | Added YAML-only approved schema registry loader with explicit malformed artifact, hash mismatch, duplicate schema ID, and unsupported-entry errors. | Step 3 |
| `src/extractor/planner/__init__.py:1` | Exported the schema registry loader and loader error from the planner package. | Step 3 |
| `src/extractor/orchestrator/service.py:1` | Added startup validation for configured schema registry artifacts before extraction stages run. | Step 3 |
| `tests/unit/test_schema_registry_loader.py:1` | Added registry loader coverage for valid artifacts, missing directories, non-directories, unsupported entries, malformed YAML, hash mismatch, and duplicate schema IDs. | Step 3 |
| `tests/unit/test_orchestrator.py:321` | Added orchestrator coverage proving invalid registry config stops before LLM calls. | Step 3 |
| `docs/boards/phase_27_planner_schema_reuse_and_schema_fit_refusal.md:1` | Updated Step 3 status, references, tests, and work log. | Step 3 |
| `PROGRESS.md:1` | Added Phase 27 Step 3 session log and next-step status. | Step 3 |
| `src/extractor/planner/schema_registry.py:45` | Added deterministic candidate selection by document class and domain hints. | Step 4 |
| `src/extractor/planner/service.py:38` | Added approved registry artifact input and reuse branch that skips schema proposal/critique when exactly one candidate matches. | Step 4 |
| `src/extractor/planner/__init__.py:16` | Exported schema registry candidate selection from the planner package. | Step 4 |
| `src/extractor/orchestrator/service.py:68` | Passed validated registry artifacts into planner creation. | Step 4 |
| `tests/unit/test_schema_registry_loader.py:158` | Added deterministic candidate matching coverage. | Step 4 |
| `tests/unit/test_planner_schema_registry_reuse.py:1` | Added focused planner reuse test proving approved schema metadata/categories are preserved and proposal/critique calls are skipped. | Step 4 |
| `docs/boards/phase_27_planner_schema_reuse_and_schema_fit_refusal.md:1` | Updated Step 4 status, references, tests, and work log. | Step 4 |
| `PROGRESS.md:1` | Added Phase 27 Step 4 session log and next-step status. | Step 4 |
| `src/extractor/planner/schema_fit.py:1` | Added deterministic schema-fit policy decision helper, selection records, structured planner refusal construction, and coverage-threshold assessment. | Step 5 |
| `src/extractor/planner/service.py:42` | Added `PlanningRefusalError`, schema-selection policy input, refusal branching, and policy-aware schema reuse/fallback routing. | Step 5 |
| `src/extractor/planner/__init__.py:18` | Exported `PlanningRefusalError` from the planner package. | Step 5 |
| `tests/unit/test_planner_schema_fit_policy.py:1` | Added planner tests for strict no-candidate refusal, strict below-threshold refusal, and explicit planner-generated fallback. | Step 5 |
| `docs/boards/phase_27_planner_schema_reuse_and_schema_fit_refusal.md:1` | Updated Step 5 status, gate interpretation, references, tests, and work log. | Step 5 |
| `PROGRESS.md:1` | Added Phase 27 Step 5 session log and next-step status. | Step 5 |

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
| 2 | `python3 -m pytest tests/unit/test_config.py -q` first failed on missing/extra `SchemaRegistryConfig` policy fields; `python3 -m pytest tests/unit/test_config.py -q`; `python3 -m py_compile src/extractor/config/__init__.py src/extractor/config/models.py src/extractor/config/loader.py`; `python3 -m pytest tests/unit/test_config.py tests/unit/test_cli.py tests/unit/test_orchestrator.py -q`; `git diff --check` | PASS | 2026-05-05 |
| 3 | `python3 -m pytest tests/unit/test_schema_registry_loader.py -q` first failed on nested registry directories being silently ignored; `python3 -m pytest tests/unit/test_schema_registry_loader.py -q`; `python3 -m py_compile src/extractor/planner/schema_registry.py src/extractor/planner/__init__.py src/extractor/orchestrator/service.py`; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_domain_pack_loader.py tests/unit/test_orchestrator.py -q` first failed in sandbox because `tiktoken` attempted a tokenizer download, then passed with network access; `python3 -m pytest tests/unit/test_config.py tests/unit/test_cli.py tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_domain_pack_loader.py tests/unit/test_orchestrator.py -q`; `git diff --check` | PASS | 2026-05-08 |
| 4 | `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_planner.py -q` first failed with missing `select_schema_registry_candidates`; reran after selector and failed with missing `approved_schema_artifacts` planner input; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_planner.py -q`; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_planner.py tests/unit/test_planner_schema_registry_reuse.py -q`; `python3 -m py_compile src/extractor/planner/schema_registry.py src/extractor/planner/service.py src/extractor/planner/__init__.py src/extractor/orchestrator/service.py tests/unit/test_planner_schema_registry_reuse.py`; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_planner.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_orchestrator.py tests/unit/test_prepare_failed_run_resume.py tests/unit/test_config.py tests/unit/test_cli.py -q`; `git diff --check` | PASS | 2026-05-08 |
| 5 | `python3 -m pytest tests/unit/test_planner_schema_fit_policy.py -q` first failed with `ImportError: cannot import name 'PlanningRefusalError'`; `python3 -m pytest tests/unit/test_planner_schema_fit_policy.py -q`; `python3 -m pytest tests/unit/test_planner_schema_fit_policy.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_planner.py -q`; `python3 -m py_compile src/extractor/planner/schema_fit.py src/extractor/planner/service.py src/extractor/planner/__init__.py tests/unit/test_planner_schema_fit_policy.py`; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_planner.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_planner_schema_fit_policy.py tests/unit/test_orchestrator.py tests/unit/test_prepare_failed_run_resume.py tests/unit/test_config.py tests/unit/test_cli.py -q`; `git diff --check` | PASS | 2026-05-09 |

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

### 2026-05-09 - Session 6

- Resumed at Step 5 after operator confirmation.
- Completed: added a policy-aware planner schema-fit decision helper, deterministic coverage-threshold assessment, structured `PlanningRefusal` construction, `PlanningRefusalError`, and explicit fallback behavior that preserves planner-generated schemas when policy allows fallback.
- Issues found: none.
- Tests: `python3 -m pytest tests/unit/test_planner_schema_fit_policy.py -q` first failed with missing `PlanningRefusalError`; `python3 -m pytest tests/unit/test_planner_schema_fit_policy.py -q` passed; `python3 -m pytest tests/unit/test_planner_schema_fit_policy.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_planner.py -q` passed; `python3 -m py_compile src/extractor/planner/schema_fit.py src/extractor/planner/service.py src/extractor/planner/__init__.py tests/unit/test_planner_schema_fit_policy.py` passed; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_planner.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_planner_schema_fit_policy.py tests/unit/test_orchestrator.py tests/unit/test_prepare_failed_run_resume.py tests/unit/test_config.py tests/unit/test_cli.py -q` passed; `git diff --check` passed.
- Next: Step 6 - propagate refusal through orchestrator, audit, resume, reporter, and CLI.

### 2026-05-08 - Session 5

- Resumed at Step 4 after operator confirmation.
- Completed: added deterministic approved-schema candidate selection by document class and domain hints; added planner reuse path that uses exactly one selected registry artifact, preserves approved schema metadata/categories, skips proposal and critique calls, and continues through strategy and budget stages; wired orchestrator to pass validated registry artifacts into planning.
- Issues found: none.
- Tests: `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_planner.py -q` first failed with missing `select_schema_registry_candidates`; reran after selector and failed with missing `approved_schema_artifacts` planner input; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_planner.py -q` passed; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_planner.py tests/unit/test_planner_schema_registry_reuse.py -q` passed; `python3 -m py_compile src/extractor/planner/schema_registry.py src/extractor/planner/service.py src/extractor/planner/__init__.py src/extractor/orchestrator/service.py tests/unit/test_planner_schema_registry_reuse.py` passed; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_planner.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_orchestrator.py tests/unit/test_prepare_failed_run_resume.py tests/unit/test_config.py tests/unit/test_cli.py -q` passed; `git diff --check` passed.
- Next: Step 5 - add planner schema-fit refusal and fallback policy.

### 2026-05-08 - Session 4

- Resumed at Step 3 after operator confirmation.
- Completed: added the approved schema registry YAML loader, explicit unsupported-entry and duplicate schema ID rejection, canonical schema hash validation through `ApprovedSchemaArtifact`, planner package exports, and orchestrator startup validation that rejects invalid registry config before LLM calls.
- Issues found: none.
- Tests: `python3 -m pytest tests/unit/test_schema_registry_loader.py -q` first failed on nested registry directories being silently ignored; `python3 -m pytest tests/unit/test_schema_registry_loader.py -q` passed; `python3 -m py_compile src/extractor/planner/schema_registry.py src/extractor/planner/__init__.py src/extractor/orchestrator/service.py` passed; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_domain_pack_loader.py tests/unit/test_orchestrator.py -q` first failed in sandbox because `tiktoken` attempted a tokenizer download, then passed with network access; `python3 -m pytest tests/unit/test_config.py tests/unit/test_cli.py tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_domain_pack_loader.py tests/unit/test_orchestrator.py -q` passed; `git diff --check` passed.
- Next: Step 4 - add planner approved-schema candidate matching and reuse path.

### 2026-05-05 - Session 3

- Resumed at Step 2 after operator confirmation.
- Completed: added typed schema-registry config fields for `require_approved_schema` and `minimum_schema_coverage`, canonical defaults in `config/default.yaml`, and environment override/validation coverage.
- Issues found: none.
- Tests: `python3 -m pytest tests/unit/test_config.py -q` first failed on missing/extra `SchemaRegistryConfig` policy fields; `python3 -m pytest tests/unit/test_config.py -q` passed; `python3 -m py_compile src/extractor/config/__init__.py src/extractor/config/models.py src/extractor/config/loader.py` passed; `python3 -m pytest tests/unit/test_config.py tests/unit/test_cli.py tests/unit/test_orchestrator.py -q` passed; `git diff --check` passed.
- Next: Step 3 - add schema registry loader validation and hash enforcement.

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
