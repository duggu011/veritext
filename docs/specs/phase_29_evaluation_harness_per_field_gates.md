# Phase 29 - Evaluation Harness: Per-Field Gates

Status: approved for implementation after operator continuation on 2026-05-10. Board: `docs/boards/phase_29_evaluation_harness_per_field_gates.md`.

Date opened: 2026-05-10

Roadmap sources:

- `docs/PROJECT_OVERVIEW.md`:
  - Evaluation roadmap
  - Highest-leverage accuracy/provenance improvement 2
- `docs/phase_26_plus_roadmap.md`
- `docs/boards/README.md`
- `PROGRESS.md`
- Phase 28 board and completed commits through `47a350d`

## Goal

Upgrade the evaluation harness from global fixture-level metrics to source-grounded suite, category, and field metrics with enforceable gates.

Phase 29 should make it impossible for later phases to hide a weak category or field behind a strong aggregate F1. The scorer must report precision, recall, F1, provenance recall, false positives, false negatives, and invariant violations globally and by category/field while preserving the existing exact-match behavior.

## Non-Goals

- Do not add the diverse cross-domain fixture corpus. That is Phase 30.
- Do not add adversarial fixtures, mutation testing, calibration reports, or confidence reliability diagrams. Those are Phase 31.
- Do not tune extraction behavior, planner prompts, executor prompts, critic/verifier behavior, reconciliation behavior, or schema artifacts to improve any fixture score.
- Do not add CI/CD integration. Current architecture rules ban CI/CD until an explicit architecture amendment phase.
- Do not add a web UI, REST API, Docker, vector DB, embeddings, fine-tuning hooks, or agent frameworks.
- Do not run live LLM extraction as part of evaluation tests.
- Do not add cost-per-correct-fact metrics, model comparison, or stage routing. Those are later deployment-economics phases.
- Do not relax exact source-span, byte-offset, character-offset, source-hash, or invariant checks.

## Domain-Scope Alignment

Phase 29 is domain-neutral evaluation infrastructure. It should work for the existing financial, policy, mixed-distractor, and legal fixtures without adding domain-specific scorer logic.

Configurable in Phase 29:

- Suite manifests listing evaluation case/report pairs.
- Suite-level, category-level, and field-level thresholds.
- Fixture metadata used for reporting and grouping.
- CLI or JSON output shape for aggregate and breakdown metrics.

Non-configurable in Phase 29:

- Exact value matching semantics already used by `evaluate_report(...)`.
- Exact provenance matching by character offsets, byte offsets, and source text.
- Source file SHA-256 loading in `load_evaluation_case(...)`.
- Invariant-violation detection for source span bounds, byte alignment, text mismatch, and byte mismatch.
- Pydantic strictness and `extra="forbid"` for evaluation contracts.
- Existing single-fixture scoring behavior and existing fixture gates.

## Stage and Module Boundaries

### Evaluation Models

Extend `src/extractor/evals/models.py` with typed models for:

- metric breakdown keys:
  - category-only breakdowns keyed by `category`
  - field breakdowns keyed by `(category, field_name)` to avoid collisions between same-named fields in different categories
- per-breakdown metrics containing expected count, actual count, true positives, false positives, false negatives, precision, recall, F1, exact provenance matches, provenance recall, and invariant violation count
- suite manifest fixtures and suite manifest thresholds
- suite-level results that aggregate multiple `EvaluationResult` records

Keep existing successful single-fixture callers working. If `EvaluationResult` gains new fields, tests must prove old fixture scoring still works through the public API and CLI.

### Scoring

Extend `src/extractor/evals/scoring.py` so `evaluate_report(...)` computes:

- existing global metrics exactly as today
- per-category metrics
- per-field metrics keyed by category plus field name
- missing expected IDs grouped by category/field
- unexpected data point IDs grouped by category/field
- invariant violations grouped by the actual data point category/field when a violation references a report data point

The grouping rules must remain deterministic:

