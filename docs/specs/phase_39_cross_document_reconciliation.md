# Phase 39 - Cross-Document Reconciliation

Status: approved for implementation.

Date drafted: 2026-05-29
Date approved: 2026-05-29

Roadmap sources: `docs/PROJECT_OVERVIEW.md` section `8. Reconciler`,
`docs/PROJECT_OVERVIEW.md` highest-leverage item 4,
`docs/phase_26_plus_roadmap.md`, `docs/boards/README.md`, `PROGRESS.md`, and
Phase 38 board/spec/commits through `e2f5008`.

## Goal

Add deterministic cross-document reconciliation for completed single-document
outputs.

Phase 39 should group the same fact across multiple documents while preserving
each document's provenance separately. It should surface unresolved conflicts
between documents as explicit cross-document conflict records and never collapse
or overwrite the single-document `DataPoint` evidence that Phase 38 now
preserves.

The central outcome is that a reviewer can ask whether several documents agree
about a fact, inspect every contributing document/span, and see unresolved
disagreements without any silent drop or LLM-generated rewrite.

## Non-Goals

- Do not replace the single-document pipeline or make single-document runs
  depend on a multi-document mode.
- Do not implement REST APIs, web UI, HTML viewer work, Docker, CI/CD, vector
  databases, embeddings, fine-tuning hooks, agent frameworks, local model
  serving, or open-web crawling.
- Do not add cross-document semantic search or entity resolution based on
  embeddings.
- Do not change existing CLI behavior or the single-source command contract.
- Do not add domain-specific authority rankings, organization names, fixture
  strings, market sectors, or proper nouns as reconciliation policy.
- Do not change `report.v2` by removing or renaming existing fields.
- Do not weaken exact source offsets, source hashes, `DataPoint.source_span`,
  `supporting_source_spans`, conflict metadata, Pydantic contracts, audit
  persistence, or forced tool use.
- Do not make relation, obligation, condition, or exception executable.
- Do not change static prompt bodies unless a readiness or implementation test
  proves deterministic reconciliation cannot preserve invariants without a
  prompt change and the operator explicitly authorizes that edit.

## Domain-Scope Alignment

Phase 39 remains domain-neutral. Cross-document grouping must work from source
role, schema role, canonical value keys, schema metadata, document identity, and
typed provenance. The same logic should apply to contracts, SEC filings,
clinical protocols, FDA labels, insurance policies, standards documents,
scientific reviews, and procurement files.

The implementation must not infer domain authority from document titles,
company names, market terminology, or fixture text. Any authority or tie-break
policy introduced in Phase 39 must be deterministic, auditable, and expressed
through typed policy inputs rather than source-code nouns.

## Current State

The CLI and orchestrator currently run one document per pipeline run. Each
`RunManifest` has one `doc_id`, each `Document` stores one source identity, and
`report.v2` serializes one document's final `DataPoint` list.

The reconciler is single-document. It sends ID-only candidate groups to the LLM
and materializes final values on the server. Phase 38 added deterministic
canonical value keys, cross-chunk duplicate merging, `supporting_source_spans`,
and unresolved same-field conflict metadata on `DataPoint`.

The audit store persists single-document run manifests, documents, chunks,
plans, candidates, critic reports, verifier reports, data points, rejections,
stage states, and LLM call logs. It has no typed cross-document run payload,
cross-document fact group, or cross-document report artifact.

## Contract Changes

Expected additive contracts:

- `CrossDocumentSourceRef`
  - `run_id`
  - `doc_id`
  - `data_point_id`
  - `source_span`
  - `supporting_source_spans`
  - `source_sha256`
  - `text_sha256`
  - `value`
  - `value_verbatim`
  - `value_canonical`
  - `value_kind`
  - `normalization_status`
- `CrossDocumentFactKey`
  - schema identity fields when available, such as schema ID or schema hash
  - `category`
  - `field_name`
  - canonical value key identity
  - policy ID and policy version when a grouping policy applies
- `CrossDocumentFactGroup`
  - stable group ID
  - group key
  - contributing source references
  - document count
  - conflict status
  - conflict IDs
- `CrossDocumentConflict`
  - stable conflict ID
  - category and field name
  - conflicting group IDs or source refs
  - reason code
  - document IDs
  - canonical key identities
- `CrossDocumentReconciliationResult`
  - cross-document run ID
  - input run IDs
  - input document IDs
  - groups
  - conflicts
  - rejected or skipped inputs with explicit reasons
- `CrossDocumentRunManifest`
  - cross-document run ID
  - audit DB path
  - status
  - started/completed timestamps
  - input run IDs
  - output group IDs
  - output conflict IDs

All contracts must use Pydantic v2, frozen models, `extra="forbid"`, stable
IDs, and legacy-safe additive fields where they extend existing payloads.

## Grouping Policy

Cross-document grouping must be deterministic and conservative:

- Group only completed or explicitly supplied single-document outputs.
- Group facts when schema identity, category, field name, and canonical value
  identity agree.
- Preserve every contributing `DataPoint` as a source reference rather than
  merging spans into a single primary source span.
- Keep per-document source hashes and text hashes on every source reference.
- Treat same schema/category/field with distinct canonicalized values as an
  unresolved cross-document conflict.
- Preserve existing single-document unresolved conflict metadata and surface it
  in the cross-document result.
- Do not guess that raw text values are equivalent when they lack a safe
  canonical value identity.
- Do not choose a winning value by recency, document type, source path,
  filename, or domain-specific authority unless a typed policy explicitly
  supplies that rule.

The default Phase 39 policy should prefer visibility over resolution: group
safe matches, emit conflicts for safe disagreements, and leave unsafe raw-text
near-matches unmerged with explicit audit reasons.

## Reconciliation Service

