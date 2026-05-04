# Phase 27 - Planner Schema Reuse and Schema-Fit Refusal

Status: approved by operator on 2026-05-05. Implementation starts only from `docs/boards/phase_27_planner_schema_reuse_and_schema_fit_refusal.md`.

Date opened: 2026-05-05

Roadmap sources:

- `docs/PROJECT_OVERVIEW.md`:
  - `Improvement Roadmap - Accuracy, Generalization, and Provenance`
  - Planner roadmap
  - Highest-leverage item 1
  - Target Domains configurable/non-configurable split
- `docs/phase_26_plus_roadmap.md`
- `docs/boards/README.md`
- `PROGRESS.md`
- Phase 26 board and completed commits through `f034356`

## Goal

Make the planner reuse explicit approved schemas when they fit the source document, and produce a structured, audited refusal when no approved schema fits under configured policy.

Phase 27 closes the main planner failure mode left by Phase 26: the planner can now carry schema identity, but it still always invents or approves a schema for the current document. This phase adds the typed selection and refusal boundary needed to prevent silent mis-extraction.

## Non-Goals

- Do not add the legal contracts domain pack. That is Phase 28.
- Do not add broad fixture-corpus scoring or per-field evaluation gates. Those begin in Phase 29.
- Do not add new extraction lenses, normalization policy, cross-document reconciliation, or ingestion formats.
- Do not add web UI, REST API, Docker, CI/CD, vector DBs, embeddings, fine-tuning hooks, or agent frameworks.
- Do not optimize for a single fixture, company, document, market sector, or expected answer.
- Do not hardcode a domain-specific approved schema in source code.
- Do not silently fall back to planner-generated schemas when configured policy requires an approved schema.
- Do not make prompt bodies domain-specific.

## Domain-Scope Alignment

Veritext remains one domain-neutral extraction kernel with configurable, auditable domain assumptions.

Configurable in Phase 27:

- Approved schema registry artifacts.
- Schema selection policy and coverage threshold.
- Whether planner-generated fallback is allowed when no registry schema fits.
- Domain-pack and schema-registry metadata used to match document class and domain hints.
- Refusal reason codes and refusal report metadata.

Non-configurable in Phase 27:

- Exact source span matching.
- Byte and character offsets.
- Source and text hashes.
- Forced tool use for all LLM structured outputs.
- Pydantic stage contracts.
- SQLite audit persistence.
- No-silent-drop rejection accounting.
- Schema hash validation against approved categories.
- Planner refusal cannot be treated as successful extraction with zero findings.

## Stage and Module Boundaries

### Contracts

Extend schema/planner contracts without weakening Phase 26 schema metadata validation.

Expected additions:

- A typed approved-schema artifact contract that combines `ApprovedSchemaMetadata` with its approved `CategoryDefinition` tuple and match metadata.
- A schema-selection contract that records candidate schema IDs, selected schema ID, document class, domain hints, match basis, and coverage estimate.
- A planner refusal contract with stable reason codes, selected or rejected schema IDs, coverage details, and source policy.
- A pipeline result or outcome contract that can represent either extraction success or schema-fit refusal without optional loose dictionaries.

Expected reason codes include:

- `no_approved_schema_candidates`
- `ambiguous_schema_candidates`
- `coverage_below_threshold`
- `document_out_of_scope`
- `schema_hash_mismatch`
- `schema_registry_invalid`

Reason code names may be refined during implementation, but the final set must be explicit, tested, and stable enough for operators to filter audit results.

### Schema Registry

Add a focused loader under `src/extractor/planner/` or a cohesive sibling module.

Registry artifacts should be YAML to match Phase 26 domain-pack artifacts and `config/default.yaml`. A registry artifact must include:

- schema metadata
- approved categories and fields
- document class
- domain hints or pack identity used for matching
- schema hash that matches the approved categories through `canonical_schema_hash(...)`

Invalid artifacts must fail explicitly before any extraction stages run. Tests must not depend on the operator's real `.veritext` state.

Phase 27 should treat the registry as approved input. Automatic registration of newly planner-generated schemas is an open implementation question below because it affects governance and the meaning of "approved".

### Planner

Planner flow should become policy-aware:

1. Classify the document as today.
2. Load and validate approved schema registry artifacts from configured paths.
3. Build a deterministic candidate set by document class, domain hints, and optional domain-pack identity.
4. If candidates exist, assess schema fit through forced structured output or a deterministic policy when enough metadata exists.
5. If exactly one schema fits above the configured threshold, construct `ExtractionPlan` from that approved schema and skip schema proposal/critique for category creation.
6. Select lenses and allocate budget as today, using the reused approved categories.
7. If no schema fits and policy requires an approved schema, stop with a structured planner refusal.
8. If policy allows planner-generated fallback, use the existing propose/critique path and keep Phase 26 planner-generated schema metadata.

The reused-schema path must not mutate approved category semantics. If the planner needs to refine category names, fields, or descriptions, that is a new schema and must not be reported as reuse of the approved schema.

