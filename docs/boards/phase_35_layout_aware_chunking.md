# Phase 35 - Layout-Aware Chunking

## Current Status

Step: 6 of 6
Branch: main
Started: 2026-05-29
Last session: 2026-05-29
Spec: `docs/specs/phase_35_layout_aware_chunking.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:2. Chunker`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 35 was accepted by the operator on 2026-05-29. Phase 36 has been approved and opened as the active board.

Next: continue from `docs/boards/phase_36_lens_taxonomy_and_normalization_contracts.md`.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add contract and config tests for additive chunk metadata, legacy chunk payload readback, tokenizer-policy validation, and unchanged public imports.
- [x] Step 2: Split reusable token-offset helpers from the current fixed-window chunker and keep the legacy path green.
- [x] Step 3: Add boundary collection and validation from page maps, layout spans, and table spans.
- [x] Step 4: Add boundary-aware packing that preserves headings, paragraphs, sentences, and tables, including explicit oversized atomic chunk handling.
- [x] Step 5: Add hierarchy and dependency metadata, audit readback coverage, resume validation coverage, and prompt-neutrality verification.
- [x] Step 6: Run final project, smoke, lint, prompt-neutrality, and evaluation gates; fill the board summary and stop for operator acceptance.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Cross-chunk markers are metadata, not injected text. | Keeps `Chunk.text` an exact source slice and preserves downstream mechanical span validation. |
| Q2 | Tables are atomic; oversized table chunks are explicit. | Prevents silent mid-table splits while making target-window violations auditable. |
| Q3 | Long prose overflow is allowed only when no safe boundary fits. | Keeps paragraph and sentence boundaries preferred without making chunking non-advancing. |
| Q4 | Tokenizer policy is explicit and local; provider APIs are not used for token counts. | Preserves deterministic offline chunking and audit-visible tokenizer assumptions. |
| Q5 | Consuming dependency metadata in executor or planner context is out of scope. | Keeps Phase 35 limited to chunker contracts, metadata, validation, and audit compatibility. |

---

## Gate Interpretations

