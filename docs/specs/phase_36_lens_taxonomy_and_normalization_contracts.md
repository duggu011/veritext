# Phase 36 - Lens Taxonomy and Normalization Contracts

Status: draft.

Date drafted: 2026-05-29

Roadmap sources: `docs/PROJECT_OVERVIEW.md` sections `4. Executor`,
`5. Dedup`, `8. Reconciler`, `Highest-leverage accuracy/provenance
improvements, ranked`, `Target domains (ranked by fit)`, `Configurable
surface`, and `Non-configurable core`; `docs/phase_26_plus_roadmap.md`;
`docs/boards/README.md`; `PROGRESS.md`; Phase 35 board and completed commits
through `5565c80`.

## Goal

Add source-grounded lens taxonomy and value-normalization contracts before
expanding executor prompts or adding new executable lenses.

Phase 36 should make lens roles, value roles, verbatim values, canonical values,
and normalization policies typed, auditable, and reusable. It is a contract
phase: it prepares Phase 37 expanded lenses and Phase 38 dedup/canonical-value
behavior without asking the LLM to extract new roles yet.

The central outcome is that every candidate and final data point can preserve
the auditor-facing source value while carrying a separate canonical value when
deterministic policy supports it.

## Non-Goals

- Do not add new executor prompt bodies or enable new executable lenses.
- Do not add relation, definition, citation, temporal, obligation, condition,
  exception, or quantity-with-unit extraction behavior yet.
- Do not change planner, critic, verifier, reconciler prompt semantics.
- Do not route normalization through an LLM.
- Do not implement cross-chunk dedup, canonical-value dedup, conflict
  preservation, or cross-document reconciliation. Those remain Phase 38 and
  Phase 39 work.
- Do not add embeddings, vector databases, retrieval indexes, search products,
  REST APIs, web UI, Docker, CI/CD, fine-tuning hooks, or agent frameworks.
- Do not tune behavior for one fixture, document title, proper noun, insurance
  form, contract type, or market sector.

## Domain-Scope Alignment

Phase 36 supports the domain-neutral extraction kernel described in
`docs/PROJECT_OVERVIEW.md`: entities, events, metrics, obligations,
conditions, exceptions, temporal facts, relations, citations, and definitions
are shared primitives across legal contracts, SEC filings, clinical documents,
regulatory rulings, insurance policies, standards, patents, audit evidence, and
procurement documents.

Configurable surface in Phase 36:

- Domain-pack and schema-template declarations of lens roles and normalization
  policy references.
- Field-level value roles such as verbatim text, normalized label, number,
  date, duration, quantity, entity key, citation, or boolean.
- Policy identifiers and versions that explain how a canonical value was
  derived.

Non-configurable core:

- Exact span matching, byte offsets, character offsets, source hashes, audit
  logging, forced tool use, Pydantic stage contracts, invariant enforcement,
  and no-silent-drop rejection accounting.
- Verbatim source values cannot be replaced by canonical values.
- Canonical values cannot claim source provenance beyond the source span that
  supports their verbatim value.

## Current State

`src/extractor/contracts/base.py` defines `LensName` as the four executable
lenses: `entity`, `event`, `claim`, and `number`. `LLMStage` mirrors those four
executor stages.

`src/extractor/contracts/models.py` uses `LensName` in `LensBudget`,
`ExtractionPlan.enabled_lenses`, and `LensCandidate.lens`. `LensCandidate` and
`DataPoint` each carry a single `value` string, a `SourceSpan`, and confidence
metadata. They do not distinguish verbatim source value from canonical value.

`src/extractor/executor/models.py` defines the LLM tool payload with
`category`, `field_name`, `value`, `source_length`, `start_char`, and
`confidence`. The service reconstructs source text and byte offsets from the
chunk before building a `LensCandidate`.

`src/extractor/executor/field_normalizers.py` contains deterministic,
field-name-specific normalizers that sometimes convert source-traced text into
a more reusable label, such as a noun-form event label. Those decisions are not
represented in a typed normalization policy.

`src/extractor/executor/dedup.py` deduplicates by exact
`(chunk_id, category, field_name, source_span.text, value)`. This is
intentionally brittle and should not be changed in Phase 36.

`src/extractor/reconciler/materialization.py` keeps the invariant that the LLM
returns candidate IDs only. The server derives `DataPoint.value` and
`DataPoint.source_span` from the selected source candidate. Phase 36 must
preserve that design.

Audit storage persists model JSON payloads for candidates and data points.
Any new fields must have compatibility behavior so older audit payloads remain
readable.

## Lens Taxonomy Policy

Phase 36 should add a typed taxonomy for extraction roles without making every
taxonomy role executable.

Planned taxonomy roles:

- `entity`
- `event`
- `claim`
- `number`
- `relation`
- `definition`
- `citation`
- `temporal`
- `quantity_with_unit`
- `obligation`
- `condition`
- `exception`

