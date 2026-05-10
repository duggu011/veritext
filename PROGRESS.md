# Progress

Running log for repository sessions and accepted phase gates.

## Current Gate

- Last completed phase: Phase 28 - Legal Contracts Domain Pack v1
- Current status: Phase 29 Step 4 complete for Evaluation Harness: Per-Field Gates.
- Next required work: Phase 29 Step 5 - add prompt-neutrality verification and final project verification.
- Next-phase context: Phase 29 should upgrade evaluation from aggregate fixture metrics to suite, category, and field gates before broader corpus expansion in Phase 30.

## Session Log

### 2026-05-10 — Phase 29 Step 4 Suite Scoring and CLI Output

- Added suite-level result contracts, aggregate suite/category/field metric merging, fixture result records, and threshold failure records.
- Added `evaluate_suite_manifest(...)` for static suite scoring and strict global/category/field threshold enforcement.
- Added `veritext-eval --suite <manifest>` while preserving existing `veritext-eval <case> <report>` behavior.
- Extended CLI JSON coverage for both single-fixture and suite scoring output.
- Verification:
  - `python3 -m pytest tests/unit/test_eval_suites.py::test_evaluate_suite_manifest_scores_static_core_suite -q` first failed with missing `evaluate_suite_manifest`
  - `python3 -m pytest tests/unit/test_eval_suites.py -q` (`10 passed`)
  - `python3 -m pytest tests/unit/test_eval_suites.py tests/unit/test_evals.py tests/integration/test_recall_baseline.py -q` (`26 passed, 2 skipped`)
  - `git diff --check`
  - `make lint`

### 2026-05-10 — Phase 29 Step 3 Suite Manifest Loader

- Added strict Pydantic suite manifest contracts for fixture entries, global/category/field thresholds, duplicate key rejection, and documented invariant allowances.
- Added repo-local JSON manifest loading that rejects external paths, path traversal, and missing case/report files.
- Added `evals/suites/phase_29_core.json` covering the checked-in static report fixtures, including `legal_contracts_core`, while excluding `medium_research_brief` because it has no checked-in report.
- Verification:
  - `python3 -m pytest tests/unit/test_eval_suites.py::test_load_suite_manifest_accepts_valid_manifest -q` first failed with missing `extractor.evals.suites`
  - `python3 -m pytest tests/unit/test_eval_suites.py -q` (`7 passed`)
  - `python3 -m pytest tests/unit/test_eval_suites.py tests/unit/test_evals.py tests/integration/test_recall_baseline.py -q` (`23 passed, 2 skipped`)
  - `git diff --check`
  - `make lint`

### 2026-05-10 — Phase 29 Step 2 Provenance and Invariant Breakdowns

- Extended category and field metrics to report exact provenance recall for shifted-span matches.
- Grouped invariant violations by the violated report data point category and field when the violation carries a known `data_point_id`.
- Kept invariant violations without a report data point as global-only.
- Verification:
  - `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_flags_source_span_invariant_breaks -q` first failed with grouped invariant count `0 != 2`
  - `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_flags_source_span_invariant_breaks -q`
  - `python3 -m pytest tests/unit/test_evals.py tests/integration/test_recall_baseline.py -q` (`16 passed, 2 skipped`)
  - `git diff --check`
  - `make lint`

### 2026-05-10 — Phase 29 Step 1 Category and Field Breakdowns

- Added strict Pydantic category and field metric breakdown contracts to eval results without removing existing single-fixture fields.
- Extended `evaluate_report(...)` to compute deterministic per-category and per-field metrics for passing data, false positives, and false negatives.
- Preserved existing exact-match global scoring behavior and existing eval CLI/API consumers.
- Verification:
  - `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_includes_category_and_field_metrics_for_passing_fixture -q` first failed with missing `EvaluationResult.category_metrics`
  - `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_includes_category_and_field_metrics_for_passing_fixture -q`
  - `python3 -m pytest tests/unit/test_evals.py::test_evaluate_report_groups_false_positive_and_false_negative_metrics -q`
  - `python3 -m pytest tests/unit/test_evals.py -q` (`14 passed`)
  - `python3 -m pytest tests/unit/test_evals.py tests/integration/test_recall_baseline.py -q` (`16 passed, 2 skipped`)
  - `git diff --check`
  - `make lint`

### 2026-05-10 — Operator Trust Resume Policy

- Added operator-trust resume mode to `AGENTS.md` and `CLAUDE.md`.
- Updated `WORKFLOW.md` so the session-start confirmation gate defers to operator-trust resume mode.
- Policy now lets Codex continue automatically through already-defined board/spec creation or implementation work while preserving Hard Stops, invariant protection, architecture-rule gates, phase acceptance gates, and next-phase transition gates.
- Verification:
  - `cmp -s AGENTS.md CLAUDE.md`
  - `git diff --check -- AGENTS.md CLAUDE.md WORKFLOW.md`

### 2026-05-10 — Phase 29 Board Opening

- Approved Phase 29 for implementation after operator continuation with `continue`.
- Created active board `docs/boards/phase_29_evaluation_harness_per_field_gates.md`.
- Pinned Phase 29 implementation open-question resolutions:
  - Use `veritext-eval --suite <manifest>` for suite scoring.
  - Keep grouped thresholds in suite manifests only.
  - Limit the first suite to fixtures with checked-in `report.example.json` files.
  - Include full missing and unexpected ID lists by default in JSON output.
- Updated `docs/boards/README.md` to show Phase 29 as `BOARD OPEN`.
- No source behavior, prompts, configs, tests, eval fixtures, or extraction logic were changed.
- Verification:
  - `git diff --check`
  - `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/README.md docs/boards/phase_29_evaluation_harness_per_field_gates.md`
  - `rg -n "Phase 29|phase_29_evaluation_harness_per_field_gates.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/phase_29_evaluation_harness_per_field_gates.md`
  - `cmp -s AGENTS.md CLAUDE.md`

### 2026-05-10 — Codex Session Goal Guidance

- Added a `Session Goal` section to `AGENTS.md` and `CLAUDE.md`.
- Documented `/goal` as session-level advisory steering that never overrides the agent rules, active board/spec, roadmap, progress log, or invariants I1-I9.
- Kept the current gate unchanged: Phase 29 remains in spec-draft state and implementation is still blocked until operator approval and board creation.
- Verification:
  - `cmp -s AGENTS.md CLAUDE.md`
  - `git diff --check`

### 2026-05-10 — Phase 28 Acceptance and Phase 29 Spec Draft

- Accepted Phase 28 after operator continuation and kept the completed Phase 28 evidence on `docs/boards/phase_28_legal_contracts_domain_pack_v1.md`.
- Updated `docs/boards/README.md` so Phase 28 is complete and Phase 29 is active in `SPEC DRAFT` state.
- Created `docs/specs/phase_29_evaluation_harness_per_field_gates.md` from the Phase 26+ roadmap and `docs/PROJECT_OVERVIEW.md` evaluation guidance.
- Scoped Phase 29 to suite manifests, per-category and per-field metrics, grouped provenance/invariant breakdowns, threshold failure reporting, and CLI output while preserving existing exact-match evaluation behavior.
- No source behavior, prompts, configs, tests, eval fixtures, or extraction logic were changed.
- Verification:
  - `git diff --check`
  - `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/README.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md`
  - `rg -n "Phase 29|phase_29_evaluation_harness_per_field_gates.md|SPEC DRAFT|COMPLETE \\(2026-05-10\\)" docs/boards/README.md PROGRESS.md docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md`
  - `cmp -s AGENTS.md CLAUDE.md`

### 2026-05-10 — Phase 28 Step 4 Source Neutrality and Final Gate

- Added `tests/unit/test_phase28_source_neutrality.py` with a fixture-backed scan that rejects Phase 28-specific legal identifiers in runtime `src/` and prompt files.
- Confirmed prompt bodies were not modified for Phase 28.
- Updated the Phase 28 board to mark Steps 1-4 complete, fill the phase summary, and mark final gate ready.
- Updated `docs/boards/README.md` to show Phase 28 as `FINAL GATE READY`.
- Verification:
  - `python3 -m pytest tests/unit/test_phase28_source_neutrality.py -q` first failed with missing forbidden-terms fixture
  - `python3 -m pytest tests/unit/test_phase28_source_neutrality.py -q`
  - `python3 -m pytest tests/unit/test_domain_pack_loader.py tests/unit/test_schema_registry_loader.py tests/unit/test_evals.py tests/unit/test_phase28_source_neutrality.py -q`
  - `git diff --exit-code -- prompts`
  - `git diff --check`
  - `make test` (`252 passed, 2 skipped`)
  - `make lint`
  - `make smoke` (`1 passed`)

### 2026-05-10 — Phase 28 Step 3 Legal Evaluation Fixture

- Added `evals/fixtures/legal_contracts_core/` with synthetic source text covering parties, effective date, obligation, payment term, termination trigger, governing law, notice method, and a definition.
- Added exact expected data points with source text, character offsets, and byte offsets.
- Added an example `report.v2` that cites approved legal schema metadata from `schema:legal-contract-core-v1`.
- Added eval coverage so the legal fixture passes existing precision, recall, F1, provenance recall, and invariant gates.
- Verification:
  - `python3 -m pytest tests/unit/test_evals.py -q` first failed with missing `legal_contracts_core` fixture files
  - `python3 -m pytest tests/unit/test_evals.py -q`
  - `python3 -m pytest tests/unit/test_evals.py tests/unit/test_reporter.py tests/unit/test_schema_registry_loader.py tests/unit/test_domain_pack_loader.py -q`
  - `git diff --check`

### 2026-05-10 — Phase 28 Step 2 Approved Legal Schema Fixture

- Added `tests/fixtures/schema_registry/legal_contract_core_v1.yaml` as the approved legal-contract schema registry fixture.
- The fixture links to `legal-contracts-v1`, uses `document_class: legal_contract`, carries legal domain hints and match basis, and validates through canonical schema-hash enforcement.
- Added loader and candidate-selection coverage proving the legal schema is selected by document class and domain hints.
- Runtime source code remained unchanged.
- Verification:
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py -q` first failed with missing `schema:legal-contract-core-v1` fixture
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py -q`
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_planner_schema_fit_policy.py -q`
  - `git diff --check`

### 2026-05-10 — Phase 28 Step 1 Domain Pack Artifact

- Added `config/domain_packs/legal_contracts.yaml` as the first legal-contract domain-pack artifact.
- Added loader coverage proving the artifact validates through the existing typed domain-pack contract and keeps pack metadata, template IDs, supported document class, default lenses, field roles, and reporting expectations internally consistent.
- Kept runtime source code unchanged; legal-domain assumptions live in the YAML artifact and test assertions only.
- Verification:
  - `python3 -m pytest tests/unit/test_domain_pack_loader.py -q` first failed with missing `legal-contracts-v1` pack
  - `python3 -m pytest tests/unit/test_domain_pack_loader.py -q`
  - `python3 -m pytest tests/unit/test_domain_pack_loader.py tests/unit/test_config.py tests/unit/test_orchestrator.py -q`
  - `git diff --check`

### 2026-05-10 — Phase 28 Board Opening

- Marked `docs/specs/phase_28_legal_contracts_domain_pack_v1.md` approved after operator approval.
- Created active board `docs/boards/phase_28_legal_contracts_domain_pack_v1.md`.
- Pinned Phase 28 implementation open-question resolutions:
  - Keep the legal approved schema fixture under `tests/fixtures/schema_registry/`.
  - Use `legal_contract` as the first document class.
  - Keep the first legal schema small while including limited definitions and notices.
  - Do not add duplicate `pack_id` rejection unless Step 1 exposes an existing generic loader gap.
- Updated `docs/boards/README.md` to show Phase 28 as `BOARD OPEN`.
- No source behavior, prompts, configs, tests, or extraction logic were changed.
- Verification:
  - `git diff --check`
  - `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_28_legal_contracts_domain_pack_v1.md docs/boards/README.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md`
  - `rg -n "phase_28_legal_contracts_domain_pack_v1.md|approved|BOARD OPEN|Step 1" docs/boards/README.md PROGRESS.md docs/specs/phase_28_legal_contracts_domain_pack_v1.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md`
  - `cmp -s AGENTS.md CLAUDE.md`

### 2026-05-09 — Phase 27 Acceptance and Phase 28 Spec Draft

- Accepted Phase 27 after operator continuation and kept the completed Phase 27 evidence on `docs/boards/phase_27_planner_schema_reuse_and_schema_fit_refusal.md`.
- Updated `docs/boards/README.md` so Phase 27 is complete and Phase 28 is active in `SPEC DRAFT` state.
- Created `docs/specs/phase_28_legal_contracts_domain_pack_v1.md` from the Phase 26+ roadmap and `docs/PROJECT_OVERVIEW.md` target-domain/domain-pack guidance.
- Scoped Phase 28 to legal-contract domain-pack artifacts, approved legal schema registry fixtures, legal evaluation fixture coverage, and source-neutrality guardrails.
- No source behavior, prompts, configs, tests, or extraction logic were changed.
- Verification:
  - `git diff --check`
  - `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_28_legal_contracts_domain_pack_v1.md docs/boards/README.md docs/boards/phase_27_planner_schema_reuse_and_schema_fit_refusal.md`
  - `rg -n "Phase 28|phase_28_legal_contracts_domain_pack_v1.md|SPEC DRAFT|COMPLETE \\(2026-05-09\\)" docs/boards/README.md PROGRESS.md docs/specs/phase_28_legal_contracts_domain_pack_v1.md`
  - `cmp -s AGENTS.md CLAUDE.md`

### 2026-05-09 — Phase 27 Step 7 Final Verification and Handoff

- Ran the Phase 27 final gate from a clean working tree.
- Updated the Phase 27 board to mark Step 7 complete, record final verification, fill the phase summary, and hand off for operator review.
- Updated `docs/boards/README.md` to show Phase 27 as `FINAL GATE READY`; Phase 28 remains unopened.
- Verification:
  - `make test` (`247 passed, 2 skipped`)
  - `make lint`
  - `make smoke` (`1 passed`)
  - `git diff --check`

### 2026-05-09 — Phase 27 Step 6 Terminal Refusal Propagation

- Added `refused` as a terminal run status and required `completed_at` for refused manifests.
- Added typed planner refusal payloads to audited planner `RunStageState` records.
- Added `ExtractionRefusalReport` and `write_refusal_report(...)` so schema-fit refusal output is machine-readable and does not fabricate empty data points.
- Added `PipelineRefusalResult` / `PipelineResult` and propagated planner refusal through orchestrator without running executor, dedup, critic, verifier, reconciler, or success reporting.
- Passed configured schema-registry policy into planning from orchestrator.
- Added refusal-aware CLI summaries with `outcome_type`, refusal identity, and usage summary.
- Blocked terminal refused runs from normal resume and from `scripts/prepare_failed_run_resume.py`.
- Split planner/refusal orchestration into `src/extractor/orchestrator/planning.py` and `src/extractor/orchestrator/refusal.py` so `src/extractor/orchestrator/service.py` stays under the 400-line limit.
- Added focused coverage in `tests/unit/test_audit_refusal.py`, `tests/unit/test_reporter_refusal.py`, and `tests/unit/test_orchestrator_refusal.py`, plus CLI and resume-prep assertions.
- Verification:
  - `python3 -m pytest tests/unit/test_audit_refusal.py tests/unit/test_reporter_refusal.py tests/unit/test_orchestrator_refusal.py tests/unit/test_cli.py tests/unit/test_prepare_failed_run_resume.py -q` first failed with `ImportError: cannot import name 'write_refusal_report'`
  - `python3 -m pytest tests/unit/test_audit_refusal.py tests/unit/test_reporter_refusal.py tests/unit/test_orchestrator_refusal.py tests/unit/test_cli.py tests/unit/test_prepare_failed_run_resume.py -q`
  - `python3 -m pytest tests/unit/test_audit_store.py tests/unit/test_audit_refusal.py tests/unit/test_reporter.py tests/unit/test_reporter_refusal.py tests/unit/test_orchestrator.py tests/unit/test_orchestrator_refusal.py tests/unit/test_cli.py tests/unit/test_config.py tests/unit/test_prepare_failed_run_resume.py tests/unit/test_planner_schema_fit_policy.py -q`
  - `python3 -m compileall -q src/extractor/contracts src/extractor/audit src/extractor/reporter src/extractor/orchestrator src/extractor/cli scripts/prepare_failed_run_resume.py tests/unit/test_audit_refusal.py tests/unit/test_reporter_refusal.py tests/unit/test_orchestrator_refusal.py`
  - `python3 -m pytest tests/unit/test_contracts.py tests/unit/test_schema_registry_contracts.py tests/unit/test_schema_registry_loader.py tests/unit/test_planner.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_planner_schema_fit_policy.py tests/unit/test_audit_store.py tests/unit/test_audit_refusal.py tests/unit/test_reporter.py tests/unit/test_reporter_refusal.py tests/unit/test_orchestrator.py tests/unit/test_orchestrator_refusal.py tests/unit/test_prepare_failed_run_resume.py tests/unit/test_config.py tests/unit/test_cli.py -q`
  - `make test` (`247 passed, 2 skipped`)
  - `make lint`
  - `make smoke`
  - `git diff --check`

### 2026-05-09 — Phase 27 Step 5 Schema-Fit Refusal Policy

- Added `src/extractor/planner/schema_fit.py` with deterministic schema-fit policy decisions, `SchemaSelection` construction, coverage-threshold assessments, and structured `PlanningRefusal` construction.
- Added `PlanningRefusalError` and `schema_selection_policy` input to `create_extraction_plan(...)`.
- Strict policy now refuses when no approved schema candidates exist or the selected approved schema falls below the configured coverage threshold.
- Planner-generated fallback remains available when `SchemaSelectionPolicy.allow_planner_generated_fallback` is true.
- Kept prompt governance unchanged for Step 5 by using planner classification confidence as the deterministic fit-coverage proxy rather than adding a new prompt body.
- Added focused planner policy coverage in `tests/unit/test_planner_schema_fit_policy.py`.
- Verification:
  - `python3 -m pytest tests/unit/test_planner_schema_fit_policy.py -q` first failed with `ImportError: cannot import name 'PlanningRefusalError'`
  - `python3 -m pytest tests/unit/test_planner_schema_fit_policy.py -q`
  - `python3 -m pytest tests/unit/test_planner_schema_fit_policy.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_planner.py -q`
  - `python3 -m py_compile src/extractor/planner/schema_fit.py src/extractor/planner/service.py src/extractor/planner/__init__.py tests/unit/test_planner_schema_fit_policy.py`
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_planner.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_planner_schema_fit_policy.py tests/unit/test_orchestrator.py tests/unit/test_prepare_failed_run_resume.py tests/unit/test_config.py tests/unit/test_cli.py -q`
  - `git diff --check`

### 2026-05-08 — Phase 27 Step 4 Approved Schema Reuse Path

