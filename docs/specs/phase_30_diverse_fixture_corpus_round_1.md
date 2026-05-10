# Phase 30 - Diverse Fixture Corpus Round 1

Status: approved for implementation after operator continuation on 2026-05-10. Board: `docs/boards/phase_30_diverse_fixture_corpus_round_1.md`.

Date opened: 2026-05-10

Roadmap sources:

- `docs/PROJECT_OVERVIEW.md`:
  - `13. Evaluation`
  - `Highest-leverage accuracy/provenance improvements, ranked`
  - `Target domains (ranked by fit)`
  - `Configurable surface`
  - `Non-configurable core`
- `docs/phase_26_plus_roadmap.md`
- `docs/boards/README.md`
- `PROGRESS.md`
- Phase 29 board and completed commits through `0f3c3a1`

## Goal

Add the first broad, source-grounded evaluation corpus across Veritext target domains, using the Phase 29 per-suite, per-category, and per-field gates.

Phase 30 should make fixture coverage visibly broader without changing extraction behavior. The result should be a portable checked-in static corpus and suite manifest that can expose weak domains, categories, and fields in later live runs while preserving exact provenance, invariant enforcement, and auditability.

## Non-Goals

- Do not tune planner, executor, critic, verifier, reconciler, reporter, source-support, or prompt behavior to improve a new fixture score.
- Do not add document-specific runtime logic, domain-name branches, proper-noun patches, or one-off phrase handling.
- Do not add adversarial fixtures, mutation testing, calibration reports, confidence reliability diagrams, or source-sensitivity tests. Those are Phase 31.
- Do not add PDF, DOCX, HTML, email, OCR, table, or layout-aware ingestion. Those start in Phase 32 and later phases.
- Do not add new domain-pack runtime behavior or schema-fit policy changes. Phase 30 may use fixture-local schema metadata in static reports, but it should not expand the planner registry mechanism.
- Do not add CI/CD integration. Current architecture rules ban CI/CD until an explicit architecture amendment phase.
- Do not run live LLM extraction as a required unit or smoke test.
- Do not relax exact value matching, source-span matching, byte offsets, character offsets, source hashes, forced tool use, Pydantic contracts, SQLite audit persistence, or no-silent-drop reporting.
- Do not claim production extraction generalization from static mirror reports alone. Static reports prove corpus validity and scorer gates; live extraction baselines require separate recorded runs.

## Domain-Scope Alignment

Phase 30 is evaluation-corpus work for the domain-neutral kernel. It should add domain diversity as fixtures and suite gates, not as source-code specialization.

Configurable in Phase 30:

- Synthetic or repo-safe fixture source texts.
- Expected data points with exact character and byte provenance.
- Static `report.example.json` files used to prove the scorer and suite gates.
- Fixture-local schema metadata inside static reports when needed for valid report contracts.
- Suite membership and suite-level, category-level, and field-level thresholds.
- Optional annotation notes that explain span-width decisions and domain intent.

Non-configurable in Phase 30:

- Exact source-span and byte/character offset validation.
- Existing fixture matching semantics in `evaluate_report(...)`.
- Suite manifest repo-local path validation.
- Category and field metric aggregation from Phase 29.
- Runtime extraction contracts, audit contracts, report contracts, and invariant rules.
- Architecture bans on web UI, REST API, Docker, CI/CD, vector DBs, embeddings, fine-tuning hooks, and agent frameworks.

## Fixture Corpus Boundaries

Add a first wave of diverse static fixtures under `evals/fixtures/`.

The target corpus should include at least one new fixture for each of these domains unless an implementation blocker is logged on the board:

- SEC filing or market disclosure.
- Clinical trial protocol or clinical-study document.
- FDA drug label, device instructions, or comparable regulated safety label.
- Regulatory ruling, guidance, or enforcement order.
- Insurance policy or claims-coverage document.
- Standards document or security-control publication.
- Scientific paper or systematic-review source.
- Government procurement RFP, SOW, or required-clause document.

The existing `legal_contracts_core` fixture remains the legal-contract baseline from Phase 28 and should be included in the Phase 30 suite. The Phase 30 suite may also include Phase 29 core fixtures when useful for regression continuity, but the main deliverable is new cross-domain fixture coverage.

