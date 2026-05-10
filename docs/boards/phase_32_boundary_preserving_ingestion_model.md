# Phase 32 - Boundary-Preserving Ingestion Model

## Current Status

Step: 4 of 6
Branch: main
Started: 2026-05-10
Last session: 2026-05-10
Spec: `docs/specs/phase_32_boundary_preserving_ingestion_model.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:1. Ingestion`; `docs/PROJECT_OVERVIEW.md:2. Chunker`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Step 4 complete. Next: Step 5 - add audit persistence/readback coverage for boundary fields.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add ingestion-boundary contract tests and models.
- [x] Step 2: Add `Document` boundary defaults and export compatibility.
- [x] Step 3: Add identity source maps for plain text and Markdown ingestion.
- [x] Step 4: Add generated-segment and source-support validation.
- [ ] Step 5: Add audit persistence/readback coverage for boundary fields.
- [ ] Step 6: Add prompt-neutrality verification and final project verification.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Add boundary contracts as a focused contracts module and expose them through `extractor.contracts`. | Keeps ingestion-boundary logic cohesive instead of growing `contracts/models.py` into a catch-all file. |
| Q2 | Keep `Document` changes additive and defaulted so existing constructors and audit payloads remain compatible. | Phase 32 must preserve existing text/Markdown behavior and avoid an unnecessary audit migration. |
| Q3 | Represent generated separators and parser-introduced text as explicit generated source-map segments. | Generated text can remain auditable without being accepted silently as source-backed evidence. |
| Q4 | Define OCR confidence span shape in Phase 32 but do not add OCR execution. | Later OCR parser work needs a contract shape, but running OCR belongs outside this phase. |
| Q5 | Keep full PDF table extraction, DOCX, HTML, email, and layout-aware chunking out of Phase 32. | Phase 32 is the boundary model substrate for later ingestion and chunking phases. |

---

## Gate Interpretations

- Phase 32 is allowed to add Pydantic ingestion-boundary contracts and additive `Document` fields, but not full format parsers.
- Existing `.txt` and `.md` ingestion output identity must remain hash- and offset-compatible.
- Generated source-map segments may exist in `Document.text`, but source-support validation must reject generated-only or unmapped spans.
- OCR confidence fields are contract shape only; they are not extraction confidence and do not imply OCR execution.
- No prompt body, runtime config, domain-pack behavior, architecture rule, or runtime LLM stage may change in Phase 32.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_32_boundary_preserving_ingestion_model.md:1` | Approved Phase 32 spec. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_32_boundary_preserving_ingestion_model.md:1` | Active Phase 32 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `tests/unit/test_ingestion_boundaries.py:1` | Added boundary-contract tests for source-map segment backing, ordered/non-overlapping maps, duplicate table cells, and context validation. | Step 1 |
| `src/extractor/contracts/ingestion.py:1` | Added focused ingestion-boundary Pydantic contracts and boundary context validation helper. | Step 1 |
| `src/extractor/contracts/__init__.py:1` | Exported the new ingestion-boundary contract surface. | Step 1 |
| `docs/boards/phase_32_boundary_preserving_ingestion_model.md:1` | Marked Step 1 complete and recorded verification. | Step 1 |
| `PROGRESS.md:1` | Recorded Phase 32 Step 1 completion and next step. | Step 1 |
| `tests/unit/test_ingestion_boundaries.py:1` | Added `Document` boundary default compatibility and boundary-field validation tests. | Step 2 |
| `src/extractor/contracts/documents.py:1` | Split `Document` and `PageSpan` into a focused module and added defaulted boundary fields with document-context validation. | Step 2 |
| `src/extractor/contracts/models.py:1` | Preserved compatibility exports for document contracts and base type aliases while reducing model-file size. | Step 2 |
| `src/extractor/contracts/__init__.py:1` | Re-exported `Document` and `PageSpan` from the focused document-contract module. | Step 2 |
| `docs/boards/phase_32_boundary_preserving_ingestion_model.md:1` | Marked Step 2 complete and recorded verification. | Step 2 |
| `PROGRESS.md:1` | Recorded Phase 32 Step 2 completion and next step. | Step 2 |
| `tests/unit/test_ingestion.py:1` | Added assertions that plain text and Markdown ingestion populate identity source-map segments. | Step 3 |
| `src/extractor/ingestion/documents.py:1` | Added identity source-map population for existing UTF-8 plain text and Markdown ingestion. | Step 3 |
| `docs/boards/phase_32_boundary_preserving_ingestion_model.md:1` | Marked Step 3 complete and recorded verification. | Step 3 |
| `PROGRESS.md:1` | Recorded Phase 32 Step 3 completion and next step. | Step 3 |
| `tests/unit/test_ingestion.py:1` | Added PDF source-map assertions for unmapped page text and generated page separators. | Step 4 |
| `tests/unit/test_source_support.py:1` | Added source-backed span helper coverage for source, generated, unmapped, spanning, and legacy no-map cases. | Step 4 |
| `src/extractor/contracts/ingestion.py:1` | Tightened boundary validation so non-empty source maps must cover document text and byte ranges. | Step 4 |
| `src/extractor/ingestion/documents.py:1` | Added generated and unmapped PDF source-map segments for page joins. | Step 4 |
| `src/extractor/source_support.py:1` | Added source-map-aware source-span validation helpers. | Step 4 |
| `docs/boards/phase_32_boundary_preserving_ingestion_model.md:1` | Marked Step 4 complete and recorded verification. | Step 4 |
| `PROGRESS.md:1` | Recorded Phase 32 Step 4 completion and next step. | Step 4 |