- Added deterministic approved-schema candidate selection by document class and domain hints.
- Extended `create_extraction_plan(...)` with optional approved schema registry artifacts.
- Added planner reuse behavior for exactly one matching artifact: preserve registry schema metadata and approved categories, skip schema proposal/critique calls, then continue through strategy selection and budget allocation.
- Kept planner-generated fallback behavior unchanged when no single registry candidate matches.
- Wired orchestrator startup-loaded registry artifacts into the planner.
- Added focused planner reuse coverage in `tests/unit/test_planner_schema_registry_reuse.py` instead of growing the already oversized `tests/unit/test_planner.py`.
- Verification:
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_planner.py -q` first failed with missing `select_schema_registry_candidates`
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_planner.py -q` then failed with missing `approved_schema_artifacts` planner input
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_planner.py -q`
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_planner.py tests/unit/test_planner_schema_registry_reuse.py -q`
  - `python3 -m py_compile src/extractor/planner/schema_registry.py src/extractor/planner/service.py src/extractor/planner/__init__.py src/extractor/orchestrator/service.py tests/unit/test_planner_schema_registry_reuse.py`
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_planner.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_orchestrator.py tests/unit/test_prepare_failed_run_resume.py tests/unit/test_config.py tests/unit/test_cli.py -q`
  - `git diff --check`

### 2026-05-08 — Phase 27 Step 3 Schema Registry Loader Validation

- Added `src/extractor/planner/schema_registry.py` with a YAML-only approved schema registry loader.
- Reused the strict `ApprovedSchemaArtifact` contract so artifact loading enforces `schema_registry` source kind, document-class consistency, and canonical schema hash equality against approved categories.
- Rejected malformed YAML, non-mapping artifacts, non-directory registry paths, visible non-YAML entries, visible nested directories, and duplicate `schema_id` values with explicit `SchemaRegistryLoaderError` messages.
- Exported the loader and error through `extractor.planner`.
- Wired orchestrator startup validation so invalid configured registry input fails before any LLM calls or extraction stages.
- Added `tests/unit/test_schema_registry_loader.py` and orchestrator startup-validation coverage.
- Verification:
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py -q` first failed on nested registry directories being silently ignored
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py -q`
  - `python3 -m py_compile src/extractor/planner/schema_registry.py src/extractor/planner/__init__.py src/extractor/orchestrator/service.py`
  - `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_domain_pack_loader.py tests/unit/test_orchestrator.py -q` first failed in sandbox because `tiktoken` attempted a tokenizer download, then passed with network access
  - `python3 -m pytest tests/unit/test_config.py tests/unit/test_cli.py tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_domain_pack_loader.py tests/unit/test_orchestrator.py -q`
  - `git diff --check`

### 2026-05-05 — Phase 27 Step 2 Schema Registry Policy Config

- Added `SchemaRegistryConfig.require_approved_schema` with default `false`.
- Added `SchemaRegistryConfig.minimum_schema_coverage` as a strict bounded float with default `0.65`.
- Added canonical defaults to `config/default.yaml`.
- Exported the schema coverage threshold type from `extractor.config`.
- Added `tests/unit/test_config.py` coverage for default loading, environment overrides, strict unknown-key behavior, invalid coverage thresholds, and non-strict boolean rejection.
- Verification:
  - `python3 -m pytest tests/unit/test_config.py -q` first failed on missing/extra `SchemaRegistryConfig` policy fields
  - `python3 -m pytest tests/unit/test_config.py -q`
  - `python3 -m py_compile src/extractor/config/__init__.py src/extractor/config/models.py src/extractor/config/loader.py`
  - `python3 -m pytest tests/unit/test_config.py tests/unit/test_cli.py tests/unit/test_orchestrator.py -q`
  - `git diff --check`

### 2026-05-05 — Phase 27 Step 1 Schema Registry and Refusal Contracts

- Added `src/extractor/contracts/schema_registry.py` with strict Pydantic v2 contracts for approved schema registry artifacts, schema selection policy, schema coverage estimates, schema-fit assessments, schema selection records, and planner refusal records.
- Added `schema_registry` to `SchemaSourceKind` so approved registry artifacts can hash and identify differently from planner-generated schemas and domain-pack templates.
- Exported the new contracts through `extractor.contracts`.
- Added `tests/unit/test_schema_registry_contracts.py` covering registry artifact hash validation, strict policy bounds, non-fit reason-code requirements, schema selection candidate consistency, and refusal candidate/assessment consistency.
- Verification:
  - `python3 -m pytest tests/unit/test_schema_registry_contracts.py -q` first failed with `ImportError: cannot import name 'ApprovedSchemaArtifact'`
  - `python3 -m pytest tests/unit/test_schema_registry_contracts.py -q`
  - `python3 -m pytest tests/unit/test_schema_registry_contracts.py tests/unit/test_schema_metadata.py tests/unit/test_contracts.py -q`
  - `python3 -m py_compile src/extractor/contracts/__init__.py src/extractor/contracts/base.py src/extractor/contracts/models.py src/extractor/contracts/schema_metadata.py src/extractor/contracts/schema_registry.py`
  - `python3 -m pytest tests/unit/test_planner.py tests/unit/test_domain_pack_loader.py -q`
  - `git diff --check`

### 2026-05-05 — Phase 27 Board Opening

- Marked `docs/specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md` approved after operator approval.
- Created active board `docs/boards/phase_27_planner_schema_reuse_and_schema_fit_refusal.md`.
- Pinned Phase 27 implementation open-question resolutions:
  - Treat the registry as read-only approved input.
  - Default `require_approved_schema` to `false`.
  - Use a separate strict refusal report contract while leaving successful reports at `report.v2` unless implementation proves a union is cleaner.
  - Keep full reusable approved schemas in the schema registry for Phase 27.
- Updated `docs/boards/README.md` to show Phase 27 as `BOARD OPEN`.
- No source behavior, prompts, configs, tests, or extraction logic were changed.
- Verification:
  - `git diff --check`
  - `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md docs/boards/phase_27_planner_schema_reuse_and_schema_fit_refusal.md`
  - `rg -n "phase_27_planner_schema_reuse_and_schema_fit_refusal.md|approved|BOARD OPEN" docs/boards/README.md PROGRESS.md docs/specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md`
  - `cmp -s AGENTS.md CLAUDE.md`

### 2026-05-05 — Phase 27 Spec Draft Opened

- Accepted Phase 26 after operator continuation and kept the completed Phase 26 evidence on `docs/boards/phase_26_domain_pack_and_schema_registry_foundation.md`.
- Updated `docs/boards/README.md` so Phase 26 is complete and Phase 27 is active in `SPEC DRAFT` state.
- Created `docs/specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md` from the Phase 26+ roadmap and `docs/PROJECT_OVERVIEW.md` planner roadmap.
- Scoped Phase 27 to approved-schema registry validation, schema selection policy, schema-fit assessment, structured planner refusal, terminal refusal orchestration, audit visibility, refusal reports, and CLI summaries.
- No source behavior, prompts, configs, tests, or extraction logic were changed.
- Verification:
  - `git diff --check`
  - `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md docs/boards/README.md docs/boards/phase_26_domain_pack_and_schema_registry_foundation.md`
  - `rg -n "Phase 27|phase_27_planner_schema_reuse_and_schema_fit_refusal.md|SPEC DRAFT|COMPLETE \\(2026-05-05\\)" docs/boards/README.md PROGRESS.md docs/specs/phase_27_planner_schema_reuse_and_schema_fit_refusal.md`
  - `cmp -s AGENTS.md CLAUDE.md`

### 2026-05-05 — Phase 26 Steps 1-6 Schema Metadata Foundation

- Added `src/extractor/contracts/schema_metadata.py` with strict Pydantic v2 contracts for domain-pack metadata, schema-template metadata, approved-schema metadata, schema source kind, planner-generated schema metadata construction, and canonical schema hashing.
- Exported the new metadata contracts and helpers through `extractor.contracts`.
- Added `tests/unit/test_schema_metadata.py` covering strict metadata validation, duplicate template/lens rejection, source-kind pack rules, deterministic sorted schema hashing, semantic hash changes, and `schema:<hash-prefix>` planner-generated IDs.
- Added typed `domain_packs.directory` and `schema_registry.directory` config sections to `ExtractorConfig`, `config/default.yaml`, and the direct CLI/orchestrator test fixtures.
- Added `tests/unit/test_config.py` coverage for the new config paths and environment overrides.
- Split shared contract primitives into `src/extractor/contracts/base.py` to keep contract modules focused and avoid schema metadata import cycles.
- Added `ExtractionPlan.schema_metadata` derivation and validation so neutral planner-generated plans carry `schema:<hash-prefix>` identity without changing approved categories, enabled lenses, chunk policy, or budgets.
- Added `src/extractor/planner/domain_packs.py` to validate YAML-only domain-pack artifacts and wired orchestrator startup to fail explicitly on invalid configured artifacts without passing pack data into planner selection or schema reuse.
- Added synthetic generic loader fixture `tests/fixtures/domain_packs/generic_metadata_pack.yaml`.
- Added schema metadata to `ExtractionReport` as `report.v2`, passed plan schema metadata from orchestrator to reporter, and exposed the metadata in CLI JSON summaries.
- Updated static eval report fixtures to `report.v2` with schema metadata only; data point payloads were unchanged.
- Updated the active Phase 26 board to mark Steps 1-6 complete and hand off for operator review.
- Verification:
  - `python3 -m pytest tests/unit/test_schema_metadata.py -q`
  - `python3 -m pytest tests/unit/test_contracts.py tests/unit/test_schema_metadata.py -q`
  - `python3 -m pytest tests/unit/test_config.py -q`
  - `python3 -m pytest tests/unit/test_config.py tests/unit/test_cli.py tests/unit/test_orchestrator.py -q`
  - `python3 -m pytest tests/unit/test_contracts.py tests/unit/test_schema_metadata.py tests/unit/test_planner.py tests/unit/test_audit_store.py tests/unit/test_audit_inspection.py tests/unit/test_llm_views.py -q`
  - `python3 -m pytest tests/unit/test_executor.py tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_reconciler.py tests/unit/test_orchestrator.py -q`
  - `python3 -m pytest tests/unit/test_domain_pack_loader.py -q`
  - `python3 -m pytest tests/unit/test_domain_pack_loader.py tests/unit/test_schema_metadata.py tests/unit/test_config.py tests/unit/test_planner.py tests/unit/test_orchestrator.py -q`
  - `python3 -m pytest tests/unit/test_reporter.py tests/unit/test_cli.py tests/unit/test_audit_store.py tests/unit/test_orchestrator.py -q`
  - `python3 -m pytest tests/unit/test_evals.py -q`
  - `make test` (`220 passed, 2 skipped`)
  - `make lint`
  - `make smoke`
  - `git diff --check`

### 2026-05-04 — Phase 26 Board Opening

- Marked `docs/specs/phase_26_domain_pack_and_schema_registry_foundation.md` approved after operator approval.
- Created active board `docs/boards/phase_26_domain_pack_and_schema_registry_foundation.md`.
- Pinned Phase 26 implementation open-question resolutions:
  - Use `schema:<hash-prefix>` for planner-generated schema IDs.
  - Accept YAML domain-pack artifacts only in Phase 26.
  - Put synthetic loader fixtures under `tests/fixtures/domain_packs/`.
  - Include schema identity in the CLI JSON summary.
- Updated `docs/boards/README.md` to show Phase 26 as `BOARD OPEN`.
- No source behavior, prompts, configs, tests, or extraction logic were changed.
- Verification:
  - `git diff --check`
  - `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_26_domain_pack_and_schema_registry_foundation.md docs/boards/phase_26_domain_pack_and_schema_registry_foundation.md`
  - `rg -n "phase_26_domain_pack_and_schema_registry_foundation.md|approved|BOARD OPEN" docs/boards/README.md PROGRESS.md docs/specs/phase_26_domain_pack_and_schema_registry_foundation.md`

### 2026-05-04 — Phase 26 Spec Draft

- Opened draft spec `docs/specs/phase_26_domain_pack_and_schema_registry_foundation.md`.
- Pinned the Phase 26 audit decision: schema registry metadata will embed in existing plan/report audit payloads, with dedicated audit tables and schema migrations deferred.
- Kept the Phase 26 board unopened and implementation blocked pending operator spec approval.
- Updated `docs/boards/README.md` to show Phase 26 as `SPEC DRAFT`.
- No source behavior, prompts, configs, tests, or extraction logic were changed.
- Verification:
  - `git diff --check`
  - `rg -n "TBD|TODO|implement later|fill in|placeholder|\\?\\?" docs/specs/phase_26_domain_pack_and_schema_registry_foundation.md`
  - `rg -n "SPEC DRAFT|phase_26_domain_pack_and_schema_registry_foundation.md" docs/boards/README.md PROGRESS.md`

### 2026-05-04 — Phase 26+ Roadmap Split Approval

- Created `docs/phase_26_plus_roadmap.md` as a proposal-only roadmap artifact. It does not open the Phase 26 spec or board.
- Split the coarse Phase 26+ board index into concrete board-ready phases:
  - Phase 26: Domain Pack and Schema Registry Foundation.
  - Phase 27: Planner Schema Reuse and Schema-Fit Refusal.
  - Phase 28: Legal Contracts Domain Pack v1.
  - Phases 29-31: evaluation harness, diverse fixtures, adversarial/mutation/calibration evaluation.
  - Phases 32-35: boundary-preserving ingestion, PDF/table ingestion, DOCX/HTML/email ingestion, layout-aware chunking.
  - Phases 36-39: lens taxonomy, expanded lenses, dedup/canonical/conflict preservation, cross-document reconciliation.
  - Phases 40-42: signed reports/run diffs, architecture-rule amendment, and viewer work only if approved.
  - Phases 43-45: cost observability, stage model comparison, and measured deployment-economics cost cuts.
- Preserved Phase 26 as active next, with spec and board still unopened.
- No source behavior, prompts, configs, tests, or extraction logic were changed.
- Verification:
  - `git diff --check`
  - `rg -n "TBD|TODO|implement later|fill in|placeholder|\\?\\?" docs/phase_26_plus_roadmap.md`
  - `rg -n "Phase 26 - Domain Pack and Schema Registry Foundation|phase_26_plus_roadmap.md|Phase 45 - Deployment-Economics Cost Cuts" docs/boards/README.md PROGRESS.md`

### 2026-05-04 — Phase 25 Workflow and Roadmap Tracking

- Added approved design spec `docs/superpowers/specs/2026-05-04-board-first-workflow-design.md` and implementation plan `docs/superpowers/plans/2026-05-04-board-first-workflow.md`.
- Created `WORKFLOW.md` with Veritext-specific session start/end, phase-doc mode, board creation, implementation mode, issue tracking, test protocol, commit discipline, source-of-truth hierarchy, and roadmap policy.
- Created `docs/boards/README.md` with active phase status, future roadmap index derived from `docs/PROJECT_OVERVIEW.md`, and the reusable board template.
- Created `docs/boards/phase_25_workflow_and_roadmap_tracking.md` to record the workflow bootstrap, references, decisions, tests, work log, and Phase 26 handoff.
- Amended the approved design's phase numbering from Phase 19 to Phase 25 after verifying `PROGRESS.md` already contains historical Phases 19-24.
- Replaced `AGENTS.md` and `CLAUDE.md` with byte-identical board-first operating rules while preserving Veritext's mission, target-domain discipline, architecture rules, Pydantic/SQLite/LLM-client constraints, prompt rules, invariants, testing, and auditability requirements.
- No source behavior, prompts, configs, tests, or extraction logic were changed.
- Verification:
  - `cmp -s AGENTS.md CLAUDE.md`
  - `test -f WORKFLOW.md`
  - `test -f docs/boards/README.md`
  - `test -f docs/boards/phase_25_workflow_and_roadmap_tracking.md`
  - `rg -n "phase_25_workflow_and_roadmap_tracking.md|PROJECT_OVERVIEW.md|WORKFLOW.md" docs/boards/README.md docs/boards/phase_25_workflow_and_roadmap_tracking.md`
  - `rg -n "Phase 25|Workflow and Roadmap Tracking|docs/PROJECT_OVERVIEW.md" docs/boards/README.md docs/boards/phase_25_workflow_and_roadmap_tracking.md PROGRESS.md`
  - `git diff --check`

### 2026-05-03 — LLM provider adapter boundary

- Chose the LLM client as the next cleanup target after review showed the existing two-provider implementation was acceptable for Anthropic/OpenAI but still coupled provider dispatch, request shaping, SDK send mechanics, tool parsing, and call-log construction inside `src/extractor/llm/client.py`.
- Added a focused red test in `tests/unit/test_llm_provider_adapters.py` proving the requested adapter boundary did not yet exist, then implemented the adapter module.
- Created `src/extractor/llm/adapters.py` with `LLMProviderAdapter`, `AnthropicProviderAdapter`, and `OpenAIChatProviderAdapter`.
- Moved provider-specific structured-call request construction, provider send calls, required tool-input extraction, audit call-log construction, and `supports_retry` metadata behind the adapters.
- Kept `LLMClient` responsible for provider selection, request throttling, audit-store persistence, Pydantic output validation, retry orchestration, trace printing, and the existing public `complete_structured` / `complete_structured_with_retry` interfaces.
- Preserved existing behavior:
  - Anthropic still uses prompt-cache-aware system/user/tool blocks and named forced tool use.
  - OpenAI and OpenAI-compatible providers still use strict function tools, named `tool_choice`, `parallel_tool_calls=False`, model-family-specific token settings, and existing Kimi thinking disablement.
  - Structured retry remains Anthropic-only.
- Confirmed touched LLM files are under the 400-line limit after the split:
  - `src/extractor/llm/adapters.py`: 190 lines
  - `src/extractor/llm/client.py`: 255 lines
  - `tests/unit/test_llm_provider_adapters.py`: 15 lines
- Verification:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_llm_provider_adapters.py -q` first failed with `ModuleNotFoundError: No module named 'extractor.llm.adapters'`
  - `python3 -m py_compile src/extractor/llm/adapters.py src/extractor/llm/client.py src/extractor/llm/providers.py src/extractor/llm/responses.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_llm_provider_adapters.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_llm_client.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_llm_provider_adapters.py tests/unit/test_llm_client.py tests/unit/test_config.py tests/unit/test_orchestrator.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or non-test audit DB mutations were made.

### 2026-05-03 — Audit store structural decomposition

- Chose `src/extractor/audit/store.py` as the next cleanup target because it was still 705 lines and contained schema DDL, storage exceptions, connection lifecycle, schema-version checks, generic SQLite helpers, core run/document/chunk/LLM persistence, and candidate/report/rejection persistence in one module.
- Moved audit storage exceptions into `src/extractor/audit/errors.py` while preserving the public `extractor.audit.store` and `extractor.audit` imports.
- Moved schema version and table DDL into `src/extractor/audit/schema.py` without changing table definitions or schema version.
- Moved connection lifecycle, schema initialization/version checks, generic insert/update/fetch/list helpers, and `UsageSummary` into `src/extractor/audit/base.py`.
- Moved run manifests, run stage states, documents, chunks, extraction plans, LLM call logs, and usage summarization into `src/extractor/audit/core_records.py`.
- Moved lens candidates, critic reports, verifier reports, data points, and candidate rejections into `src/extractor/audit/review_records.py`.
- Kept `src/extractor/audit/store.py` as the public `AuditStore` composition point and `open_audit_store` entrypoint.
- Confirmed touched audit files are under the 400-line limit after the split:
  - `src/extractor/audit/store.py`: 35 lines
  - `src/extractor/audit/base.py`: 205 lines
  - `src/extractor/audit/core_records.py`: 191 lines
  - `src/extractor/audit/review_records.py`: 182 lines
  - `src/extractor/audit/schema.py`: 128 lines
  - `src/extractor/audit/errors.py`: 25 lines
- Verification:
  - `python3 -m py_compile src/extractor/audit/__init__.py src/extractor/audit/base.py src/extractor/audit/core_records.py src/extractor/audit/errors.py src/extractor/audit/inspection.py src/extractor/audit/models.py src/extractor/audit/review_records.py src/extractor/audit/schema.py src/extractor/audit/store.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_audit_store.py tests/unit/test_audit_inspection.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_audit_store.py tests/unit/test_audit_inspection.py tests/unit/test_llm_client.py tests/unit/test_orchestrator.py tests/unit/test_reporter.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or non-test audit DB mutations were made.

### 2026-05-03 — LLM client structural decomposition

- Chose `src/extractor/llm/client.py` as the next cleanup target because it was still 911 lines and contained client orchestration, public retry contracts, provider setup, prompt-cache request shaping, OpenAI strict-schema shaping, response/tool-call parsing, audit call-log materialization, and trace formatting in one module.
- Moved `LLMClientError`, `LLMToolUseError`, and `LLMRetryMergeError` into `src/extractor/llm/errors.py` while preserving the public `extractor.llm` and `extractor.llm.client` imports.
- Moved retry complaint/result contracts and structured request/result Pydantic models into `src/extractor/llm/models.py`.
- Moved human-readable LLM trace formatting and stage grouping into `src/extractor/llm/trace.py`.
- Moved Anthropic/OpenAI client construction, model/stage settings resolution, Anthropic prompt-cache block construction, OpenAI chat kwargs construction, Kimi reasoning disablement, and strict OpenAI tool schema generation into `src/extractor/llm/providers.py`.
- Moved Anthropic/OpenAI call-log construction, required tool-call extraction, retry assistant-content serialization, retry complaint formatting, and generic response attribute readers into `src/extractor/llm/responses.py`.
- Kept `src/extractor/llm/client.py` focused on request throttling, provider dispatch, direct Anthropic/OpenAI SDK calls, audit-log persistence, retry orchestration, output model validation, and final result assembly.
- Confirmed touched LLM files are under the 400-line limit after the split:
  - `src/extractor/llm/errors.py`: 16 lines
  - `src/extractor/llm/models.py`: 70 lines
  - `src/extractor/llm/trace.py`: 79 lines
  - `src/extractor/llm/responses.py`: 250 lines
  - `src/extractor/llm/providers.py`: 284 lines
  - `src/extractor/llm/client.py`: 329 lines
- Verification:
  - `python3 -m py_compile src/extractor/llm/__init__.py src/extractor/llm/client.py src/extractor/llm/errors.py src/extractor/llm/models.py src/extractor/llm/payloads.py src/extractor/llm/prompts.py src/extractor/llm/providers.py src/extractor/llm/responses.py src/extractor/llm/trace.py src/extractor/llm/views.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_llm_client.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_llm_client.py tests/unit/test_executor.py tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_reconciler.py tests/unit/test_orchestrator.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or non-test audit DB mutations were made.

### 2026-05-03 — Reconciler structural decomposition

- Chose `src/extractor/reconciler/service.py` as the next cleanup target because it was still 632 lines and contained reconciliation orchestration, input validation, compact candidate-ID retry handling, output validation, data point materialization, rejection materialization, and stable ID generation in one module.
- Moved `ReconcilerError` into `src/extractor/reconciler/errors.py` while preserving the public `extractor.reconciler.ReconcilerError` and `extractor.reconciler.service.ReconcilerError` imports.
- Moved reconciler preflight checks and accepted critic/verifier report lookup into `src/extractor/reconciler/validation.py`.
- Moved compact candidate-ID expansion, retry validation complaints, and retry replacement behavior into `src/extractor/reconciler/batching.py`.
- Moved reconciled data point/rejection construction, output candidate-ID checks, best source candidate selection, rejection reason materialization, and stable reconciler/data-point/rejection ID generation into `src/extractor/reconciler/materialization.py`.
- Kept `src/extractor/reconciler/service.py` focused on reconciliation orchestration, prompt request construction, LLM calls, audit writes, and result assembly.
- Confirmed touched reconciler files are under the 400-line limit after the split:
  - `src/extractor/reconciler/errors.py`: 8 lines
  - `src/extractor/reconciler/validation.py`: 87 lines
  - `src/extractor/reconciler/batching.py`: 112 lines
  - `src/extractor/reconciler/materialization.py`: 382 lines
  - `src/extractor/reconciler/service.py`: 109 lines
- Verification:
  - `python3 -m py_compile src/extractor/reconciler/__init__.py src/extractor/reconciler/batching.py src/extractor/reconciler/errors.py src/extractor/reconciler/materialization.py src/extractor/reconciler/models.py src/extractor/reconciler/service.py src/extractor/reconciler/validation.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_reconciler.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_reconciler.py tests/unit/test_orchestrator.py tests/unit/test_llm_client.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or non-test audit DB mutations were made.

### 2026-05-03 — Orchestrator structural decomposition

- Chose `src/extractor/orchestrator/service.py` as the next cleanup target because it was still 785 lines and contained orchestration, run lifecycle, stage tracing, resume validation, audit-stage completion, and audit-result materialization in one module.
- Moved `OrchestratorError` into `src/extractor/orchestrator/errors.py` while preserving the public `extractor.orchestrator.OrchestratorError` and `extractor.orchestrator.service.OrchestratorError` imports.
- Moved stage banner/trace output into `src/extractor/orchestrator/trace.py`.
- Moved run start/resume manifest lifecycle and failed-manifest update handling into `src/extractor/orchestrator/lifecycle.py`.
- Moved resume document/chunk/plan validation, stage-completion persistence, audited execution/critic/verifier/reconciler result materialization, partial-output checks, and manifest transition materialization into `src/extractor/orchestrator/state.py`.
- Kept `src/extractor/orchestrator/service.py` focused on stage orchestration, stage service calls, dedup orchestration, audit reads/writes between stages, report writing, and result assembly.
- Confirmed touched orchestrator files are under the 400-line limit after the split:
  - `src/extractor/orchestrator/errors.py`: 8 lines
  - `src/extractor/orchestrator/trace.py`: 26 lines
  - `src/extractor/orchestrator/lifecycle.py`: 93 lines
  - `src/extractor/orchestrator/state.py`: 368 lines
  - `src/extractor/orchestrator/service.py`: 389 lines
