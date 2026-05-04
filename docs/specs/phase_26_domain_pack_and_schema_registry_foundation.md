# Phase 26 - Domain Pack and Schema Registry Foundation

Status: draft for operator approval. This spec does not authorize implementation until the operator approves it and a Phase 26 board is created.

Date opened: 2026-05-04

Roadmap sources:

- `docs/PROJECT_OVERVIEW.md`:
  - `Improvement Roadmap - Accuracy, Generalization, and Provenance`
  - Planner roadmap
  - Highest-leverage item 1
  - Target Domains configurable/non-configurable split
- `docs/phase_26_plus_roadmap.md`
- `docs/boards/README.md`
- `PROGRESS.md`

## Goal

Create the typed, versioned, hashed foundation for domain packs and approved schema metadata without changing extraction decisions yet.

Phase 26 makes future planner phases auditable by giving every run a stable schema identity and a validated domain-pack metadata surface. The planner may still propose schemas exactly as it does today, but the resulting plan/report/audit payload must carry explicit schema metadata and deterministic hashes.

## Non-Goals

- Do not implement schema-fit refusal. That is Phase 27.
- Do not implement schema reuse or planner cache lookup. That is Phase 27.
- Do not add the legal contracts domain pack. That is Phase 28.
- Do not add new extraction lenses, normalization policy, or cross-document reconciliation.
- Do not change prompt bodies beyond any mechanical schema-field naming needed to preserve existing behavior.
- Do not add new audit DB tables or schema migrations in this phase.
- Do not add web UI, REST API, Docker, CI/CD, vector DBs, embeddings, fine-tuning hooks, or agent frameworks.
- Do not optimize for a single fixture, company, document, market sector, or expected answer.

## Domain-Scope Alignment

Veritext must keep one domain-neutral extraction kernel and many configurable domain packs.

Configurable in Phase 26:

- Domain-pack identity and metadata.
- Schema template identity and metadata.
- Field-role and lens-selection declarations as metadata only.
- Reporting expectation declarations as metadata only.
- Canonical schema hash and version strings.

Non-configurable in Phase 26:

- Exact source span matching.
- Byte and character offsets.
- Source and text hashes.
- Forced tool use.
- Pydantic stage contracts.
- SQLite audit persistence.
- No-silent-drop rejection accounting.
- Invariant enforcement.

The first proving-ground domain remains legal contracts, but Phase 26 must not add legal-specific behavior. Any sample domain-pack fixture used for tests must be small, synthetic, and generic enough to validate metadata mechanics rather than extraction quality.

## Stage and Module Boundaries

### Contracts

Add schema/domain-pack metadata contracts under `src/extractor/contracts/` or a cohesive sibling module imported by `src/extractor/contracts/__init__.py`.

Expected model responsibilities:

- Domain-pack metadata: stable ID, display name, version, domain hints, schema template IDs, supported document classes, and optional reporting/lens metadata.
- Approved-schema metadata: schema ID, schema version, schema hash, source kind, domain-pack ID if present, document class if present, and created/refined provenance.
- Canonical hash input: deterministic, sorted, audit-safe projection of approved categories and schema-relevant metadata.

The existing `ExtractionPlan` should gain schema metadata while preserving current approved categories, lenses, chunk policy, and budget behavior.

### Config

Add typed config for domain-pack and schema-registry locations. Keep runtime tuning in `config/default.yaml`; do not hardcode paths in source or tests.

Suggested config shape:

```yaml
domain_packs:
  directory: config/domain_packs
schema_registry:
  directory: .veritext/schema_registry
```

Implementation may choose clearer names during code work, but both config areas must validate through Pydantic and support environment/local YAML overrides.

### Planner

Planner behavior remains decision-equivalent in Phase 26:

- It still calls classify, propose, critique, select strategy, and allocate budget as today.
- It still records the plan after critique and strategy/budget construction.
- It derives schema metadata from the approved categories plus explicit pack/registry metadata.
- If no domain pack is configured, it must use an explicit neutral source kind such as `planner_generated`.

Phase 26 may add a domain-pack loader that validates artifacts but does not yet make planner selection or refusal decisions.

