# Phase 28 - Legal Contracts Domain Pack v1

Status: draft opened after Phase 27 operator acceptance on 2026-05-09. Implementation starts only after operator approval and creation of `docs/boards/phase_28_legal_contracts_domain_pack_v1.md`.

Date opened: 2026-05-09

Roadmap sources:

- `docs/PROJECT_OVERVIEW.md`:
  - `Target domains (ranked by fit)`
  - `First-domain-pack proving ground`
  - `Configurable surface`
  - `Non-configurable core`
  - Planner roadmap
- `docs/phase_26_plus_roadmap.md`
- `docs/boards/README.md`
- `PROGRESS.md`
- Phase 27 board and completed commits through `090251a`

## Goal

Prove the domain-pack mechanism with a first legal-contract pack while keeping Veritext one domain-neutral extraction kernel.

Phase 28 should add legal-contract assumptions as typed, versioned, hashed, auditable artifacts and fixtures. The extraction source code must remain reusable for other target domains.

## Non-Goals

- Do not turn Veritext into a contract-specific extractor.
- Do not add contract-specific branching, category names, clause labels, or legal nouns under `src/` implementation code.
- Do not add legal UI, REST API, document viewer, CLM integration, export format, Docker, CI/CD, vector DBs, embeddings, fine-tuning hooks, or agent frameworks.
- Do not add broad per-field evaluation gates or a diverse fixture corpus. Those begin in Phase 29 and Phase 30.
- Do not add PDF, DOCX, HTML, email, table, or layout-aware ingestion.
- Do not optimize for one contract, counterparty, clause phrase, governing law, business sector, or expected answer.
- Do not use a legal-domain artifact to relax exact source-span matching, offsets, hashes, forced tool use, Pydantic contracts, SQLite audit persistence, or rejection accounting.
- Do not make prompt bodies legal-specific.

## Domain-Scope Alignment

Veritext should stay one domain-neutral extraction kernel with configurable legal-contract assumptions.

Configurable in Phase 28:

- Legal-contract domain-pack metadata.
- Legal-contract schema template metadata.
- Approved legal-contract registry schema artifact with full approved categories and fields.
- Legal fixture text and expected outputs.
- Legal domain hints, document classes, field roles, enabled lenses, and reporting expectations.
- Test-time config paths that point to synthetic legal artifacts.

Non-configurable in Phase 28:

- Exact source span matching.
- Byte and character offsets.
- Source and text hashes.
- Forced tool use for structured LLM outputs.
- Pydantic stage contracts.
- SQLite audit persistence.
- Planner refusal behavior from Phase 27.
- No-silent-drop rejection accounting.
- Schema hash validation against approved categories.
- Candidate category validation and data-point provenance rules.

## Stage and Module Boundaries

### Domain-Pack Artifact

Add a legal-contract domain pack as a YAML artifact under `config/domain_packs/`.

The artifact should use the existing `DomainPackArtifact` contract and include:

- `pack_id`
- `display_name`
- `version`
- legal-contract `domain_hints`
- one or more schema template IDs
- supported document classes
- default lenses
- reporting expectations
- schema template metadata with field roles and enabled lenses

The domain pack may name legal concepts because it is an approved configuration artifact. The source implementation under `src/` must not special-case those names.

### Approved Schema Registry Artifact

Add a synthetic approved legal-contract schema registry artifact for tests, likely under `tests/fixtures/schema_registry/`.

The artifact should use `ApprovedSchemaArtifact` and include:

- `schema_metadata` with `source_kind: schema_registry`
- `domain_pack_id` linking to the legal domain pack
- `document_class` matching the legal pack
- full approved categories and fields
- legal domain hints
- match basis
- a schema hash that matches `canonical_schema_hash(...)`

The approved categories should be useful legal-contract primitives such as parties, effective dates, obligations, payment terms, termination rights, governing law, notices, conditions, exceptions, definitions, or renewal terms. Keep the first schema small enough to audit, but broad enough that it proves the pack mechanism rather than one clause.

### Evaluation Fixture

Add at least one legal-contract fixture under `evals/fixtures/`.

The fixture should include:

- source text with multiple contract-style obligations or clauses
- expected data points with exact byte and character offsets
- a deterministic example report using the approved legal schema metadata
- thresholds requiring precision, recall, F1, provenance recall, and invariant violations to meet existing strict fixture expectations

The fixture must not require external files or the operator's real `.veritext` state.

### Tests

Add focused unit coverage rather than a broad new evaluation harness.

Expected coverage:

- `config/domain_packs/` loads with the legal pack.
- The legal domain-pack metadata and schema template IDs are internally consistent.
- The approved legal registry artifact validates, including canonical schema hash equality.
- Candidate selection matches the legal schema by document class and domain hints.
- The legal evaluation fixture loads and its example report passes existing evaluation scoring.
- No source implementation file under `src/` contains legal-domain branching or category-name constants introduced by this phase.

If implementation needs a new helper to create canonical schema-registry YAML fixtures, keep it in tests or fixture-generation scripts. Do not add runtime legal logic.

## Contract Changes

Expected model changes are limited.

Allowed if required:

- Extend domain-pack artifact validation with generic duplicate pack ID or template consistency checks.
- Add test-only helpers for writing approved schema registry artifacts with correct hashes.

Disallowed in Phase 28:

- New legal-specific Pydantic models.
- New legal-specific planner contracts.
- New audit tables.
- New report schema version solely for legal contracts.
- New source-code enums containing legal category names.

Any needed generic contract change must be justified on the board before implementation and covered by tests.

## Audit and Provenance Effects