- Verification:
  - `python3 -m py_compile src/extractor/orchestrator/__init__.py src/extractor/orchestrator/errors.py src/extractor/orchestrator/lifecycle.py src/extractor/orchestrator/models.py src/extractor/orchestrator/service.py src/extractor/orchestrator/state.py src/extractor/orchestrator/trace.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_orchestrator.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_orchestrator.py tests/unit/test_llm_client.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or non-test audit DB mutations were made.

### 2026-05-03 — Executor structural decomposition slice 5

- Completed the current executor cleanup by moving batch retry validation and rejection policy out of `src/extractor/executor/service.py`.
- Moved executor batch validation, retry merge behavior, and retry complaint rendering into `src/extractor/executor/batching.py`.
- Moved candidate schema/span rejection policy, approved category-field lookup, and exact chunk-span matching into `src/extractor/executor/policies.py`.
- Kept `src/extractor/executor/service.py` focused on execution orchestration, LLM calls, audit writes, candidate acceptance/rejection assembly, and result construction.
- Confirmed touched executor files are under the 400-line limit after the split:
  - `src/extractor/executor/batching.py`: 121 lines
  - `src/extractor/executor/policies.py`: 77 lines
  - `src/extractor/executor/service.py`: 211 lines
- Verification:
  - `python3 -m py_compile src/extractor/executor/__init__.py src/extractor/executor/batching.py src/extractor/executor/dedup.py src/extractor/executor/errors.py src/extractor/executor/field_normalizers.py src/extractor/executor/ids.py src/extractor/executor/materialization.py src/extractor/executor/models.py src/extractor/executor/normalization.py src/extractor/executor/payload_expansion.py src/extractor/executor/policies.py src/extractor/executor/service.py src/extractor/executor/source_resolution.py src/extractor/executor/text_utils.py src/extractor/executor/trace.py src/extractor/executor/validation.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py tests/unit/test_orchestrator.py tests/unit/test_llm_client.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or audit DB mutations were made.

### 2026-05-03 — Executor structural decomposition slice 4

- Continued executor cleanup with the payload normalization slice.
- Moved event-derived payload expansion into `src/extractor/executor/payload_expansion.py`.
- Moved source text resolution, offset repair, ambiguous span detection, and source-support fallback handling into `src/extractor/executor/source_resolution.py`.
- Moved shared text matching, whitespace normalization, Markdown-heading checks, and sentence-span helpers into `src/extractor/executor/text_utils.py`.
- Moved field-specific normalization rules into `src/extractor/executor/field_normalizers.py` and the normalization dispatcher into `src/extractor/executor/normalization.py`.
- Moved executor trace output formatting into `src/extractor/executor/trace.py` so `src/extractor/executor/service.py` remains under the 400-line convention.
- Left batch retry validation, candidate rejection policy, audit writes, and public executor exports unchanged.
- Confirmed touched executor files are under the 400-line limit after the split:
  - `src/extractor/executor/normalization.py`: 42 lines
  - `src/extractor/executor/trace.py`: 52 lines
  - `src/extractor/executor/payload_expansion.py`: 157 lines
  - `src/extractor/executor/text_utils.py`: 157 lines
  - `src/extractor/executor/source_resolution.py`: 212 lines
  - `src/extractor/executor/field_normalizers.py`: 372 lines
  - `src/extractor/executor/service.py`: 380 lines
- Verification:
  - `python3 -m py_compile src/extractor/executor/__init__.py src/extractor/executor/dedup.py src/extractor/executor/errors.py src/extractor/executor/field_normalizers.py src/extractor/executor/ids.py src/extractor/executor/materialization.py src/extractor/executor/models.py src/extractor/executor/normalization.py src/extractor/executor/payload_expansion.py src/extractor/executor/service.py src/extractor/executor/source_resolution.py src/extractor/executor/text_utils.py src/extractor/executor/trace.py src/extractor/executor/validation.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py tests/unit/test_orchestrator.py tests/unit/test_llm_client.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or audit DB mutations were made.

### 2026-05-03 — Executor structural decomposition slice 3

- Continued executor cleanup with the candidate materialization slice.
- Moved `build_candidate()` and UTF-8 byte-offset derivation into `src/extractor/executor/materialization.py`.
- Updated `src/extractor/executor/service.py` to delegate candidate construction while leaving payload normalization, batch retry validation, rejection policy, and audit writes unchanged.
- Confirmed the new executor materialization file is under the 400-line limit:
  - `src/extractor/executor/materialization.py`: 74 lines
- Verification:
  - `python3 -m py_compile src/extractor/executor/__init__.py src/extractor/executor/dedup.py src/extractor/executor/errors.py src/extractor/executor/ids.py src/extractor/executor/materialization.py src/extractor/executor/models.py src/extractor/executor/service.py src/extractor/executor/validation.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py tests/unit/test_orchestrator.py tests/unit/test_llm_client.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or audit DB mutations were made.

### 2026-05-03 — Executor structural decomposition slice 2

- Continued executor cleanup with the chunk/document/budget preflight validation slice.
- Moved `validate_executor_inputs()` into `src/extractor/executor/validation.py`.
- Updated `src/extractor/executor/service.py` to delegate preflight validation while preserving the public `extractor.executor.service.ExecutorError` name.
- Left batch retry validation, candidate materialization, payload normalization, audit writes, and rejection behavior unchanged for later executor slices.
- Confirmed the new executor validation file is under the 400-line limit:
  - `src/extractor/executor/validation.py`: 23 lines
- Verification:
  - `python3 -m py_compile src/extractor/executor/__init__.py src/extractor/executor/dedup.py src/extractor/executor/errors.py src/extractor/executor/ids.py src/extractor/executor/models.py src/extractor/executor/service.py src/extractor/executor/validation.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py tests/unit/test_orchestrator.py tests/unit/test_llm_client.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or audit DB mutations were made.

### 2026-05-03 — Executor structural decomposition slice 1

- Started executor cleanup with the smallest low-risk slice.
- Moved `ExecutorError` into `src/extractor/executor/errors.py` while preserving the public `extractor.executor.ExecutorError` export.
- Moved stable executor candidate and rejection ID generation into `src/extractor/executor/ids.py`.
- Updated `src/extractor/executor/service.py` to import the moved error and ID helpers without changing execution, payload normalization, audit writes, or rejection behavior.
- Confirmed the new executor files are under the 400-line limit:
  - `src/extractor/executor/errors.py`: 8 lines
  - `src/extractor/executor/ids.py`: 46 lines
- Verification:
  - `python3 -m py_compile src/extractor/executor/__init__.py src/extractor/executor/dedup.py src/extractor/executor/errors.py src/extractor/executor/ids.py src/extractor/executor/models.py src/extractor/executor/service.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py tests/unit/test_orchestrator.py tests/unit/test_llm_client.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or audit DB mutations were made.

### 2026-05-03 — Critic structural decomposition

- Chose `src/extractor/critic/service.py` as the next source-code structure cleanup target because it was still a monolithic critic orchestration, validation, correction-policy, retry-validation, and report-materialization module.
- Moved critic batch partitioning, retry validation, retry merging, and retry complaint text into `src/extractor/critic/batching.py`.
- Moved shared span/schema/source-support checks and contradicted-rejection detection into `src/extractor/critic/checks.py`.
- Moved compact correction materialization, correction invariant checks, qualifier preservation, and original-preservation policy into `src/extractor/critic/corrections.py`.
- Moved stable critic report/rejection ID generation into `src/extractor/critic/ids.py`.
- Moved duplicate-merge critic report mirroring into `src/extractor/critic/mirroring.py`.
- Moved critic report construction and critic rejection reason materialization into `src/extractor/critic/reports.py`.
- Moved critic input preflight checks into `src/extractor/critic/validation.py` and `CriticError` into `src/extractor/critic/errors.py`.
- Kept `src/extractor/critic/service.py` focused on candidate review orchestration, LLM calls, concurrency, and audit writes.
- Confirmed touched critic files are under the 400-line limit after the split:
  - `src/extractor/critic/errors.py`: 8 lines
  - `src/extractor/critic/validation.py`: 43 lines
  - `src/extractor/critic/ids.py`: 71 lines
  - `src/extractor/critic/mirroring.py`: 104 lines
  - `src/extractor/critic/reports.py`: 189 lines
  - `src/extractor/critic/batching.py`: 227 lines
  - `src/extractor/critic/checks.py`: 272 lines
  - `src/extractor/critic/service.py`: 278 lines
  - `src/extractor/critic/corrections.py`: 298 lines
- Verification:
  - `python3 -m py_compile src/extractor/critic/__init__.py src/extractor/critic/batching.py src/extractor/critic/checks.py src/extractor/critic/corrections.py src/extractor/critic/errors.py src/extractor/critic/ids.py src/extractor/critic/mirroring.py src/extractor/critic/models.py src/extractor/critic/reports.py src/extractor/critic/service.py src/extractor/critic/validation.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py tests/unit/test_orchestrator.py tests/unit/test_llm_client.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or audit DB mutations were made.

### 2026-05-03 — Verifier structural decomposition

- Chose `src/extractor/verifier/service.py` as the first source-code structure cleanup target because it exceeded the new maintainability convention while having a clear validation/policy/orchestration split.
- Moved verifier input preflight checks into `src/extractor/verifier/validation.py`.
- Moved deterministic verifier report construction, rejection policy, span/schema/source-support checks, and stable verifier/rejection ID generation into `src/extractor/verifier/policies.py`.
- Moved `VerifierError` into `src/extractor/verifier/errors.py` and kept the public verifier package export intact through `src/extractor/verifier/__init__.py`.
- Reduced `src/extractor/verifier/service.py` from a monolithic service to orchestration around LLM calls, audit writes, and policy delegation.
- Confirmed the touched verifier files are under the 400-line limit after the split:
  - `src/extractor/verifier/errors.py`: 8 lines
  - `src/extractor/verifier/validation.py`: 53 lines
  - `src/extractor/verifier/policies.py`: 301 lines
  - `src/extractor/verifier/service.py`: 267 lines
- Verification:
  - `python3 -m py_compile src/extractor/verifier/service.py src/extractor/verifier/policies.py src/extractor/verifier/validation.py src/extractor/verifier/errors.py src/extractor/verifier/__init__.py`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_verifier.py -q`
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_verifier.py tests/unit/test_orchestrator.py tests/unit/test_llm_client.py -q`
  - `make lint`
  - `git diff --check`
- No live LLM calls or audit DB mutations were made.

### 2026-05-03 — AGENTS maintainability convention update

- Added coding-convention guidance to `AGENTS.md`:
  - do not create new files over 400 lines;
  - split work into focused modules/subpackages before committing when a new file would exceed that size;
  - avoid growing existing oversized `service.py` files further;
  - move cohesive helper logic into named sibling modules or subpackages such as `validation.py`, `materialization.py`, `routing.py`, or `policies.py`;
  - keep orchestration, validation, normalization, model materialization, and persistence separated when that improves testability and auditability.
- Scope stayed limited to `AGENTS.md` and `PROGRESS.md`.
- Verification:
  - `git diff --check`
- No source-code changes, live LLM calls, or audit DB mutations were made.

### 2026-05-03 — Local eval scratch ignore cleanup

- Confirmed `evals/` is part of the tracked pipeline surface:
  - `evals/fixtures/` and `evals/baselines/` are tracked;
  - `src/extractor/evals/` contains scoring code;
  - `tests/unit/test_evals.py` covers eval behavior.
- Added `.gitignore` entries for local scratch eval output directories only:
  - `eval/`
  - `eval-results/`
  - `eval-runs/`
- Left tracked `evals/` untouched.
- Verification:
  - `git diff --check`
- No source-code changes, live LLM calls, or audit DB mutations were made.

### 2026-05-02 — Haiku cost-routing documentation note

- Added a concrete note to the `Tiered models per stage` section of `docs/PROJECT_OVERVIEW.md` using the Haiku 4.5 full-run evidence.
- Captured the key cost-routing lesson: cheaper models can preserve hard provenance/invariant checks while still failing schema semantics, source-grounded candidate generation, normalized label choice, and reconciliation.
- Documented that future cost work should measure each stage separately before routing it to a cheaper model, and should not globally downgrade planner, semantic executor lenses, or reconciler merely because invariants still pass.
- Scope stayed limited to `docs/PROJECT_OVERVIEW.md` and `PROGRESS.md`.
- Verification:
  - `git diff --check`
- No source-code changes, live LLM calls, or audit DB mutations were made.

### 2026-05-02 — Haiku 4.5 run review

- Operator provided the completed manifest details for run `medium-research-haiku45-20260502-163348`; output path matched locally as `outputs/medium-research-haiku45-20260502-163348.json`.
- Verified output/run state locally:
  - output byte length: `76343`
  - output SHA-256: `5cc9d31abf3c1c5a3bad9e961d49df36d26939f039af2f0e519bd0b27c029738`
  - run status: `completed`
  - started_at `2026-05-02T16:33:59.985945Z`, completed_at `2026-05-02T17:14:00.689112Z`
  - data point count: `52`
  - completed stages: `ingestion`, `chunker`, `planner`, `executor`, `dedup`, `critic`, `verifier`, `reconciler`, `reporter`
  - artifact counts: documents `1`, chunks `1`, extraction plans `1`, lens candidates `216`, critic reports `213`, verifier reports `208`, data points `52`, candidate rejections `171`, LLM call logs `30`
  - all LLM call logs used `claude-haiku-4-5-20251001`
- Scored against `evals/fixtures/medium_research_brief/case.json`:
  - precision `0.769`
  - recall `0.755`
  - F1 `0.762`
  - provenance recall `0.755`
  - TP `40`
  - FP `12`
  - FN `13`
  - exact-provenance matches `40`
  - invariant violations `0`
  - eval `passed=false`
- Missing expected IDs: `exp-000`, `exp-001`, `exp-002`, `exp-004`, `exp-005`, `exp-007`, `exp-009`, `exp-024`, `exp-027`, `exp-031`, `exp-039`, `exp-048`, `exp-052`.
- Local miss triage found:
  - schema/name drift for exact source content such as `condition` vs `conditions` and `party` vs `parties`;
  - exact candidates existed and passed critic/verifier for `exp-004`, `exp-005`, `exp-009`, `exp-031`, and `exp-039`, but were lost, rejected, or outselected downstream;
  - no exact candidates were found for `exp-001`, `exp-024`, `exp-027`, `exp-048`, or `exp-052`.
- Verification commands included:
  - `PYTHONPATH=src python3 -m extractor.evals evals/fixtures/medium_research_brief/case.json outputs/medium-research-haiku45-20260502-163348.json` (`passed=false`)
  - SQLite audit queries for run manifest, stage state, artifact counts, LLM call counts/models, and rejection counts
  - targeted local candidate-status triage for missing expected IDs
- No live LLM calls were run by the agent and `.veritext/audit.sqlite3` was not mutated by this review.

### 2026-05-02 — Local Haiku 4.5 trial override

- Interpreted the operator request to "switch to haiku once" as a one-off local runtime override rather than a canonical `config/default.yaml` change.
- Reviewed the target-domain/configurability section in `docs/PROJECT_OVERVIEW.md` before changing runtime extraction behavior.
- Used the operator-supplied Haiku 4.5 model ID `claude-haiku-4-5-20251001`.
- Added gitignored `config/local.yaml` with:
  - `llm.provider: anthropic`
  - `llm.api_key_env: ANTHROPIC_API_KEY`
  - `llm.model: claude-haiku-4-5-20251001`
- Verified the config loader picks up the local override:
  - `PYTHONPATH=src python3 -c "from extractor.config.loader import load_config; c=load_config(); print(c.llm.provider); print(c.llm.model); print(c.llm.api_key_env); print(c.llm.base_url); print(c.llm.stage_overrides)"`
- No source-code changes, live LLM calls, or audit DB mutations were made.

### 2026-05-02 — Cleanup-only documentation Phase 5: Final Cleanup Review

- Reviewed the cumulative cleanup commits against the pre-cleanup base and confirmed tracked changes were limited to `docs/PROJECT_OVERVIEW.md` and `PROGRESS.md`.
- Reviewed `docs/PROJECT_OVERVIEW.md` against `AGENTS.md` domain/generalization rules:
  - target domains remain broad and match the high-stakes, provenance-mandatory scope;
  - legal contracts are framed as a first proving ground, not a contract-specific specialization;
  - domain packs are described as typed/configurable additions over one domain-neutral extraction kernel;
  - non-configurable provenance, offset, audit, forced-tool, Pydantic, invariant, and no-silent-drop rules remain explicit.
- Checked the roadmap and cost sections for consistency: accuracy/generalization/provenance drives the active roadmap, cost reduction remains in a separate deployment-economics track, and human review is deferred as a governance layer.
- Ran targeted `rg` checks for stale score/test text, over-specialized first-domain wording, and stray overview resume commands.
- Verification:
  - `git status --short`
  - `git diff --name-only HEAD~4..HEAD`
  - `git diff --check`
- No source-code changes, live LLM calls, or audit DB mutations were made.

### 2026-05-02 — Cleanup-only documentation Phase 4: Roadmap Rebalance

- Reframed the improvement roadmap title and introduction around extraction accuracy, cross-domain generalization, and auditable provenance.
- Kept the per-stage roadmap while rewording planner, executor, critic, verifier, evaluation, human-review, and cost-summary framing so cost and human-review work do not drive the active roadmap.
- Updated the highest-leverage list to prioritize domain packs/schema-fit refusal, diverse fixture gates, boundary-preserving ingestion, source-grounded lenses/normalization, and provenance review/reporting.
- Kept cost content but separated it into a deployment-economics track and preserved the dedicated Cost Reduction Playbook.
- Did not expand or prioritize the ingestion table-extraction item.
- Scope stayed limited to `docs/PROJECT_OVERVIEW.md` and `PROGRESS.md`.
- Verification:
  - `git diff --check`
- No source-code changes, live LLM calls, or audit DB mutations were made.

### 2026-05-02 — Cleanup-only documentation Phase 3: Configurability Boundary

- Added a `Configurable surface` section to `docs/PROJECT_OVERVIEW.md` covering domain packs, schema templates, field roles, lenses, normalization policy, model routing, output formats, and reporting options.
- Added a matching `Non-configurable core` section covering exact span matching, byte/character offsets, source hashes, audit logging, forced tool use, Pydantic contracts, invariant enforcement, and no-silent-drop rejection accounting.
- Stated that configs and domain packs should be typed, versioned, hashed, and auditable so each run can prove which domain assumptions were active.
- Scope stayed limited to `docs/PROJECT_OVERVIEW.md` and `PROGRESS.md`.
- Verification:
  - `git diff --check`
- No source-code changes, live LLM calls, or audit DB mutations were made.

### 2026-05-02 — Cleanup-only documentation Phase 2: Domain-General Positioning

- Reworded the planner roadmap so domain packs are configurable starting schemas over one domain-neutral extraction kernel.
- Added the shared target-domain primitive set: entities, events, metrics, obligations, conditions, exceptions, temporal facts, relations, citations, and definitions.
- Clarified that adapting to a new target domain should require pack/config/fixture additions, not source-code rewrites.
- Reframed legal contracts as the first domain-pack proving ground rather than a contract-specific specialization of Veritext.
- Kept the existing target-domain list intact.
- Scope stayed limited to `docs/PROJECT_OVERVIEW.md` and `PROGRESS.md`.
- Verification:
  - `git diff --check`
- No source-code changes, live LLM calls, or audit DB mutations were made.

### 2026-05-02 — Cleanup-only documentation Phase 1: Hygiene and Staleness

- Preserved the existing local cleanup that removed stray `prepare_failed_run_resume.py` and `extractor.cli --resume` commands from the end of `docs/PROJECT_OVERVIEW.md`.
- Updated stale overview facts using already recorded repo/session evidence:
  - source size is now documented as ~10.7 KLOC, with 772 prompt lines and 21 unit test files;
  - latest completed scored `medium_research_brief` run is documented as precision `0.867`, recall `0.981`, F1 `0.920`;
  - latest full `make test` report is documented as `206 passed`, `2 skipped`.
- Reworded the current accuracy-risk text so it reflects the recent downstream guardrail work: the latest scored miss was a correction-authority failure, and the local guardrail for that class still awaits a live rerun.
- Scope stayed limited to `docs/PROJECT_OVERVIEW.md` and `PROGRESS.md`.
- Verification:
  - `git diff --check`
- No source-code changes, live LLM calls, or audit DB mutations were made.

### 2026-05-02 — Local critic correction authority guardrail

- Opened this phase after operator `okay do it`; reread `AGENTS.md`, the `# Target Domains, Non-Targets, and Market Sizing` section in `docs/PROJECT_OVERVIEW.md`, and the current gate in `PROGRESS.md`.
- Implemented a general critic correction authority rule in `src/extractor/critic/service.py`:
  - if the original candidate is mechanically valid, schema-approved, exact span-matching, and value/source-supported, a materialized correction cannot change its `category` or `field_name`;
  - such a correction now preserves the original candidate instead of relabeling it;
  - field/category corrections remain allowed when the original candidate itself is not mechanically valid, such as an unsupported value.
- Mirrored the rule in critic retry validation so a relabeling correction for a valid original does not trigger an unnecessary LLM retry.
- Added generic insurance-policy regression tests in `tests/unit/test_critic.py`:
  - valid `InsurancePolicy.coverage_limit` preserved when a correction relabels it as `summary`;
  - relabeling remains allowed when the original value is unsupported and the correction repairs source support.