- Phase 35 may add defaulted `Chunk` and `ChunkingConfig` fields, helper modules under `src/extractor/chunker/`, and focused unit tests.
- Existing `chunk_document(document, config, audit_store=None)` and public imports from `extractor.chunker` and `extractor.contracts` must remain compatible.
- Chunk text must remain an exact contiguous `Document.text` slice with valid character, UTF-8 byte, and token offsets.
- Boundary-aware behavior must consume typed `page_map`, `layout_spans`, and `table_spans`; no document-specific tokens, named entities, industry nouns, or fixture patches are allowed.
- Tables must not be split across chunks; oversized atomic table chunks must be flagged or rejected by explicit config behavior.
- Cross-chunk dependencies and section hierarchy are metadata only; no runtime LLM stage, prompt body, planner behavior, executor behavior, critic behavior, verifier behavior, reconciler behavior, reporter behavior, domain-pack behavior, or architecture rule changes are in scope.
- Prompt-neutrality verification is required before Phase 35 completion.
- If chunk payload changes risk audit idempotency conflicts, resolve with deterministic compatibility behavior or log a board issue before continuing.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_35_layout_aware_chunking.md:1` | Approved Phase 35 spec. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_35_layout_aware_chunking.md:1` | Active Phase 35 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `tests/unit/test_phase_35_chunk_contracts.py:1` | Added Phase 35 RED/GREEN tests for defaulted chunk metadata, legacy chunk audit readback, tokenizer-policy config validation, and legacy token-window defaults. | Step 1 |
| `src/extractor/contracts/models.py:1` | Added defaulted chunk metadata fields and typed chunk metadata literals while preserving legacy payload readability. | Step 1 |
| `src/extractor/contracts/__init__.py:1` | Exported additive chunk metadata literal types without removing existing public contract imports. | Step 1 |
| `src/extractor/config/models.py:1` | Added boundary mode, tokenizer policy, and oversized atomic chunk config fields with strict validation and legacy defaults. | Step 1 |
| `src/extractor/config/__init__.py:1` | Exported additive chunking config literal types without removing existing public config imports. | Step 1 |
| `config/default.yaml:1` | Declared Phase 35 chunking defaults in canonical runtime config. | Step 1 |
| `tests/unit/test_chunker_token_offsets.py:1` | Added RED/GREEN coverage for reusable token-offset helper reconstruction, UTF-8 character-boundary advancement, and mismatch rejection. | Step 2 |
| `src/extractor/chunker/token_offsets.py:1` | Added reusable tokenizer byte, character, and token-span offset helpers for legacy and future boundary-aware chunking. | Step 2 |
| `src/extractor/chunker/tokenizer.py:1` | Routed the fixed-window chunker through reusable token-offset helpers without changing the public `chunk_document(...)` behavior. | Step 2 |
| `tests/unit/test_chunker_boundaries.py:1` | Added RED/GREEN coverage for page, layout, and table boundary collection plus invalid page/span reconciliation failures. | Step 3 |
| `src/extractor/chunker/errors.py:1` | Added shared public chunking error type for tokenizer and boundary validation failures. | Step 3 |
| `src/extractor/chunker/boundaries.py:1` | Added boundary collection and validation for document, page, layout, and table spans. | Step 3 |
| `src/extractor/chunker/__init__.py:1` | Preserved public `ChunkingError` export after moving the error type into a shared module. | Step 3 |
| `tests/unit/test_chunker_layout_aware.py:1` | Added RED/GREEN coverage for layout-aware sentence/heading boundaries, atomic oversized tables, and oversized-table rejection. | Step 4 |
| `src/extractor/chunker/packing.py:1` | Added boundary-aware block packing for paragraphs, headings, tables, sentence boundaries, whitespace gaps, and oversized atomic handling. | Step 4 |
| `src/extractor/chunker/tokenizer.py:1` | Routed explicit `boundary_mode: layout_aware` chunking through the boundary-aware packer while preserving the default token-window path. | Step 4 |
| `tests/unit/test_chunker_hierarchy.py:1` | Added RED/GREEN coverage for section hierarchy metadata, dependency metadata, audit readback, and resume validation failures. | Step 5 |
| `src/extractor/chunker/tokenizer.py:1` | Added post-materialization hierarchy and dependency metadata for layout-aware section chunks. | Step 5 |
| `src/extractor/orchestrator/state.py:1` | Added resume validation for chunk parent and dependency references. | Step 5 |
| `docs/boards/phase_35_layout_aware_chunking.md:1` | Recorded final verification, Phase 35 summary, and acceptance handoff. | Step 6 |
| `docs/boards/README.md:1` | Marked Phase 35 as awaiting operator acceptance. | Step 6 |
| `PROGRESS.md:1` | Recorded Step 6 final verification and acceptance handoff. | Step 6 |
| `docs/boards/README.md:1` | Marked Phase 35 complete and opened Phase 36 as a spec draft. | Acceptance |
| `docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md:1` | Drafted the Phase 36 lens taxonomy and normalization contracts spec. | Acceptance |
| `docs/boards/phase_35_layout_aware_chunking.md:1` | Recorded Phase 35 operator acceptance. | Acceptance |
| `PROGRESS.md:1` | Recorded Phase 35 acceptance and Phase 36 spec-draft handoff. | Acceptance |

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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_35_layout_aware_chunking.md docs/boards/README.md docs/boards/phase_35_layout_aware_chunking.md`; `rg -n "Phase 35|phase_35_layout_aware_chunking.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_35_layout_aware_chunking.md docs/boards/phase_35_layout_aware_chunking.md`; `cmp -s AGENTS.md CLAUDE.md` returned `1` because of pre-existing local `AGENTS.md` drift unrelated to this phase. | PASS with noted unrelated drift | 2026-05-29 |
| 1 | `python3 -m pytest tests/unit/test_phase_35_chunk_contracts.py -q` first failed with missing chunk metadata and config policy fields, then passed with 6 passed; `python3 -m pytest tests/unit/test_phase_35_chunk_contracts.py tests/unit/test_chunker.py tests/unit/test_contracts.py tests/unit/test_config.py tests/unit/test_audit_store.py -q` passed with 49 passed; `make lint` passed; `git diff --check` passed; `wc -l tests/unit/test_phase_35_chunk_contracts.py src/extractor/contracts/models.py src/extractor/config/models.py` reported 146, 355, and 137 lines. | PASS | 2026-05-29 |
| 2 | `python3 -m pytest tests/unit/test_chunker_token_offsets.py -q` first failed with missing `extractor.chunker.token_offsets`, then passed after helper extraction; `python3 -m pytest tests/unit/test_chunker_token_offsets.py tests/unit/test_chunker.py -q` passed with 6 passed; `python3 -m pytest tests/unit/test_chunker_token_offsets.py tests/unit/test_chunker.py tests/unit/test_phase_35_chunk_contracts.py tests/unit/test_contracts.py tests/unit/test_config.py tests/unit/test_audit_store.py -q` passed with 51 passed; `make lint` passed; `git diff --check` passed; `wc -l src/extractor/chunker/tokenizer.py src/extractor/chunker/token_offsets.py tests/unit/test_chunker_token_offsets.py` reported 135, 128, and 40 lines. | PASS | 2026-05-29 |
| 3 | `python3 -m pytest tests/unit/test_chunker_boundaries.py -q` first failed with missing `extractor.chunker.boundaries`, then passed after collector implementation; `python3 -m pytest tests/unit/test_chunker_boundaries.py tests/unit/test_chunker.py -q` passed with 8 passed; `python3 -m pytest tests/unit/test_chunker_boundaries.py tests/unit/test_chunker_token_offsets.py tests/unit/test_chunker.py tests/unit/test_phase_35_chunk_contracts.py tests/unit/test_ingestion_boundaries.py tests/unit/test_contracts.py tests/unit/test_config.py tests/unit/test_audit_store.py -q` passed with 60 passed; `make lint` passed; `git diff --check` passed; `wc -l src/extractor/chunker/boundaries.py src/extractor/chunker/errors.py src/extractor/chunker/tokenizer.py tests/unit/test_chunker_boundaries.py` reported 221, 5, 132, and 144 lines. | PASS | 2026-05-29 |
| 4 | `python3 -m pytest tests/unit/test_chunker_layout_aware.py -q` first failed against the legacy fixed-window path, then passed after layout-aware packing; `python3 -m pytest tests/unit/test_chunker_layout_aware.py tests/unit/test_chunker.py -q` passed with 7 passed; `python3 -m pytest tests/unit/test_chunker_layout_aware.py tests/unit/test_chunker_boundaries.py tests/unit/test_chunker_token_offsets.py tests/unit/test_chunker.py tests/unit/test_phase_35_chunk_contracts.py tests/unit/test_ingestion_boundaries.py tests/unit/test_contracts.py tests/unit/test_config.py tests/unit/test_audit_store.py -q` passed with 63 passed; `make lint` passed; `git diff --check` passed; `wc -l src/extractor/chunker/packing.py src/extractor/chunker/tokenizer.py tests/unit/test_chunker_layout_aware.py` reported 323, 198, and 176 lines. | PASS | 2026-05-29 |
| 5 | `python3 -m pytest tests/unit/test_chunker_hierarchy.py -q` first failed with missing hierarchy metadata and resume dependency validation, then passed with 3 passed; `python3 -m pytest tests/unit/test_chunker_hierarchy.py tests/unit/test_chunker_layout_aware.py tests/unit/test_chunker_boundaries.py tests/unit/test_chunker_token_offsets.py tests/unit/test_chunker.py tests/unit/test_phase_35_chunk_contracts.py tests/unit/test_ingestion_boundaries.py tests/unit/test_contracts.py tests/unit/test_config.py tests/unit/test_audit_store.py tests/unit/test_orchestrator.py -q` passed with 73 passed; `git diff --exit-code -- prompts` passed; `make lint` passed; `git diff --check` passed; `wc -l src/extractor/chunker/tokenizer.py src/extractor/orchestrator/state.py tests/unit/test_chunker_hierarchy.py` reported 235, 376, and 116 lines. | PASS | 2026-05-29 |
| 6 | `make test` passed with 323 passed and 2 skipped; `make lint` passed; `make smoke` passed with 1 passed; `git diff --check` passed; `git diff --exit-code -- prompts` passed; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual/true positives, 21 exact provenance matches, and zero invariant violations; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 expected/actual/true positives, 49 exact provenance matches, and zero invariant violations; `PYTHONPATH=src python3 -m extractor.evals --adversarial-suite evals/suites/phase_31_adversarial.json` passed; `PYTHONPATH=src python3 -m extractor.evals --mutation-suite evals/suites/phase_31_mutation.json` passed with source-sensitivity 1.0; `PYTHONPATH=src python3 -m extractor.evals --calibration-suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 matched data points, 0 unmatched data points, expected calibration error 0.048979591836734754, and provenance calibration error 0.048979591836734754. | PASS | 2026-05-29 |
| Acceptance | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md docs/boards/README.md docs/boards/phase_35_layout_aware_chunking.md`; `rg -n "Phase 35|Phase 36|phase_36_lens_taxonomy_and_normalization_contracts.md|SPEC DRAFT|COMPLETE \\(2026-05-29\\)|ACTIVE - SPEC DRAFT" docs/boards/README.md PROGRESS.md docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md docs/boards/phase_35_layout_aware_chunking.md`; `cmp -s AGENTS.md CLAUDE.md` returned `1` because of pre-existing local `AGENTS.md` drift unrelated to this acceptance step. | PASS with noted unrelated drift | 2026-05-29 |

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