### Audit

Do not add new audit tables in Phase 26.

The accepted decision for this phase is to embed schema metadata in existing Pydantic payloads:

- `ExtractionPlan` payload in `extraction_plans.payload_json`.
- Final report payload.
- Any CLI summary field needed to make the schema identity visible.

Dedicated schema registry audit tables, schema migrations, and backward-compatible audit DB evolution are deferred to a later schema-migration or audit phase.

### Reporter

Add schema metadata to `ExtractionReport` so every report can cite the schema ID/version/hash used for extraction.

The report schema version may advance if required. If it advances, tests must prove old report behavior is intentionally updated and the serialized output remains deterministic.

### Orchestrator and CLI

The orchestrator should pass enough configured pack/registry context into the planner to build schema metadata.

The CLI should expose schema identity in its JSON summary if the final `PipelineRunResult` includes it. A new CLI flag is not required in Phase 26 unless implementation shows config-only pack selection is insufficient.

## Contract Changes

Expected Pydantic additions:

- `DomainPackMetadata`
- `SchemaTemplateMetadata` or equivalent if pack artifacts need template entries.
- `ApprovedSchemaMetadata`
- `SchemaSourceKind` literal, with at least `planner_generated` and `domain_pack_template`.

Expected existing model changes:

- `ExtractionPlan` gains `schema_metadata: ApprovedSchemaMetadata`.
- `ExtractionReport` gains `schema_metadata: ApprovedSchemaMetadata`.
- `PipelineRunResult` continues to expose `plan`; no new result field is required if schema metadata is available through `plan` and `report`.

Model constraints:

- Extra fields remain forbidden.
- Models remain frozen.
- Hash inputs must not include run IDs, timestamps, absolute local paths, data point IDs, LLM call IDs, or any nondeterministic ordering.
- Schema hashes must change when category/field semantics change.
- Schema hashes must not change when run-specific identifiers change.

## Audit and Provenance Effects

Phase 26 improves auditability by making the schema identity explicit in existing persisted payloads. It must not weaken any current audit path.

Required audit properties:

- A stored extraction plan is sufficient to recover the schema ID, version, source kind, hash, approved categories, enabled lenses, chunk policy, and budget.
- A final report is sufficient to cite the same schema identity as the stored extraction plan.
- Existing audit-store idempotency and resume checks continue to validate the full Pydantic payload.
- No candidate, critic, verifier, reconciler, or data-point provenance fields are removed or relaxed.

## Invariant Impact

The current docs require preserving I1-I9 but do not enumerate their names in a single source file. Phase 26 must therefore treat the enforced invariant surfaces as non-negotiable and avoid changing them unless tests prove behavior is unchanged.

Required invariant protections:

- Exact source text, byte offsets, character offsets, and source hashes remain unchanged.
- Domain-pack metadata cannot relax source-span validation.
- Domain-pack metadata cannot relax approved-category validation for candidates.
- Forced tool use remains the only LLM structured-output path.
- Pydantic contracts remain strict at stage boundaries.
- SQLite remains the audit state backend.
- No rejection or candidate accounting path may silently drop records.
- Schema hash computation must be deterministic and covered by tests.
- Existing evaluator invariant checks must continue to pass.

If implementation exposes an ambiguity in I1-I9 definitions, log it on the Phase 26 board and stop before editing invariant behavior.

## Configuration Changes

Add canonical config entries to `config/default.yaml` for domain-pack and schema-registry locations.

Rules:

- Defaults must be safe for local runs.
- `config/local.yaml` and environment variables may override locations.
- Tests must not depend on the user's real `.veritext` state.
- Missing optional directories should not break current extraction runs unless a pack is explicitly requested.
- Invalid configured artifacts must fail with explicit errors.

## Prompt Changes

Prompt bodies should remain behavior-equivalent in Phase 26.

Allowed prompt-related work:

- Mechanical updates needed if compact schema cards or plan metadata field names change.
- Tests that prove existing prompt loading and structured tool calls still work.

Disallowed prompt-related work:

- Domain-specific examples.
- Legal-contract extraction instructions.
- Schema-fit refusal instructions.
- Planner few-shot approved-schema examples.
- Coverage threshold instructions.

