# Phase 36 - Lens Taxonomy and Normalization Contracts

## Current Status

Step: 6 of 6
Branch: main
Started: 2026-05-29
Last session: 2026-05-29
Spec: `docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:4. Executor`; `docs/PROJECT_OVERVIEW.md:5. Dedup`; `docs/PROJECT_OVERVIEW.md:8. Reconciler`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 36 was accepted by operator continuation on 2026-05-29.

Next: Phase 37 spec review and prompt-content gate resolution.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add lens taxonomy and normalization contract tests, including legacy audit payload readability and executable-vs-contract-only lens validation.
- [x] Step 2: Add focused Pydantic taxonomy and normalization modules plus public exports.
- [x] Step 3: Extend `LensCandidate` and `DataPoint` additively with verbatim/canonical value metadata and validation.
- [x] Step 4: Populate candidate normalization metadata during server-side materialization without changing executor prompt bodies or tool payload requirements.
- [x] Step 5: Carry normalization metadata through reconciler materialization, audit readback, and compact inspection output while preserving ID-only reconciler behavior.
- [x] Step 6: Run final project, smoke, lint, prompt-neutrality, and evaluation gates; fill the board summary and stop for operator acceptance.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Planned lens roles are contract-only in Phase 36 unless already executable. | Prevents prompt/stage expansion before Phase 37 while making future roles auditable. |
| Q2 | Existing `value` remains a compatibility field. | Keeps old audit payloads and downstream consumers readable while adding verbatim/canonical fields. |
| Q3 | Verbatim and canonical values are separate. | Auditors need source-facing values; downstream tooling needs canonical comparison values. |
| Q4 | Canonical values are metadata and do not create source spans. | Preserves exact span provenance and prevents normalized strings from claiming source bytes. |
| Q5 | Unsupported normalization fails explicitly. | Prevents silent invention of canonical values and preserves no-silent-drop behavior. |

---

## Gate Interpretations

- Phase 36 may add focused contract modules under `src/extractor/contracts/` and optional metadata fields on schema/domain-pack contracts.
- Phase 36 may extend `LensCandidate` and `DataPoint` additively with defaults or compatibility validators.
- Phase 36 must preserve the existing four executable lenses and must not schedule planned-only lenses through executor runtime.
- Phase 36 must not change executor prompt bodies, add new executor prompt files, or require the LLM to emit new candidate payload fields.
- Phase 36 must not change dedup keys, conflict behavior, cross-document reconciliation, reporter formats, or architecture rules.
- Existing audit payload JSON for candidates and data points must remain readable.
- Prompt-neutrality verification is required before Phase 36 completion.
- If normalization metadata changes report JSON or audit inspection output, record before/after payload shape and extraction metrics on this board.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md:1` | Approved Phase 36 spec. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_36_lens_taxonomy_and_normalization_contracts.md:1` | Active Phase 36 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `tests/unit/test_phase_36_lens_normalization_contracts.py:1` | Added RED/GREEN coverage for lens taxonomy contracts, normalization policy contracts, legacy payload readability, canonicalization metadata validation, contract-only lens execution rejection, executor materialization, and reconciler propagation. | Steps 1-5 |
| `src/extractor/contracts/lens_taxonomy.py:1` | Added typed Phase 36 lens taxonomy registry with executable-vs-contract-only runtime status validation. | Step 2 |
| `src/extractor/contracts/normalization.py:1` | Added value-kind, normalization status, normalization policy, field policy, registry, and shared metadata validation contracts. | Step 2 |
| `src/extractor/contracts/__init__.py:1` | Exported Phase 36 taxonomy and normalization contracts. | Step 2 |
| `src/extractor/contracts/models.py:1` | Added defaulted verbatim/canonical value metadata fields and validation to `LensCandidate` and `DataPoint` while preserving legacy payload readability. | Step 3 |
| `src/extractor/executor/materialization.py:1` | Populated server-derived normalization metadata during candidate materialization without changing executor prompt bodies or LLM tool payloads. | Step 4 |
| `src/extractor/reconciler/materialization.py:1` | Carried selected source candidate normalization metadata into final data points while preserving ID-only reconciler behavior. | Step 5 |
| `tests/unit/test_audit_inspection.py:1` | Added compact audit-inspection coverage for candidate and data-point normalization metadata. | Step 5 |
| `src/extractor/audit/inspection.py:1` | Included normalization metadata in compact audit inspection details. | Step 5 |
| `docs/boards/README.md:1` | Marked Phase 36 awaiting operator acceptance after final verification. | Step 6 |
| `docs/boards/phase_36_lens_taxonomy_and_normalization_contracts.md:1` | Recorded final gate verification, work log, and phase summary. | Step 6 |
| `PROGRESS.md:1` | Recorded Phase 36 final verification and handoff. | Step 6 |