### Orchestrator

The orchestrator must handle a planner refusal as a terminal audited outcome, not as an exception that marks the run failed.

Expected behavior:

- Ingestion and chunking remain recorded.
- Planner LLM calls and selection/refusal payloads remain auditable.
- Executor, dedup, critic, verifier, reconciler, and success reporter do not run after refusal.
- The run manifest uses an explicit terminal status or equivalent strict contract that distinguishes refusal from failure and success.
- The CLI returns a clear refusal summary and non-success extraction path without hiding the reason code.

Implementation may still raise explicit errors for malformed registry artifacts or invariant failures. Those are defects, not planner refusals.

### Audit

Do not store refusal only in terminal output.

The accepted audit surface for Phase 27 should use existing SQLite payload mechanisms unless implementation proves a new table is required. Acceptable approaches include embedding refusal details in a strict planner-stage audit payload or adding a small refusal payload record through an auditable model. If a new audit table or schema version is required, the board must pin the migration interpretation before code changes.

Required audit properties:

- A stored run is sufficient to distinguish extraction success, schema-fit refusal, and infrastructure failure.
- A refusal stores reason codes, candidate schema IDs, coverage estimates if present, document class, domain hints, and policy threshold.
- Stored LLM calls continue to show forced tool use and prompt hashes.
- Resume behavior refuses to continue a terminal refusal as though it were an incomplete run.

### Reporter and CLI

Refusal output must be machine-readable.

Expected report behavior:

- Successful extraction reports continue to include schema metadata and data points.
- Refusal reports include run ID, document ID, refusal reason codes, candidate schema IDs, coverage details, policy threshold, and schema registry identity.
- Refusal reports must not include fabricated empty data points.
- Report serialization remains deterministic.

The CLI JSON summary should expose the outcome type and schema/refusal identity so operators do not need to open the report file to know whether extraction ran or refused.

## Contract Changes

Expected Pydantic additions or equivalent focused models:

- `ApprovedSchemaArtifact`
- `SchemaSelectionPolicy`
- `SchemaFitAssessment`
- `SchemaCoverageEstimate`
- `PlanningRefusal`
- `PipelineRefusalResult` or a strict discriminated outcome model
- `ExtractionRefusalReport` or a strict report union if report schema advances

Expected existing model changes:

- `SchemaSourceKind` may need a new source kind if reused registry schemas need to distinguish registry selection from planner generation and domain-pack templates.
- `RunStatus` may need a terminal refusal status.
- `PlanningStageInput` may need approved schema candidates or compact schema cards.
- `PipelineRunResult` consumers may need to handle a success/refusal outcome union.

Model constraints:

- Extra fields remain forbidden.
- Models remain frozen.
- Registry schemas must validate their canonical hash before use.
- Refusal reason codes must be strict literals, not free-form strings.
- Coverage estimates must be bounded floats and must identify the schema and category they evaluate.

## Audit and Provenance Effects

Phase 27 improves auditability by making "do not extract" a first-class outcome.

Required properties:

- A planner refusal preserves document identity, source hashes, chunk records, prompt hashes, LLM call logs, candidate schema IDs, and reason codes.
- A reused schema plan preserves the exact approved schema ID, version, hash, source kind, approved categories, enabled lenses, chunk policy, and budget.
- No candidate, critic, verifier, reconciler, or data-point provenance fields are removed or relaxed.
- A schema-fit refusal never emits source-backed data points because no approved extraction schema was selected.

## Invariant Impact

Do not weaken I1-I9. Phase 27 touches planner and orchestrator control flow, so invariant risk is high.

Required protections:

- Source text, byte offsets, character offsets, and source hashes remain unchanged.
- Registry metadata cannot relax source-span validation.
- Reused schemas cannot relax approved-category validation for candidates.
- Forced tool use remains the only LLM structured-output path.
- Pydantic contracts remain strict at stage boundaries.
- SQLite remains the audit state backend.
- No rejection, refusal, or terminal-outcome accounting path may silently drop records.
- Existing success runs remain decision-equivalent unless a configured approved-schema policy is enabled.
- Refusal is not failure; malformed artifacts or invariant violations are failures.

If implementation exposes ambiguity in terminal run status, audit schema evolution, or default fallback policy, log it on the Phase 27 board and stop before editing behavior.

## Configuration Changes

Extend canonical config in `config/default.yaml`.

Expected settings:

```yaml
schema_registry:
  directory: .veritext/schema_registry
  require_approved_schema: false
  minimum_schema_coverage: 0.65
```

The exact names may be refined during implementation, but runtime tuning values must live in config and validate through Pydantic.

Rules:

- Default local runs should remain safe when no registry directory exists.
- Tests must use temporary schema registry directories or fixtures.
- `config/local.yaml` and environment variables may override policy and threshold.
- Enabling `require_approved_schema` must prevent silent fallback to invented schemas.
- Invalid thresholds, malformed registry artifacts, and hash mismatches fail explicitly.

## Prompt Changes