Fixture source text should stay synthetic, short enough to audit by hand, and domain-realistic enough to exercise field semantics. It must not embed real personal data, secrets, confidential documents, or copyrighted long-form source material.

Each new fixture should include:

- `source.txt` or `source.md` using the ingestion formats already supported by current static eval tooling.
- `expected.json` with exact source text, character offsets, byte offsets, and strict thresholds.
- `report.example.json` that validates as `ExtractionReport` and passes exact scoring against `expected.json`.
- Optional `annotation.md` when span-width choices need human-readable justification outside the strict `expected.json` contract.

## Annotation Discipline

All expected data points must follow `docs/annotation-conventions.md`.

Required properties:

- `source_text` equals the exact source character slice.
- `start_byte` and `end_byte` equal UTF-8 byte offsets for the chosen character slice.
- `value` is either the source text or a controlled normalization whose content words are all supported by the source text.
- Field span widths follow the Type A/B/C/D conventions.
- Expected IDs are stable, descriptive, and unique within the fixture.
- Category and field names are domain-relevant but not tailored to one proper noun or one sentence.

Do not use a new fixture to redefine annotation policy. If a domain exposes an annotation ambiguity, log it on the Phase 30 board and resolve it as a general source-span convention before adding the affected fixture.

## Suite Manifest

Add a Phase 30 suite manifest under `evals/suites/`, likely:

```text
evals/suites/phase_30_diverse_corpus_round_1.json
```

The suite should use repo-relative paths and strict thresholds:

- Global precision, recall, F1, provenance recall: `1.0`.
- Global max invariant violations: `0`.
- Category thresholds for every category introduced by the new fixtures.
- Field thresholds for every `(category, field_name)` introduced by the new fixtures.

Non-zero invariant allowances are not expected in Phase 30. If a deliberately broken fixture is needed for a validation test, keep it temporary in tests and require a rationale through existing suite-manifest contracts.

## Stage and Module Boundaries

### Evaluation Artifacts

Expected new files are under:

- `evals/fixtures/<fixture_id>/source.txt` or `source.md`
- `evals/fixtures/<fixture_id>/expected.json`
- `evals/fixtures/<fixture_id>/report.example.json`
- `evals/fixtures/<fixture_id>/annotation.md` if needed
- `evals/suites/phase_30_diverse_corpus_round_1.json`

### Tests

Expected test edits are limited to evaluation tests, likely:

- `tests/unit/test_evals.py`
- `tests/unit/test_eval_suites.py`
- a focused new test file under `tests/unit/` if fixture-corpus inventory validation becomes cleaner there

Do not edit runtime pipeline stages for Phase 30. If a fixture cannot be represented without changing runtime contracts, log the design issue and stop before changing contracts.

## Contract Changes

Expected contract changes: none.

Allowed only if implementation proves a generic evaluation gap:

- Additive validation around static fixture inventory.
- Additive suite-manifest checks that remain domain-neutral and are covered by tests.

Disallowed in Phase 30:

- Changes to `DataPoint`, `SourceSpan`, `ExtractionReport`, planner contracts, executor contracts, audit tables, or report schema solely for new fixtures.
- Domain-specific Pydantic models.
- Source-code enums or constants for SEC, clinical, FDA, insurance, standards, scientific, or procurement categories.
- Fuzzy matching, model-assisted scoring, or prompt-based scoring.

## Audit and Provenance Effects

Phase 30 does not change the extraction audit store.

Required properties:

- Every static report remains a valid `report.v2` artifact.
- Static reports preserve run ID, document ID, schema metadata when available, data-point IDs, output IDs, source spans, and source hashes.
- Evaluation output for the Phase 30 suite identifies fixture ID, case path, report path, category failures, field failures, missing IDs, unexpected IDs, and invariant violations through existing Phase 29 output.
- No expected data point or static report data point may silently drop source provenance.

## Invariant Impact

Do not weaken I1-I9.

Phase 30 protects invariants by expanding fixture coverage. Required protections:

- New fixtures must load through strict Pydantic evaluation contracts.
- New static reports must validate through existing report contracts.
- Suite gates must fail on any source-span, byte-offset, source-text, or invariant violation.
- Existing Phase 29 core suite behavior must remain unchanged.
- Adding a domain fixture cannot introduce a runtime exception path, fallback, or category bypass.
- All new fixture assumptions must stay in eval artifacts, tests, or docs unless a later approved phase adds a domain pack.