### 2026-05-29 - Acceptance

- Resumed from the completed Phase 35 final gate after operator continuation.
- Completed: accepted Phase 35, marked it complete in the board index, and opened Phase 36 as a spec draft.
- Issues found: none in Phase 35.
- Tests: no Phase 35 runtime behavior changed in this acceptance step; documentation verification passed as recorded above, with the known unrelated `AGENTS.md`/`CLAUDE.md` drift preserved outside this phase.
- Next: operator review of `docs/specs/phase_36_lens_taxonomy_and_normalization_contracts.md`. Do not start Phase 36 until the spec is approved and its board is opened.

### 2026-05-29 - Session 1

- Resumed at Step 0 from the Phase 35 spec draft after operator `start`.
- Completed: approved the Phase 35 spec for implementation, opened this board, pinned open-question resolutions and gate interpretations, and updated active phase tracking.
- Completed Step 1: added additive chunk metadata and chunking config contracts, legacy chunk payload readback coverage, tokenizer-policy validation, and focused tests without growing oversized existing test files.
- Completed Step 2: split reusable token-offset mapping helpers from the fixed-window chunker and kept legacy chunking behavior green.
- Completed Step 3: added page, layout, and table boundary collection/validation with explicit `ChunkingError` failures for unreconciled page gaps and spans outside declared pages.
- Completed Step 4: added explicit layout-aware chunk packing for headings, paragraph sentence boundaries, atomic oversized tables, and oversized-table rejection.
- Completed Step 5: added section hierarchy metadata, dependency metadata, chunk audit readback coverage, resume dependency validation, and prompt-neutrality verification.
- Completed Step 6: ran final project, smoke, lint, prompt-neutrality, and evaluation gates; filled the final gate and phase summary.
- Issues found: none.
- Tests: board-opening and Steps 1-6 verification passed as recorded above, with the known unrelated `AGENTS.md`/`CLAUDE.md` drift preserved outside this phase.
- Next: operator acceptance of Phase 35. Do not start Phase 36 without explicit operator continuation.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

### What shipped vs spec

- Built as specified: additive chunk metadata and config; reusable token offset helpers; page/layout/table boundary collection and validation; explicit `boundary_mode: layout_aware` packing for headings, paragraphs, sentence boundaries, and atomic tables; oversized atomic chunk flagging or rejection; section hierarchy and dependency metadata; audit readback; resume validation; prompt-neutrality verification; and final evaluation gates.
- Deferred: none within the approved Phase 35 scope. Downstream planner/executor consumption of chunk dependency metadata remains Phase 36+ work as specified.
- Added beyond spec: no runtime LLM, prompt body, domain-pack, planner, executor, critic, verifier, reconciler, reporter, API, UI, or architecture-rule changes.

### Lessons for downstream phases

- Default chunking remains `token_window`; layout-aware behavior is explicit through `boundary_mode: layout_aware`.
- Dependency metadata is persisted and resume-validated, but downstream LLM stages do not consume it yet.
- Table and prose packing now depend on typed boundary contracts, not document names, domain nouns, or fixture-specific text.
- Whitespace-only gaps are folded into adjacent blocks so emitted chunks remain contiguous exact `Document.text` slices with valid offsets.
