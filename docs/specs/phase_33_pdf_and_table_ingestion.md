# Phase 33 - PDF and Table Ingestion

Status: approved for implementation and board opened on 2026-05-11.

Date drafted: 2026-05-10

Roadmap sources:

- `docs/PROJECT_OVERVIEW.md`:
  - `1. Ingestion`
  - `2. Chunker`
  - `Highest-leverage accuracy/provenance improvements, ranked`
  - `Target domains (ranked by fit)`
  - `Configurable surface`
  - `Non-configurable core`
- `docs/phase_26_plus_roadmap.md`
- `docs/boards/README.md`
- `PROGRESS.md`
- Phase 32 board and completed commits through `494dc41`

## Goal

Add layout-aware PDF text and table ingestion on top of the Phase 32 boundary model.

Phase 33 should turn the existing shallow PDF path into a domain-neutral parser adapter that preserves immutable source identity, extracted-text character and byte offsets, page boundaries, page geometry, table spans, table cell spans, and audit payload readback. It should make parser-introduced text explicit and fail closed whenever PDF text or table cells cannot be mapped into `Document.text` with exact offsets.

## Non-Goals

- Do not add OCR fallback or scanned-PDF text recognition. PDFs without extractable text should fail explicitly.
- Do not add DOCX, HTML, email, spreadsheet, image, audio, video, or web ingestion. Those belong to Phase 34 or remain outside target scope.
- Do not add layout-aware chunking behavior. That belongs to Phase 35.
- Do not add executor table lenses, table-specific prompts, planner schema changes, domain-pack runtime behavior, critic/verifier/reconciler behavior, or report schema changes.
- Do not add PyMuPDF, Tesseract, PaddleOCR, Camelot, Tabula, Java tooling, REST APIs, web UI, Docker, CI/CD, vector DBs, embeddings, fine-tuning hooks, or agent frameworks.
- Do not treat parser-extracted PDF text, generated separators, table linearization, or normalized whitespace as raw source-backed text unless the implementation proves a source byte mapping against the original PDF bytes.
- Do not silently drop parser-reported pages, words, layout spans, tables, or cells that the adapter claims to support.

## Domain-Scope Alignment

Phase 33 is ingestion work for the domain-neutral kernel. Target domains need PDFs and tables, but the implementation must stay reusable across legal contracts, SEC filings, clinical protocols, regulatory orders, insurance policies, standards, scientific papers, and procurement documents.

Configurable in Phase 33:

- Parser adapter behavior that is specific to the existing `pdfplumber` dependency.
- Synthetic PDF fixtures and expected boundary assertions.
- Table identifiers, row and column indexes, header labels, and bounding boxes reported by the parser.
- Generic layout roles from the Phase 32 `LayoutRole` vocabulary.
- Parser metadata values stored in `Document.metadata`.

Non-configurable in Phase 33:

- Source hash and text hash calculation.
- `Document.doc_id` derivation from source bytes.
- Extracted text character and byte offset validation.
- Page map ordering and byte/character range validation.
- Source-map fail-closed behavior for generated and unmapped regions.
- Pydantic stage contracts and frozen model behavior.
- SQLite audit preservation through document payload JSON.
- Architecture bans on web UI, REST API, Docker, CI/CD, vector DBs, embeddings, fine-tuning hooks, and agent frameworks.

## Current State

`src/extractor/ingestion/documents.py` detects `.pdf`, imports `pdfplumber`, extracts page text with `page.extract_text()`, joins pages with generated `"\n\n"` separators, and records page ranges. Phase 32 made those page text ranges explicit as `unmapped` source-map segments and the page separators explicit as `generated` segments.

`src/extractor/contracts/ingestion.py` now defines the boundary contracts Phase 33 should populate: `DocumentMetadata`, `SourceMapSegment`, `LayoutSpan`, `TableSpan`, `TableCellSpan`, `BoundingBox`, and validation helpers. `src/extractor/contracts/documents.py` stores those fields on `Document` with default compatibility. `src/extractor/source_support.py` rejects source spans that overlap generated or unmapped source-map segments when a source map is present.