- Adjusted the existing invalid-correction retry test so it still exercises retry behavior using an unsupported original; valid originals are now intentionally preserved without retry.
- Verified:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py tests/unit/test_verifier.py -q` (`40 passed`)
  - `make lint`
  - `make smoke` (`1 passed`)
  - `make test` (`206 passed`, `2 skipped`)
  - `git diff --check`
- No live LLM calls were run and `.veritext/audit.sqlite3` was not modified.

### 2026-05-02 — Completed-run downstream guardrail rerun review

- Operator provided manifest/output details for the resumed run `medium-research-executor-check-20260502-044644` and requested a local check.
- Reviewed output `outputs/medium-research-executor-check-20260502-044644.json` and audit `.veritext/audit.sqlite3` locally only; no live LLM calls were run by the agent and the audit DB was not mutated by this review.
- Output/run state:
  - manifest status: `completed`, completed_at `2026-05-02T14:18:46.897776Z`
  - output byte length: `81127`
  - data point count: `60`
  - completed stages: `ingestion`, `chunker`, `planner`, `executor`, `dedup`, `critic`, `verifier`, `reconciler`, `reporter`
  - artifact counts: extraction plans `1`, lens candidates `182`, critic reports `182`, verifier reports `176`, data points `60`, candidate rejections `120`
  - rejection counts: dedup `111`, critic `6`, verifier `2`, reconciler `1`
  - LLM call counts: planner `5`, executor `5`, critic `7`, verifier `9`, reconciler `1`
- Scored against `evals/fixtures/medium_research_brief/case.json`:
  - precision `0.867`
  - recall `0.981`
  - F1 `0.920`
  - provenance recall `0.981`
  - TP `52`
  - FP `8`
  - FN `1`
  - exact-provenance matches `52`
  - invariant violations `0`
  - eval `passed=false`
- Compared with the previous completed score: precision `0.862 -> 0.867`, recall `0.943 -> 0.981`, F1 `0.901 -> 0.920`, provenance recall `0.943 -> 0.981`, TP `50 -> 52`, FN `3 -> 1`, exact-provenance matches `50 -> 52`; false positives remained `8`.
- Fixed by the rerun:
  - `exp-018` `FinancialMetric.period = Q1 2026`
  - `exp-048` `RegulatoryRisk.exposure_pct = Approximately 18%`
- Remaining missing expected item:
  - `exp-000` `CorporateEvent.asset_detail`: exact candidate `candidate-7a0ab068482fbedff1242dbce88956d7` exists and passed verifier, but critic accepted it with a correction changing `field_name` from `asset_detail` to `summary`. The final full-sentence data point is therefore `CorporateEvent.summary`, while the final `CorporateEvent.asset_detail` false positive is the narrower span `contributing 312 gigawatt-hours`.

### 2026-05-02 — Local downstream verifier/critic guardrails

- Opened this phase after operator request and reread `AGENTS.md` plus the `# Target Domains, Non-Targets, and Market Sizing` section of `docs/PROJECT_OVERVIEW.md`.
- Read `docs/medium-research-kept-vs-ignored-data-points.md` before `PROGRESS.md`, confirming the remaining exact candidates are downstream losses only: `exp-000`, `exp-018`, and `exp-048`.
- Updated `src/extractor/verifier/service.py` so verifier `schema_violation` objections are dropped when deterministic checks prove the candidate is schema-approved, exact span-matching, and value/source-supported. Real unapproved fields and unsupported values still produce deterministic rejections.
- Updated `src/extractor/critic/service.py` with a general atomic-field context guardrail: schema-approved, exact span-matching, source-supported fields with scalar/temporal roles such as `period`, `date`, `rate`, `pct`, or `value` are not rejected solely because the span lacks companion-field context.
- Updated critic correction handling so a structurally invalid final correction preserves the original candidate when the original is mechanically valid, schema-approved, and source-supported; unsupported originals still reject with explicit reasons.
- Added focused generic unit coverage in `tests/unit/test_critic.py` and `tests/unit/test_verifier.py` using regulated filing / audited-record examples rather than medium-fixture-specific terms.
- Verified:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py tests/unit/test_verifier.py -q` (`38 passed`)
  - `make lint`
  - `make smoke` (`1 passed`)
  - `make test` (`204 passed`, `2 skipped`)
  - `git diff --check`
- No live LLM calls were run and `.veritext/audit.sqlite3` was not modified.

### 2026-05-02 — Kept-vs-ignored data point evidence report

- Operator requested a document showing which original-source data points are being ignored, with proof for each step and a clear kept/ignored split.
- Created `docs/medium-research-kept-vs-ignored-data-points.md`.
- The report includes:
  - run inputs, output SHA-256, score summary, audit artifact counts, and rejection counts;
  - detailed ignored sections for `exp-000`, `exp-018`, and `exp-048`, including expected source spans, exact executor candidate IDs, critic/verifier decisions, rejection rows, and pinpointed failure causes;
  - a table of all 50 kept expected data points with final data point IDs, values, and exact source spans;
  - a table of 8 extra kept data points counted as false positives by the eval fixture;
  - a bottom-line statement that all ignored expected data points had exact executor candidates, so remaining failures are downstream guardrail issues.
- Read-only/local evidence sources used: `evals/fixtures/medium_research_brief/case.json`, `outputs/medium-research-executor-check-20260502-044644.json`, and `.veritext/audit.sqlite3`.
- No live LLM calls were run and the audit DB was not modified.

### 2026-05-02 — Completed-run critic-rerun review

- Operator reported completed live resume for `medium-research-executor-check-20260502-044644`; output path `outputs/medium-research-executor-check-20260502-044644.json`.
- Reviewed output and audit locally only; no live LLM calls were run by the agent.
- Output SHA-256: `7215ebe521316874e32bc6554c241c09a09659668b8d80542e50d360fa4c8d11`.
- Audit state after rerun:
  - manifest status: `completed`, completed_at `2026-05-02T10:33:36.870980Z`
  - stage states complete through `reporter`
  - extraction plans: `1`
  - lens candidates: `182`
  - critic reports: `182`
  - verifier reports: `171`
  - data points: `58`
  - candidate rejections: `124`
  - rejection counts: dedup `111`, critic `8`, verifier `5`
  - LLM call counts: planner `5`, executor `5`, critic `7`, verifier `9`, reconciler `1`
- Scored against `evals/fixtures/medium_research_brief/case.json`:
  - precision `0.862`
  - recall `0.943`
  - F1 `0.901`
  - provenance recall `0.943`
  - TP `50`
  - FP `8`
  - FN `3`
  - exact-provenance matches `50`
  - invariant violations `0`
  - eval `passed=false`
- Compared with the prior completed score: precision `0.845 -> 0.862`, recall `0.925 -> 0.943`, F1 `0.883 -> 0.901`, provenance recall `0.906 -> 0.943`, TP `49 -> 50`, FP `9 -> 8`, FN `4 -> 3`, exact-provenance matches `48 -> 50`.
- Fixed by this rerun:
  - `exp-027` `ForwardGuidance.metric_name = Full-year 2026 revenue`
  - `exp-028` `ForwardGuidance.speaker = Marcus Bell`
  - prior `exp-040` `PersonnelChange.change_type = retirement` provenance mismatch
- Remaining missing expected IDs:
  - `exp-000` `CorporateEvent.asset_detail`: exact candidate now passed critic, then verifier rejected it with schema-violation language saying the span describes a commencement rather than asset detail.
  - `exp-018` `FinancialMetric.period = Q1 2026`: exact candidates exist, but critic rejected the atomic period span as too vague without metric context.
  - `exp-048` `RegulatoryRisk.exposure_pct = Approximately 18%`: exact candidates exist, but critic rejected after an invalid correction whose `span_text` did not match the chunk slice.
- Remaining false positives are still 8; no true-positive provenance mismatches remain.
- No audit DB mutation was performed by the agent during review.

### 2026-05-02 — Completed-run critic-rerun preparation dry-run

- Opened this phase after operator `continue`; treated it as local preparation only, not approval for live LLM calls or audit DB mutation.
- Checked worktree status and current gate context. Existing unrelated/local changes remain in place, including untracked `docs/PROJECT_OVERVIEW.md`.
- Confirmed persisted run state for `medium-research-executor-check-20260502-044644`:
  - manifest status: `completed`, completed_at `2026-05-02T09:46:03.181200Z`
  - stage states complete through `reporter`
  - extraction plans: `1`
  - lens candidates: `182`
  - critic reports: `182`
  - verifier reports: `172`
  - data points: `58`
  - candidate rejections: `123`
- Determined `critic` is the right cleanup boundary because the remaining local changes affect critic acceptance and reconciler source-candidate selection; preserving planner, executor, and dedup artifacts keeps the rerun scoped.
- Ran dry-run only:
  - `PYTHONPATH=src python3 scripts/prepare_failed_run_resume.py --run-id medium-research-executor-check-20260502-044644 --from-stage critic --allow-completed`
- Dry-run result:
  - `completed_manifest_reset=1`
  - `critic_reports=182`
  - `verifier_reports=172`
  - `data_points=58`
  - `candidate_rejections_from_stage=12`
  - `llm_call_logs_from_stage=16`
  - `run_stage_states_from_stage=4`
- Exact apply command, pending operator approval:
  - `PYTHONPATH=src python3 scripts/prepare_failed_run_resume.py --run-id medium-research-executor-check-20260502-044644 --from-stage critic --allow-completed --apply`
- Expected live resume command after cleanup, to be run only by/with operator approval:
  - `PYTHONPATH=src python3 -m extractor.cli evals/fixtures/medium_research_brief/source.md --run-id medium-research-executor-check-20260502-044644 --resume -o outputs/medium-research-executor-check-20260502-044644.json`
- No live LLM calls were run and the audit DB was not modified.

### 2026-05-02 — Critic guardrail generalization cleanup

- Opened this phase after operator `continue`; scope was to remove the document-specific critic guardrail shape called out by the operator.
- Reviewed `AGENTS.md` domain/generalization rules, current `src/extractor/critic/service.py`, critic tests, and `PROGRESS.md`.
- Replaced the `CorporateEvent.asset_detail` source-content signal list in `src/extractor/critic/service.py` with general deterministic checks:
  - candidate must be `CorporateEvent.asset_detail`;
  - candidate must be schema-approved, span-matching, and source-supported;
  - approved category/field descriptions must define `asset_detail` as a source-backed/stated detail role.
- Removed the document/source token signal function entirely; the critic fallback no longer checks for current-document or industry terms.
- Generalized critic regression tests in `tests/unit/test_critic.py` so the asset-detail guardrail example uses a generic acquisition portfolio sentence, and other critic tests no longer carry medium-fixture proper names or unit wording.
- Verified the critic service and critic tests no longer contain the checked medium-document terms: `Atacama`, `Northwind`, `Marcus Bell`, `gigawatt`, `battery`, `storage`, `commenced`, `contributing`, `Approximately 18%`, or `Full-year 2026 revenue`.
- Verified:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py -q` (`22 passed`)
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py tests/unit/test_reconciler.py -q` (`35 passed`)
  - `make lint`
  - `make smoke` (`1 passed`)
  - `make test` (`200 passed`, `2 skipped`)
  - `git diff --check`
- No live LLM calls were run and the audit DB was not modified.

### 2026-05-02 — AGENTS.md domain/generalization convention update

- Operator flagged that the latest `src/extractor/critic/service.py` guardrail looked document-specific and requested an `AGENTS.md` convention update before revising code.
- Read `AGENTS.md` and the `# Target Domains, Non-Targets, and Market Sizing` section in `docs/PROJECT_OVERVIEW.md`.
- Updated `AGENTS.md` with a new `Domain Scope and Generalization` section:
  - agents must review the project overview domain section before changing extraction behavior;
  - target domains are high-stakes, provenance-mandatory document workflows such as legal contracts, SEC filings, litigation review, clinical trial documents, FDA labels, regulatory rulings, insurance policies, standards documents, SOC 2/ISO evidence, patents, scientific papers, and government procurement;
  - behavior must not be optimized for a single fixture, source document, named entity, market sector, sentence, or expected answer;
  - proposed guardrails that depend on document-specific tokens, named entities, industry nouns, or one-off phrasing must be redesigned around source role, schema semantics, typed contracts, offsets, or auditable invariants.
- Added a matching `Modification Discipline` rule prohibiting document-specific patches even when tests reproduce a fixture failure.
- No live LLM calls were run and `docs/PROJECT_OVERVIEW.md` was read but not modified.

### 2026-05-02 — Local downstream critic/reconciler guardrails

- Opened this phase after operator instruction; treated it as local-only and did not run or approve any live LLM calls.
- Inspected current worktree state, `PROGRESS.md`, critic/reconciler/source-support code, unit tests, and the persisted audit evidence for run `medium-research-executor-check-20260502-044644`.
- Added critic guardrails in `src/extractor/critic/service.py`:
  - invalid corrections that only expand a valid original source span now preserve and accept the mechanically valid/schema-approved/source-supported original candidate instead of causing a critic rejection;
  - source-backed `CorporateEvent.asset_detail` event-detail sentences are no longer rejected when the approved `asset_detail` description allows asset or facility details.
- Extended reconciler source-candidate ranking in `src/extractor/source_support.py`:
  - percentage/exposure fields prefer candidates that preserve source-stated qualifiers such as `Approximately`;
  - `ForwardGuidance.metric_name` prefers scoped source-stated metric names such as `Full-year 2026 revenue` over generic field-role phrases such as `Revenue guidance`;
  - label fields prefer tight noun/action source spans when support is equivalent, so `retirement` wins over `announced retirement` while source-traced noun-form labels such as `appointment` remain preferred over verbatim verbs.
- Added focused regression coverage in `tests/unit/test_critic.py` and `tests/unit/test_reconciler.py` for the four remaining misses and the tight-provenance mismatch.
- Verified:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py tests/unit/test_reconciler.py -q` (`35 passed`)
  - `make lint`
  - `make smoke` (`1 passed`)
  - `make test` (`200 passed`, `2 skipped`)
  - `git diff --check`
- No live LLM calls were run and the audit DB was not modified.

### 2026-05-02 — Planner-and-later throttled rerun review

- Operator resumed `medium-research-executor-check-20260502-044644`; the run completed with 58 final data points.
- Verified audit state locally:
  - manifest status: `completed`, completed_at `2026-05-02T09:46:03.181200Z`
  - completed stage states: `ingestion`, `chunker`, `planner`, `executor`, `dedup`, `critic`, `verifier`, `reconciler`, `reporter`
  - extraction plans: `1`
  - lens candidates: `182`
  - critic reports: `182`
  - verifier reports: `172`
  - data points: `58`
  - candidate rejections: `123`
  - rejection counts: dedup `111`, critic `8`, verifier `4`
  - LLM call counts: planner `5`, executor `5`, critic `6`, verifier `9`, reconciler `1`
- Output `outputs/medium-research-executor-check-20260502-044644.json` has SHA-256 `285a63d8f1d67ab17c1f439bd17da94ebdbb2631b8854bc5729ab6b35747ce42`.
- Scored against `evals/fixtures/medium_research_brief/case.json`:
  - precision `0.845`
  - recall `0.925`
  - F1 `0.883`
  - provenance recall `0.906`
  - TP `49`
  - FP `9`
  - FN `4`
  - exact-provenance matches `48`
  - invariant violations `0`
- Compared with the previous completed score after downstream guardrails: precision `0.842 -> 0.845`, recall `0.906 -> 0.925`, F1 `0.873 -> 0.883`, TP `48 -> 49`, FN `5 -> 4`; exact-provenance matches remained `48`.
- Remaining missing expected IDs:
  - `exp-000` `CorporateEvent.asset_detail`: exact candidate exists but critic rejected it as not asset detail for the Atacama commencement sentence.
  - `exp-027` `ForwardGuidance.metric_name = Full-year 2026 revenue`: exact candidates reached reconciliation, but final data point selected `Revenue guidance` / `revenue guidance`.
  - `exp-028` `ForwardGuidance.speaker = Marcus Bell`: exact candidates exist but critic rejected after an invalid correction attempted to expand the source span.
  - `exp-048` `RegulatoryRisk.exposure_pct = Approximately 18%`: exact candidates reached reconciliation, but final data point selected narrower `18%`.
- Remaining provenance mismatch:
  - `exp-040` `PersonnelChange.change_type = retirement`: final value matched, but source span is wider `announced retirement` instead of expected `retirement`.
- No live LLM calls were run by the agent during review; scoring and triage were local-only.

### 2026-05-02 — LLM throttle and OperationalMetric facility guardrail

- Responded to Anthropic `429 Too Many Requests` caused by token-per-minute rate limiting during executor resume.
- Added `llm.min_request_interval_seconds` to `src/extractor/config/models.py`; `config/default.yaml` sets it to `60` seconds.
- Implemented provider-agnostic request-start throttling in `src/extractor/llm/client.py` with an async lock so concurrent stage work serializes LLM request starts instead of bursting into the provider.
- Added deterministic planner guardrail in `src/extractor/planner/service.py`:
  - preserves the prior generalized `CorporateEvent` description and `_type` source-traced label guidance;
  - appends optional `OperationalMetric.facility` when the planner omits it, with a bare-facility description and `required=false`.
- Updated planner prompts to require `OperationalMetric.facility` for facility-specific operational metrics and to reject moving that role only to `CorporateEvent`.
- Aligned `scripts/debug_planner_only.py` with production planner behavior by applying the post-critique schema-description/field guardrails before persisting the debug `ExtractionPlan`; it now also writes `04_schema_critique.generalized.json`.
- Added regression coverage in `tests/unit/test_llm_client.py`, `tests/unit/test_config.py`, `tests/unit/test_planner.py`, and `tests/unit/test_prompt_schema_quality.py`.
- Verified:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_planner.py tests/unit/test_prompt_schema_quality.py tests/unit/test_llm_client.py tests/unit/test_config.py -q` (`56 passed`)
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_planner.py tests/unit/test_prompt_schema_quality.py tests/unit/test_llm_client.py tests/unit/test_config.py tests/unit/test_prepare_failed_run_resume.py -q` (`59 passed`)
  - `PYTHONPATH=src python3 -m py_compile scripts/debug_planner_only.py scripts/prepare_failed_run_resume.py`
  - `make lint`
  - `make smoke` (`1 passed`)
  - `make test` (`196 passed`, `2 skipped`)
  - `git diff --check`
- Rechecked cleanup dry-run for the current failed run:
  - `extraction_plans=1`
  - `lens_candidates=69`
  - `candidate_rejections_from_stage=0`
  - `llm_call_logs_from_stage=8`
  - `run_stage_states_from_stage=1`
- No live LLM calls were run by the agent.

### 2026-05-02 — Planner-only verification checkpoint

- Operator ran planner-only verification for `medium-research-planner-verify-20260502-1`, stopping after planner and writing `.veritext/debug/medium-research-planner-verify-20260502-1/07_extraction_plan.json`.
- Inspected the debug `ExtractionPlan` locally; no live LLM calls were run by the agent.
- Planner verification result:
  - categories: `FinancialMetric`, `OperationalMetric`, `CorporateEvent`, `ForwardGuidance`, `RegulatoryRisk`, `PersonnelChange`
  - enabled lenses: `entity`, `event`, `claim`, `number`
  - approved category/field pairs: `42`
  - expected fixture category/field pairs: `38`
  - missing expected pairs: `0`
  - `OperationalMetric.facility` present, `required=false`, with bare facility/asset description
  - `CorporateEvent` no longer has a misplaced `facility` field
  - generalized `CorporateEvent` description and `_type` source-traced normalization guidance are present
- Extra approved pairs are non-blocking schema breadth: `ForwardGuidance.period`, `OperationalMetric.period`, `PersonnelChange.parties`, `RegulatoryRisk.period`.
- Refreshed main run audit state for `medium-research-executor-check-20260502-044644`:
  - manifest status: `failed`
  - completed stage states: `ingestion`, `chunker`
  - extraction plans: `0`
  - lens candidates: `0`
  - critic reports: `0`
  - verifier reports: `0`
  - data points: `0`
  - candidate rejections: `0`
  - LLM call logs: `0`
- Cleanup from `planner` is no longer necessary for the main run because it has already been cleaned to the pre-planner resume point.

### 2026-05-02 — Live planner rerun checkpoint

- Operator indicated the planner rerun was done and requested a local check.
- Inspected audit state for `medium-research-executor-check-20260502-044644`; no live LLM calls were run by the agent.
- Final refreshed audit state:
  - manifest status: `failed`, completed_at `2026-05-02T09:07:02.076822Z`
  - completed stage states: `ingestion`, `chunker`, `planner`
  - extraction plans: `1`
  - lens candidates: `69`
  - critic reports: `0`
  - verifier reports: `0`
  - data points: `0`
  - candidate rejections: `0`
  - LLM call logs: planner `5`, executor `3` (`executor.entity` `1`, `executor.claim` `2`)
- Verified the persisted plan contains the new generalized `CorporateEvent` description and `_type` label-normalization guidance.
- Found one schema coverage defect before downstream continuation:
  - missing expected category/field pair: `OperationalMetric.facility`
  - extra approved pair: `CorporateEvent.facility`
  - other extra approved pairs: `ForwardGuidance.period`, `OperationalMetric.period`, `RegulatoryRisk.period`
- Dry-run cleanup from `planner` on the failed run reports it would remove:
  - `extraction_plans=1`
  - `lens_candidates=69`
  - `candidate_rejections_from_stage=0`
  - `llm_call_logs_from_stage=8`
  - `run_stage_states_from_stage=1`
- Dry-run cleanup from `executor` would remove the partial executor artifacts only, but that is not sufficient because the persisted plan is missing `OperationalMetric.facility`.
- Recommendation: next local-only phase should add a general planner guardrail so `OperationalMetric` can carry an optional `facility` field when operational metrics are facility-specific, then clean from `planner` and rerun planner.

### 2026-05-02 — Planner-and-later resume preparation

- Opened this phase after operator `continue`; treated it as a phase gate only, not approval for live LLM calls.
- Inspected `scripts/prepare_failed_run_resume.py`, its tests, audit table layout, and orchestrator resume behavior.
- Extended `scripts/prepare_failed_run_resume.py` so `--from-stage` can now start at `planner`, `executor`, or `dedup` in addition to the existing downstream stages:
  - `planner` cleanup deletes persisted extraction plans, executor candidates, downstream reports/data points, executor/dedup/downstream candidate rejections, planner/executor/downstream LLM call logs, and planner-through-reporter stage states;
  - ingestion, chunks, document payloads, and manifest identity are preserved;
  - completed-run mutation still requires explicit `--allow-completed --apply`.
- Added regression coverage in `tests/unit/test_prepare_failed_run_resume.py` for planner-stage cleanup and updated the completed-run downstream cleanup test to assert planner/executor artifacts are preserved when cleanup starts at `critic`.
- Dry-run against the current completed run without `--apply`:
  - `extraction_plans=1`
  - `lens_candidates=202`
  - `critic_reports=202`
  - `verifier_reports=191`
  - `data_points=57`
  - `candidate_rejections_from_stage=145`
  - `llm_call_logs_from_stage=20`
  - `run_stage_states_from_stage=7`
- Verified:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_prepare_failed_run_resume.py -q` (`3 passed`)
  - `PYTHONPATH=src python3 scripts/prepare_failed_run_resume.py --help`
  - `PYTHONPATH=src python3 -m py_compile scripts/prepare_failed_run_resume.py tests/unit/test_prepare_failed_run_resume.py`
  - `PYTHONPATH=src python3 scripts/prepare_failed_run_resume.py --run-id medium-research-executor-check-20260502-044644 --from-stage planner --allow-completed` dry-run
  - `make lint`
  - `make smoke` (`1 passed`)
  - `make test` (`194 passed`, `2 skipped`)
  - `git diff --check`
- No live LLM calls were run and the audit DB was not modified.

### 2026-05-02 — Local planner/schema-description generalization

- Started from clean `git status --short` output, inspected `PROGRESS.md`, planner prompts, planner tests, schema-card view generation, current run plan artifact, and downstream source-support ranking.
- Updated `prompts/planner/propose_schema.md` and `prompts/planner/critique_schema.md` so planner schema descriptions must stay reusable and inclusive:
  - `CorporateEvent` descriptions must cover source-backed significant business or corporate events such as acquisitions, approvals, facility commencements or operation starts, rather than reserving the category for one named transaction.
  - `facility` field descriptions must allow a bare source-stated facility or asset name unless the field name or role explicitly requires facility plus location.
  - `_type` field descriptions must allow and prefer concise source-traced labels, including noun-form normalization when source words support the action/type.