Phase 39 should add a focused cross-document reconciliation module under
`src/extractor/reconciler/` or a cohesive subpackage with a public service such
as `reconcile_documents(...)`.

The service should accept typed completed run inputs, report inputs, or audited
run IDs loaded through `AuditStore`. It should return a
`CrossDocumentReconciliationResult` without requiring an LLM call.

The service must:

- Validate that every input run is completed and has readable data points.
- Reject duplicate input run IDs or duplicate document IDs unless the API
  explicitly accepts rerun comparison as a separate mode.
- Validate that every source reference points back to an existing `DataPoint`
  and `Document`.
- Build stable group and conflict IDs from source identities and canonical
  value key identities.
- Preserve deterministic ordering for groups, source refs, conflicts, and
  skipped inputs.
- Log every skipped data point or input run with a typed reason.
- Preserve single-document conflict metadata in the cross-document result.

## Orchestrator and Batch Mode

Phase 39 adds a multi-document orchestration entrypoint after the pure
reconciliation service is tested. The entrypoint should be callable from Python
code and tests; CLI behavior remains unchanged in this phase.

The conservative batch shape is:

1. Run the existing single-document pipeline independently for each source.
2. Stop if any single-document run fails or refuses, unless the caller chooses
   an explicit partial-results mode.
3. Pass completed run outputs into cross-document reconciliation.
4. Persist and report the cross-document result.

This must not change existing single-document `run_extraction_pipeline(...)`
behavior or CLI summary output.

## Audit and Provenance Effects

Phase 39 should add audit persistence for cross-document reconciliation rather
than overloading single-document `data_points`.

Allowed audit changes:

- Additive cross-document audit table or tables for manifests and result
  payloads.
- Audit store methods to record, fetch, and list cross-document run manifests
  and reconciliation results.
- Audit inspection output that summarizes cross-document groups, conflicts,
  input runs, input documents, skipped inputs, and source reference counts.

Required compatibility:

- Existing audit DBs must remain readable.
- Existing single-document tables and payloads must remain unchanged.
- Existing `report.v2` payloads must remain readable.
- Existing audit idempotency and run-resume behavior must keep passing.

Every cross-document group and conflict must remain traceable to original
`Document` identities, source hashes, `DataPoint` IDs, and exact source spans.

## Reporter Effects

Phase 39 writes a report artifact using an additive schema such as
`cross_document_report.v1`. It must not modify `report.v2` semantics.

The report should include:

- cross-document run ID
- input run IDs and document IDs
- group IDs
- conflict IDs
- source references with exact spans and hashes
- skipped inputs or data points with reasons
- generated timestamp and output hash through the existing reporter discipline

## Configuration Changes

No new runtime tuning keys are expected.

If implementation proves a grouping or authority policy needs configuration,
the policy must be typed, defaulted, and stored under `config/default.yaml`.
It must not be hardcoded in source or tests as fixture-specific behavior.

## Prompt Changes

No static prompt body changes are planned for Phase 39.

The first implementation should be deterministic and server-side, using
canonical value keys and typed policy inputs. If tests prove an LLM is required
for a narrow cross-document decision, stop before editing prompts or routing a
new LLM call.

## Tests and Evaluation Gates

Narrow tests:

- Contract tests for cross-document source refs, fact keys, fact groups,
  conflicts, result payloads, and run manifests.
- Grouping tests proving identical canonical same-field values across distinct
  documents become one deterministic group with separate source refs.
- Conflict tests proving same schema/category/field with distinct canonicalized
  values produces unresolved cross-document conflicts without dropping either
  side.
- Safety tests proving raw text near-matches without safe canonical keys do not
  merge.
- Validation tests for duplicate run IDs, duplicate document IDs, incomplete
  runs, missing documents, missing data points, and unreadable audit inputs.
- Audit persistence/readback tests for cross-document manifests and results.
- Audit inspection tests for group/conflict/source-ref summaries.
- Reporter tests for additive cross-document report output.
- Orchestrator tests for multi-document batch mode.
- CLI regression tests proving existing single-source behavior remains
  unchanged.

Regression and final gates:

- Existing unit tests for contracts, reconciler, orchestrator, audit store,
  audit inspection, reporter, and evaluation scoring.
- `git diff --exit-code -- prompts`
- `make test`
- `make lint`
- `make smoke`
- `git diff --check`
- Phase 29 and Phase 30 evaluation suites.
- Phase 31 adversarial, mutation, and calibration suites.
- Phase 37 expanded-lens evaluation suite.

Evaluation acceptance:

- No regression in existing precision, recall, F1, provenance recall, false
  positives, false negatives, or invariant violations.
- New cross-document tests or fixtures prove deterministic grouping and
  conflict surfacing without document-specific source patches.

## Implementation Order

1. Add RED tests for cross-document contract models and legacy single-document
   payload compatibility.
2. Add cross-document Pydantic contracts and exports.
3. Add RED tests for deterministic grouping, source references, and conflict
   surfacing across completed single-document outputs.
4. Implement canonical-key-based cross-document reconciliation without LLM
   calls.
5. Add validation and skipped-input accounting for duplicate, incomplete,
   missing, or unreadable inputs.
6. Add audit persistence and readback for cross-document manifests and results.
7. Extend audit inspection and reporter output for additive cross-document
   fields.
8. Add multi-document orchestrator batch mode only after the pure
   reconciliation service and audit path are passing; keep CLI behavior
   unchanged.
9. Add focused source-neutral cross-document fixture or equivalent unit
   coverage for evaluation acceptance.
10. Run final project, prompt-neutrality, smoke, lint, and evaluation gates.
11. Fill the Phase 39 board summary and stop for operator acceptance.

## Open Questions Before Approval

_(None.)_
