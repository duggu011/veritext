# Phase 32 - Boundary-Preserving Ingestion Model

Status: draft awaiting operator approval. Board not opened.

Date opened: 2026-05-10

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
- Phase 31 board and completed commits through `4b202e9`

## Goal

Add a domain-neutral ingestion boundary model that can represent layout, tables, document metadata, source-to-text mapping, and OCR-confidence shape while preserving exact source hashes, text hashes, byte offsets, character offsets, and existing text ingestion behavior.

Phase 32 should create the typed substrate required by later PDF, table, DOCX, HTML, email, and layout-aware chunking phases. It should make lossy or unmapped extracted text explicit and reject source-backed spans that cannot be traced to the document text and source identity.

## Non-Goals

- Do not implement full PDF, table, DOCX, HTML, email, OCR, spreadsheet, or web ingestion. Those belong to Phase 33 and Phase 34.
- Do not add layout-aware chunking behavior. That belongs to Phase 35.
- Do not change planner, executor, critic, verifier, reconciler, reporter, prompt, model-routing, or domain-pack behavior.
- Do not add a table extraction lens or table-specific extraction prompts.
- Do not add PII detection, redaction, audit encryption, review UI, REST API, web UI, Docker, CI/CD, vector DBs, embeddings, or agent frameworks.
- Do not weaken exact source-span validation, byte/character offsets, source hashes, forced tool use, Pydantic contracts, SQLite audit persistence, or no-silent-drop reporting.
- Do not silently treat generated separators, parser-normalized whitespace, OCR text, or table linearization as source-backed text unless the boundary map records the transformation.

## Domain-Scope Alignment

Phase 32 is ingestion-contract work for the domain-neutral kernel. Target domains vary in layout complexity, but the runtime proof rules must stay shared.

Configurable in Phase 32:

- Format adapters that populate the shared boundary contracts.
- Document metadata values and parser-reported metadata keys.
- Layout roles such as page header, page footer, heading, paragraph, list item, table, table cell, figure caption, and unknown.
- OCR-confidence spans when an adapter has OCR evidence in a later phase.
- Table identifiers, row/column indexes, header labels, and geometry reported by future parsers.

Non-configurable in Phase 32:

- Source hash and text hash calculation.
- UTF-8 byte and Python character offset validation.
- Requirement that source-backed spans map to document text and source identity.
- Explicit representation of generated text segments.
- Pydantic stage contracts and frozen model behavior.
- SQLite audit preservation through document payload JSON.
- Architecture bans on web UI, REST API, Docker, CI/CD, vector DBs, embeddings, fine-tuning hooks, and agent frameworks.

## Current State

`Document` currently records source path, format, text, source hash, text hash, source byte length, text byte length, and a page map. Plain text and Markdown ingestion preserve identity between source bytes and extracted text. PDF ingestion currently uses `pdfplumber` page text and joins pages with generated separators, but it does not expose page geometry, table cells, or a source-to-text transformation map.

Phase 32 must preserve existing `.txt` and `.md` behavior while adding enough structure for future parsers to prove where every extracted text range came from.

## Boundary Model

Add additive Pydantic contracts for ingestion boundaries, preferably in a focused contracts module rather than growing `contracts/models.py` into a catch-all file.

Expected concepts:

- Document metadata: parser-independent metadata such as source name, MIME type when known, parser name/version when known, declared encoding when known, creation/modification timestamps when available, and raw metadata as string-keyed values.
- Text source map segments: extracted-text ranges mapped to source byte ranges, source character ranges when available, or an explicit generated segment kind for inserted separators or parser-introduced text.
- Layout spans: page-scoped text ranges with optional bounding boxes and a generic role.
- Table spans: table-level text ranges plus table-cell spans with row/column indexes, row/column spans, optional header labels, optional bounding boxes, and source-backed text ranges.
- OCR confidence spans: text ranges with a confidence value and optional engine label. Phase 32 defines the shape but does not add an OCR engine.

Generated segments must be auditable. They may appear in `Document.text`, but they must be marked as generated and must not be accepted as source support for extracted facts.

## Contract Changes

