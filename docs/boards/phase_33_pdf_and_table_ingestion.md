# Phase 33 - PDF and Table Ingestion

## Current Status

Step: 6 of 6
Branch: main
Started: 2026-05-11
Last session: 2026-05-11
Spec: `docs/specs/phase_33_pdf_and_table_ingestion.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:1. Ingestion`; `docs/PROJECT_OVERVIEW.md:2. Chunker`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 33 implementation and final verification are complete. Awaiting operator acceptance before Phase 34.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add PDF/table ingestion tests and parser fixture strategy.
- [x] Step 2: Split and harden the PDF adapter boundary.
- [x] Step 3: Populate PDF metadata, page maps, and layout spans.
- [x] Step 4: Populate table spans and table cell provenance.
- [x] Step 5: Add unalignable-cell failure handling and audit readback coverage.
- [x] Step 6: Add prompt-neutrality verification and final project verification.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Use the existing `pdfplumber` dependency for Phase 33 and do not add a second PDF parser. | Keeps the phase inside current architecture and dependency boundaries while improving PDF provenance. |
| Q2 | Keep parser-extracted PDF text `unmapped` unless source byte ranges into the original PDF are proven. | Avoids inventing raw source-byte provenance that `pdfplumber` does not provide. |
| Q3 | Treat table extraction as ingestion-boundary population only. | Executor table lenses, prompts, planner changes, and report semantics belong to later phases. |
| Q4 | Keep OCR fallback out of Phase 33. | Scanned/no-text PDFs fail explicitly; OCR execution remains downstream work. |
| Q5 | Use explicit `IngestionError` for unalignable table cells. | Supported table content must not be silently dropped or partially emitted. |

---

## Gate Interpretations

- Phase 33 may populate Phase 32 boundary fields for PDF text, layout, and tables, but must not add runtime LLM, planner, executor, prompt, domain-pack, report, config, or architecture-rule behavior.
- PDF parser-extracted text remains `unmapped` unless a test-proven raw PDF byte mapping exists.
- Generated page separators and table linearization characters are allowed only when represented as generated source-map segments.
- Table extraction is accepted only when parser cells can be aligned exactly into `Document.text`.
- No-text, encrypted, malformed, unsupported, or unalignable PDFs fail explicitly with `EmptyDocumentError` or `IngestionError`.
- Existing plain text and Markdown ingestion identity must remain hash- and offset-compatible.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_33_pdf_and_table_ingestion.md:1` | Approved Phase 33 spec. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_33_pdf_and_table_ingestion.md:1` | Active Phase 33 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `tests/unit/test_ingestion_pdf_tables.py:1` | Added deterministic fake `pdfplumber` coverage for PDF adapter boundaries, metadata, layout spans, table cell provenance, failure handling, audit readback, and generated/unmapped source-support rejection. | Steps 1, 3, 4, 5 |
| `src/extractor/ingestion/errors.py:1` | Split ingestion error classes into a small shared module so the focused PDF adapter can raise canonical ingestion errors without circular imports. | Step 2 |
| `src/extractor/ingestion/pdf.py:1` | Added focused PDF adapter for parser metadata, page maps, generated/unmapped source maps, layout word spans, table spans/cells, and explicit parser/table failure handling. | Steps 2, 3, 4, 5 |
| `src/extractor/ingestion/documents.py:1` | Wired PDF ingestion through the focused adapter while preserving the public `ingest_document(...)` interface and plain text/Markdown identity behavior. | Steps 2, 3, 4, 5 |
| `src/extractor/ingestion/__init__.py:1` | Preserved public ingestion exports after moving error classes. | Step 2 |

---

## Issues

_(No issues yet.)_