The current PDF path does not expose page geometry, layout spans, table spans, table cells, parser metadata, or any real source-to-text map beyond generated/unmapped regions.

## Boundary and Mapping Policy

Phase 33 must distinguish three evidence layers:

1. Immutable source identity: source path, source byte length, source SHA-256, and stable `doc_id`.
2. Extracted-text identity: `Document.text`, text SHA-256, exact character offsets, exact UTF-8 byte offsets, page map, layout spans, table spans, and table cell spans.
3. Raw source-byte backing: `SourceMapSegment.kind == "source"` with source byte offsets into the original PDF file.

The first two layers are required for Phase 33. The third layer is allowed only if implementation and tests prove a stable mapping to original PDF bytes. If `pdfplumber` cannot prove raw PDF byte ranges, the adapter must keep parser-extracted text as `unmapped` and preserve page/table geometry instead of inventing source byte offsets.

Generated text remains allowed only when explicit. Examples include page separators, table row separators, column delimiters, or other adapter-inserted text required to linearize PDF content. Generated segments must have no source byte offsets and must not be accepted by `require_source_backed_span(...)`.

## PDF Text Extraction

Replace the current monolithic PDF helper with a focused PDF ingestion module, for example `src/extractor/ingestion/pdf.py`, while preserving the public `ingest_document(...)` interface.

The PDF adapter should:

- Use the existing `pdfplumber>=0.11` dependency.
- Extract page text in deterministic page order.
- Preserve the existing page separator as generated text unless the board pins a different generated separator before implementation.
- Populate `Document.metadata` with parser name, parser version when available, source name, and MIME type.
- Populate `page_map` so every page range is ordered, non-overlapping, and within `Document.text`.
- Populate layout spans for page-scoped text ranges when the parser reports enough geometry to align words or lines to `Document.text`.
- Preserve `.txt` and `.md` ingestion behavior exactly.
- Raise `EmptyDocumentError` or `IngestionError` for no-text PDFs, parser failures, unsupported encrypted PDFs, or malformed parser outputs.

The adapter must not normalize text in a way that breaks offset accounting. If whitespace must be inserted to make page or table text readable, those characters must be covered by generated source-map segments.

## Table Extraction

Phase 33 table work is ingestion-boundary population, not runtime extraction semantics.

The PDF adapter should populate `Document.table_spans` when `pdfplumber` reports table structures that can be aligned into `Document.text`. Each table span must include:

- A stable table ID derived from document identity, page number, table order, and text range.
- A page number.
- A table-level text range within `Document.text`.
- One or more cells with stable cell IDs.
- Non-negative row and column indexes.
- Row and column spans when reported or defaulted to `1`.
- Header labels when they can be derived from parser output without domain assumptions.
- Bounding boxes when the parser provides page geometry.
- Cell text ranges that are within the table text range and within `Document.text`.

Cells that cannot be aligned into `Document.text` must not be silently omitted from a table the adapter claims to emit. The implementation must fail table population for that PDF with an explicit `IngestionError` instead of emitting a partial table.

Table linearization must be deterministic. Any row separators, column delimiters, or blank-cell markers introduced by the adapter must be represented as generated source-map segments.

## Contract Changes

Allowed:

- Add focused PDF parser helper models inside `src/extractor/ingestion/` when they reduce adapter complexity.
- Add small ingestion-only helper functions for aligning parser text fragments to `Document.text`.
- Add additive contract helpers if Phase 32 validation is insufficient for PDF/table alignment.
- Add synthetic PDF fixtures under `tests/fixtures/` or `evals/fixtures/` when they are small, repo-safe, and auditable.
- Add tests for parser metadata, layout spans, table spans, source-map generated/unmapped coverage, and audit readback.

Required compatibility:

- Existing `.txt` and `.md` ingestion tests must keep passing without changed expected hashes, IDs, text, byte lengths, or page maps.
- Existing public imports from `extractor.ingestion` and `extractor.contracts` must remain valid.
- Existing audit document payloads must remain readable without a schema migration.
- Existing Phase 29, Phase 30, and Phase 31 eval suites must remain passing.

Disallowed:

- Removing or renaming existing `Document`, `PageSpan`, `SourceMapSegment`, `LayoutSpan`, `TableSpan`, `TableCellSpan`, `Chunk`, or `SourceSpan` fields.
- Extending `DocumentFormat` beyond `"pdf"` for this phase.
- Adding parser dependencies beyond existing `pdfplumber`.
- Adding table-specific executor, planner, prompt, domain-pack, reporter, or evaluation scorer semantics.
- Marking PDF text as source-backed solely because it appears in `Document.text`.

## Validation Rules

Phase 33 must enforce at least these rules:

- Every PDF page range is within `Document.text` and `text_byte_length`.
- Page ranges are ordered and non-overlapping.
- Every populated layout span references a known page and valid text range.
- Every populated table span references a known page and valid text range.
- Every table cell range is within its parent table range and within `Document.text`.
- Table and cell IDs are unique within a document.
- Generated source-map segments have no source byte offsets.
- PDF parser text remains `unmapped` unless a raw source-byte mapping is proven.
- `require_source_backed_span(...)` continues to reject generated or unmapped PDF ranges.
- No-text PDFs fail explicitly instead of producing empty documents.

If a parser output would require guessing offsets or silently dropping supported content, the adapter must fail closed with an explicit `IngestionError`.

## Stage and Module Boundaries

### Expected Code Areas

- `src/extractor/ingestion/documents.py`
- `src/extractor/ingestion/pdf.py` or an equivalent focused PDF adapter module
- `src/extractor/contracts/ingestion.py` only if additional additive validation helpers are required
- `src/extractor/contracts/documents.py` only if additive document validation is required
- `src/extractor/source_support.py` only if tests expose a generated/unmapped support gap
- `tests/unit/test_ingestion.py`
- `tests/unit/test_ingestion_pdf_tables.py` or an equivalent focused new test file
- `tests/unit/test_audit_document_boundaries.py` if audit readback coverage needs PDF/table-specific assertions

Do not edit runtime LLM stages for Phase 33.

### Tests

Expected test coverage:

- Existing text and Markdown ingestion compatibility.
- PDF parser metadata population.
- PDF page map and generated page separator source-map coverage.
- Layout span population with page geometry from parser output.
- Table span and table cell population with exact text ranges.
- Rejection of unalignable table cells with an explicit `IngestionError`.
- Scanned/no-text PDF explicit failure.
- Audit readback of PDF metadata, layout spans, table spans, and source maps.
- Source-support rejection for generated and unmapped PDF ranges.

## Audit and Provenance Effects

Phase 33 should improve PDF provenance representation without changing the audit database schema unless implementation proves an indexed field is required.

Required properties:

- Document payload JSON includes parser metadata, page map, source map, layout spans, and table spans for supported PDF fixtures.
- Audit readback preserves all populated PDF/table boundary fields.
- Generated and unmapped source-map regions remain visible in payload JSON.
- Unsupported or unalignable parser outputs are rejected explicitly; they are not silently dropped.
- Existing audit idempotency and conflicting-document detection remain intact.

## Invariant Impact

Do not weaken I1-I9.

Phase 33 strengthens provenance for PDFs by populating the Phase 32 boundary model. Required protections:

- Existing exact text and Markdown offset behavior remains unchanged.
- PDF extracted-text offsets are exact in `Document.text`.
- Parser-introduced text is generated, not source-backed.
- Parser-extracted PDF text is not marked raw source-backed unless proven by tests.
- Table cells carry exact extracted-text ranges and optional geometry.
- Existing Phase 29, Phase 30, and Phase 31 evaluation gates remain passing.
- No prompt body, runtime config, domain-pack behavior, runtime LLM stage, or architecture rule is changed.

## Configuration Changes

Expected configuration work: none.

Runtime tuning values must remain in `config/`. Parser constants used only to interpret `pdfplumber` output should live near the PDF adapter and be covered by tests.

## Prompt Changes

No prompt body should be changed in Phase 33.

Allowed prompt-related work:

- Run prompt-no-change verification.

Disallowed prompt-related work:

- Prompt instructions about PDF layout, tables, OCR, parser behavior, target domains, or table extraction.
- Free-text JSON parsing.