Allowed:

- Additive ingestion-boundary contracts exported from `extractor.contracts`.
- Additive defaulted fields on `Document` for metadata, source map, layout spans, table spans, and OCR confidence spans.
- Additive optional location context on source-span-adjacent contracts only when defaults preserve existing callers.
- Helper validation functions that verify boundary ranges against a `Document`.
- Rejection errors for malformed or unmapped ingestion boundaries.

Required compatibility:

- Existing test constructors for `Document`, `PageSpan`, `Chunk`, and `SourceSpan` should continue to work with defaults unless a failing test proves an unsafe ambiguity.
- Existing text and Markdown ingestion should produce the same `doc_id`, `source_sha256`, `text_sha256`, `text`, and `page_map` values as before.
- Existing audit storage can continue to persist the document as payload JSON without a SQLite schema migration unless implementation proves indexed columns are required.

Disallowed:

- Removing or renaming existing `Document`, `PageSpan`, `Chunk`, or `SourceSpan` fields.
- Making existing stored document payloads unreadable without an explicit migration plan and tests.
- Adding domain-specific layout roles, table schemas, or parser behavior.
- Treating OCR confidence as extraction confidence.
- Adding non-SDK LLM framework integrations or retrieval infrastructure.

## Validation Rules

New boundary contracts must enforce at least these rules:

- Every text range has `end_char > start_char` and `end_byte > start_byte` unless the contract explicitly allows an empty boundary marker.
- Every text range is within `Document.text` and `text_byte_length`.
- Every source-backed source-map segment has valid source byte bounds within `source_byte_length`.
- Source-map segments are ordered and non-overlapping in extracted-text coordinates.
- Generated segments are explicit and have no source byte range.
- Layout spans and table spans reference valid page numbers and text ranges.
- Table cell IDs are unique within a document, and row/column coordinates are non-negative.
- OCR-confidence spans use confidence values in `[0.0, 1.0]` and valid text ranges.
- A source-support helper rejects spans that fall only inside generated segments or any gap in the source map.

If an adapter cannot prove a mapping, it must fail explicitly or mark the text as generated/unmapped in a way that prevents downstream source support from accepting it silently.

## Stage and Module Boundaries

### Expected Code Areas

- `src/extractor/contracts/base.py`
- `src/extractor/contracts/models.py`
- `src/extractor/contracts/__init__.py`
- `src/extractor/contracts/ingestion.py` or an equivalent focused contracts module
- `src/extractor/ingestion/documents.py`
- `src/extractor/source_support.py` if source support needs boundary-map validation
- `src/extractor/audit/core_records.py` only if document persistence needs an explicit additive guard

Do not edit runtime LLM stages for Phase 32.

### Tests

Expected test files:

- `tests/unit/test_contracts.py`
- `tests/unit/test_ingestion.py`
- `tests/unit/test_audit_store.py` if document payload persistence changes
- a focused new test file under `tests/unit/` if boundary-map validation becomes clearer outside existing contract tests

## Audit and Provenance Effects

Phase 32 should improve provenance representation without changing the audit database schema unless necessary.

Required properties:

- Document payload JSON includes boundary metadata needed to reconstruct source-to-text mapping.
- Audit readback of a stored `Document` preserves all boundary fields.
- Existing audit document idempotency behavior remains intact.
- Generated text segments, parser-normalized spans, and unmapped ranges remain visible in payload JSON and cannot be silently used as source-backed evidence.
- Later extraction reports must be able to cite the same source hashes and text offsets after this phase.

## Invariant Impact

Do not weaken I1-I9.

Phase 32 strengthens provenance invariants by adding explicit ingestion boundaries. Required protections:

- Existing exact text and Markdown offset behavior remains unchanged.
- Any new boundary field is validated by Pydantic contracts or focused helper validation.
- New source-map logic fails closed on gaps, overlaps, invalid source byte ranges, or generated-only spans.
- Existing Phase 29, Phase 30, and Phase 31 evaluation gates remain passing.
- No prompt body, runtime config, or domain-pack behavior is changed to accommodate new boundaries.

## Configuration Changes