---

## Issues

_(No issues yet.)_

<!--
### ISS-001 - <short title>
**Status:** OPEN | **Severity:** high/medium/low | **Found:** Step K, 2026-05-29
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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md docs/boards/README.md docs/boards/phase_36_lens_taxonomy_and_normalization_contracts.md`; `rg -n "Phase 36|phase_36_lens_taxonomy_and_normalization_contracts.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md docs/boards/phase_36_lens_taxonomy_and_normalization_contracts.md`; `cmp -s AGENTS.md CLAUDE.md` returned `1` because of pre-existing local `AGENTS.md` drift unrelated to this phase. | PASS with noted unrelated drift | 2026-05-29 |
| 1 | `python3 -m pytest tests/unit/test_phase_36_lens_normalization_contracts.py -q` first failed with missing Phase 36 contract exports, then passed the initial contract set with 6 passed after adding focused contracts and defaulted metadata fields. | PASS | 2026-05-29 |
| 2 | `python3 -m pytest tests/unit/test_phase_36_lens_normalization_contracts.py -q` passed with taxonomy and normalization policy contracts; `wc -l src/extractor/contracts/normalization.py src/extractor/contracts/lens_taxonomy.py src/extractor/contracts/models.py` later reported 131, 177, and 392 lines. | PASS | 2026-05-29 |
| 3 | `python3 -m pytest tests/unit/test_phase_36_lens_normalization_contracts.py -q` passed legacy `LensCandidate`/`DataPoint` payload readability and canonicalization metadata validation. | PASS | 2026-05-29 |
| 4 | `python3 -m pytest tests/unit/test_phase_36_lens_normalization_contracts.py -q` first failed because executor materialization left `value_verbatim` unset, then passed with 8 passed after server-side normalization metadata population. | PASS | 2026-05-29 |
| 5 | `python3 -m pytest tests/unit/test_audit_inspection.py -q` first failed with missing `value_verbatim` in compact inspection output, then `python3 -m pytest tests/unit/test_audit_inspection.py tests/unit/test_phase_36_lens_normalization_contracts.py -q` passed with 10 passed; `python3 -m pytest tests/unit/test_phase_36_lens_normalization_contracts.py tests/unit/test_audit_inspection.py tests/unit/test_contracts.py tests/unit/test_executor.py tests/unit/test_reconciler.py tests/unit/test_dedup.py tests/unit/test_audit_store.py tests/unit/test_domain_pack_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_orchestrator.py tests/unit/test_reporter.py -q` passed with 95 passed; `git diff --exit-code -- prompts` passed; `make lint` passed; `git diff --check` passed; `wc -l src/extractor/contracts/normalization.py src/extractor/contracts/lens_taxonomy.py src/extractor/contracts/models.py src/extractor/executor/materialization.py src/extractor/reconciler/materialization.py src/extractor/audit/inspection.py tests/unit/test_phase_36_lens_normalization_contracts.py tests/unit/test_audit_inspection.py` reported 131, 177, 392, 92, 389, 294, 322, and 281 lines. | PASS | 2026-05-29 |
| 6 | `make test` passed with 331 passed, 2 skipped; `make lint` passed; `make smoke` passed with 1 passed; `git diff --check` passed; `git diff --exit-code -- prompts` passed; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual/true positives, 21 exact provenance matches, and zero invariant violations; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 expected/actual/true positives, 49 exact provenance matches, and zero invariant violations; `PYTHONPATH=src python3 -m extractor.evals --adversarial-suite evals/suites/phase_31_adversarial.json` passed; `PYTHONPATH=src python3 -m extractor.evals --mutation-suite evals/suites/phase_31_mutation.json` passed with source sensitivity 1.0; `PYTHONPATH=src python3 -m extractor.evals --calibration-suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 matched data points, 0 unmatched data points, expected calibration error 0.048979591836734754, and provenance calibration error 0.048979591836734754. | PASS | 2026-05-29 |

### Final Gate

- [x] Narrow relevant tests pass
- [x] `make test` passes when feasible
- [x] `make lint` passes
- [x] `make smoke` passes when feasible
- [x] `git diff --check` passes
- [x] Evaluation gates pass, if this phase changes extraction behavior
- [x] All OPEN issues are resolved or explicitly deferred
- [x] Phase Summary filled in
- [x] `PROGRESS.md` updated

---

## Work Log

Reverse chronological. Log every session.

### 2026-05-29 - Session 1

- Resumed from the Phase 36 spec draft under operator-trust resume mode.
- Completed: approved the Phase 36 spec for implementation, opened this board, pinned gate interpretations, and updated active phase tracking.
- Completed Step 1: added focused RED/GREEN tests for lens taxonomy contracts, normalization policy contracts, legacy candidate/data-point payload readability, canonicalization metadata validation, and planned-only lens execution rejection.
- Completed Step 2: added focused Pydantic taxonomy and normalization modules plus public exports.
- Completed Step 3: extended `LensCandidate` and `DataPoint` additively with verbatim/canonical metadata and strict normalization validation.
- Completed Step 4: populated server-derived normalization metadata during executor materialization without changing prompt bodies or tool payloads.
- Completed Step 5: carried normalization metadata through reconciler materialization and compact audit inspection while preserving ID-only reconciler behavior.
- Completed Step 6: ran final project, smoke, lint, prompt-neutrality, Phase 29/30 extraction, Phase 31 adversarial/mutation, and calibration gates; filled the final gate and phase summary.
- Issues found: none.
- Tests: board-opening, Steps 1-5 red/green/regression verification, and Step 6 final verification passed as recorded above, with the known unrelated `AGENTS.md`/`CLAUDE.md` drift preserved outside this phase.
- Accepted by operator continuation after final verification.
- Next: Phase 37 spec review and prompt-content gate resolution.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

### What shipped vs spec

- Built as specified: typed lens taxonomy contracts; executable-vs-contract-only lens validation; typed normalization policy/value-kind/status contracts; additive `LensCandidate` and `DataPoint` verbatim/canonical metadata; strict canonicalization validation; server-side executor materialization of normalization metadata without prompt/tool-payload changes; reconciler propagation from selected candidate to data point; compact audit inspection readback; legacy payload compatibility tests; prompt-neutrality and extraction evaluation gates.
- Deferred: new executable lenses, prompt expansion, LLM normalization, dedup canonical-value/conflict behavior, cross-document reconciliation, reporter format changes, and architecture-rule changes remain for later phases.
- Added beyond spec: none.

### Lessons for downstream phases

- Keep `LensName` executable-only and use `LensTaxonomyName` for planned roles until each new lens has runtime, prompt, budget, and verification support.
- Treat `value` as a compatibility field. Use `value_verbatim` for auditor-facing source text and `value_canonical` for deterministic comparison metadata.
- Canonical values remain metadata; exact source spans continue to point only at source text.
- The current `source-traced-label` policy is server-derived metadata, not an LLM output requirement.
