# Phase 31 - Adversarial, Mutation, and Calibration Evaluation

Status: draft for operator review after Phase 30 acceptance on 2026-05-10. Implementation is blocked until this spec is approved and a Phase 31 board is created.

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
- Phase 30 board and completed commits through `d083384`

## Goal

Add deterministic robustness evaluation on top of the Phase 30 diverse static corpus.

Phase 31 should measure whether extraction outputs remain source-grounded when fixture content is paraphrased, reformatted, distracted, or mutated. It should also add a reproducible confidence-calibration report over checked-in static reports. The result should be a portable evaluation layer that future live runs can use to reveal fixture overfitting, source-insensitive extraction, and overconfident outputs without changing runtime extraction behavior.

## Non-Goals

- Do not tune planner, executor, critic, verifier, reconciler, reporter, source-support, prompts, or runtime config to pass a robustness fixture.
- Do not add adversarial verifier runtime mode, model routing changes, confidence rewriting, or provider/model comparison. Those are outside this evaluation phase.
- Do not add document-specific runtime branches, proper-noun patches, domain-name branches, or one-off phrase handling.
- Do not add PDF, DOCX, HTML, email, OCR, table, or layout-aware ingestion. Those start in Phase 32 and later phases.
- Do not add new domain-pack runtime behavior or schema-fit policy changes.
- Do not add CI/CD integration. Current architecture rules ban CI/CD until an explicit architecture amendment phase.
- Do not require live LLM extraction, API keys, `.veritext` state, or local audit databases for required tests.
- Do not relax exact value matching, source-span matching, byte offsets, character offsets, source hashes, forced tool use, Pydantic contracts, SQLite audit persistence, or no-silent-drop reporting.
- Do not claim live extraction robustness from static mirror reports alone. Static reports prove fixture, scorer, mutation, and calibration contracts; live robustness baselines require separate recorded runs.

## Domain-Scope Alignment

Phase 31 is evaluation work for the domain-neutral kernel. It should add stress cases and measurement contracts as fixtures, suite manifests, and scoring code, not as extraction specialization.

Configurable in Phase 31:

- Synthetic or repo-safe adversarial fixture variants.
- Synthetic or repo-safe mutation fixtures derived from Phase 30-style source documents.
- Expected data points with exact character and byte provenance for every variant and mutation fixture.
- Static `report.example.json` files used to prove scorer and suite gates.
- Robustness suite membership, mutation mapping metadata, and calibration report settings.
- Optional annotation notes for non-obvious adversarial distractors, mutation scope, or span-width decisions.

Non-configurable in Phase 31:

- Exact source-span and byte/character offset validation.
- Existing fixture matching semantics in `evaluate_report(...)`.
- Suite manifest repo-local path validation.
- Category and field metric aggregation from Phase 29.
- Runtime extraction contracts, audit contracts, report contracts, and invariant rules.
- Architecture bans on web UI, REST API, Docker, CI/CD, vector DBs, embeddings, fine-tuning hooks, and agent frameworks.

## Terminology

- An adversarial variant is a source fixture that preserves the intended extractable facts while changing surface form, section order, labels, formatting, or nearby distractors. The expected data points must be anchored to the variant source, not copied from the base fixture offsets.
- A mutation fixture is a source fixture where one or more source-backed facts are changed, removed, or re-scoped. The expected outputs must change accordingly, and the mutation metadata must name the changed expected IDs or replacement values.
- Source sensitivity is the fraction of declared mutation changes that are reflected by scored report outputs without retaining retired source values.
- A calibration report groups report data-point confidence scores into deterministic bins and compares predicted confidence to observed exact correctness and exact provenance correctness.

## Robustness Fixture Boundaries

Add a first wave of adversarial and mutation fixtures under `evals/fixtures/`.

The target corpus should include at least four adversarial variants and at least four mutation fixtures across at least four Phase 30 target domains unless an implementation blocker is logged on the board. Recommended domains are SEC disclosure, clinical or FDA safety text, regulatory or standards text, insurance policy, scientific review, and procurement RFP.

Each adversarial or mutation fixture should include:

- `source.txt` or `source.md` using ingestion formats already supported by current static eval tooling.
- `expected.json` with exact source text, character offsets, byte offsets, and strict thresholds.
- `report.example.json` that validates as `ExtractionReport` and passes exact scoring against `expected.json`.
- `annotation.md` when distractor design, mutation intent, or span-width choices need human-readable justification outside the strict `expected.json` contract.

Fixture source text should stay synthetic, short enough to audit by hand, and domain-realistic enough to exercise field semantics. It must not embed real personal data, secrets, confidential documents, or copyrighted long-form source material.

## Robustness Manifests

Add Phase 31 robustness manifests under `evals/suites/`:

```text
evals/suites/phase_31_adversarial.json
evals/suites/phase_31_mutation.json
```

The adversarial manifest should identify each base fixture and variant fixture pair. It should require:

- Every pair references repo-relative checked-in case and report paths.
- Every variant fixture passes strict global, category, and field thresholds.
- Pair metadata records the adversarial mode, such as paraphrase, reordering, distractor insertion, label replacement, or formatting change.
- No pair can reuse base fixture offsets for variant expected data points unless the variant source text genuinely keeps the same offset.

The mutation manifest should identify base and mutated fixtures plus declared change metadata. It should require:

- Every mutation references repo-relative checked-in case and report paths.
- Every mutation fixture passes strict global, category, and field thresholds.
- Mutation metadata declares changed expected IDs, retired source values, and introduced source values when applicable.
- The mutation scorer reports source sensitivity and fails when a declared mutation keeps a retired value or omits an introduced source-backed value.

The existing Phase 29 and Phase 30 suite manifest behavior must remain unchanged. Implement Phase 31 robustness manifests as separate evaluation-only Pydantic contracts in `src/extractor/evals/robustness.py` rather than extending `EvaluationSuiteManifest`.

Add explicit CLI modes for the new manifest types:

- `veritext-eval --adversarial-suite <manifest>` for adversarial pair scoring.
- `veritext-eval --mutation-suite <manifest>` for mutation scoring and source-sensitivity checks.
- `veritext-eval --calibration-suite <manifest>` for calibration JSON over an existing `EvaluationSuiteManifest`.

## Calibration Report

Add a deterministic calibration report over checked-in static report outputs.

The report should be JSON, generated from suite results, and include:

- The suite or suite set being calibrated.
- Total matched and unmatched data points.
- Confidence bins with lower bound, upper bound, count, average confidence, exact-match accuracy, exact-provenance accuracy, calibration gap, and representative fixture IDs.
- Aggregate expected calibration error over exact-match accuracy.
- Aggregate provenance calibration error over exact-provenance accuracy.
- Lists of bins with zero observations so consumers can distinguish empty bins from perfect bins.

Default bins should be deterministic and documented in the code or manifest. A reasonable first set is `[0.0, 0.5)`, `[0.5, 0.8)`, `[0.8, 0.9)`, `[0.9, 0.95)`, and `[0.95, 1.0]`.

Phase 31 should not add plotting dependencies. A JSON reliability-table payload is enough; chart rendering belongs to a later reporting or viewer phase if approved.

## Annotation Discipline

All expected data points must follow `docs/annotation-conventions.md`.

Required properties:

- `source_text` equals the exact source character slice.
- `start_byte` and `end_byte` equal UTF-8 byte offsets for the chosen character slice.
- `value` is either the source text or a controlled normalization whose content words are all supported by the source text.
- Field span widths follow the Type A/B/C/D conventions.
- Expected IDs are stable, descriptive, and unique within the fixture.
- Category and field names are domain-relevant but not tailored to one proper noun or one sentence.

Adversarial and mutation fixtures must not redefine annotation policy. If a stress case exposes annotation ambiguity, log it on the Phase 31 board and resolve it as a general source-span convention before adding the affected fixture.

## Stage and Module Boundaries

### Evaluation Code

Expected new or modified files are limited to evaluation modules:

- `src/extractor/evals/models.py`
- `src/extractor/evals/suites.py`
- `src/extractor/evals/robustness.py`
- `src/extractor/evals/calibration.py`
- `src/extractor/evals/cli.py`
- `src/extractor/evals/__init__.py`

Do not edit runtime pipeline stages for Phase 31. If a robustness gate cannot be represented without changing runtime contracts, log the design issue and stop before changing contracts.