Phase 28 should make legal-domain assumptions auditable through artifacts, not runtime branches.

Required properties:

- Report schema metadata for the legal fixture cites the approved schema ID, version, hash, source kind, domain pack ID, and document class.
- Approved legal schema artifacts validate their canonical hash before use.
- Fixture expected outputs preserve exact source text, byte offsets, and character offsets.
- Existing refusal behavior remains available when strict approved-schema policy is enabled and no legal schema matches.
- Legal artifacts do not remove or weaken rejection, audit, LLM call, prompt hash, stage state, or final report provenance fields.

## Invariant Impact

Do not weaken I1-I9.

Phase 28 is artifact-heavy, but invariant risk remains high because it adds the first real domain assumptions. Required protections:

- Legal artifact fields can describe what to extract; they cannot loosen how source support is proven.
- Approved schema categories cannot bypass deterministic candidate category validation.
- Fixture expected spans must be mechanically checked against source text.
- Planner-generated fallback remains disabled only when strict policy requires approved schemas; default local behavior remains safe.
- No code path may infer legal fit from document-specific names or one-off phrase matches.
- A missing optional runtime registry directory must not break local runs.
- Malformed legal artifacts must fail explicitly through existing loader errors.

If implementation reveals that the existing domain-pack contract cannot carry enough schema semantics to prove the pack mechanism, log the design issue on the Phase 28 board and stop before expanding runtime contracts.

## Configuration Changes

Expected configuration work:

- Add `config/domain_packs/legal_contracts.yaml`.
- Keep `config/default.yaml` directory paths unchanged unless a generic path correction is required.
- Use tests or temporary config to point schema-registry loading at legal registry fixtures.
- Do not require a real `.veritext/schema_registry` directory for test or local success.

Runtime tuning values must remain in `config/`. Domain assumptions must live in YAML artifacts or eval fixtures, not source constants.

## Prompt Changes

No prompt body should be changed for legal-contract specificity in Phase 28.

Allowed prompt-related work:

- Add prompt metadata documentation only if a generic artifact field requires it.
- Add tests proving legal pack work does not require legal-specific prompt text.

Disallowed prompt-related work:

- Legal examples inside planner, executor, critic, verifier, reconciler, or reporter prompt bodies.
- Prompt instructions that privilege one contract fixture or clause phrase.
- Free-text JSON parsing.

## Tests and Evaluation Gates

Required narrow tests:

- Domain-pack loader test for `config/domain_packs/legal_contracts.yaml`.
- Schema-registry loader test for the legal approved schema fixture.
- Candidate selection test for legal document class and domain hints.
- Evaluation fixture test for the legal-contract fixture and example report.
- Guard test or review check proving legal-domain nouns are confined to approved artifacts, fixtures, tests, docs, or progress files, not new runtime branching under `src/`.

Required broader verification before Phase 28 completion:

```bash
make test
make lint
make smoke
git diff --check
```

Evaluation gate:

- The legal fixture passes existing exact matching thresholds.
- Existing fixtures continue passing.
- No invariant violations are introduced.
- No existing successful report drops schema metadata.
- Strict approved-schema policy can select the legal schema from the registry fixture in tests without planner schema invention.

## Implementation Order

1. Add failing tests for legal domain-pack artifact loading from `config/domain_packs/`.
2. Add the minimal legal domain-pack YAML artifact needed to pass loader tests.
3. Add failing tests for a legal approved schema registry artifact and candidate selection.
4. Add the legal schema registry fixture with canonical hash enforcement.
5. Add failing evaluation coverage for a legal-contract fixture.
6. Add the legal fixture source, expected outputs, and example report with approved schema metadata.
7. Add a guard test or documented verification that legal-domain assumptions did not enter runtime source branching.
8. Run narrow tests.
9. Run project-level verification.
10. Update the Phase 28 board and `PROGRESS.md`.
11. Commit the completed step or hand off explicitly.

## Expected Board Steps

When the board is created after spec approval, use these steps unless implementation planning exposes a better equivalent split:

1. Add legal-contract domain-pack artifact and loader coverage.
2. Add approved legal schema registry fixture and schema-selection coverage.
3. Add legal-contract evaluation fixture and report-schema coverage.
4. Add source-neutrality guard and final verification.

## Gate Criteria

Phase 28 is complete only when:

- The legal domain pack validates through existing typed domain-pack contracts.
- The approved legal schema registry artifact validates through strict Pydantic contracts and canonical hash enforcement.
- Candidate selection can match the legal schema by document class and domain hints.
- The legal fixture passes existing evaluation scoring with exact provenance.
- Existing fixture tests remain passing.
- No legal-domain branching or category constants are introduced under runtime `src/` implementation code.
- No prompt body is made legal-specific.
- No architecture rule is violated.
- Relevant narrow tests pass.
- `make test`, `make lint`, `make smoke`, and `git diff --check` pass when feasible.
- All Phase 28 board issues are resolved or explicitly deferred.
- `PROGRESS.md` is updated.

## Open Questions Before Implementation

1. Should the legal approved schema fixture live under `tests/fixtures/schema_registry/` only, or should Phase 28 also introduce a repo-tracked canonical `config/schema_registry/` directory for approved schemas?
2. Should the first legal document class be `legal_contract` broadly, or a narrower class such as `commercial_agreement` to reduce ambiguous matches?
3. Should the first legal schema stay small with only operational terms, or include definitions and notice provisions to better exercise legal-contract structure?
4. Should Phase 28 add a generic duplicate `pack_id` rejection in the domain-pack loader, or leave that for a later multi-pack governance phase?