## Tests and Evaluation Gates

Required narrow tests:

- PDF ingestion populates parser metadata, page map, source map, layout spans, and table spans from a deterministic parser fixture.
- Table cell text ranges align exactly to `Document.text` in both character and UTF-8 byte coordinates.
- Generated page and table separators are represented as generated source-map segments.
- Parser-extracted PDF text remains unmapped unless source byte offsets are proven.
- Unalignable table cells fail with an explicit `IngestionError`.
- No-text PDFs fail explicitly.
- Audit readback preserves PDF/table boundary fields.
- `require_source_backed_span(...)` rejects generated and unmapped PDF ranges.
- Plain text and Markdown ingestion identity remains unchanged.

Required broader verification before Phase 33 completion:

```bash
python3 -m pytest tests/unit/test_ingestion.py tests/unit/test_ingestion_boundaries.py tests/unit/test_source_support.py tests/unit/test_audit_document_boundaries.py -q
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

## Implementation Order

1. Add failing PDF/table ingestion tests using deterministic `pdfplumber` fakes and at least one repo-safe synthetic PDF fixture if practical.
2. Split PDF ingestion into a focused adapter module while preserving `ingest_document(...)`.
3. Populate PDF parser metadata, page map, and generated/unmapped source-map segments through the focused adapter.
4. Add layout span extraction and exact text-range alignment for parser-reported page geometry.
5. Add table span and table cell extraction with deterministic IDs, text ranges, row/column metadata, optional headers, and optional bounding boxes.
6. Add explicit `IngestionError` handling for unalignable table cells.
7. Add audit readback coverage for PDF metadata, layout spans, table spans, and source maps.
8. Add source-support regression coverage for generated and unmapped PDF ranges.
9. Run narrow tests.
10. Run project-level and evaluation verification.
11. Update the Phase 33 board and `PROGRESS.md`.
12. Commit the completed step or hand off explicitly.

## Expected Board Steps

When the board is created after spec approval, use these steps unless implementation planning exposes a better equivalent split:

1. Add PDF/table ingestion tests and parser fixture strategy.
2. Split and harden the PDF adapter boundary.
3. Populate PDF metadata, page maps, and layout spans.
4. Populate table spans and table cell provenance.
5. Add unalignable-cell failure handling and audit readback coverage.
6. Add prompt-neutrality verification and final project verification.

## Gate Criteria

Phase 33 is complete only when:

- PDF ingestion uses a focused adapter and preserves the public ingestion interface.
- Supported PDF fixtures produce stable source hashes, text hashes, document IDs, text, page maps, source maps, layout spans, and table spans.
- Table cells have exact character and UTF-8 byte ranges within `Document.text`.
- Generated parser text is explicit and cannot be accepted as source-backed evidence.
- Parser-extracted PDF text is not marked raw source-backed unless source byte offsets are proven by tests.
- No-text PDFs fail explicitly.
- Unalignable table cells fail with an explicit `IngestionError` and no silent drops.
- Audit document persistence round-trips PDF/table boundary fields.
- Existing `.txt` and `.md` ingestion behavior remains hash- and offset-compatible.
- Existing Phase 29, Phase 30, and Phase 31 eval gates remain passing.
- No OCR, DOCX, HTML, email, prompt, runtime LLM, domain-pack runtime, config, or architecture-rule change is added.
- Relevant narrow tests pass.
- `make test`, `make lint`, `make smoke`, `git diff --check`, and `git diff --exit-code -- prompts` pass when feasible.
- All Phase 33 board issues are resolved or explicitly deferred.
- `PROGRESS.md` is updated.

## Board Decisions to Pin at Opening

1. Use the existing `pdfplumber` dependency for Phase 33 and do not add a second PDF parser.
2. Keep parser-extracted PDF text `unmapped` unless source byte ranges into the original PDF are proven.
3. Treat table extraction as ingestion-boundary population only; do not add executor table lenses or prompts.
4. Keep OCR fallback out of Phase 33; no-text PDFs fail explicitly.
5. Use explicit `IngestionError` for unalignable table cells; do not emit partial tables.

## Open Questions

_(None.)_