- True positives are grouped by the matched expected point's category and field.
- False negatives are grouped by the missing expected point's category and field.
- False positives are grouped by the unexpected report data point's category and field.
- Invariant violations with a `data_point_id` are grouped through the corresponding report data point. Invariant violations without a report data point remain global-only.

Do not introduce fuzzy matching or semantic equivalence in Phase 29.

### Suite Manifests

Add JSON suite manifests under `evals/suites/`.

The first suite should cover the existing static fixture/report pairs, including the Phase 28 legal fixture. Suite entries should use repo-relative paths so they are portable and do not require the operator's local `.veritext` state.

The manifest contract should reject:

- duplicate suite fixture IDs
- missing or non-repo-local case paths
- missing or non-repo-local report paths
- duplicate category/field threshold keys
- thresholds outside `[0.0, 1.0]`
- non-zero invariant allowances unless explicitly declared by a test fixture with a documented rationale

Use JSON rather than YAML for suite manifests in Phase 29 to stay aligned with existing eval fixture and report files and avoid expanding configuration formats.

### CLI and Output

Keep the existing single-fixture `veritext-eval <case> <report>` behavior.

Add a suite scoring path, either through a new `veritext-eval-suite <manifest>` console script or a backwards-compatible `veritext-eval --suite <manifest>` mode. The board should pin this choice before implementation.

CLI JSON output must expose:

- global suite metrics
- per-fixture pass/fail results
- per-category metrics
- per-field metrics
- missing expected IDs and unexpected data point IDs
- invariant violations
- threshold failures with enough detail to identify the suite, fixture, category, or field that failed

## Contract Changes

Allowed:

- New Pydantic evaluation models under `src/extractor/evals/`.
- Additive fields on `EvaluationResult` if old call sites and tests remain compatible.
- New suite-manifest loader and result contracts.
- New CLI output fields and, if chosen on the board, one new eval console script.

Disallowed:

- Changes to `DataPoint`, `SourceSpan`, `ExtractionReport`, `ApprovedSchemaMetadata`, audit tables, planner contracts, or runtime extraction contracts solely for evaluation reporting.
- Any source-specific or domain-specific scoring branch.
- Any fuzzy, model-assisted, or prompt-based scoring.
- Any architecture-rule amendment for CI/CD.

## Audit and Provenance Effects

Phase 29 does not change the extraction audit store.

Required properties:

- Evaluation output continues to be derived from static expected cases and `report.v2` reports.
- Per-category and per-field provenance recall must use exact source spans only.
- Invariant violations must preserve their existing reason codes and data-point IDs.
- Suite output must preserve source report identities: suite ID, fixture ID, case path, report path, run ID, document ID, and schema metadata when available from the report.
- No evaluation result may silently drop missing expected IDs or unexpected data point IDs from global or grouped output.

## Invariant Impact

Do not weaken I1-I9.

Evaluation is not a runtime pipeline stage, but it protects invariant enforcement. Required protections:

- Existing exact-match fixture behavior must remain unchanged.
- Existing invariant violations must still fail global gates.
- Category/field gates cannot pass a fixture that fails global invariant constraints.
- Grouped metrics cannot reclassify a wrong category or wrong field as correct.
- Suite manifests cannot reference external paths or generated local state by default.
- Missing optional suite manifests must not break existing single-fixture eval CLI behavior.

If implementation reveals that the current evaluation result model cannot carry breakdowns without breaking existing consumers, log the design issue on the Phase 29 board and stop before changing reporter or extraction contracts.

## Configuration Changes

Expected configuration work:

- Add `evals/suites/phase_29_core.json` or equivalent.
- Do not change `config/default.yaml`; evaluation suite manifests are test/eval artifacts, not runtime extraction tuning.
- Do not require `.veritext` state, environment variables, API keys, or live model access.

Runtime tuning values must remain in `config/`. Evaluation gates live in eval suite manifests or expected fixture JSON, not source constants.

## Prompt Changes

No prompt body should be changed in Phase 29.

Allowed prompt-related work:

- Add a guard test or verification command proving prompts were not changed.

Disallowed prompt-related work:

- Prompt examples to improve fixture scores.
- Prompt instructions that mention specific evaluation fixtures.
- Free-text JSON parsing.

## Tests and Evaluation Gates

Required narrow tests:

- Per-category metrics for a passing fixture.
- Per-field metrics for a passing fixture.
- Per-category and per-field false positive, false negative, precision, recall, and F1 behavior.
- Per-category and per-field provenance recall when a source span is shifted but category/field/value still match.
- Invariant violation grouping by category and field when a violated data point has a known ID.
- Suite manifest loader validation for valid manifest, duplicate fixture IDs, bad paths, duplicate threshold keys, and invalid thresholds.
- Suite scoring result for the static fixture suite.
- CLI JSON output for single-fixture and suite scoring.
- Existing fixture tests continue passing.

Required broader verification before Phase 29 completion:

```bash
make test
make lint
make smoke
git diff --check
git diff --exit-code -- prompts
```

Evaluation gate:

- The Phase 29 core suite passes global, category, and field thresholds.
- Existing fixture exact-match scores remain precision 1.0, recall 1.0, F1 1.0, provenance recall 1.0, and zero invariant violations.
- Failure tests demonstrate that a single weak category or field fails even when aggregate metrics remain above threshold.

## Implementation Order

1. Add failing tests for per-category and per-field metric models and scorer output.
2. Implement the minimal breakdown models and scorer aggregation needed to pass those tests.
3. Add failing tests for grouped false positives, false negatives, provenance recall, and invariant violations.
4. Implement deterministic grouping rules for matched, missing, unexpected, and invariant-violating data points.
5. Add failing tests for JSON suite manifest loading and validation.
6. Add the suite manifest contract, loader, and `evals/suites/phase_29_core.json`.
7. Add failing tests for suite scoring and threshold failures.
8. Implement suite scoring and threshold failure reporting.
9. Add failing CLI tests for single-fixture breakdown output and suite output.
10. Implement the chosen CLI surface without breaking existing `veritext-eval <case> <report>`.
11. Add or run prompt-no-change verification.
12. Run narrow tests.
13. Run project-level verification.
14. Update the Phase 29 board and `PROGRESS.md`.
15. Commit the completed step or hand off explicitly.

## Expected Board Steps

When the board is created after spec approval, use these steps unless implementation planning exposes a better equivalent split:

1. Add category and field metric breakdown contracts and scorer coverage.
2. Add provenance and invariant breakdown grouping coverage.
3. Add suite manifest contracts, loader, and core suite artifact.
4. Add suite scoring, threshold failure reporting, and CLI output.
5. Add prompt-neutrality verification and final project verification.

## Gate Criteria

Phase 29 is complete only when:

- Single-fixture evaluation still works through the existing public API and CLI.
- Evaluation results include per-category and per-field precision, recall, F1, provenance recall, false positives, false negatives, and invariant counts.
- Suite manifests validate through strict Pydantic contracts.
- The core suite scores existing static fixtures, including the legal fixture, without external local state.
- Threshold failures identify the exact suite, fixture, category, or field that failed.
- No extraction behavior, prompt body, or domain artifact is changed to improve evaluation scores.
- No CI/CD behavior is added.
- Relevant narrow tests pass.
- `make test`, `make lint`, `make smoke`, `git diff --check`, and `git diff --exit-code -- prompts` pass when feasible.
- All Phase 29 board issues are resolved or explicitly deferred.
- `PROGRESS.md` is updated.

## Open Questions Before Implementation

1. Should suite scoring be exposed as `veritext-eval --suite <manifest>` or as a separate `veritext-eval-suite <manifest>` console script?
2. Should category and field thresholds live only in suite manifests, or should individual `expected.json` fixtures also support grouped thresholds?
3. Should the first suite manifest include `medium_research_brief`, which currently lacks a static `report.example.json`, or should Phase 29 keep the first suite limited to fixtures with checked-in reports?
4. Should threshold failure output include full missing/unexpected ID lists by default, or only counts plus a separate verbose mode?