### Evaluation Artifacts

Expected new files are under:

- `evals/fixtures/<fixture_id>/source.txt` or `source.md`
- `evals/fixtures/<fixture_id>/expected.json`
- `evals/fixtures/<fixture_id>/report.example.json`
- `evals/fixtures/<fixture_id>/annotation.md` if needed
- `evals/suites/phase_31_adversarial.json`
- `evals/suites/phase_31_mutation.json`

### Tests

Expected test edits are limited to evaluation tests:

- `tests/unit/test_eval_suites.py`
- `tests/unit/test_evals.py`
- `tests/unit/test_eval_robustness.py`
- `tests/unit/test_eval_calibration.py`

Do not add tests that require live provider calls, API keys, or local run state.

## Contract Changes

Expected contract changes are additive evaluation-only contracts.

Allowed:

- Pydantic contracts for adversarial pair manifests.
- Pydantic contracts for mutation manifests and mutation result summaries.
- Pydantic contracts for calibration bins and calibration reports.
- Additive CLI JSON output for robustness and calibration modes.

Disallowed:

- Changes to `DataPoint`, `SourceSpan`, `ExtractionReport`, planner contracts, executor contracts, audit tables, or report schema solely for robustness scoring.
- Domain-specific Pydantic models outside evaluation artifacts.
- Source-code enums or constants for SEC, clinical, FDA, insurance, standards, scientific, or procurement categories.
- Fuzzy matching, model-assisted scoring, prompt-based scoring, or confidence rewriting.

## Audit and Provenance Effects

Phase 31 does not change the extraction audit store.

Required properties:

- Every static report remains a valid `report.v2` artifact.
- Static reports preserve run ID, document ID, schema metadata when available, data-point IDs, output IDs, source spans, confidence values, and source hashes.
- Evaluation output identifies fixture ID, case path, report path, pair ID or mutation ID, category failures, field failures, missing IDs, unexpected IDs, invariant violations, source-sensitivity failures, and calibration bins through typed result models.
- No expected data point or static report data point may silently drop source provenance.

## Invariant Impact

Do not weaken I1-I9.

Phase 31 protects invariants by adding stress measurement. Required protections:

- New fixtures must load through strict Pydantic evaluation contracts.
- New static reports must validate through existing report contracts.
- Robustness suite gates must fail on any source-span, byte-offset, source-text, invariant, mutation, or source-sensitivity violation.
- Existing Phase 29 and Phase 30 suite behavior must remain unchanged.
- Adding a robustness fixture cannot introduce a runtime exception path, fallback, or category bypass.
- All adversarial and mutation assumptions must stay in eval artifacts, tests, or docs unless a later approved phase adds runtime behavior.

## Configuration Changes

Expected configuration work:

- Add only evaluation suite or robustness manifests under `evals/suites/`.
- Do not change `config/default.yaml`.
- Do not require `.veritext` state, environment variables, API keys, or live model access.

Runtime tuning values must remain in `config/`. Evaluation gates live in suite manifests, robustness manifests, or expected fixture files, not source constants unless they are structural default calibration bins.

## Prompt Changes

No prompt body should be changed in Phase 31.

Allowed prompt-related work:

- Run prompt-no-change verification.

Disallowed prompt-related work:

- Domain examples added to planner, executor, critic, verifier, reconciler, or reporter prompt bodies.
- Prompt instructions that mention a new fixture, domain source name, adversarial pattern, mutation value, or expected answer.
- Free-text JSON parsing.

## Tests and Evaluation Gates

Required narrow tests:

- Every new `expected.json` loads through `load_evaluation_case(...)`.
- Every new `report.example.json` validates as `ExtractionReport`.
- Every new fixture scores precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, and zero invariant violations against its static report.
- The Phase 31 adversarial manifest loads and rejects duplicate pair IDs, bad paths, missing reports, unsupported adversarial modes, and offset-reuse violations when applicable.
- The Phase 31 mutation manifest loads and rejects duplicate mutation IDs, bad paths, missing reports, empty declared changes, and mutation metadata that names retired values absent from the base fixture.
- The mutation scorer fails when a static mutation report keeps a retired value or misses an introduced value.
- The calibration report bins confidence values deterministically and computes exact-match and exact-provenance calibration errors from suite results.
- Existing Phase 29 core suite and Phase 30 diverse corpus suite still score successfully.