Expected configuration work: none.

Runtime tuning values must remain in `config/`. Parser-specific constants should not be added to source unless they are structural defaults required by the contract and covered by tests.

## Prompt Changes

No prompt body should be changed in Phase 32.

Allowed prompt-related work:

- Run prompt-no-change verification.

Disallowed prompt-related work:

- Prompt instructions about layout, tables, OCR, parser behavior, or target domains.
- Free-text JSON parsing.

## Tests and Evaluation Gates

Required narrow tests:

- Boundary contracts reject invalid ranges, duplicate IDs, overlapping source-map segments, generated segments with source byte ranges, source-backed segments outside `source_byte_length`, and spans outside `Document.text`.
- `Document` defaults preserve compatibility for existing constructors.
- Plain text and Markdown ingestion produce identity source maps and preserve existing hashes, IDs, text, byte lengths, and page maps.
- PDF ingestion, if touched, must mark generated page separators explicitly and must not claim geometry or table support.
- Audit document persistence round-trips new boundary fields if those fields are added to `Document`.
- Source-support validation rejects generated-only or unmapped spans when Phase 32 adds that helper.

Required broader verification before Phase 32 completion:

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

## Implementation Order

1. Add failing contract tests for source-map ranges, generated segments, layout spans, table cell spans, OCR confidence spans, and `Document` default compatibility.
2. Add focused ingestion-boundary contracts and exports.
3. Add defaulted boundary fields to `Document` and keep existing constructor/readback compatibility.
4. Add plain text and Markdown identity source-map population in ingestion.
5. Add explicit generated-separator handling for PDF page joins if PDF ingestion remains in scope for the implementation step.
6. Add source-support helper validation for generated-only or unmapped spans if the boundary map is available on `Document`.
7. Add audit readback regression coverage for boundary fields.
8. Run narrow tests.
9. Run project-level and evaluation verification.
10. Update the Phase 32 board and `PROGRESS.md`.
11. Commit the completed step or hand off explicitly.

## Expected Board Steps

When the board is created after spec approval, use these steps unless implementation planning exposes a better equivalent split:

1. Add ingestion-boundary contract tests and models.
2. Add `Document` boundary defaults and export compatibility.
3. Add identity source maps for plain text and Markdown ingestion.
4. Add generated-segment and source-support validation.
5. Add audit persistence/readback coverage for boundary fields.
6. Add prompt-neutrality verification and final project verification.

## Gate Criteria

Phase 32 is complete only when:

- Boundary, metadata, source-map, layout, table-cell, and OCR-confidence contracts exist as domain-neutral Pydantic models.
- Existing `.txt` and `.md` ingestion output identity remains hash- and offset-compatible with prior behavior.
- Generated text segments are represented explicitly and cannot be accepted as source-backed support.
- Source-map validation rejects gaps, overlaps, invalid ranges, and unmapped source-backed spans.
- Audit document persistence round-trips boundary fields.
- Existing Phase 29, Phase 30, and Phase 31 eval gates remain passing.
- No full parser implementation for PDF tables, DOCX, HTML, email, OCR, or layout-aware chunking is added.
- No prompt body, runtime config, domain-pack runtime behavior, or architecture rule is changed.
- Relevant narrow tests pass.
- `make test`, `make lint`, `make smoke`, `git diff --check`, and `git diff --exit-code -- prompts` pass when feasible.
- All Phase 32 board issues are resolved or explicitly deferred.
- `PROGRESS.md` is updated.

## Board Decisions to Pin at Opening

1. Add boundary contracts as a focused contracts module and expose them through `extractor.contracts`.
2. Keep `Document` changes additive and defaulted so existing constructors and audit payloads remain compatible.
3. Represent generated separators and parser-introduced text as explicit generated source-map segments.
4. Define OCR confidence span shape in Phase 32 but do not add OCR execution.
5. Keep full PDF table extraction, DOCX, HTML, email, and layout-aware chunking out of Phase 32.

## Open Questions

_(None. If implementation exposes a conflict between source-map strictness and existing PDF text extraction, log it on the Phase 32 board before changing contracts.)_