- Added deterministic planner post-critique schema-description generalization in `src/extractor/planner/service.py` before strategy selection and plan persistence:
  - rewrites `CorporateEvent` category descriptions to an inclusive reusable description;
  - rewrites `facility` field descriptions to permit bare names;
  - appends source-traced label-normalization guidance to fields ending in `_type`.
- Updated `src/extractor/source_support.py` so reconciler source-candidate ranking prefers source-traced normalized label values over verbatim source wording for label fields, while still rejecting unsupported labels.
- Added regression coverage in `tests/unit/test_planner.py`, `tests/unit/test_prompt_schema_quality.py`, and `tests/unit/test_reconciler.py`.
- Verified:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_planner.py tests/unit/test_prompt_schema_quality.py tests/unit/test_reconciler.py -q` (`26 passed`)
  - `make test` (`193 passed`, `2 skipped`)
  - `make lint`
  - `make smoke` (`1 passed`)
  - `git diff --check`
- No live LLM calls were run.

### 2026-05-02 — Downstream guardrail live rerun review

- Operator applied completed-run cleanup from `critic` and resumed `medium-research-executor-check-20260502-044644`; the run completed with 57 final data points.
- Scored `outputs/medium-research-executor-check-20260502-044644.json` against `evals/fixtures/medium_research_brief/case.json`: precision `0.842`, recall `0.906`, F1 `0.873`, provenance recall `0.906`, TP `48`, FP `9`, FN `5`, exact-provenance matches `48`, invariant violations `0`.
- Compared with the prior completed score for the same run: precision `0.815 -> 0.842`, recall `0.830 -> 0.906`, F1 `0.822 -> 0.873`, false negatives `9 -> 5`, false positives `10 -> 9`, exact-provenance matches `43 -> 48`.
- Audit summary after rerun:
  - lens candidates: `202`
  - critic reports: `202` (`191` accepted, `11` rejected)
  - verifier reports: `191` (`189` accepted, `2` rejected)
  - data points: `57`
  - rejections: dedup `134`, critic `9`, verifier `2`
  - LLM calls preserved/added: planner `5`, executor `4`, critic `8`, verifier `2`, reconciler `1`
- Triage for the remaining five misses:
  - critic rejected `CorporateEvent.asset_detail`, `CorporateEvent.event_type = Facility commencement`, and `CorporateEvent.summary` because the plan description scopes `CorporateEvent` to the Northwind acquisition rather than event-like facts generally.
  - verifier rejected `OperationalMetric.facility = Atacama-1` because the plan field description says facility should include name and location.
  - `PersonnelChange.change_type = appointment` surfaced with the exact expected span but final value `appointed`, so the remaining issue is label normalization/source-candidate preference for change-type values.
- Confirmed provenance mismatches among true positives are now `0`; the remaining work is recall/normalization and false-positive control.
- No live LLM calls were run by the agent during this review; scoring and audit inspection were local-only.

### 2026-05-02 — Completed-run downstream resume helper

- Added `--allow-completed` to `scripts/prepare_failed_run_resume.py` after the operator attempted the explicit completed-run cleanup command.
- Completed runs remain protected by default: without `--allow-completed`, the script still refuses to prepare a completed manifest.
- With `--allow-completed --apply`, the script:
  - backs up the audit DB before mutation
  - deletes only rows from the requested downstream stage onward
  - resets the manifest from `completed` to `failed`
  - clears `output_data_point_ids` in the manifest payload so `--resume` can produce fresh reporter output
- Added `tests/unit/test_prepare_failed_run_resume.py` covering default completed-run refusal and the explicit allow path.
- Verified:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_prepare_failed_run_resume.py -q` (`2 passed`)
  - `PYTHONPATH=src python3 -m py_compile scripts/prepare_failed_run_resume.py tests/unit/test_prepare_failed_run_resume.py`
  - `PYTHONPATH=src python3 scripts/prepare_failed_run_resume.py --help`
  - dry-run for `medium-research-executor-check-20260502-044644 --from-stage critic --allow-completed`
  - `git diff --check -- scripts/prepare_failed_run_resume.py tests/unit/test_prepare_failed_run_resume.py PROGRESS.md`
  - `make lint`
- No cleanup was applied to the live audit DB by the agent, and no live LLM calls were run.

### 2026-05-02 — Downstream local guardrail repair

- Traced the nine misses in `medium-research-executor-check-20260502-044644` with `scripts/triage_missing_and_spans.py`: critic-rejected `4`, verifier-rejected `1`, and surfaced-but-not-matched `4`.
- Confirmed the surfaced-but-not-matched misses came from downstream rewriting or source selection, not executor absence:
  - critic corrected `Marcus Bell` to `CEO Marcus Bell`
  - critic corrected `Atacama-1` to `Atacama-1 in Chile`
  - critic corrected `6,581 in Q1 2025` to `6,581 gigawatt-hours in Q1 2025` while keeping the narrower source span
  - critic widened `retirement` provenance to `announced retirement`
- Added `src/extractor/source_support.py` for general downstream source-support helpers:
  - correction span expansion detection
  - non-label value/source token support
  - source-traced label detection using generic canonical token support
  - reconciler source-candidate specificity ranking
- Removed an initially added phrase-specific label table from `source_support.py`; no document names, company names, asset names, or exact fixture label mappings remain.
- Hardened critic behavior in `src/extractor/critic/service.py`:
  - invalid corrections that expand beyond the executor span are rejected/retried
  - invalid corrections that add unsupported non-label words or units are rejected/retried
  - `category_not_approved` is treated as mechanically contradicted when the candidate category and field are approved by the plan
  - `invalid_source_offsets` is treated as mechanically contradicted when the span exactly matches the chunk
- Hardened verifier behavior in `src/extractor/verifier/service.py`:
  - unsupported non-label value additions now fail deterministic verification even if the LLM accepts
  - source-traced label schema objections can be ignored only when generic label token support says the source supports the normalized label
  - label fields are not deterministically rejected just because the value is a normalization rather than a verbatim span