<!--
### ISS-001 - <short title>
**Status:** OPEN | **Severity:** high/medium/low | **Found:** Step K, 2026-05-11
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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_33_pdf_and_table_ingestion.md docs/boards/README.md docs/boards/phase_33_pdf_and_table_ingestion.md`; `rg -n "Phase 33|phase_33_pdf_and_table_ingestion.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_33_pdf_and_table_ingestion.md docs/boards/phase_33_pdf_and_table_ingestion.md`; `cmp -s AGENTS.md CLAUDE.md` | PASS | 2026-05-11 |
| 1 | `python3 -m pytest tests/unit/test_ingestion_pdf_tables.py::test_pdf_adapter_uses_fake_pdfplumber_pages_for_text_boundaries -q` first failed with missing `extractor.ingestion.pdf`, then passed with 1 passed; existing PDF/text ingestion focused tests passed with 3 passed. | PASS | 2026-05-11 |
| 2 | `python3 -m pytest tests/unit/test_ingestion_pdf_tables.py::test_pdf_adapter_uses_fake_pdfplumber_pages_for_text_boundaries -q`; `python3 -m pytest tests/unit/test_ingestion.py::test_ingest_pdf_uses_pdfplumber_pages_and_tracks_page_offsets -q`; plain text/Markdown focused ingestion tests. | PASS | 2026-05-11 |
| 3 | `python3 -m pytest tests/unit/test_ingestion_pdf_tables.py::test_pdf_adapter_populates_parser_metadata_and_layout_word_spans -q` first failed because metadata/layout spans were missing, then passed with 1 passed; `python3 -m pytest tests/unit/test_ingestion_pdf_tables.py tests/unit/test_ingestion.py -q` passed with 6 passed. | PASS | 2026-05-11 |
| 4 | `python3 -m pytest tests/unit/test_ingestion_pdf_tables.py::test_pdf_adapter_populates_table_spans_and_cell_ranges -q` first failed on missing `source_sha256` adapter support, then passed with 1 passed; `python3 -m pytest tests/unit/test_ingestion_pdf_tables.py tests/unit/test_ingestion.py -q` passed with 7 passed. | PASS | 2026-05-11 |
| 5 | `python3 -m pytest tests/unit/test_ingestion_pdf_tables.py::test_pdf_adapter_rejects_no_text_and_wraps_parser_failures -q` first failed because parser `RuntimeError` leaked, then passed with 1 passed; `python3 -m pytest tests/unit/test_ingestion_pdf_tables.py -q` passed with 7 passed; `python3 -m pytest tests/unit/test_ingestion_pdf_tables.py tests/unit/test_ingestion.py tests/unit/test_audit_document_boundaries.py -q` passed with 11 passed. | PASS | 2026-05-11 |
| 6 | `python3 -m pytest tests/unit/test_ingestion.py tests/unit/test_ingestion_boundaries.py tests/unit/test_source_support.py tests/unit/test_audit_document_boundaries.py tests/unit/test_ingestion_pdf_tables.py -q`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json`; `PYTHONPATH=src python3 -m extractor.evals --adversarial-suite evals/suites/phase_31_adversarial.json`; `PYTHONPATH=src python3 -m extractor.evals --mutation-suite evals/suites/phase_31_mutation.json`; `PYTHONPATH=src python3 -m extractor.evals --calibration-suite evals/suites/phase_30_diverse_corpus_round_1.json`; `make test`; `make lint`; `make smoke`; `git diff --check`; `git diff --exit-code -- prompts` | PASS | 2026-05-11 |

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

### 2026-05-11 - Session 1

- Resumed after operator continued from the Phase 33 spec draft.
- Completed: approved the Phase 33 spec for implementation, opened this board, pinned Phase 33 open-question resolutions, and updated active phase tracking.
- Completed Step 1: added a focused PDF/table ingestion test file with deterministic fake `pdfplumber` pages, words, and tables.
- Completed Step 2: split PDF ingestion into `src/extractor/ingestion/pdf.py`, moved ingestion errors to a shared module, and preserved `ingest_document(...)`.
- Completed Step 3: populated PDF parser metadata, existing page maps/source maps, and word-level layout spans with exact character/byte ranges and bounding boxes.
- Completed Step 4: populated table spans and table cell spans with stable table/cell IDs, row/column indexes, header labels, exact character/byte ranges, and optional table bounding boxes.
- Completed Step 5: added explicit no-text/parser failure and unalignable-cell rejection coverage plus audit readback and source-support regression coverage.
- Completed Step 6: ran final prompt-neutrality, evaluation, and project verification gates.
- Issues found: none.
- Tests: board-opening verification passed; Step 1-5 focused red/green tests passed as recorded above; Step 6 final verification passed with `20 passed` for the narrow ingestion/boundary/source/audit set, Phase 29 core eval passed with 21 expected/actual/true positives and zero invariant violations, Phase 30 diverse eval passed with 49 expected/actual/true positives and zero invariant violations, Phase 31 adversarial and mutation suites passed with source sensitivity 1.0, calibration passed with 49 matched data points and expected/provenance calibration error 0.048979591836734754, `make test` passed with 294 passed and 2 skipped, `make lint` passed, `make smoke` passed with 1 passed, `git diff --check` passed, and `git diff --exit-code -- prompts` passed.
- Next: operator acceptance of Phase 33. Do not start Phase 34 until explicit continuation after acceptance.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

### What shipped vs spec

- Built as specified: focused PDF adapter; deterministic fake parser test strategy; parser metadata; page maps; generated/unmapped source-map preservation; word layout spans with bounding boxes; table spans/cell spans with exact text ranges, row/column indexes, header labels, stable IDs, and optional table boxes; explicit no-text, parser failure, and unalignable-cell errors; audit readback; source-support rejection for PDF generated/unmapped ranges; prompt-neutrality and final project gates.
- Deferred: raw PDF byte-backed source-map segments remain unmapped because Phase 33 does not prove stable byte ranges into original PDF bytes; OCR, DOCX, HTML, email, layout-aware chunking, executor table lenses, and prompt changes remain downstream.
- Added beyond spec: split ingestion errors into `src/extractor/ingestion/errors.py` to avoid circular imports between the public ingestion API and the focused PDF adapter.

### Lessons for downstream phases

- Parser geometry can be preserved as extracted-text provenance even when raw PDF bytes remain unmapped.
- Table population should fail closed at the first unalignable supported cell instead of emitting partial table provenance.
- Later chunking work can use `table_spans` to avoid mid-table splits without needing table-specific executor semantics yet.