## Configuration Changes

Expected configuration work:

- Add only evaluation suite manifests under `evals/suites/`.
- Do not change `config/default.yaml`.
- Do not require `.veritext` state, environment variables, API keys, or live model access.

Runtime tuning values must remain in `config/`. Evaluation gates live in suite manifests or expected fixture files, not source constants.

## Prompt Changes

No prompt body should be changed in Phase 30.

Allowed prompt-related work:

- Run prompt-no-change verification.

Disallowed prompt-related work:

- Domain examples added to planner, executor, critic, verifier, reconciler, or reporter prompt bodies.
- Prompt instructions that mention a new fixture, domain source name, or expected answer.
- Free-text JSON parsing.

## Tests and Evaluation Gates

Required narrow tests:

- Every new `expected.json` loads through `load_evaluation_case(...)`.
- Every new `report.example.json` validates as `ExtractionReport`.
- Every new fixture scores precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, and zero invariant violations against its static report.
- The Phase 30 suite manifest loads through `load_suite_manifest(...)`.
- The Phase 30 suite scores successfully through `evaluate_suite_manifest(...)`.
- Category and field thresholds in the Phase 30 suite cover every new category and field.
- Existing Phase 29 core suite still scores successfully.

Required broader verification before Phase 30 completion:

```bash
PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json
PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json
make test
make lint
make smoke
git diff --check
git diff --exit-code -- prompts
```

Evaluation gate:

- The Phase 30 diverse corpus suite passes global, category, and field thresholds.
- All new fixtures have exact provenance recall `1.0`.
- All new fixtures have zero invariant violations.
- The Phase 29 core suite remains passing.
- No extraction behavior, prompt body, runtime config, or domain-pack runtime behavior is changed to improve a fixture score.

## Implementation Order

1. Add failing tests or assertions for the Phase 30 fixture inventory and suite manifest.
2. Add the Phase 30 suite skeleton after the test proves the missing manifest.
3. Add the SEC, regulatory, standards, and procurement fixtures with exact annotations and static reports.
4. Add the clinical, FDA-label, insurance, and scientific fixtures with exact annotations and static reports.
5. Fill category and field thresholds for every new fixture category and field in the Phase 30 suite manifest.
6. Add or update tests that prove every new fixture and the whole suite score cleanly.
7. Run prompt-no-change verification.
8. Run narrow tests.
9. Run project-level verification.
10. Update the Phase 30 board and `PROGRESS.md`.
11. Commit the completed step or hand off explicitly.

## Expected Board Steps

When the board is created after spec approval, use these steps unless implementation planning exposes a better equivalent split:

1. Add corpus inventory validation and Phase 30 suite skeleton.
2. Add SEC, regulatory, standards, and procurement fixtures.
3. Add clinical, FDA-label, insurance, and scientific fixtures.
4. Add complete suite thresholds, prompt-neutrality verification, and final project verification.

## Gate Criteria

Phase 30 is complete only when:

- At least eight new cross-domain fixtures are checked in, covering the listed target domains or documenting any approved substitution on the board.
- Every new fixture has source text, expected data points, and a static example report.
- Every new expected data point satisfies exact source text and byte/character offset validation.
- The Phase 30 suite manifest includes strict global, category, and field thresholds.
- The Phase 30 suite passes through the public eval CLI.
- The Phase 29 core suite remains passing.
- No runtime extraction behavior, prompt body, runtime config, domain-pack runtime behavior, or architecture rule is changed.
- Relevant narrow tests pass.
- `make test`, `make lint`, `make smoke`, `git diff --check`, and `git diff --exit-code -- prompts` pass when feasible.
- All Phase 30 board issues are resolved or explicitly deferred.
- `PROGRESS.md` is updated.

## Open Questions Before Implementation

1. Should Round 1 require exactly eight new fixtures, or allow a smaller first pass if each fixture has deeper field coverage?
2. Should Phase 30 require live LLM baseline reports, or keep live extraction baselines as optional operator-run evidence outside required tests?
3. Should every new fixture include an `annotation.md`, or only fixtures with non-obvious span-width decisions?
4. Should new domain schemas stay embedded in static report metadata for Phase 30, or should any of these domains receive domain-pack/schema-registry artifacts in a later dedicated phase?