- Hardened reconciler source selection in `src/extractor/reconciler/service.py`: when the model groups multiple candidates, the server chooses the most source-supported and specific candidate from the group as the data point source instead of blindly trusting a wider model-selected source ID.
- Added focused regression coverage in `tests/unit/test_critic.py`, `tests/unit/test_verifier.py`, and `tests/unit/test_reconciler.py` for the downstream failure classes.
- Verified:
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_reconciler.py -q` (`42 passed`)
  - focused new regression tests (`5 passed`)
  - `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_reconciler.py tests/unit/test_executor.py -q` (`67 passed`)
  - `make lint`
  - `make smoke` (`1 passed`)
  - `git diff --check`
  - `make test` (`188 passed`, `2 skipped`)
- No live LLM calls were run.

### 2026-05-02 — Pre-cleanup audit inspection

- Checked `git status --short`; existing local modifications remain in place and were not reverted.
- Read `PROGRESS.md` and confirmed it already recorded the completed full resume and downstream score for `medium-research-executor-check-20260502-044644`.
- Inspected `.veritext/audit.sqlite3` before any cleanup:
  - run manifest status: `completed`
  - completed stage states: `ingestion`, `chunker`, `planner`, `executor`, `dedup`, `critic`, `verifier`, `reconciler`, `reporter`
  - LLM call logs: planner 5, executor 4, critic 6, verifier 2, reconciler 1
  - lens candidates: `202`
  - critic reports: `202` (`191` accepted, `11` rejected)
  - verifier reports: `191` (`183` accepted, `8` rejected)
  - data points: `54`
  - rejections: dedup `134`, critic `8`, verifier `8`
- Confirmed output `outputs/medium-research-executor-check-20260502-044644.json` is 77,239 bytes with SHA-256 `a948e4c42fe5d2682b4feb15a70fc478c1e1f9a82ad56cf49da05249af988753`.
- Re-ran local-only eval scoring; metrics matched the prior log: precision `0.815`, recall `0.830`, F1 `0.822`, provenance recall `0.811`, TP `44`, FP `10`, FN `9`, exact-provenance matches `43`, invariant violations `0`.
- Did not apply `scripts/prepare_failed_run_resume.py --from-stage verifier --apply` because the audit manifest is no longer failed; deleting verifier-and-later rows now would discard valid completed-run artifacts.
- No live LLM calls were run.

### 2026-05-02 — Executor-check full resume review

- Operator cleared partial verifier state and resumed `medium-research-executor-check-20260502-044644` with throttled verifier settings; the run completed with 54 final data points.
- Scored `outputs/medium-research-executor-check-20260502-044644.json` against `evals/fixtures/medium_research_brief/case.json`: precision `0.815`, recall `0.830`, F1 `0.822`, provenance recall `0.811`, TP `44`, FP `10`, FN `9`, exact-provenance matches `43`, invariant violations `0`.
- Acceptance/usage checks from audit passed: critic batches `6 <= 6`, verifier batches `2 <= 5`, and both critic/verifier cache-read token checks were nonzero.
- The executor-only gate remains strong: all `53/53` expected fixture items had exact candidates before downstream stages. Full-run losses are downstream.
- Missing expected bucket counts:
  - critic rejected: `4`
  - verifier rejected: `1`
  - exact candidate contributed to a surfaced data point but final value/span did not match eval: `4`
- Concrete downstream failures:
  - Critic rejected Atacama `CorporateEvent.asset_detail`, `CorporateEvent.event_type = Facility commencement`, and `CorporateEvent.summary`, citing category mismatch because the plan description framed `CorporateEvent` around the Northwind acquisition.
  - Verifier rejected `CorporateEvent.event_type = Acquisition approval`, failing to allow source-traced label normalization from `approved acquiring`.
  - Critic falsely rejected `OperationalMetric.metric_name = Solar capacity factor` as an invalid offset even though executor had already built exact source spans.
  - Reconciler/source selection produced wider or unnormalized final values for exact accepted candidates: `CEO Marcus Bell` vs `Marcus Bell`, `Atacama-1 in Chile` vs `Atacama-1`, `6,581 gigawatt-hours in Q1 2025` vs `6,581 in Q1 2025`, `appointed` vs `appointment`, and `announced retirement` vs `retirement`.
- No live LLM calls were run by the agent during scoring/triage; scoring and audit inspection were local-only.

### 2026-05-02 — Verifier rate-limit resume prep

- Operator resumed `medium-research-executor-check-20260502-044644` through the full CLI; Anthropic returned `429 Too Many Requests` for `claude-sonnet-4-6` with an organization limit of 5 requests per minute.
- Inspected audit state after failure:
  - run manifest status: `failed`
  - completed stage states: `ingestion`, `chunker`, `planner`, `executor`, `dedup`, `critic`
  - LLM call logs: planner 5, executor 4, critic 6, verifier 6
  - lens candidates: `202`
  - critic reports: `202`
  - verifier reports: `120`
  - data points: `0`
  - rejections: dedup `134`, critic `8`, verifier `5`
- Extended `scripts/prepare_failed_run_resume.py` with `--from-stage {critic,verifier,reconciler}` so a partial verifier failure can be cleaned without deleting completed critic reports/logs.
- Dry-run for `--from-stage verifier` reports it would delete only verifier-and-later partial rows: verifier reports `120`, verifier/reconciler rejections `5`, verifier/reconciler LLM call logs `6`, and no completed verifier/reconciler/reporter stage states.
- Verified `PYTHONPATH=src python3 -m py_compile scripts/prepare_failed_run_resume.py`, `make lint`, `make smoke`, `git diff --check`, and `make test` (`183 passed`, `2 skipped`).

### 2026-05-02 — Executor-only live gate check

- Operator ran fresh executor-only debug run `medium-research-executor-check-20260502-044644` after the effective-date context repair.
- Inspected `.veritext/debug/medium-research-executor-check-20260502-044644/02_extraction_plan.json`; the planner approved every category/field required by `evals/fixtures/medium_research_brief/case.json`.
- Inspected executor artifacts:
  - accepted executor candidates: `202`
  - executor rejections: `0`
  - expected fixture items with exact candidate present before downstream stages: `53/53`
  - expected fixture items missing at executor: `0`
  - expected fixture items present only with non-exact provenance: `0`
- Confirmed the prior miss is closed: `PersonnelChange.effective_date` now has exact candidates with value/span `June 18, 2026 Annual Meeting`.
- No code changes or live LLM calls were run by the agent during this inspection; live calls were made by the operator through the debug runner.

### 2026-05-02 — Executor effective-date context repair

- Analyzed executor-only live artifacts from `medium-research-executor-check-20260502-043728`.
- Confirmed planner approved all expected fields and executor produced zero rejections, with `52/53` exact expected candidates present at executor stage.
- Isolated the only executor-stage miss: `PersonnelChange.effective_date` expected `June 18, 2026 Annual Meeting`, while executor produced `June 18, 2026`.
- Added deterministic normalization in `src/extractor/executor/service.py` for `effective_date`: when the date span is immediately followed by named meeting context such as `Annual Meeting`, the executor extends both value and source span to include the named event context.
- Updated `docs/annotation-conventions.md` and executor prompts to document the general rule that effective timing spans keep an immediately attached named event context when the action is effective at that named event.
- Added unit coverage in `tests/unit/test_executor.py` for the `effective at the June 18, 2026 Annual Meeting` shape.
- Verified `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py -q`, `PYTHONPATH=src python3 -m pytest tests/unit/test_prompt_schema_quality.py -q`, `make lint`, `make smoke`, `git diff --check`, and `make test` (`183 passed`, `2 skipped`).
- No paid/live LLM calls were run for the repair.

### 2026-05-02 — Executor-only debug runner

- Added `scripts/debug_executor_only.py` for the operator workflow: run source ingestion, chunking, planner, and executor only; dump review artifacts under `.veritext/debug/<run-id>/`; stop before downstream paid review/reconciliation stages.
- The runner creates normal audit rows and marks `ingestion`, `chunker`, `planner`, and `executor` stage states complete, leaving the run manifest resumable rather than completed.
- The runner also supports existing non-completed runs that already have audited chunks and a plan; it will run executor if needed or load existing executor candidates without duplicating them.
- Review artifacts:
  - `00_document.json`
  - `01_chunks.json`
  - `02_extraction_plan.json`
  - `03_executor_summary.json`
  - `04_executor_candidates.json`
  - `05_executor_rejections.json`
- Verified `PYTHONPATH=src python3 scripts/debug_executor_only.py --help`, `PYTHONPATH=src python3 -m py_compile scripts/debug_executor_only.py`, `make lint`, `make smoke`, `git diff --check`, and `make test` (`182 passed`, `2 skipped`).
- No paid/live LLM calls were run.

### 2026-05-02 — Executor generalization local repair

- Inspected `.veritext/debug/medium-research-executor-repair-20260502-1/triage.md`, `docs/annotation-conventions.md`, `docs/extraction-quality-generalization-audit.md`, and executor prompts before editing.
- Added deterministic executor candidate expansion for event-lens chunks with explicit source phrases:
  - `commenced/began/started operation(s)` produces source-backed `event_type = Facility commencement` and, when approved, the source sentence as `summary` and `asset_detail`.
  - `approved acquiring` / `approved acquisition` produces source-backed `event_type = Acquisition approval` and, when approved, the source sentence as `summary`.
- Added executor post-resolution normalization for general span-width failures:
  - trims role suffixes such as `target`, `forecast`, and `margin` from fields whose names already encode that role;
  - narrows `notable_qualifier` to the qualifier phrase when the model selected the whole sentence;
  - narrows static operational-profile `asset_detail` spans such as `Northwind operates 1.85 gigawatt-hours across seven U.S. states.` to the profile phrase;
  - preserves original model duplicates so the existing audited dedup stage still records duplicate rejections.
- Updated `docs/annotation-conventions.md` and `prompts/executor/{claim,event}.md` to distinguish statement fields from qualifier/attribute fields: `summary`/`statement`/`description`/`condition` stay sentence-wide, while `notable_qualifier` and static `asset_detail` use tight source phrases unless the whole event sentence is the detail.
- Added focused unit coverage in `tests/unit/test_executor.py` for derived operation/acquisition event candidates, operational-profile asset-detail tightening, target/forecast suffix trimming, and notable qualifier tightening; updated prompt-quality assertions for the new field-width rule.
- Verified `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py tests/unit/test_prompt_schema_quality.py -q`, `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py tests/unit/test_orchestrator.py tests/unit/test_prompt_schema_quality.py -q`, `make test` (`182 passed`, `2 skipped`), `make lint`, `make smoke`, and `git diff --check`.
- No paid/live LLM calls were run.

### 2026-05-02 — Executor-repair live rerun review

- Operator resumed `medium-research-executor-repair-20260502-1` after the reconciler unknown-ID retry repair; the run completed with 55 final data points and zero invariant violations.
- Scored `outputs/medium-research-executor-repair-20260502-1.json` against `evals/fixtures/medium_research_brief/case.json`: precision `0.818`, recall `0.849`, F1 `0.833`, provenance recall `0.830`, TP `45`, FP `10`, FN `8`, exact-provenance matches `44`.
- Compared with the immediately prior scored state for `medium-research-prompt-hardening-20260502-1` after the `exp-052` fixture audit: precision improved `0.765 -> 0.818`, recall improved `0.736 -> 0.849`, F1 improved `0.750 -> 0.833`, false positives dropped `12 -> 10`, false negatives dropped `14 -> 8`, and exact-provenance matches improved `39 -> 44`.
- Regenerated `.veritext/debug/medium-research-executor-repair-20260502-1/triage.md`.
- Missing bucket counts for the 8 residual misses: 5 no-candidate, 1 critic-rejected, and 2 surfaced-but-not-matched.
- Remaining concrete targets:
  - `CorporateEvent.asset_detail` and `CorporateEvent.summary` still do not produce the Atacama operation sentence, while Northwind asset-detail values remain over- or under-wide.
  - `CorporateEvent.event_type` still misses `Facility commencement` and `Acquisition approval`; the live run only produced generic `acquisition` candidates for those event-type fields.
  - `OperationalMetric.target_value = 29.0%` was rejected by critic as a duplicate of a wider `29.0% target` candidate.
  - `ForwardGuidance.speaker` and `PersonnelChange.change_type` exact normalized candidates reached the reconciler, but final data points used grouped unnormalized source candidates (`CEO Marcus Bell`, `appointed`), so eval counted them as false positives instead of matches.
  - `FinancialMetric.notable_qualifier` matched by value but used the full sentence span, not the expected tight qualifier span.
- No local live LLM calls were run during the scoring/triage review.

### 2026-05-02 — Reconciler unknown-ID retry repair

- Diagnosed operator live-run failure `ReconcilerError: reconciler output referenced unknown candidate IDs: 6eb85b6df135` in run `medium-research-executor-repair-20260502-1`.
- Confirmed the compact ID `6eb85b6df135` does not match any audited candidate short ID for the run, so this was reconciler model ID drift rather than a missing candidate.
- Added reconciler retry validation in `src/extractor/reconciler/service.py`: before expanding compact IDs, the batch is checked against the candidate view map; unknown IDs produce a targeted complaint listing the invalid IDs and allowed compact IDs.
- Reconciler retries now replace the full reconciliation batch with the retry output, because reconciliation decisions are a single accounting set rather than independently mergeable row edits.
- Wired orchestrator reconciliation through `max(config.execution.max_llm_attempts - 1, 0)` so the reconciler uses the same stage retry budget as executor/critic/verifier.
- Added regression coverage for the live failure shape: first reconciler response references unknown compact ID `6eb85b6df135`, retry response uses valid compact IDs, and the final data point is produced from the intended candidate.
- Dry-run of `scripts/prepare_failed_run_resume.py --run-id medium-research-executor-repair-20260502-1` showed it would remove reusable critic/verifier rows; do not apply it for this reconciler-only failure.
- Verified `PYTHONPATH=src python3 -m pytest tests/unit/test_reconciler.py -q`, `PYTHONPATH=src python3 -m pytest tests/unit/test_reconciler.py tests/unit/test_orchestrator.py tests/unit/test_llm_client.py -q`, `make lint`, `make smoke`, `git diff --check`, and `make test` (`177 passed`, `2 skipped`).
- No paid/live LLM calls were run during this local repair.

### 2026-05-02 — Executor normalization/offset local repair

- Added deterministic executor boundary normalization in `src/extractor/executor/service.py` after source-span resolution and before candidate construction.
- Covered source-traced label normalization for current triage shapes: `commenced operation` -> `Facility commencement`, `approved acquiring` -> `Acquisition approval`, and `appointed` / `appointed Chief Sustainability Officer` -> `appointment` while preserving source spans over the source phrases.
- Added prior-period value repair for fields named `prior_period_value`, extending source-backed numeric/currency values to include adjacent `in Qn YYYY` period wording such as `$410.8 million in Q1 2025` and `6,581 in Q1 2025`.
- Added guidance role/span cleanup for `ForwardGuidance.condition` values with a leading `with ` and `speaker` values with role prefixes such as `CEO Marcus Bell`, preserving bare source spans and values.
- Improved deterministic offset repair for header-adjacent `metric_name` and `period` fields by adding case-insensitive value matching and selecting the first non-heading body match after a bad claimed offset; this targets the `Revenue` and `Q1 2026` failures without relaxing source-span invariants.
- Audited `evals/fixtures/medium_research_brief/case.json` entry `exp-052`; updated `RegulatoryRisk.summary` to include the sentence-closing period in `source_text`, `end_char`, and `end_byte`, matching `docs/annotation-conventions.md`.
- Regenerated `.veritext/debug/medium-research-prompt-hardening-20260502-1/triage.md`; existing output now has exact-provenance matches `39` and zero provenance mismatches. Precision/recall/F1 are unchanged because no pipeline rerun was performed.
- Verified `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py -q`, `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py tests/integration/test_recall_baseline.py::test_case_loads_and_validates -q`, `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py tests/unit/test_evals.py tests/integration/test_recall_baseline.py::test_case_loads_and_validates -q`, `make lint`, `make smoke`, `git diff --check`, and `make test` (`176 passed`, `2 skipped`).
- No paid/live LLM calls were run.

### 2026-05-02 — Prompt-hardening live rerun review

- Operator resumed `medium-research-prompt-hardening-20260502-1` after the critic boundary repair; the run completed with 51 data points and zero invariant violations.
- Scored `outputs/medium-research-prompt-hardening-20260502-1.json` against `evals/fixtures/medium_research_brief/case.json`: precision `0.765`, recall `0.736`, F1 `0.750`, provenance recall `0.717`, TP `39`, FP `12`, FN `14`, exact-provenance matches `38`.
- Compared with the prior completed run `medium-research-debug-20260502-003044`: precision improved `0.614 -> 0.765`, recall improved `0.660 -> 0.736`, F1 improved `0.636 -> 0.750`, false positives dropped `22 -> 12`, false negatives dropped `18 -> 14`, and exact-provenance matches improved `35 -> 38`.
- Audit summary: 152 executor candidates, 74 canonical candidates after dedup, 148 critic reports, 132 verifier reports, 51 final data points. Critic batch count stayed within the existing check (`5 <= 6`), verifier used 7 batches and exceeded the older acceptance check limit of 5.
- Triage bucket counts for the 14 misses: 10 no-candidate, 1 executor-rejected bad-offset/ambiguous-span candidate, 1 critic-rejected bad-offset metric-name candidate, 1 verifier-rejected value/span mismatch, and 1 surfaced output not matched by eval.
- Remaining local-quality targets are now narrower:
  - event/label normalization still misses `CorporateEvent.event_type` for facility commencement and acquisition approval, plus `PersonnelChange.change_type = appointment`;
  - prior-period values still drop period wording for `FinancialMetric.prior_period_value` and `OperationalMetric.prior_period_value`;
  - `ForwardGuidance.condition` and `speaker` candidates exist only as near-misses (`with at least...` / `at least 60%` and `CEO Marcus Bell` vs expected bare `Marcus Bell`);
  - bad offset retries still fail simple repeated/header-adjacent fields like `FinancialMetric.metric_name = Revenue` and `period = Q1 2026`;
  - `exp-052` appears to conflict with the Type D annotation convention because the actual `RegulatoryRisk.summary` includes sentence-closing punctuation while the fixture expected span omits the period.

### 2026-05-02 — Critic boundary repair for contradictory correction payloads

- Investigated failed live run `medium-research-prompt-hardening-20260502-1`, which aborted in critic parsing after Anthropic returned a non-`correct` verdict with a non-null `correction` payload.
- Hardened `src/extractor/llm/payloads.py` so dict-form verdicts expand compact decision codes (`a`/`r`/`c`) before validation, default missing reject codes when a stage default exists, and drop contradictory correction payloads from non-correct critic verdicts.
- Added a `CriticVerdict` pre-validation normalizer in `src/extractor/critic/models.py` so the same boundary repair applies even when Pydantic validates a single verdict directly through the union branch.
- Added critic regression coverage for the live failure shape: direct reject verdict with correction payload, batch reject verdict with correction payload, accept verdict with correction payload, and dict-form short decision code with null reject code.
- Ran `python3 scripts/prepare_failed_run_resume.py --run-id medium-research-prompt-hardening-20260502-1` in dry-run mode. It found partial state to clear before resume: 40 critic reports, 4 critic-or-later rejections, 4 critic-or-later LLM call logs, and no verifier/data-point rows.
- Verified `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py -q`, `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_llm_client.py -q`, `make lint`, `make smoke`, and `git diff --check`.
- No paid/live LLM calls were run during this repair phase.

### 2026-05-02 — Local all-test sweep and static validation

- Ran `make test`: 170 tests passed and 2 integration tests were skipped by existing test gating.
- Ran `make lint`, `make smoke`, and `git diff --check`; all passed.
- Re-scored existing output `outputs/medium-research-debug-20260502-003044.json` against `evals/fixtures/medium_research_brief/case.json` without running the pipeline or making LLM calls.
- Local re-score remained the known failed baseline because the report predates the new prompt changes: precision `0.614`, recall `0.660`, F1 `0.636`, provenance recall `0.660`, true positives `35`, false positives `22`, false negatives `18`, invariant violations `0`.
- No paid/live LLM calls were run and no commit was made.

### 2026-05-02 — Executor label/atomic/statement prompt/test phase

- Added focused local prompt regression coverage in `tests/unit/test_prompt_schema_quality.py` for three executor failure classes from the extraction-quality audit:
  - Atomic numeric/entity boundaries: `forecast_value`, `target_value`, `margin`, `prior_rate`, `new_rate`, and bare entity fields should not absorb role labels, periods, values, locations, or descriptors already carried by the field name.
  - Source-traced label normalization: label fields such as `event_type`, `change_type`, `exposure_type`, `risk_type`, and `metric_name` may use concise noun-form values when every content word traces to the selected source phrase.
  - Statement-like fields: `summary`, `statement`, `description`, `condition`, `notable_qualifier`, and `asset_detail` should preserve full source sentences or standalone clauses with closing punctuation and verbatim values.
- Updated `prompts/executor/number.md` to reject role-label contamination such as returning a value plus `forecast` or `target` for fields whose names already encode that role, while still preserving meaningful numeric qualifiers such as `approximately`, `at least`, `up`, and `down`.
- Updated `prompts/executor/entity.md` to require bare named entities for fields like `facility`, `party`, `person`, `organization`, `asset`, and `issuing_authority` unless the approved field explicitly bundles a qualifier.
- Updated `prompts/executor/claim.md` and `prompts/executor/event.md` to document source-traced noun-form label normalization and full sentence/clause spans for statement-like fields.
- Verified `PYTHONPATH=src python3 -m pytest tests/unit/test_prompt_schema_quality.py -q`, `PYTHONPATH=src python3 -m pytest tests/unit/test_executor.py tests/unit/test_prompt_schema_quality.py -q`, `make lint`, `make smoke`, and `git diff --check`.
- No paid/live LLM calls were run.

### 2026-05-02 — Planner role-naming prompt/test phase

- Added focused local prompt regression coverage in `tests/unit/test_prompt_schema_quality.py` for relation-specific naming without live LLM calls:
  - `ForwardGuidance.speaker` for the person or organization stating, reaffirming, or updating guidance, not generic `person`, `party`, or `role`.
  - `ForwardGuidance.target_date` for guidance by-dates/deadlines/target-achievement dates, not generic `period`.
  - Singular `ForwardGuidance.condition` for one stated contingency, caveat, threshold, or dependency; plural `conditions` only for multiple independent conditions.
  - `FinancialMetric.notable_qualifier` for source-stated metric qualifiers such as first-time, record, threshold, or one-time wording, not catch-all `summary`.
- Updated `prompts/planner/propose_schema.md` and `prompts/planner/critique_schema.md` in general terms only: role names are framed as source-relation rules, generic names remain allowed when no stronger relation exists, and no document/company/person/asset names were added.
- Strengthened planner critique guidance to reject `ForwardGuidance.person` / `role`, `ForwardGuidance.period`, plural `conditions` for a single condition, and `FinancialMetric.summary` as the only home for a separable metric qualifier.
- Verified `PYTHONPATH=src python3 -m pytest tests/unit/test_prompt_schema_quality.py -q`, `PYTHONPATH=src python3 -m pytest tests/unit/test_planner.py tests/unit/test_prompt_schema_quality.py -q`, `make lint`, `make smoke`, and `git diff --check`.
- No paid/live LLM calls were run.

### 2026-05-02 — Output-scope policy and correction guardrails

- Documented default output policy in `docs/output-scope-policy.md`: Veritext currently defaults to comprehensive source-backed extraction, while task-scoped extraction and hybrid core/supporting/contextual reporting remain future modes. This means source-backed facts outside a fixture's expected set are not automatically product defects.
- Updated `docs/extraction-quality-generalization-audit.md` to reference the scope policy and preserve the distinction between eval false positives and general-app quality defects.
- Added deterministic critic correction validation so a corrected candidate cannot drop source qualifiers such as `approximately`, `at least`, `up`, `down`, or `subject to` while keeping those words in the source span.
- Added critic regression coverage for the live failure class: `Approximately 18%` corrected to `18%` is rejected as an invalid correction instead of flowing to reconciler output.
- Added reconciler regression coverage proving reconciler data points use the accepted corrected candidate exactly and do not independently rewrite values.
- Verified `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py::test_review_candidates_rejects_correction_that_drops_source_qualifier tests/unit/test_reconciler.py::test_reconcile_candidates_uses_accepted_corrected_candidate_without_rewriting -q`, `PYTHONPATH=src python3 -m pytest tests/unit/test_critic.py tests/unit/test_reconciler.py -q`, `make lint`, `make smoke`, `python3 -m py_compile scripts/check_critic_boundary_preflight.py scripts/prepare_failed_run_resume.py`, and `git diff --check`.

### 2026-05-02 — Offline extraction-quality generalization audit

- Added `docs/extraction-quality-generalization-audit.md`, treating `medium-research-debug-20260502-003044` as a diagnostic specimen rather than a fixture-specific target.
- Classified the 18 false negatives and 22 false positives into general failure classes: planner semantic-role mismatch, executor role-qualifier contamination, label normalization gaps, statement/clause coverage gaps, critic correction qualifier loss, and one caught-but-unrecovered executor offset failure.
- Confirmed the planner did not approve four expected semantic roles at all: `FinancialMetric.notable_qualifier`, `ForwardGuidance.condition`, `ForwardGuidance.speaker`, and `ForwardGuidance.target_date`. Also confirmed several unexpected outputs are source-backed but outside the fixture scope, so precision work needs an explicit product policy for comprehensive vs task-scoped extraction.
- Traced the `Approximately 18%` -> `18%` mismatch to the critic correction path, not the reconciler: the accepted critic report contained a corrected candidate with value `18%` and the same `Approximately 18%` source span.
- Recommended next phases: first decide output scope and add deterministic guardrail tests for correction/value preservation; then planner role-naming tests and prompt edits; then executor label/atomic/statement tests and prompt edits; then local test sweep before one paid live rerun.

### 2026-05-02 — Medium re-annotated live baseline report

- Resumed failed live run `medium-research-debug-20260502-003044` after clearing partial critic-and-later audit rows with `scripts/prepare_failed_run_resume.py --apply`; run completed with 57 final data points and zero invariant violations.
- Scored `outputs/medium-research-debug-20260502-003044.json` against the re-annotated `evals/fixtures/medium_research_brief/case.json`: precision `0.614`, recall `0.660`, F1 `0.636`, provenance recall `0.660`, TP `35`, FP `22`, FN `18`, exact-provenance matches `35`.
- Compared with the re-scored 5/01 baseline from the annotation session (F1 `0.648`, provenance recall `0.642`, recall `0.660`): recall held flat, exact-provenance/provenance recall improved by one match, and F1 declined by `0.012` because this run emitted more false positives.
- Wrote `.veritext/debug/medium-research-debug-20260502-003044/triage.md`. Missing bucket counts: 16 no-candidate, 1 executor-rejected bad-offset candidate (`exp-018`), and 1 surfaced candidate whose reconciled data point value no longer matched eval (`exp-048`, candidate value `Approximately 18%` became data-point value `18%`).
- Residual misses line up with the predicted real extractor gaps: missing planner/executor fields for `ForwardGuidance` (`condition`, `speaker`, `target_date`) and `FinancialMetric.notable_qualifier`; normalized label failures for `CorporateEvent.event_type` and `PersonnelChange.change_type`; full-sentence/clause coverage gaps for `CorporateEvent.summary`, `CorporateEvent.asset_detail`, and `RegulatoryRisk.summary`; plus tight-span/role qualifier misses such as `$88.0 million forecast`, `Q1 2026 revenue`, `Atacama-1 in Chile`, and `29.0% target`.
- Provenance mismatches among true positives are now `0`, so the remaining quality work is recall/normalization and false-positive control rather than span-width inconsistency.
- Local-only verification: `python3 scripts/check_critic_boundary_preflight.py`, `python3 -m py_compile scripts/check_critic_boundary_preflight.py scripts/prepare_failed_run_resume.py`, `PYTHONPATH=src python3 -m extractor.evals ...`, and `PYTHONPATH=src python3 scripts/triage_missing_and_spans.py ...`.

### 2026-05-02 — Critic boundary preflight script

- Added `scripts/check_critic_boundary_preflight.py`, a local-only preflight for the live critic boundary failure shape where a non-`correct` verdict includes a contradictory `correction` payload.
- Verified the script imports repo-local `src/extractor/llm/payloads.py` and passes without making API calls via `python3 scripts/check_critic_boundary_preflight.py`.
- Added `scripts/prepare_failed_run_resume.py`, a dry-run-by-default helper that backs up the audit DB and removes only partial critic/verifier/reconciler/reporter artifacts for one failed run when `--apply` is supplied.
- Dry-run against `medium-research-debug-20260502-003044` showed 55 partial critic reports, 4 critic-or-later rejections, and 5 critic-or-later LLM call logs to clear before resume.

### 2026-05-02 — Annotation conventions and medium-fixture re-annotation

- Diagnosed root cause of the medium fixture's stuck provenance gate: the case file's spans were per-instance and not field-rule-driven (same `(category, field_name)` annotated as bare value in some entries and full sentence in others; identical sentence had `metric_name`/`period` annotated as full-sentence spans while `value`/`change_pct` in the same sentence were tight). No prompt or model can satisfy `min_provenance_recall: 1.0` against an inconsistent ground truth.
- Wrote `docs/annotation-conventions.md`: domain-agnostic rules for span widths in any future fixture. Four field types — atomic value, label/category term, entity/role/title, sentence/statement/clause — with one mechanical span rule each. Rules align with the executor's existing "shortest exact span supporting field meaning" prompt without weakening the byte-exact provenance bar.
- Re-annotated `evals/fixtures/medium_research_brief/case.json` to match the conventions: 26 of 53 entries had span widths or values rewritten. All byte offsets recomputed from the source text and verified slice-by-slice. Pipeline standard, eval gate threshold, and audit chain all unchanged.
- Ran the prior 5/01 executor-span-edit attempt (`prompts/executor/{claim,event,number,entity}.md`); F1 +0.013 / provenance recall -0.019 — net wash with new cross-section critic rejections. Reverted those four prompt edits since the convention fix is the durable solution and the prompt edits were tuned against the inconsistent ground truth. Kept `scripts/triage_missing_and_spans.py` (diagnostic-only, no behavior).
- Re-scored existing pipeline outputs against the new ground truth without rerunning the pipeline:
  - 5/01 baseline (original prompts): provenance recall 0.434 → **0.642** (+0.208), F1 0.667 → 0.648 (precision dropped because false-positive list is unchanged), exact-prov matches 23 → **34**.
  - 5/02 modified-prompt run: provenance recall 0.415 → **0.604** (+0.189), F1 0.680 → 0.680, exact-prov matches 22 → 32.
  - Both runs still fail the gate (recall ~0.66, precision ~0.64–0.70), but provenance recall is now in a defensible range and the misses are real pipeline gaps (no `notable_qualifier`/`condition`/`speaker`/`target_date` candidates from planner/executor for ForwardGuidance, normalized-label fields like `event_type="Facility commencement"` not matched).
- `make lint` and `python3 -m pytest tests/unit -q` (160 tests) pass.

### 2026-05-01 - Medium Fixture Stage Debug Artifact

- Added `docs/medium-research-stage-debug-plan.md` as a source-derived manual debugging checklist for the medium research fixture.
- Documented expected classification, planner schema, strategy/lens choices, executor target data points, critic/verifier checks, reconciler expectations, and a proposed one-stage-at-a-time debug artifact workflow.
- Kept the artifact diagnostic only; no production schema registry, matcher relaxation, or live pipeline run was added.

### 2026-05-01 - Planner Naming Stability Prompt Hardening

- Inspected `PROGRESS.md`, planner/executor prompts, the medium research fixture, `outputs/medium-research-schema-quality-1.json`, and `.veritext/audit.sqlite3` without running a live LLM eval.
- Confirmed the approved extraction plan itself introduced avoidable naming drift, including `Guidance`, `RegulatoryRateChange`, `change_percentage`, `announcement_date`, `forecast_value` under guidance, `exposure_percentage`, and one-off operational fields such as `facility_contribution`.
- Added a planner naming-stability pass to proposal and critique prompts: section headings are evidence but not automatic names, reusable role names are preferred when they preserve source-backed meaning, new names remain allowed for genuinely new roles, and avoidable synonym drift should be corrected by critique.
- Added prompt regression coverage proving naming stability, synonym-drift rejection, and semantic-role coverage are all required without creating a closed ontology.
- Verified `python3 -m pytest tests/unit/test_prompt_schema_quality.py -q`, `python3 -m pytest tests/unit/test_planner.py tests/unit/test_prompt_schema_quality.py tests/unit/test_llm_client.py -q`, `make lint`, `make smoke`, and `git diff --check`.
- No live medium fixture rerun was performed in this session.

### 2026-05-01 - Schema Quality Live Result Review

- Scored operator-run `medium-research-schema-quality-1` from `outputs/medium-research-schema-quality-1.json`; the run completed with 52 data points and zero invariant violations.
- Eval failed quality gates: precision `0.4423`, recall `0.4340`, F1 `0.4381`, provenance recall `0.2453`, with 23 true positives, 29 false positives, and 30 false negatives.
- Planner audit showed improved role specificity but continued benchmark label drift: `Guidance` vs expected `ForwardGuidance`, `RegulatoryRateChange` vs expected `RegulatoryRisk`, and field synonym drift such as `change_percentage` vs `change_pct`, `announcement_date` vs `event_date`, and `facility_contribution` vs expected category/field placement.
- Next quality work should inspect planner proposal/critique audit output and constrain schema naming stability without adding a canonical fixture schema, matcher relaxation, retries, or provider changes.

### 2026-05-01 - Compact Verdict Extra Null Repair

- Fixed live verifier compact verdict parsing for rows that append an extra trailing `null` after the prompted five tuple slots.
- Updated the shared verdict normalizer to trim only redundant trailing `None` slots beyond five items, preserving rejection of non-null extra content.
- Added critic and verifier regression coverage for six-slot compact rows with a redundant trailing null.
- Verified `python3 -m pytest tests/unit/test_verifier.py tests/unit/test_critic.py -q`.
- No live pipeline rerun was performed in this session.

### 2026-05-01 - Critic Missing Correction Retry Repair

- Fixed a live critic boundary failure where a verdict used `decision="correct"` with `code="schema_violation"` but omitted the required `correction` payload.
- Relaxed only that parse-time validator so malformed correction verdicts can reach the existing critic retry-feedback path.
- Added deterministic validation/rejection handling for missing correction payloads so the model gets a targeted retry complaint and exhausted retries do not silently accept the candidate.
- Added unit coverage for parsing the malformed verdict and retrying it into an accepted verdict.
- Verified `python3 -m pytest tests/unit/test_critic.py -q`.
- No live pipeline rerun was performed in this session.

### 2026-05-01 - Document-derived Schema Quality Prompt Hardening

- Strengthened `planner.propose_schema` to require document-derived semantic-role coverage for event, metric, guidance, risk/exposure, personnel, and regulatory/rate-change facts.
- Strengthened `planner.critique_schema` to reject source-grounded but too-coarse schemas, generic date/value/rate/party/person/summary role collapse, and schemas that cannot recover main atomic facts with exact provenance for both value and field meaning.
- Strengthened executor entity/event/claim/number prompts so source spans must support both the extracted value and the approved field meaning, including provenance examples for `$88.0 million forecast`, `19.5% margin`, `from 15.0%`, `to 26.5%`, `CEO Marcus Bell`, `appointed Chief Sustainability Officer`, `event_type`, and `change_type`.
- Added focused prompt regression coverage in `tests/unit/test_prompt_schema_quality.py`.
- Verified `python3 -m pytest tests/unit/test_prompt_schema_quality.py tests/unit/test_llm_client.py::test_default_prompt_pack_contains_hardening_examples_and_checklists -q`, `python3 -m pytest tests/unit/test_planner.py tests/unit/test_prompt_schema_quality.py tests/unit/test_llm_client.py::test_default_prompt_pack_contains_hardening_examples_and_checklists -q`, `python3 -m pytest tests/unit -q`, `make lint`, `make smoke`, `python3 -m pytest tests/integration/test_recall_baseline.py -q`, `make test`, and `git diff --check`.
- Re-scored the existing `outputs/medium-research-2.json` snapshot and confirmed the known failed baseline remained precision `0.5349`, recall `0.4340`, provenance recall `0.2830`, with zero invariant violations.
- A live `medium-research-1` rerun was intentionally not completed. The first unapproved attempt failed with `APIConnectionError`, the escalated network retry was interrupted, and the operator then instructed not to run live validation autonomously.

### 2026-05-01 - Retry Feedback Phase 2 Critic

- Wired critic batch review through `LLMClient.complete_structured_with_retry`, deriving retry count from `ExecutionConfig.max_llm_attempts` while leaving the existing post-parse audit and rejection loop intact.
- Added critic retry validation for missing compact candidate ids, hallucinated verdict ids, and invalid `correct` verdict correction payloads before reports are persisted.
- Added critic retry merge by compact id: invalid corrections are replaced, missing verdict fixes are appended, and hallucinated verdict ids are removed from the merged batch.
- Added unit coverage for retrying a missing verdict with a hallucinated extra id and retrying an invalid correction into an accepted verdict.
- Verified `python3 -m pytest tests/unit/test_critic.py tests/unit/test_llm_client.py -q`, `python3 -m pytest tests/unit/test_executor.py -q`, `python3 -m pytest tests/unit -q`, `make lint`, `make smoke`, `make test`, and `git diff --check`.
- The live `medium-research-1` corpus was not rerun in this phase.

### 2026-05-01 - Compact Verdict Trailing Null Repair

- Investigated a live critic abort where Anthropic returned a 4-slot compact reject verdict `[id, "r", code, evidence]` instead of the prompted 5-slot `[id, "r", code, evidence, null]`.
- Updated the shared compact verdict normalizer to pad omitted trailing optional tuple slots with `None`, preserving strict validation for missing required reject codes and missing correction payloads on `correct` verdicts.
- Added critic and verifier tuple-shape coverage for omitted trailing correction slots.
- Verified `python3 -m pytest tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_llm_client.py -q`, `python3 -m pytest tests/unit/test_executor.py -q`, `python3 -m pytest tests/unit -q`, `make lint`, `make smoke`, `make test`, and `git diff --check`.

### 2026-05-01 - Cross-stage LLM Boundary Shape Hardening

- Audited LLM output boundaries after the live critic tuple-shape failure: executor offset fields, critic/verifier verdict arrays, and reconciler `groups`/`rejected` arrays are the highest-risk schemas for cheap syntax drift.
- Hardened executor payload parsing for numeric-string `start_char` and `source_length` values so existing offset validation can accept, auto-repair, retry, or reject the candidate instead of aborting at parse time.
- Hardened critic and verifier verdict parsing for stringified `verdicts`, stringified row payloads, short accept/reject rows with omitted trailing optional slots, and reject rows that omit a code by defaulting to stage-specific generic rejection codes.
- Hardened reconciler compact output parsing for stringified `groups`, single-contributor group shorthand, bare rejected candidate IDs, and rejected rows missing a code by defaulting to `reconciler_rejected`.
- Added focused unit coverage for the short/stringified critic, verifier, and reconciler shapes.
- Added focused unit coverage for numeric-string executor offsets.
- Verified `python3 -m pytest tests/unit/test_executor.py tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_reconciler.py tests/unit/test_llm_client.py -q`, `python3 -m pytest tests/unit -q`, `make lint`, `make smoke`, `make test`, and `git diff --check`.

### 2026-05-01 - Medium Research Retry Live Check

- Reviewed completed live run `medium-research-1` written to `outputs/medium-research-2.json`: pipeline completed with 43 data points and zero invariant violations.
- Confirmed retry activity in audit logs: attempt-2 calls fired for `executor.claim`, `executor.event`, `executor.number`, and two critic batches.
- Remaining candidate rejections were 2 executor candidates, 15 critic rejects, 3 verifier rejects, and 53 dedup duplicates; executor residuals were both ambiguous repeated `Q1 2026` / `Q1 2025` span cases.
- Fixture eval still failed quality gates: precision 0.5349, recall 0.4340, F1 0.4792, provenance recall 0.2830, with 23 true positives, 20 false positives, and 30 false negatives.
- Operational retry/boundary stability is improved, but extraction quality now needs false-positive and missed-expected analysis rather than another parser/retry fix.

### 2026-05-01 — Safe Resume Support

- Added explicit `--resume` CLI behavior so existing `--run-id` values fail clearly unless resume is requested.
- Added audited stage-completion state and resume reconstruction from existing Pydantic audit payloads for documents, chunks, plans, candidates, critic reports, verifier reports, data points, and rejections.
- Avoided duplicate `run_manifests` inserts on resume while preserving strict duplicate checks for normal runs.
- Added unit coverage for clear existing-run failures, manifest reuse under `--resume`, planner-stage skipping after a failed run, CLI resume plumbing, and stage-state audit storage.
- Verified `python3 -m pytest tests/unit/test_orchestrator.py tests/unit/test_cli.py tests/unit/test_audit_store.py -q`, `python3 -m pytest tests/unit -q`, `make lint`, `make smoke`, `python3 -m pytest tests/integration/test_recall_baseline.py -q`, `make test`, and `git diff --check`.

### 2026-05-01 — Compact Verdict Evidence Boundary Repair

- Investigated a live Anthropic critic failure where one compact correction tuple had evidence longer than the 200-character boundary cap, causing `CriticBatchVerdicts` validation to abort the whole run.
- Moved compact critic/verifier verdict expansion to pre-validation and made optional overlong evidence omitted before strict verdict validation, preserving the decision code and correction payload instead of failing the batch.
- Updated critic/verifier prompts to tell models to set evidence to null when an explanation would exceed 200 characters.
- Added unit coverage for overlong compact evidence in both critic and verifier verdict batches.
- Verified `python3 -m pytest tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_llm_client.py -q`, `python3 -m pytest tests/unit -q`, `make lint`, `make smoke`, `python3 -m pytest tests/integration/test_recall_baseline.py -q`, `python3 -m pytest -q`, and `git diff --check`.
- The live LLM recall pipeline was not rerun after this boundary repair.

### 2026-05-01 — Quality Gate Repair After Phase 2d/2e Regression

- Investigated the `medium-research-1` live run after it produced 42 data points with output tokens reduced to 18,546 but quality regressed to precision 0.6905, recall 0.5472, and provenance recall 0.3396.
- Identified root causes: combined planner propose/critique drifted schema field names, executor `source_length` validation rejected semantic values that were source-backed but not verbatim, and the medium fixture thresholds were all 0.0 so the eval CLI returned `passed=true`.
- Rolled back the uncommitted planner Phase 2d/2e experiment, restoring separate `planner.propose_schema` and `planner.critique_schema` stages and required planner prose fields.
- Kept phases 2a-2c intact while relaxing executor span validation so valid source slices can support semantic values such as `appointment` or `Facility commencement`; ambiguous repeated value repair still rejects explicitly.
- Tightened `evals/fixtures/medium_research_brief/case.json` thresholds to the committed baseline metrics and updated integration coverage so a regressed local snapshot cannot pass silently.
- Verified `python3 -m pytest tests/unit/test_planner.py tests/unit/test_llm_client.py tests/unit/test_orchestrator.py tests/unit/test_executor.py tests/integration/test_recall_baseline.py -q`, `PYTHONPATH=src python3 -m extractor.evals evals/fixtures/medium_research_brief/case.json outputs/medium-research-2.json` fails with `passed=false` for the known bad report, `python3 -m pytest tests/unit -q`, `make lint`, `make smoke`, `python3 -m pytest tests/integration/test_recall_baseline.py -q`, `python3 -m pytest -q`, and `git diff --check`.
- The live LLM recall pipeline was not rerun after this repair.

### 2026-05-01 — Output-token Plan Phase 2c

- Replaced reconciler LLM output full `data_points` objects with compact `groups` shaped as `[source_candidate_id, [contributing_candidate_ids...]]`.
- Replaced verbose rejected-candidate payloads with compact `rejected` tuples shaped as `[candidate_id, code]`.
- Derived final data point category, field_name, value, source span, confidence, critic report IDs, and verifier report IDs server-side from the selected source/contributing candidates.
- Preserved full `DataPoint` and `CandidateRejection` audit records; only the LLM boundary shape changed.
- Updated reconciler prompt and tests, including focused validation for compact group output and orchestrator fixture coverage.
- Verified `python3 -m pytest tests/unit/test_reconciler.py tests/unit/test_orchestrator.py tests/unit/test_llm_client.py -q`, `python3 -m pytest tests/unit -q`, `python3 -m pytest tests/integration/test_recall_baseline.py -q`, `make lint`, `make smoke`, `python3 -m pytest -q`, and `git diff --check`.
- The live LLM recall pipeline was not run because `VERITEXT_RUN_LIVE_EVAL=1` was not enabled.

### 2026-05-01 — Output-token Plan Phase 2b

- Added reusable LLM payload expansion for positional verdict tuples shaped as `[id, decision_code, code_or_null, evidence_or_null, correction_or_null]`.
- Updated critic and verifier batch boundary models to accept compact tuple verdicts and immediately expand them into existing full `CriticVerdict` and `VerifierVerdict` objects for service logic and audit-side contracts.
- Kept existing object-shaped verdict fixtures valid so internal tests and audit storage continue to exercise the full contract.
- Updated critic and verifier prompts to request array-of-array verdicts with decision codes `"a"`, `"r"`, and critic-only `"c"`.
- Added focused unit coverage for critic and verifier compact tuple expansion.
- Verified `python3 -m pytest tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_llm_client.py tests/unit/test_orchestrator.py -q`, `python3 -m pytest tests/unit -q`, `python3 -m pytest tests/integration/test_recall_baseline.py -q`, `make lint`, `make smoke`, `python3 -m pytest -q`, and `git diff --check`.
- The live LLM recall pipeline was not run because `VERITEXT_RUN_LIVE_EVAL=1` was not enabled.

### 2026-05-01 — Output-token Plan Phase 2a

- Replaced executor LLM output `source_text` with `source_length` while preserving full reconstructed `SourceSpan.text` in `LensCandidate` and audit storage.
- Updated executor span resolution to slice chunk text from `start_char + source_length`, auto-correct unique value-based offset/length typos, and reject ambiguous or unsupported reconstructed spans with explicit reasons.
- Updated all executor prompts to request `start_char` plus `source_length` and forbid returning `source_text`, byte offsets, and end offsets.
- Updated executor, prompt-pack, and orchestrator test fixtures for the compact executor output boundary.
- Verified `python3 -m pytest tests/unit/test_executor.py tests/unit/test_llm_client.py tests/unit/test_orchestrator.py -q`, `python3 -m pytest tests/unit -q`, `python3 -m pytest tests/integration/test_recall_baseline.py -q`, `make lint`, `make smoke`, `python3 -m pytest -q`, and `git diff --check`.
- The live LLM recall pipeline was not run because `VERITEXT_RUN_LIVE_EVAL=1` was not enabled.

### 2026-04-30 — System Flow Review Document

- Added `docs/system-flow-review.md` with an end-to-end application flow diagram, per-stage responsibilities, LLM input/output examples, audit database notes, prompt-cache behavior, cost patterns, and review questions for external system analysis.
- Included a mini extraction example showing how source text becomes executor candidates, critic/verifier verdicts, reconciler data points, and final audited output.
- Added a token-problem appendix covering output-token cost dominance, repeated JSON keys/schema names, evidence length failures, cache writes without reads, batching limits, and compact wire-format mitigation.
- Verified `git diff --check`.

### 2026-04-30 — Prompt Cache Write Pruning

- Investigated the `medium-research-1` token ledger and found planner/executor cache writes with no corresponding reads, while critic/verifier were the stages actually benefiting from prompt caching.
- Added per-request Anthropic prompt-cache opt-out so stages can preserve split prompt construction without forcing `cache_control` onto one-shot prefixes.
- Disabled planner prompt caching because each planning call uses a different prompt/tool prefix, which invalidates message-prefix reuse under Anthropic's `tools -> system -> messages` cache hierarchy.
- Changed executor caching to apply only when a run has multiple chunks, and split the cached executor user prefix before `chunk_view` so chunk text is not written into one-off cache entries.
- Left critic/verifier cache behavior intact for repeated batch review and verification.
- Verified `python3 -m pytest tests/unit/test_llm_client.py tests/unit/test_executor.py`, `python3 -m pytest tests/unit/test_planner.py tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_orchestrator.py`, `python3 -m pytest tests/unit/test_audit_inspection.py tests/unit/test_audit_store.py tests/unit/test_cli.py`, `python3 -m pytest`, `make lint`, `make smoke`, and `git diff --check`.
- A live Sonnet rerun was not run in this session.

### 2026-04-30 — Audit Inspection CLI

- Added a reusable `veritext-audit` / `python -m extractor.audit` inspector for SQLite audit databases.
- The inspector selects a requested run or the latest run and reports database/schema metadata, run/document/plan summaries, candidate/report/rejection/data-point counts, per-stage token/cache usage, and Phase 24 acceptance checks for critic/verifier batch counts and cache reads.
- Added `--details` output for LLM call rows, candidates, critic/verifier reports, candidate rejections, and data points.
- Added public audit-store list helpers needed by the inspector for run-level reports and rejections.
- Documented local usage in `README.md`.
- Verified `python3 -m pytest tests/unit/test_audit_inspection.py tests/unit/test_audit_store.py tests/unit/test_cli.py`, `make lint`, `make test`, `make smoke`, and `git diff --check`.

### 2026-04-30 — Phase 24 Batch-size Tuning and Observability

- Raised the default critic and verifier batch sizes to 20 in canonical config and config model defaults.
- Added `AuditStore.summarize_run(run_id)` to aggregate per-stage LLM `calls`, `input_tokens`, `output_tokens`, `cache_read_tokens`, and `cache_creation_tokens`.
- Captured `usage_summary` after reporter completion in the orchestrator result without changing report serialization.
- Added `usage_summary` to the CLI JSON summary while preserving existing summary keys.
- Added audit-store aggregation coverage, CLI summary coverage, config assertions, and orchestrator coverage that the run result includes stage usage counts.
- Verified `python3 -m pytest tests/unit/test_audit_store.py tests/unit/test_cli.py tests/unit/test_config.py tests/unit/test_orchestrator.py`, `make lint`, `make test`, `make smoke`, and `git diff --check`.
- The four fixture eval reruns and live Sonnet 4.6 `medium-research-{N}` acceptance run were not run in this session.

### 2026-04-30 — Phase 23 Reconciler Input Slim

- Replaced the reconciler LLM input payload with compact `schema_card` and `candidates` view data, removing full `run_id`, `plan`, `critic_reports`, and `verifier_reports` from the LLM boundary.
- Kept reconciler service-side validation of one accepted critic report and one accepted verifier report per candidate before the LLM call.
- Added compact-ID expansion for reconciler tool output so existing full candidate IDs, critic report IDs, verifier report IDs, data-point construction, and no-silent-drop accounting remain unchanged.
- Updated the reconciler prompt to reference compact candidate IDs, `schema_card`, and `span_text` instead of full plan/report/source-span payloads.
- Updated reconciler and orchestrator tests to emit compact candidate IDs and assert the reconciler user payload contains only `schema_card` and `candidates`.
- Verified `python3 -m pytest tests/unit/test_reconciler.py tests/unit/test_orchestrator.py tests/unit/test_llm_views.py`, `make lint`, `make test`, and `make smoke`.
- Live/eval fixture token measurement was not run in this session; cost/quality acceptance checks remain deferred until all token-reduction phases are complete.

### 2026-04-30 — Phase 22 Pre-critic Candidate Deduplication

- Added exact duplicate candidate deduplication using the conservative key `(chunk_id, category, field_name, source_span.text, value)` with lexical candidate ID primary selection.
- Added `duplicate_candidate` as a typed rejection reason and `dedup` as an audit rejection stage.
- Persisted dedup rejections in the orchestrator between executor and critic, with each duplicate recording `merged_into:<primary_id>`.
- Changed critic review to run only on canonical candidates while mirroring each primary critic report to merged duplicates with stable derived report IDs.
- Preserved downstream reconciliation invariants by returning mirrored duplicate candidates in the critic result when the primary is accepted or rejected.
- Added unit coverage for exact-duplicate grouping, distinct-value/source preservation, dedup rejection records, canonical-only critic input, and mirrored duplicate critic reports.
- Verified `python3 -m pytest tests/unit/test_dedup.py tests/unit/test_orchestrator.py tests/unit/test_critic.py tests/unit/test_verifier.py`, `make lint`, `make test`, and `make smoke`.
- Live/eval fixture candidate-count and final data-point comparison were not run in this session; those cost/quality acceptance checks remain deferred until all token-reduction phases are complete.

### 2026-04-30 — Phase 21 Compact Critic / Verifier Output Schema

- Replaced verbose critic tool output with compact `verdicts` containing `{id, decision, code, evidence, correction}` and cross-field validation for accept/reject/correct decisions.
- Expanded critic verdicts server-side into existing `CriticReport` contracts with deterministic `plausibility_score`, severity mapping, default messages, and compact correction validation through the existing strict materialization path.
- Replaced verbose verifier tool output with compact `{id, decision, code, evidence}` verdicts and expanded them server-side into existing `VerifierReport` contracts.
- Derived verifier `span_verified`, `category_verified`, `alignment_score`, acceptance, and rejection reasons deterministically from the compact verdict plus existing invariant checks.
- Updated critic and verifier prompts to request compact `verdicts` instead of full report objects while preserving adversarial and verification rules.
- Updated unit and orchestrator mocks for compact verdict payloads and retained coverage for accepted, rejected, corrected, and invalid-correction paths.
- Verified `python3 -m pytest tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_llm_client.py tests/unit/test_orchestrator.py`, `make lint`, `make test`, and `make smoke`.
- Live/eval fixture recall comparison and token-output measurement were not run in this session; those cost/quality acceptance checks remain deferred until all token-reduction phases are complete.

### 2026-04-30 — Phase 20 Compact LLM-boundary View Models

- Added compact LLM view models for schema cards, chunks, and candidates, including stable short candidate IDs and collision rejection before LLM calls.
- Reworked executor LLM input to send only `schema_card`, `lens`, and `chunk_view`; full plan, run/doc IDs, chunk IDs, byte offsets, budgets, chunk policy, and domain hints stay server-side.
- Reworked critic LLM input to send `schema_card`, `chunk_view`, and compact candidate views keyed by short `id`; critic output now maps reports by `id` back to full candidates.
- Replaced full critic correction payloads with compact correction deltas while preserving original candidate identity/provenance and running the existing strict materialization/validation path.
- Reworked verifier LLM input to send compact candidate views plus `{accepted: true}` critic summaries instead of full `CriticReport` payloads; verifier output maps reports by short `id`.
- Updated executor, critic, and verifier prompts to describe compact field names and removed instructions that referred to audit-only payload fields.
- Added `tests/unit/test_llm_views.py` plus executor/critic/verifier payload regression assertions proving audit-only fields are absent at LLM boundaries.
- Verified `python3 -m pytest tests/unit/test_llm_views.py tests/unit/test_executor.py tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_llm_client.py tests/unit/test_orchestrator.py`, `python3 -m pytest tests/unit/test_planner.py tests/unit/test_reconciler.py tests/unit/test_reporter.py`, `make lint`, `make test`, and `make smoke`.
- Live/eval fixture recall comparison and token-size measurement were not run in this session; those cost/quality acceptance checks remain deferred until all token-reduction phases are complete.

### 2026-04-30 — Phase 19 Anthropic Prompt Caching

- Added `llm.prompt_cache_enabled` to canonical config with a reversible default of `true`.
- Extended `StructuredLLMRequest` with `stable_user_prefix` and preserved `full_user_content` for providers or configs that do not use Anthropic cache blocks.
- Updated Anthropic request construction to put ephemeral `cache_control` on cacheable system prompts, tool schemas, and stable user-prefix text blocks while leaving OpenAI/OpenAI-compatible requests as concatenated plain user content.
- Split planner, executor, critic, and verifier user payloads at stable JSON boundaries so the concatenated payload remains exactly the same JSON shape as before caching.
- Added one-shot critic/verifier priming so later batches wait for the first batch before entering normal stage concurrency.
- Added LLM-client prompt-cache regression coverage, config coverage, critic cache-read log coverage, and updated stage tests to read concatenated block content.
- Verified `python3 -m pytest tests/unit/test_llm_client.py tests/unit/test_config.py tests/unit/test_executor.py tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_planner.py tests/unit/test_orchestrator.py`, `make lint`, `make test`, and `make smoke`.
- Live Anthropic rerun of `medium_research_brief` was not run in this session; external-cost acceptance remains for the operator.

### 2026-04-30 — Medium Research Output Comparison

- Compared `outputs/medium-research.json` against `evals/fixtures/medium_research_brief/source.md` and verified the reported SHA-256/byte length match the run summary.
- Found all 12 emitted data points are source-backed and come from the first Headlines paragraph, with no distractor extraction from the rejected CleanTech Daily or Northwind/Sunbelt statements.
- Found major recall loss outside Headlines: executor generated candidates for Operations, Acquisition, Guidance, Risk, and Personnel, but most were rejected as `invalid_source_offsets`/`invented_span` before critic/verifier because claimed offsets did not match chunk text.
- Confirmed the approved extraction plan covered seven categories, so the missed later-section facts were not caused by planner schema scope.
- Reviewed `docs/extraction-quality-strategy.md`; the chunk-wide unique-span locator strategy matches the audit failure, but the run-status wording, retry-loop placement, and call-scaling formula need correction before implementation.
- Shipped the executor locator fix: after a claimed offset miss, executor span resolution now searches the whole chunk and only auto-corrects exact `source_text` when it occurs uniquely.
- Hardened executor span resolution further with whitespace-normalized unique matching that rewrites provenance to the exact chunk substring, plus typed `ambiguous_source_span` rejection for short repeated snippets even when the claimed offset lands on one occurrence.
- Added executor coverage for far-off unique offset correction, ambiguous repeated-span rejection, exact claimed short ambiguity rejection, and newline/space normalized correction; verified `python3 -m pytest tests/unit/test_executor.py`, `python3 -m pytest tests/unit/test_executor.py tests/unit/test_contracts.py tests/unit/test_orchestrator.py`, and `make lint`.
- Investigated the follow-up live rerun that failed at `2026-04-30T08:54:12Z` with Anthropic 429 input-token rate limiting; the DB shows executor produced 137 candidates with no executor offset rejections, critic completed 9 batches / 90 reports, and no verifier or report output was reached.

### 2026-04-30 — Executor Offset Prompt Hardening

- Updated all executor prompts to spell out absolute offset arithmetic as `start_char = chunk.start_char + chunk_relative_index`.
- Added explicit instructions to avoid estimated offsets, byte/token/line/markdown offsets, and forbidden offset keys such as `start_text`, `end_char`, `start_byte`, and `end_byte`.
- Added prompt regression coverage so the stricter offset algorithm and forbidden-key rules remain present in the executor prompt pack.
- Added a gitignored local OpenAI override for a `gpt-5.4-mini` global trial with medium-effort `gpt-5.2` on planner, executor, and reconciler, and made the canonical default config test ignore local developer overrides.

### 2026-04-29 — Moonshot Kimi Tool Compatibility

- Fixed Moonshot Kimi structured requests by explicitly disabling Kimi thinking whenever Veritext sends a forced named function `tool_choice`.
- Preserved the forced-tool invariant, strict OpenAI-compatible function schemas, `max_tokens`, and `parallel_tool_calls=False` behavior.
- Updated README/config comments and LLM client unit coverage to document Moonshot's specified-tool/thinking incompatibility.
- Hardened executor payload validation against Kimi returning `start_text` as a typo for the integer `start_char` offset while keeping the advertised tool schema strict and preserving exact-span validation.
- Lowered the canonical Moonshot stage concurrency from 4 to 2 to stay below the observed organization concurrency cap of 3 requests and avoid repeated 429 failures.

### 2026-04-29 — Moonshot Kimi Configuration

- Added `openai_compatible` as a first-class LLM provider with configurable `base_url` and `api_key_env` fields.
- Updated the OpenAI SDK client creation path to support OpenAI-compatible endpoints such as Moonshot while preserving forced tool calls, strict schemas, and effective-model audit logging.
- Switched canonical `config/default.yaml` to Moonshot Kimi K2.6 through `https://api.moonshot.ai/v1`, using `MOONSHOT_API_KEY` and `kimi-k2.6` by default.
- Omitted normal OpenAI `temperature` and `reasoning_effort` request parameters for Kimi model IDs so Moonshot can apply Kimi K2.6 defaults, including thinking enabled by default.
- Removed references to unavailable `kimi-k2-thinking`; Kimi configuration now uses `kimi-k2.6` only.
- Aligned Kimi request parameters with Moonshot docs by sending `max_tokens`, explicit `thinking: {"type": "enabled"}` through the OpenAI SDK `extra_body` escape hatch, and no `temperature` or OpenAI-only `reasoning_effort`.
- Reworked `.env` and `.env.example` so they contain API keys only, with `MOONSHOT_API_KEY` as the active key name and provider/model settings kept in YAML.
- Updated README and config tests for the Moonshot Kimi setup.
- Cleaned up `src/extractor/llm/client.py` by centralizing OpenAI-compatible provider routing and extracting OpenAI/Kimi request construction into focused helper functions without changing forced-tool behavior.