The first four remain the only executable lenses in Phase 36. Future roles may
appear in taxonomy and schema metadata as contract-only roles, but
`ExtractionPlan.enabled_lenses` must not silently schedule an executor stage
unless that lens has a prompt, LLM stage, budget validation, and tests.

Recommended contract shape:

- `LensTaxonomyName`: all planned lens roles.
- `ExecutableLensName` or current `LensName`: roles that can be run by the
  executor in this phase.
- `LensRuntimeStatus`: `contract_only` or `executable`.
- `LensDefinition`: name, status, source requirements, allowed value kinds, and
  short description.
- `LensRegistry`: a typed registry that rejects duplicate lens names and
  rejects executable roles missing the current runtime support.

If implementation chooses a different naming split, it must still preserve this
behavior: contract-only planned roles are visible to metadata, but not executed.

## Normalization Contracts

Phase 36 should add typed normalization metadata while preserving existing
`value` fields for compatibility.

Recommended additive fields on `LensCandidate` and `DataPoint`:

- `value_verbatim`: optional source-facing value. For new records this should
  normally equal `source_span.text` or a source-backed subset selected by a
  deterministic normalizer.
- `value_canonical`: optional canonical value for downstream comparison.
- `value_kind`: a literal such as `text`, `number`, `date`, `datetime`,
  `duration`, `quantity`, `entity`, `citation`, or `boolean`.
- `normalization_status`: `not_normalized`, `verbatim_only`,
  `canonicalized`, or `unsupported`.
- `normalization_policy_id`: optional stable policy identifier.
- `normalization_policy_version`: optional policy version.
- `normalization_notes`: optional short machine-readable reason when a value is
  not canonicalized.

Compatibility rules:

- Existing audited candidate and data-point payloads without new fields remain
  readable.
- The existing `value` field remains present. For new records, it should equal
  `value_canonical` when a canonical value exists and equal `value_verbatim`
  otherwise.
- Canonical values are metadata; they do not create source spans.
- If `normalization_status` is `canonicalized`, `value_canonical`,
  `value_verbatim`, `normalization_policy_id`, and
  `normalization_policy_version` must be present.
- If `normalization_status` is `not_normalized`, no canonical value should be
  present.
- If `normalization_status` is `unsupported`, the record must explain the
  unsupported policy through `normalization_notes` or reject before candidate
  materialization, depending on the configured policy strictness.

Unsupported normalization must fail explicitly when it would otherwise produce
ambiguous or unauditable output. Silent fallback from an unsupported canonical
policy to a made-up canonical value is forbidden.

## Policy Registry

Phase 36 should add normalization policy contracts that can later be referenced
from domain packs and schema templates.

Recommended contract shape:

- `ValueKind`: typed canonical value kind.
- `NormalizationMode`: `none`, `verbatim`, `source_traced_label`, `number`,
  `date`, `datetime`, `duration`, `quantity`, `entity_key`, `citation_key`, or
  `boolean`.
- `NormalizationPolicy`: policy ID, version, mode, input kind, output kind,
  and deterministic requirements.
- `FieldNormalizationPolicy`: category name, field name, value kind, required
  policy ID, and whether unsupported normalization is a rejection.
- `NormalizationPolicyRegistry`: typed registry with unique policy IDs and
  versions.

Phase 36 may extend `DomainPackMetadata` and `SchemaTemplateMetadata`
additively so domain packs can name supported lens roles and normalization
policies. Those metadata additions must be optional with defaults so existing
domain-pack fixtures remain readable.

## Contract Changes

Expected contract areas:

- Add a focused module such as `src/extractor/contracts/lens_taxonomy.py` for
  taxonomy models.
- Add a focused module such as `src/extractor/contracts/normalization.py` for
  value-kind and normalization-policy models.
- Export the new models from `src/extractor/contracts/__init__.py`.
- Extend `LensCandidate` and `DataPoint` additively with normalization fields.
- Extend schema/domain-pack metadata additively only where policy references
  need to be audit-visible.
- Keep old payload JSON readable through defaults or before validators.

Do not remove or rename existing fields on `LensCandidate`, `DataPoint`,
`ExtractionPlan`, `LensBudget`, `SourceSpan`, `ApprovedSchemaMetadata`,
`DomainPackMetadata`, or `SchemaTemplateMetadata`.

Do not change the executor LLM tool payload schema in Phase 36 unless tests
prove there is no provider strict-tool impact. The preferred approach is to
derive normalization metadata server-side after source resolution.

## Runtime Boundaries

Allowed runtime changes:

- Populate new normalization metadata during candidate materialization from
  deterministic server-side rules.
- Preserve reconciler ID-only behavior while carrying selected source
  candidate normalization metadata into final data points.
- Validate that canonicalized data points are backed by canonicalized
  contributing candidates with the same category and field.