Phase 27 may need a schema-fit assessment planner stage.

Allowed prompt-related work:

- Add or update prompt metadata for a schema-fit assessment stage.
- Add typed input and output documentation for schema candidates, coverage estimates, and refusal reason codes.
- Add human-authored instruction blocks only where project prompt rules allow.
- Keep all new structured outputs behind forced tool use.

Disallowed prompt-related work:

- Domain-specific examples for legal contracts, SEC filings, clinical documents, or other target domains.
- Prompt text that tells the model to invent a schema when approved-schema policy requires refusal.
- Free-text JSON parsing.
- Refusal reason text that only exists in prose and not in typed contracts.

## Tests and Evaluation Gates

Required narrow tests:

- Contract tests for registry artifact validation, hash mismatch rejection, selection policy validation, coverage estimates, and refusal models.
- Loader tests for valid YAML registry artifacts, missing directories, malformed artifacts, duplicate schema IDs, and unsupported files.
- Planner tests proving approved schemas are reused without propose/critique schema invention when a candidate fits.
- Planner tests proving below-threshold coverage or out-of-scope classification produces structured refusal when policy requires approved schemas.
- Planner tests proving fallback to planner-generated schemas remains decision-equivalent when policy allows fallback and no registry schema fits.
- Orchestrator tests proving refusal stops before executor and records a terminal non-failure outcome.
- Resume tests proving terminal refusals cannot resume as incomplete runs.
- Reporter and CLI tests proving refusal reports and summaries serialize deterministically.
- Audit-store tests proving refusal or planner-stage payloads round-trip through SQLite.

Required broader verification before Phase 27 completion:

```bash
make test
make lint
make smoke
git diff --check
```

Evaluation gate:

- Existing smoke/eval fixtures remain decision-equivalent unless a test explicitly enables approved-schema policy.
- A generic out-of-scope fixture with strict approved-schema policy produces a structured refusal, not fabricated extraction output.
- No existing successful report drops schema metadata.

## Implementation Order

1. Add failing contract tests for registry artifacts, schema selection policy, fit assessment, and planner refusal.
2. Implement the smallest contract additions needed to pass those tests.
3. Add failing config tests for schema registry policy and coverage threshold.
4. Implement config model/default YAML support.
5. Add failing schema registry loader tests with synthetic generic fixtures.
6. Implement registry artifact loading and canonical hash validation.
7. Add failing planner tests for candidate matching and reused-schema plan construction.
8. Implement deterministic candidate matching and approved-schema plan materialization.
9. Add failing planner tests for coverage-based refusal and fallback behavior.
10. Implement schema-fit assessment, refusal construction, and policy branching.
11. Add failing orchestrator/audit tests for terminal refusal handling.
12. Implement terminal refusal flow, audit persistence, and resume safeguards.
13. Add failing reporter and CLI tests for refusal reports and JSON summaries.
14. Implement refusal report serialization and CLI summary output.
15. Run narrow tests, project-level verification, and update board/progress after the board exists.

## Expected Board Steps

When the board is created after spec approval, use these steps unless implementation planning exposes a better equivalent split:

1. Schema registry, selection policy, fit assessment, and refusal contracts.
2. Config surface for schema registry policy and coverage threshold.
3. Schema registry loader validation and hash enforcement.
4. Planner approved-schema candidate matching and reuse path.
5. Planner schema-fit refusal and fallback policy.
6. Orchestrator, audit, resume, reporter, and CLI refusal propagation.
7. Final verification, board/progress updates, and commit hygiene.

## Gate Criteria

Phase 27 is complete only when:

- Approved schema registry artifacts validate through strict Pydantic contracts.
- Schema registry hash mismatches fail before use.
- Planner can reuse a fitting approved schema without mutating approved category semantics.
- Planner emits structured refusal with stable reason codes when policy requires approved schema and no candidate fits.
- Planner-generated fallback remains available only when configured policy allows it.
- Terminal refusal is audited and distinguishable from success and failure.
- Refusal report and CLI summary are deterministic and machine-readable.
- Existing success smoke/eval behavior is unchanged unless approved-schema policy is explicitly enabled.
- No domain-specific source-code patch is introduced.
- No prompt body is made domain-specific.
- Relevant narrow tests pass.
- `make test`, `make lint`, `make smoke`, and `git diff --check` pass when feasible.
- All Phase 27 board issues are resolved or explicitly deferred.
- `PROGRESS.md` is updated.

## Open Questions Before Implementation

1. Should the Phase 27 registry be read-only approved input, or should planner-generated schemas be written as proposed registry artifacts for later approval?
2. Should `require_approved_schema` default to `false` to preserve existing local runs, or should strict refusal be the default once any registry artifact exists?
3. Should refusal output advance the main report schema to a success/refusal union, or use a separate refusal report contract while leaving success reports at `report.v2`?
4. Should Phase 27 extend domain-pack schema templates to include full approved categories, or keep full reusable schemas in the schema registry until the Phase 28 legal pack?