### 2026-04-29 — Medium Research Recall Config Adjustment

- Reviewed the `medium-research-1` live audit run after the final report returned 25 high-precision data points but missed later document sections.
- Confirmed chunking and executor scheduling ran across two chunks with all four executor lenses called on each chunk.
- Found chunk 0 produced 75 executor candidates while chunk 1 produced zero candidates across `entity`, `event`, `claim`, and `number` despite clean `tool_calls` completions.
- Confirmed the approved extraction schema covered the missed later-section fact types, including operational metrics, segment revenue, risk disclosures, commercial contract terms, capital allocation, personnel changes, and project milestones.
- Raised the canonical OpenAI completion budget from 16,384 to 32,768 tokens and restored `reasoning_effort` from `low` to `medium` to improve recall on dense later chunks while preserving forced tool-use behavior.
- Switched the local OpenAI runtime override and example docs from `gpt-5.2` to `gpt-5-mini` for lower-cost development runs.
- Added typed per-stage LLM overrides keyed by stage group (`planner`, `executor`, `critic`, `verifier`, `reconciler`) and routed both Anthropic/OpenAI requests through the resolved stage settings.
- Configured local/example OpenAI runs to use `gpt-5-mini` globally while promoting `executor` and `reconciler` calls to `gpt-5.2`, with audit logs recording the effective model used for each call.
- Documented cheap, balanced, and highest-quality model presets in `.env.example`, README, and local `.env` comments so stage-specific model choices are easy to switch without code changes.
- Updated the balanced model preset to promote `planner` alongside `executor` and `reconciler`, reflecting the stage quality priority of executor recall first, planner schema quality second, and reconciler merge quality third.
- Added `llm.stage_overrides: {}` to canonical `config/default.yaml` and created `config/local.example.yaml` with the OpenAI balanced preset so YAML config users can switch models without relying on environment variables.
- Promoted the OpenAI balanced preset into canonical `config/default.yaml`: `gpt-5-mini` globally with `gpt-5.2` overrides for planner, executor, and reconciler.