---

## Issues

_(No issues yet.)_

<!--
### ISS-001 - <short title>
**Status:** OPEN | **Severity:** high/medium/low | **Found:** Step K, 2026-05-10
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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_32_boundary_preserving_ingestion_model.md docs/boards/README.md docs/boards/phase_32_boundary_preserving_ingestion_model.md`; `sed -n '261,263p' docs/specs/phase_32_boundary_preserving_ingestion_model.md`; `rg -n "Phase 32|phase_32_boundary_preserving_ingestion_model.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_32_boundary_preserving_ingestion_model.md docs/boards/phase_32_boundary_preserving_ingestion_model.md`; `cmp -s AGENTS.md CLAUDE.md` | PASS | 2026-05-10 |
| 1 | `python3 -m pytest tests/unit/test_ingestion_boundaries.py -q` first failed with missing `BoundaryValidationContext`, then passed with 3 passed; `python3 -m pytest tests/unit/test_ingestion_boundaries.py tests/unit/test_contracts.py tests/unit/test_ingestion.py -q`; `wc -l src/extractor/contracts/ingestion.py src/extractor/contracts/__init__.py tests/unit/test_ingestion_boundaries.py`; `git diff --check`; `make lint` | PASS | 2026-05-10 |
| 2 | `python3 -m pytest tests/unit/test_ingestion_boundaries.py -q` first failed because `Document` had no boundary fields and rejected them as extras, then passed with 5 passed; `python3 -m pytest tests/unit/test_ingestion_boundaries.py tests/unit/test_contracts.py tests/unit/test_ingestion.py tests/unit/test_audit_store.py -q` first exposed a compatibility import for `DocumentFormat`, then passed with 31 passed; `python3 -m pytest tests/unit/test_ingestion_boundaries.py::test_document_defaults_preserve_existing_constructor_compatibility tests/unit/test_ingestion_boundaries.py::test_document_validates_boundary_fields_against_text_source_and_pages -q`; `make lint`; `git diff --check`; `wc -l src/extractor/contracts/documents.py src/extractor/contracts/models.py src/extractor/contracts/ingestion.py src/extractor/contracts/__init__.py tests/unit/test_ingestion_boundaries.py` | PASS | 2026-05-10 |
| 3 | `python3 -m pytest tests/unit/test_ingestion.py::test_ingest_plain_text_preserves_hashes_offsets_and_stable_id tests/unit/test_ingestion.py::test_ingest_markdown_detects_format_and_records_audit_document -q` first failed because ingested documents had empty `source_map`, then passed with 2 passed; `python3 -m pytest tests/unit/test_ingestion.py tests/unit/test_ingestion_boundaries.py tests/unit/test_contracts.py tests/unit/test_audit_store.py -q`; `make lint`; `git diff --check`; `wc -l src/extractor/ingestion/documents.py tests/unit/test_ingestion.py` | PASS | 2026-05-10 |
| 4 | `python3 -m pytest tests/unit/test_ingestion.py::test_ingest_pdf_uses_pdfplumber_pages_and_tracks_page_offsets -q` first failed because PDF `source_map` was empty, then passed with 1 passed; `python3 -m pytest tests/unit/test_source_support.py -q` first failed with missing source-backed span helpers, then passed with 2 passed; `python3 -m pytest tests/unit/test_ingestion.py tests/unit/test_ingestion_boundaries.py tests/unit/test_source_support.py tests/unit/test_contracts.py tests/unit/test_audit_store.py -q`; `python3 -m pytest tests/unit/test_executor.py tests/unit/test_critic.py tests/unit/test_verifier.py -q`; `wc -l src/extractor/source_support.py src/extractor/ingestion/documents.py src/extractor/contracts/ingestion.py tests/unit/test_source_support.py tests/unit/test_ingestion.py`; `git diff --check`; `make lint` | PASS | 2026-05-10 |

### Final Gate

- [ ] Narrow relevant tests pass
- [ ] `make test` passes when feasible
- [ ] `make lint` passes
- [ ] `make smoke` passes when feasible
- [ ] `git diff --check` passes
- [ ] Evaluation gates pass, if this phase changes extraction behavior
- [ ] All OPEN issues are resolved or explicitly deferred
- [ ] Phase Summary filled in
- [ ] `PROGRESS.md` updated