Those belong to later phases.

## Tests and Evaluation Gates

Required narrow tests:

- Contract tests for schema/domain-pack metadata validation.
- Hash tests proving deterministic schema hashes and expected hash changes.
- Config tests for new pack/registry config sections and overrides.
- Planner tests proving schema metadata is attached to generated plans without changing approved categories/lenses/budget.
- Reporter tests proving schema metadata serializes into final reports.
- Audit-store tests proving extraction plans round-trip with schema metadata through existing payload storage.
- CLI or orchestrator summary tests if schema identity is exposed in summaries.

Required broader verification before Phase 26 completion:

```bash
make test
make lint
make smoke
git diff --check
```

Evaluation gate:

- Because Phase 26 should not change extraction behavior, existing smoke/eval fixtures should produce decision-equivalent extraction behavior except for added schema metadata.
- If data points change, treat it as a defect unless the operator explicitly approves a spec amendment.

## Implementation Order

1. Add failing tests for schema metadata contracts and deterministic hashing.
2. Implement the smallest contract module changes needed to pass those tests.
3. Add failing config tests for domain-pack and schema-registry settings.
4. Implement config model/default YAML support.
5. Add failing planner tests for `ExtractionPlan.schema_metadata`.
6. Implement neutral planner-generated schema metadata attachment.
7. Add failing domain-pack loader validation tests with a synthetic generic pack artifact.
8. Implement loader validation without planner selection/reuse behavior.
9. Add failing reporter/audit serialization tests for schema metadata.
10. Implement report/audit payload propagation through existing Pydantic payloads.
11. Add CLI/orchestrator summary coverage if schema identity is surfaced there.
12. Run narrow tests, project-level verification, and update board/progress after the board exists.

## Expected Board Steps

When the board is created after spec approval, use these steps unless implementation planning exposes a better equivalent split:

1. Schema metadata contracts and deterministic hashing.
2. Config surface for domain packs and schema registry.
3. Neutral planner-generated schema metadata on extraction plans.
4. Domain-pack loader validation without planner selection.
5. Reporter, audit, orchestrator, and CLI schema metadata propagation.
6. Final verification, board/progress updates, and commit hygiene.

## Gate Criteria

Phase 26 is complete only when:

- Domain-pack and approved-schema metadata are strict Pydantic v2 contracts.
- Schema hashes are deterministic and stable across repeated loads.
- Schema hashes change when approved category or field semantics change.
- Invalid domain-pack/schema artifacts fail with explicit errors.
- Existing text/markdown extraction behavior is unchanged except for added schema metadata.
- Schema metadata is visible in stored extraction plans and final reports.
- No new audit DB tables are introduced.
- No domain-specific source-code patch is introduced.
- No prompt body is made domain-specific.
- Relevant narrow tests pass.
- `make test`, `make lint`, `make smoke`, and `git diff --check` pass when feasible.
- All Phase 26 board issues are resolved or explicitly deferred.
- `PROGRESS.md` is updated.

## Open Questions Resolved For This Spec

| Question | Resolution | Rationale |
|---|---|---|
| Should Phase 26 add new audit DB tables? | No. Embed schema metadata in existing plan/report payloads. | Avoids coupling the schema foundation to audit migrations; existing payload storage already preserves full Pydantic contracts. |
| Should Phase 26 add legal contracts as the first pack? | No. Legal contracts remain Phase 28. | Phase 26 validates pack mechanics without adding domain-specific behavior. |
| Should Phase 26 implement schema-fit refusal? | No. Defer to Phase 27. | Refusal depends on the schema metadata foundation created here. |

## Open Questions Before Implementation

1. What exact neutral schema ID format should Phase 26 use for planner-generated schemas: `schema:<hash-prefix>`, `planner-generated:<hash-prefix>`, or another deterministic pattern?
2. Should domain-pack artifacts be YAML only, or should JSON also be accepted?
3. Should the synthetic loader fixture live under `tests/fixtures/` or `config/domain_packs/_examples/`?
4. Should CLI summary output include schema metadata in Phase 26, or is final report visibility sufficient?