- Record new fields in audit JSON payloads.
- Reject unsupported normalization policies explicitly.

Out of scope:

- Prompt changes under `prompts/`.
- New executor stages.
- New `executor.<lens>` LLM stages for planned-only lenses.
- New LLM calls for normalization.
- Dedup key changes, conflict surfacing, or cross-document grouping.

## Audit and Provenance Effects

Phase 36 should strengthen auditability by separating three concepts:

- The source span that proves the extraction.
- The verbatim source-facing value.
- The canonical value used for comparison or downstream tooling.

The audit trail must show which normalization policy produced a canonical value
and which source text supported it. Audit inspection should remain able to list
candidates and data points even when older rows do not include normalization
fields.

Canonical values must not weaken source support. A normalized number, date, or
label is accepted only because the source span and verbatim value support it.

## Invariant Impact

Do not weaken I1-I9.

Phase 36 should improve invariant enforcement by making normalization explicit
instead of implicit in field-name-specific code.

- Source spans remain mechanical document/chunk slices.
- Verbatim values remain source-backed.
- Canonical values are derived metadata, not source spans.
- Unsupported normalization policies reject explicitly.
- Existing four-lens executor behavior remains compatible.
- Existing Phase 29, Phase 30, and Phase 31 evaluation suites remain passing.
- No prompt body, runtime LLM call path, domain-specific fixture patch, or
  architecture rule changes.

## Configuration Changes

No new runtime tuning is required unless implementation introduces a strictness
switch for unsupported normalization. If such a switch is needed, it must live
in `config/default.yaml` and default to preserving current behavior while
rejecting unauditable canonicalization.

Domain-pack and schema-template metadata may gain optional policy-reference
fields. Existing config artifacts must remain valid.

## Prompt Changes

No prompt body should change in Phase 36.

- Run prompt-no-change verification.
- Do not add prompt instructions for planned-only lenses.
- Do not change executor tool output unless implementation proves the strict
  tool schema remains compatible.

## Tests and Evaluation Gates

Required narrow tests:

- Lens taxonomy contracts accept the current executable four lenses and planned
  contract-only roles.
- Runtime validation rejects attempts to execute planned-only roles before
  prompts and LLM stages exist.
- Normalization policy contracts reject duplicate policies, unsupported value
  kinds, and inconsistent canonicalization metadata.
- Older `LensCandidate` and `DataPoint` audit payload JSON without
  normalization fields remains readable.
- New candidates and data points can carry `value_verbatim`,
  `value_canonical`, policy ID, policy version, status, and value kind.
- Candidate materialization preserves `value` compatibility while deriving
  verbatim/canonical metadata server-side.
- Reconciler materialization carries selected source candidate normalization
  metadata into the final data point without asking the LLM for rewritten
  values.
- Domain-pack and schema-template metadata remain backward-compatible.
- Prompt-neutrality verification proves files under `prompts/` did not change.

Required broader verification before Phase 36 completion:

```bash
python3 -m pytest tests/unit/test_contracts.py tests/unit/test_executor.py tests/unit/test_reconciler.py tests/unit/test_dedup.py tests/unit/test_domain_pack_loader.py tests/unit/test_schema_registry_contracts.py -q
make test
make lint
make smoke
git diff --check
git diff --exit-code -- prompts
PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json
PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json
PYTHONPATH=src python3 -m extractor.evals --adversarial-suite evals/suites/phase_31_adversarial.json
PYTHONPATH=src python3 -m extractor.evals --mutation-suite evals/suites/phase_31_mutation.json
PYTHONPATH=src python3 -m extractor.evals --calibration-suite evals/suites/phase_30_diverse_corpus_round_1.json
```

If normalization metadata changes report JSON or audit inspection output, record
before/after payload shape and extraction metrics on the Phase 36 board. Do not
accept a metric regression without a board issue and operator decision.

## Implementation Order

1. Add lens taxonomy and normalization contract tests, including legacy audit
   payload readability and executable-vs-contract-only lens validation.
2. Add focused Pydantic taxonomy and normalization modules plus public exports.
3. Extend `LensCandidate` and `DataPoint` additively with verbatim/canonical
   value metadata and validation.
4. Populate candidate normalization metadata during server-side materialization
   without changing executor prompt bodies or tool payload requirements.
5. Carry normalization metadata through reconciler materialization, audit
   readback, and compact inspection output while preserving ID-only reconciler
   behavior.
6. Run final project, smoke, lint, prompt-neutrality, and evaluation gates; fill
   the board summary and stop for operator acceptance.

## Open Questions

None. This draft pins the main design decisions so the implementation board can
open cleanly after operator approval:

- Planned lens roles are contract-only in Phase 36 unless already executable.
- Existing `value` remains a compatibility field.
- Verbatim and canonical values are separate.
- Canonical values are metadata and do not create source spans.
- Unsupported normalization fails explicitly instead of silently inventing a
  canonical value.