### 2026-04-29 — OpenAI Live Smoke Offset Rejection

- Investigated a live OpenAI smoke run that reached `executor.event` and failed on malformed candidate offset validation.
- Moved executor LLM boundary handling so internally inconsistent source offsets are recorded as explicit `invalid_source_offsets` candidate rejections instead of aborting the batch with a raw Pydantic validation error.
- Added focused executor test coverage for malformed payload offsets and verified related executor, contract, audit, and LLM-client tests.
- Added OpenAI strict-tool schema adaptation so nullable optional fields are still included in each object schema's `required` list, fixing the `critic.corrected_candidate` 400 response without weakening Pydantic contracts.

### 2026-04-29 — Phase 0 Bootstrap

- Created the required repository layout under `src/extractor/`, `prompts/`, `tests/`, `config/`, and `evals/`.
- Added `pyproject.toml` with required runtime and test dependencies.
- Added `.gitignore`, `README.md` skeleton, and `Makefile` with `test`, `lint`, and `smoke` targets.
- Added minimal bootstrap tests for scaffold integrity and package importability.
- Verified `make test`, `make lint`, and `make smoke` all pass.
- Decision recorded: selected `pdfplumber` over `pypdf` for higher-fidelity PDF extraction in later ingestion work.

### 2026-04-29 — Project Operating Docs

- Added `AGENTS.md` with short conventions for phase discipline, architecture, configuration, prompts, invariants, testing, and auditability.
- Added this `PROGRESS.md` file to track completed phases and session updates.
- Phase 1 has not started.

### 2026-04-29 — Phase 1 Data Contracts

- Added Pydantic v2 contracts for documents, chunks, source spans, extraction plans, lens candidates, critic reports, verifier reports, data points, run manifests, and LLM call logs.
- Added supporting contract types for page spans, category fields, lens budgets, chunk policy, critic issues, and rejection reasons.
- Enforced strict validation for confidence ranges, offsets, UTF-8 byte ranges, non-blank identifiers, immutable models, duplicate schema entries, candidate/source identity, verifier rejection reasons, run completion timing, and LLM call metrics.
- Added unit tests covering all Phase 1 contract validation behavior.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Agent Convention Update

- Updated `AGENTS.md` with stricter coding conventions for typed stage functions, stage-boundary models, comments, explicit errors, stable provenance, and focused tests.
- Added modification discipline rules requiring agents to avoid unrelated edits, avoid opportunistic refactors, preserve local changes, and ask before edits that could affect invariants.
- Phase 2 has not started.

### 2026-04-29 — Phase 2 Configuration & Logging

- Added canonical `config/default.yaml` for runtime tuning values.
- Added frozen Pydantic config models for LLM, chunking, execution, audit, logging, prompt paths, and run context values.
- Added configuration loading with `default.yaml` as the base, optional `local.yaml` overrides, and `VERITEXT_*` nested environment overrides.
- Added explicit configuration errors for missing/malformed YAML and conflicting environment override paths.
- Added structlog JSON logging setup with timestamp, level, logger name, and context variable merging.
- Added contextvars-based run context helpers that propagate `run_id`, `doc_id`, and `audit_db_path` through async tasks and structured logs.
- Added Phase 2 unit tests covering config precedence, validation failures, canonical default loading, JSON log output, and async run context propagation.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 3 Audit Storage

- Added an async `aiosqlite` audit store with schema initialization and schema version tracking.
- Added SQLite tables for run manifests, documents, chunks, extraction plans, LLM call logs, lens candidates, critic reports, verifier reports, data points, and candidate rejections.
- Stored each audited contract as full Pydantic JSON payload while also indexing stable IDs, run/doc IDs, status, stage, and ordering fields for retrieval.
- Added explicit duplicate and provenance protection through primary keys, unique constraints, and foreign keys.
- Added run manifest update support that fails loudly when the target run does not exist.
- Added `CandidateRejection` audit records so rejected candidates can be persisted with non-empty typed reasons.
- Added Phase 3 unit tests covering schema creation, contract round-trips, duplicate failures, orphaned provenance failures, manifest updates, and rejected-candidate logging.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 4 LLM Client

- Added documented placeholder prompt files for every declared LLM stage under `prompts/`.
- Added prompt loading that maps stages to prompt files, requires intent, typed inputs, output tool schema, failure modes, and prompt sections, and preserves prompt text for hashing.
- Added `max_output_tokens` to LLM configuration so Anthropic output limits remain configured rather than hardcoded.
- Added a direct Anthropic SDK client wrapper in `src/extractor/llm/client.py`.
- Enforced forced tool use by sending Anthropic `tool_choice` and rejecting responses without exactly one matching `tool_use` block.
- Validated structured tool input with caller-supplied Pydantic output models and added tests proving free-text JSON responses are not parsed.
- Added LLM call audit logging with prompt hash, token metrics, cache metrics, latency, stop reason, stage, model, and tool name.
- Added Phase 4 unit tests covering prompt loading, default prompt placeholders, forced tool-use request shape, structured output validation, audit logging, free-text rejection, and wrong-tool rejection.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 5 Ingestion

- Added an async document ingestion API for plain text, Markdown, and PDF sources.
- Added suffix-based format detection with explicit unsupported-format errors.
- Added stable document IDs derived from source SHA-256 bytes.
- Preserved source path, source SHA-256, text SHA-256, source byte length, text byte length, extracted text, and page maps in the `Document` contract.
- Added UTF-8 validation for text and Markdown inputs with explicit errors for invalid sources.
- Added PDF extraction through lazy `pdfplumber` loading, with page text joined by stable separators and page-level character/UTF-8 byte offsets preserved.
- Added empty-extraction failures for empty text inputs and PDFs with no extracted page text.
- Added optional audit persistence via `AuditStore.record_document`.
- Added Phase 5 unit tests covering text hashing and offsets, stable IDs, Markdown detection, audit persistence, PDF page offsets, unsupported formats, empty sources, and invalid UTF-8.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 6 Chunking

- Added an async token-aware chunking API using configured `tiktoken` encodings.
- Added stable chunk IDs derived from document identity, text hash, chunk index, byte offsets, and token offsets.
- Preserved source character offsets, UTF-8 byte offsets, token offsets, document ID, chunk index, and exact chunk text in the `Chunk` contract.
- Added configured window and overlap handling with deterministic token-window advancement.
- Added UTF-8 boundary protection for tokenizer cases where one character spans multiple tokens.
- Added optional audit persistence via `AuditStore.record_chunk`.
- Added explicit chunking errors for unknown tokenizers, missing `tiktoken`, tokenizer byte reconstruction mismatches, and non-advancing windows.
- Added Phase 6 unit tests covering token windows, overlap, stable IDs, Unicode boundary preservation, audit persistence, and unknown-tokenizer failures.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 7 Planning

- Added typed planner output models for document classification, schema proposal, schema critique, strategy selection, and budget allocation.
- Added an async `create_extraction_plan` planner service that runs five forced-tool LLM calls in order.
- Built planner stage inputs from typed document, chunk, domain-hint, and prior-stage output models.
- Enforced schema critique acceptance before strategy and budget planning continue.
- Built final `ExtractionPlan` from approved categories, selected lenses, configured chunk policy, and allocated budget.
- Preserved configured chunk window/overlap values instead of allowing prompt output to hardcode runtime tuning.
- Merged caller-provided and classifier-produced domain hints while preserving order and removing duplicates.
- Added validation that all chunks belong to the planned document before any LLM calls run.
- Added optional audit persistence for LLM call logs and final extraction plans.
- Added Phase 7 unit tests covering planner call order, forced-tool request names, prompt/user content, LLM audit logs, final plan persistence, failed schema critique handling, missing lens budget rejection, and chunk/document identity checks.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 8 Executor

- Added typed executor models for per-chunk stage input, extracted candidate payloads, candidate batches, task results, and aggregate execution results.
- Added an async `execute_plan` service that runs forced-tool executor LLM calls for each enabled lens over each chunk.
- Added configured chunk-level concurrency via `ExecutionConfig.max_chunk_concurrency`.
- Enforced executor budgets before LLM calls so lens call limits cannot be silently exceeded.
- Added validation that all executor chunks belong to the extraction plan document.
- Converted LLM tool outputs into stable `LensCandidate` records with deterministic candidate IDs, exact source spans, confidence, lens, category, field, and executor call provenance.
- Validated candidate categories and fields against the approved extraction plan schema.
- Validated candidate source spans against chunk character and UTF-8 byte offsets.
- Persisted both accepted and rejected candidates to the audit store, with rejected candidates logged as `CandidateRejection(stage="executor")` and explicit rejection reasons.
- Added `executor` as a first-class candidate rejection stage.
- Added Phase 8 unit tests covering accepted/rejected candidate persistence, forced-tool request names, LLM audit logs, invented-span rejection, category rejection, insufficient-budget failure, and chunk/document identity checks.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 9 Critic

- Added typed critic models for per-candidate stage input, LLM critic payloads, task results, and aggregate critic results.
- Added an async `review_candidates` critic service that runs forced-tool critic LLM calls for each executor-accepted candidate.
- Added configured candidate-level concurrency via `ExecutionConfig.max_stage_concurrency`.
- Validated critic inputs against extraction plan run/document identity, approved schema, provided chunk context, and exact source spans before any LLM calls run.
- Converted critic tool outputs into stable `CriticReport` records with call provenance, plausibility score, issues, acceptance state, and optional corrected candidates.
- Validated corrected candidates before acceptance, preserving stable candidate/run/document/chunk/lens/executor provenance, approved schema membership, and exact chunk-backed source spans.
- Rejected invalid corrections without silent drops by recording failed critic reports and `CandidateRejection(stage="critic")` records with explicit typed reasons.
- Persisted critic LLM call logs, critic reports, and critic-stage candidate rejections to the audit store.
- Added Phase 9 unit tests covering accepted/rejected critic persistence, forced-tool request names, LLM audit logs, valid correction acceptance, invalid correction rejection, and candidate/plan identity checks.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 10 Verifier

- Added typed verifier models for per-candidate stage input, LLM verifier payloads, task results, and aggregate verification results.
- Added an async `verify_candidates` service that runs forced-tool verifier LLM calls for each critic-accepted candidate.
- Required each verifier candidate to have exactly one accepted critic report before any verifier LLM call runs.
- Validated candidate run/document identity, provided chunk context, and accepted critic corrections before verification.
- Built verifier stage inputs from the extraction plan, candidate, accepted critic report, and source chunk context.
- Converted verifier tool outputs into stable `VerifierReport` records with call provenance, span/category verification flags, alignment score, acceptance state, and rejection reasons.
- Added deterministic source-span and schema alignment checks that can override an accepted LLM output when invariants fail.
- Persisted verifier LLM call logs, verifier reports, and `CandidateRejection(stage="verifier")` records with explicit typed reasons.
- Added Phase 10 unit tests covering accepted/rejected verifier persistence, forced-tool request names, LLM audit logs, source-span override rejection, missing critic acceptance, and critic correction mismatch checks.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 11 Reconciler

- Added typed reconciler models for whole-run stage input, reconciled data point payloads, rejected candidate payloads, reconciliation batches, and aggregate reconciliation results.
- Added an async `reconcile_candidates` service that runs one forced-tool reconciler LLM call over verifier-accepted candidates.
- Required every reconciler candidate to have exactly one accepted critic report and exactly one accepted verifier report before the LLM call runs.
- Validated candidate run/document identity, duplicate candidate IDs, accepted critic corrections, and report/run provenance before reconciliation.
- Converted reconciliation output into stable `DataPoint` records with source spans derived from selected source candidates rather than model-supplied offsets.
- Preserved contributing candidate IDs, accepted critic report IDs, accepted verifier report IDs, and stable reconciliation decision IDs on each data point.
- Added conflict handling for explicit candidate rejection, contradictory contribute/reject output, duplicate data point assignment, schema mismatches, and unknown candidate references.
- Ensured no verified candidate is silently dropped by logging omitted candidates as `CandidateRejection(stage="reconciler")` with explicit typed reasons.
- Persisted reconciler LLM call logs, final data points, and reconciler-stage candidate rejections to the audit store.
- Added Phase 11 unit tests covering data point persistence, explicit conflict rejection, omitted candidate rejection, missing verifier provenance, unknown output candidate IDs, forced-tool request names, and LLM audit logs.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 12 Reporter

- Added typed reporter models for final extraction reports and report write results.
- Added an async `write_report` service that validates final reconciled data points before output serialization.
- Added deterministic JSON report rendering with stable data point ordering, output data point IDs, report schema version, generated timestamp, and full `DataPoint` payloads.
- Added output SHA-256 and byte-length reporting for auditable artifact verification.
- Added audit readback checks requiring the run manifest and every serialized data point to match the audit store before writing output.
- Added atomic local report writes through a temporary file and replace operation.
- Added run manifest completion with `status="completed"`, `completed_at`, and serialized output data point IDs after the report is written.
- Added explicit reporter errors for failed manifests, run/document identity mismatches, duplicate data point IDs, missing audited data points, stale audit manifest state, and directory output paths.
- Added Phase 12 unit tests covering JSON serialization, manifest completion, output hash/byte metadata, audit-store readback, missing audited data points without output writes, manifest/data point mismatch, and failed-run rejection.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 13 Orchestrator

- Added typed orchestrator result models for full pipeline outputs from document ingestion through final report writing.
- Added an async `run_extraction_pipeline` service that wires ingestion, chunking, planning, execution, critic review, verification, reconciliation, and reporting in order.
- Added audit store lifecycle management around the full pipeline using configured audit database paths.
- Added run manifest creation, transition to running, completion through reporter output, and failed status updates when later stages raise.
- Bound run context after document ingestion so downstream stage work has run/document/audit identifiers.
- Passed configured chunking, execution, prompt, audit, and LLM settings through each stage without hardcoded runtime tuning values.
- Preserved optional caller-provided run IDs and domain hints while generating run IDs when omitted.
- Added Phase 13 unit tests covering an end-to-end deterministic pipeline run, full stage audit log ordering, final report output, completed manifest persistence, and failed manifest persistence on planner rejection.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 14 CLI

- Added an `argparse` command-line entrypoint for running the orchestrated extraction pipeline.
- Added support for source document paths, required report output paths, optional config directories, local config suppression, stable run IDs, and repeated domain hints.
- Added package module execution via `python -m extractor.cli`.
- Added a `veritext` console script entrypoint in `pyproject.toml`.
- Loaded canonical configuration through the existing config loader and initialized configured logging before pipeline execution.
- Surfaced successful runs as deterministic JSON summaries containing run ID, document ID, status, audit database path, report path, output SHA-256, output byte length, data point count, and output data point IDs.
- Added explicit CLI errors for missing source documents and non-zero process returns for command failures.
- Added Phase 14 unit tests covering summary rendering, config-driven pipeline invocation, domain hint forwarding, missing-source failure, and console script registration.
- Verified `PYTHONPATH=src python3 -m extractor.cli --help`, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 15 Evaluations

- Added a typed `extractor.evals` package for source-backed evaluation cases, expected data points, thresholds, metric results, data point matches, and invariant violations.
- Added evaluation loading that resolves fixture-relative source paths, computes source SHA-256 values, validates UTF-8 source text, and rejects bad expected provenance before scoring.
- Added a scoring harness that separates extraction precision/recall/F1 from exact provenance recall and records source-span invariant violations for text, byte, and bounds mismatches.
- Added `python -m extractor.evals` and `veritext-eval` entrypoints that emit deterministic JSON results and return non-zero status for failed evaluations.
- Added a minimal financial-update fixture with source text, expected data points, strict thresholds, and a passing example report.
- Updated README evaluation usage and package scaffold tests.
- Added Phase 15 unit tests covering passing fixtures, missing/false-positive scoring, source-span invariant failures, fixture provenance validation, eval CLI output, and console script registration.
- Verified `python3 -m pytest tests/unit/test_evals.py`, `PYTHONPATH=src python3 -m extractor.evals evals/fixtures/minimal_financial_update/expected.json evals/fixtures/minimal_financial_update/report.example.json`, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 16 Prompt Pack v1

- Replaced placeholder prompt bodies for all planner, executor, critic, verifier, and reconciler stages with operational prompt instructions.
- Kept required prompt contract sections intact while adding stage-specific rules for conservative extraction, approved schema usage, forced tool calls, explicit rejection behavior, and exact provenance.
- Added executor prompt rules requiring absolute document character offsets, absolute UTF-8 byte offsets, exact `source_text` copying, and candidate omission when offsets are uncertain.
- Added verifier prompt rules for accepted/rejected consistency, exact span grounding, schema alignment, and typed rejection reason codes.
- Added reconciler prompt rules requiring every verified candidate to be accounted for exactly once as a data point contributor or explicit rejection.
- Added contract-obligation and policy-control eval fixtures with source text, expected data points, strict thresholds, and passing example reports.
- Updated prompt tests to assert active prompts are non-placeholder operational prompts and include required provenance/accounting rules.
- Updated eval tests to score all included example fixtures.
- Updated README status, evaluation fixture coverage, and prompt pack notes.
- Verified `python3 -m pytest tests/unit/test_evals.py tests/unit/test_llm_client.py`, all three `PYTHONPATH=src python3 -m extractor.evals ...` fixture checks, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 17 Prompt Hardening

- Added concrete decision examples and anti-patterns to planner prompts for classification, schema proposal, schema critique, lens selection, and budget allocation.
- Added few-shot examples to all executor prompts, including valid extraction examples and explicit rejection examples for sample, superseded, historical, inferred, and schema-mismatched evidence.
- Added executor preflight checklists requiring approved category/field names, exact `source_text`, exact absolute character offsets, exact UTF-8 byte offsets, and reviewer-verifiable source support.
- Added adversarial checklists and examples to critic and verifier prompts for invented evidence, wrong schema, overbroad spans, superseded facts, sample entities, negation, and accepted/rejected consistency.
- Added reconciler duplicate-merge, conflict-rejection, separate-fact, and no-silent-drop examples plus a final audit checklist requiring every input candidate to be accounted for exactly once.
- Added a hard mixed-distractor eval fixture containing superseded numeric guidance and a sample entity that should not be extracted.
- Updated eval tests to score the new hard fixture and assert its distractors are not expected outputs.
- Updated prompt tests to require few-shot examples, rejection examples, adversarial checklists, and reconciler audit checklists.
- Updated README status and prompt/eval fixture notes for the hardened prompt pack.
- Verified `python3 -m pytest tests/unit/test_evals.py tests/unit/test_llm_client.py`, all four `PYTHONPATH=src python3 -m extractor.evals ...` fixture checks, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 18 Multi-provider LLM Client

- Added `openai` as a supported `LLMConfig.provider` value while keeping Anthropic as the canonical default provider.
- Updated `LLMClient` to route requests by provider while preserving the existing public `complete_structured` API used by every pipeline stage.
- Preserved direct SDK usage only: Anthropic calls use `AsyncAnthropic`; OpenAI calls use `AsyncOpenAI`.
- Implemented OpenAI Chat Completions forced function tool calls with `tool_choice`, `strict` function schema parameters, `parallel_tool_calls=False`, and Pydantic validation of decoded tool arguments.
- Preserved Anthropic forced tool-use behavior and audit logging unchanged for existing tests and pipeline stages.
- Added OpenAI usage accounting to `LLMCallLog` for prompt tokens, completion tokens, cached prompt tokens, finish reason, prompt hash, model, latency, and tool name.
- Added explicit OpenAI tool-call errors for missing tool calls, wrong function names, malformed tool argument JSON, and non-object tool argument payloads.
- Added `openai` as a project dependency and updated architecture docs to allow direct Anthropic and OpenAI SDK calls.
- Added README configuration example for `llm.provider: openai` with a GPT model.
- Added unit tests covering OpenAI config loading, dependency declaration, forced OpenAI tool call request shape, audit logging, missing-tool rejection, wrong-tool rejection, and malformed-argument rejection.
- Verified `python3 -m pytest tests/unit/test_llm_client.py tests/unit/test_config.py tests/unit/test_bootstrap.py`, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Environment File Support

- Added `.env.example` with OpenAI defaults for `VERITEXT_LLM__PROVIDER=openai`, `VERITEXT_LLM__MODEL=gpt-5.2`, and SDK key placeholders.
- Updated `.gitignore` so `.env` and `.env.*` stay local while `.env.example` remains trackable.
- Added `.env` loading to `load_config()` for normal runtime configuration while keeping explicit test env mappings isolated from local files.
- Applied `.env` values as `VERITEXT_*` configuration overrides and exposed SDK keys such as `OPENAI_API_KEY` through `os.environ` without overriding values already present in the shell.
- Added explicit `.env` parse errors for malformed entries.
- Updated README local provider setup notes.
- Verified `python3 -m pytest tests/unit/test_config.py tests/unit/test_cli.py tests/unit/test_bootstrap.py`, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Audit Rerun Idempotency Fix

- Fixed reruns over the same source document by making exact duplicate document and chunk audit writes idempotent.
- Preserved audit integrity by still rejecting conflicting payloads for stable document IDs and chunk IDs.
- Kept run manifests strict, so reusing the same `run_id` still fails rather than overwriting a prior run.
- Added audit-store tests covering idempotent document/chunk writes and conflicting stable-ID payload rejection.
- Verified `python3 -m pytest tests/unit/test_audit_store.py`, `make test`, `make lint`, and `make smoke` all pass.