---

## Work Log

Reverse chronological. Log every session.

### 2026-05-10 - Session 1

- Resumed after operator approved the Phase 32 spec with `continue`.
- Completed: approved the Phase 32 spec for implementation, opened this board, pinned Phase 32 open-question resolutions, and updated active phase tracking.
- Completed Step 1: added focused ingestion-boundary contracts for text ranges, metadata, source-map segments, layout spans, table spans/cells, OCR confidence spans, and context validation.
- Completed Step 2: split `Document`/`PageSpan` into a focused document contract module, added defaulted boundary fields, validated provided boundaries against document text/source/page context, and preserved public contract imports.
- Completed Step 3: populated identity source-map segments for plain text and Markdown ingestion while preserving existing hashes, stable IDs, page maps, and audit readback.
- Completed Step 4: marked PDF page text as unmapped and page separators as generated, tightened source-map coverage validation, and added source-map-aware source-span helpers that reject generated/unmapped evidence while preserving legacy exact-span behavior when no source map exists.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_32_boundary_preserving_ingestion_model.md docs/boards/README.md docs/boards/phase_32_boundary_preserving_ingestion_model.md` returned no matches; `sed -n '261,263p' docs/specs/phase_32_boundary_preserving_ingestion_model.md` confirmed the Open Questions section is `_(None...)`; `rg -n "Phase 32|phase_32_boundary_preserving_ingestion_model.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_32_boundary_preserving_ingestion_model.md docs/boards/phase_32_boundary_preserving_ingestion_model.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed.
- Tests for Step 1: `python3 -m pytest tests/unit/test_ingestion_boundaries.py -q` first failed with missing `BoundaryValidationContext`, then passed with 3 passed; `python3 -m pytest tests/unit/test_ingestion_boundaries.py tests/unit/test_contracts.py tests/unit/test_ingestion.py -q` passed with 20 passed; `wc -l src/extractor/contracts/ingestion.py src/extractor/contracts/__init__.py tests/unit/test_ingestion_boundaries.py` reported 300, 103, and 177 lines; `git diff --check` passed; `make lint` passed.
- Tests for Step 2: `python3 -m pytest tests/unit/test_ingestion_boundaries.py -q` first failed because `Document` had no boundary fields and rejected them as extras, then passed with 5 passed; `python3 -m pytest tests/unit/test_ingestion_boundaries.py tests/unit/test_contracts.py tests/unit/test_ingestion.py tests/unit/test_audit_store.py -q` first exposed a compatibility import for `DocumentFormat`, then passed with 31 passed; the two focused Step 2 tests passed; `make lint` passed; `git diff --check` passed; line counts are 113 for `contracts/documents.py`, 332 for `contracts/models.py`, 300 for `contracts/ingestion.py`, 102 for `contracts/__init__.py`, and 285 for `test_ingestion_boundaries.py`.
- Tests for Step 3: `python3 -m pytest tests/unit/test_ingestion.py::test_ingest_plain_text_preserves_hashes_offsets_and_stable_id tests/unit/test_ingestion.py::test_ingest_markdown_detects_format_and_records_audit_document -q` first failed because ingested documents had empty `source_map`, then passed with 2 passed; `python3 -m pytest tests/unit/test_ingestion.py tests/unit/test_ingestion_boundaries.py tests/unit/test_contracts.py tests/unit/test_audit_store.py -q` passed with 31 passed; `make lint` passed; `git diff --check` passed; line counts are 192 for `src/extractor/ingestion/documents.py` and 146 for `tests/unit/test_ingestion.py`.
- Tests for Step 4: `python3 -m pytest tests/unit/test_ingestion.py::test_ingest_pdf_uses_pdfplumber_pages_and_tracks_page_offsets -q` first failed because PDF `source_map` was empty, then passed with 1 passed; `python3 -m pytest tests/unit/test_source_support.py -q` first failed with missing source-backed span helpers, then passed with 2 passed; `python3 -m pytest tests/unit/test_ingestion.py tests/unit/test_ingestion_boundaries.py tests/unit/test_source_support.py tests/unit/test_contracts.py tests/unit/test_audit_store.py -q` passed with 33 passed; `python3 -m pytest tests/unit/test_executor.py tests/unit/test_critic.py tests/unit/test_verifier.py -q` passed with 65 passed; `make lint` passed; `git diff --check` passed; line counts remain below 400 for touched files.
- Next: Step 5 - add audit persistence/readback coverage for boundary fields.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: _(phase in progress; see Work Log)_
- Deferred: _(phase in progress)_
- Added beyond spec: _(phase in progress)_

### Lessons for downstream phases

- _(phase in progress)_