Required broader verification before Phase 31 completion:

```bash
PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json
PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json
PYTHONPATH=src python3 -m extractor.evals --adversarial-suite evals/suites/phase_31_adversarial.json
PYTHONPATH=src python3 -m extractor.evals --mutation-suite evals/suites/phase_31_mutation.json
PYTHONPATH=src python3 -m extractor.evals --calibration-suite evals/suites/phase_30_diverse_corpus_round_1.json
make test
make lint
make smoke
git diff --check
git diff --exit-code -- prompts
```

Evaluation gate:

- Phase 29 and Phase 30 suites remain passing.
- Phase 31 adversarial fixtures pass strict global, category, and field thresholds.
- Phase 31 mutation fixtures pass strict global, category, and field thresholds.
- Mutation source-sensitivity score is 1.0 for declared mutations in static mirror reports.
- Calibration JSON is generated deterministically and contains no invalid confidence bins.
- No extraction behavior, prompt body, runtime config, or domain-pack runtime behavior is changed to improve a robustness score.

## Implementation Order

1. Add failing tests for adversarial manifest loading, duplicate-pair rejection, bad-path rejection, and Phase 31 adversarial suite absence.
2. Add additive adversarial manifest contracts and loader code.
3. Add the first adversarial fixtures and static reports across at least four domains.
4. Add adversarial suite scoring coverage and `--adversarial-suite` CLI output.
5. Add failing tests for mutation manifest loading, declared-change validation, source-sensitivity failure reporting, and Phase 31 mutation suite absence.
6. Add additive mutation manifest contracts, source-sensitivity scoring, and result models.
7. Add the first mutation fixtures and static reports across at least four domains.
8. Add failing tests for calibration binning and deterministic calibration JSON over suite results.
9. Add additive calibration contracts, report generation, and CLI output.
10. Run prompt-no-change verification.
11. Run narrow tests.
12. Run project-level verification.
13. Update the Phase 31 board and `PROGRESS.md`.
14. Commit the completed step or hand off explicitly.

## Expected Board Steps

When the board is created after spec approval, use these steps unless implementation planning exposes a better equivalent split:

1. Add adversarial manifest contracts, loader validation, and suite skeleton.
2. Add adversarial fixture variants and strict suite gates.
3. Add mutation manifest contracts, source-sensitivity scoring, and suite skeleton.
4. Add mutation fixtures and strict source-sensitivity gates.
5. Add calibration report generation and CLI JSON output.
6. Add prompt-neutrality verification and final project verification.

## Gate Criteria

Phase 31 is complete only when:

- At least four adversarial variants are checked in across at least four Phase 30 target domains or approved substitutions are documented on the board.
- At least four mutation fixtures are checked in across at least four Phase 30 target domains or approved substitutions are documented on the board.
- Every new fixture has source text, expected data points, and a static example report.
- Every new expected data point satisfies exact source text and byte/character offset validation.
- Phase 31 robustness manifests include strict thresholds and source-sensitivity metadata.
- Phase 31 adversarial and mutation suites pass through public eval CLI modes `--adversarial-suite` and `--mutation-suite`.
- Calibration JSON passes through public eval CLI mode `--calibration-suite`.
- Calibration report generation is deterministic and covered by tests.
- Phase 29 and Phase 30 suites remain passing.
- No runtime extraction behavior, prompt body, runtime config, domain-pack runtime behavior, or architecture rule is changed.
- Relevant narrow tests pass.
- `make test`, `make lint`, `make smoke`, `git diff --check`, and `git diff --exit-code -- prompts` pass when feasible.
- All Phase 31 board issues are resolved or explicitly deferred.
- `PROGRESS.md` is updated.

## Board Decisions to Pin at Opening

1. Require at least four adversarial variants and four mutation fixtures across at least four Phase 30 target domains.
2. Keep live LLM robustness baselines optional operator-run evidence outside required tests.
3. Keep calibration output as deterministic JSON reliability tables without plotting dependencies.
4. Add evaluation-only robustness contracts rather than changing runtime report, data point, planner, or audit contracts.
