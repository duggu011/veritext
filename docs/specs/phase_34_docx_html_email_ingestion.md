# Phase 34 - DOCX, HTML, and Email Ingestion

Status: approved for implementation and board opened on 2026-05-29.

Date drafted: 2026-05-29

Roadmap sources:

- `docs/PROJECT_OVERVIEW.md`:
  - `1. Ingestion`
  - `Highest-leverage accuracy/provenance improvements, ranked`
  - `Target domains (ranked by fit)`
  - `Configurable surface`
  - `Non-configurable core`
- `docs/phase_26_plus_roadmap.md`
- `docs/boards/README.md`
- `PROGRESS.md`
- Phase 33 board and completed commits through `a66cf6c`

## Goal

Add boundary-preserving ingestion for DOCX, HTML, and RFC 5322 `.eml` email documents while preserving the Phase 32 and Phase 33 source identity, extracted-text offset, source-map, layout, and audit rules.

Phase 34 should make common compliance, litigation, contract, procurement, and audit-evidence formats usable by the existing domain-neutral extraction kernel. It should extract deterministic text, metadata, page or logical section ranges, layout spans where format structure supports them, explicit generated separators, and explicit unmapped ranges where raw source byte offsets are not proven.

## Non-Goals

- Do not add OCR, scanned-image text recognition, image extraction, audio, video, spreadsheet, archive, or web-crawling ingestion.
- Do not add `.msg` support. Outlook MSG parsing requires a separate parser decision and belongs to a later phase unless the operator amends this spec before approval.
- Do not add attachment extraction from email. Emails with non-alternative attachments should fail explicitly or be rejected before producing a partial document.
- Do not add runtime LLM, planner, executor, critic, verifier, reconciler, prompt, domain-pack, report, config, web UI, REST API, Docker, CI/CD, vector DB, embedding, fine-tuning, or agent-framework behavior.
- Do not add document-specific parsing rules for one vendor template, contract form, email sender, website, or fixture.
- Do not mark DOCX, decoded HTML, or decoded email text as raw source-backed unless implementation proves exact source byte offsets into the original source bytes.
- Do not silently drop document parts, unsupported encodings, unsupported MIME parts, parser errors, or unalignable text fragments.

## Domain-Scope Alignment

Phase 34 is ingestion work for the domain-neutral kernel. The target domains need DOCX, HTML, and email, but the implementation must stay reusable across legal contracts, e-discovery, procurement, SOC 2/ISO evidence, standards, regulatory guidance, scientific review, insurance, and clinical documents.

Configurable in Phase 34:

- Format adapter behavior for DOCX, HTML, and `.eml` files.
- Parser metadata values stored in `Document.metadata`.
- Fixture source files and expected boundary assertions.
- Generic layout roles from the Phase 32 `LayoutRole` vocabulary.

Non-configurable in Phase 34:

- Source hash and text hash calculation.
- `Document.doc_id` derivation from source bytes.
- Extracted text character and UTF-8 byte offset validation.
- Page or logical section map ordering and byte/character range validation.
- Source-map fail-closed behavior for generated and unmapped regions.
- Pydantic stage contracts and frozen model behavior.
- SQLite audit preservation through document payload JSON.
- No-silent-drop rejection accounting.
- Architecture bans on web UI, REST API, Docker, CI/CD, vector DBs, embeddings, fine-tuning hooks, and agent frameworks.

## Current State

`src/extractor/ingestion/documents.py` supports `.txt`, `.md`, and `.pdf`. Plain text and Markdown use identity source maps. PDF ingestion uses the focused Phase 33 adapter to populate parser metadata, page maps, generated/unmapped source maps, layout spans, table spans, and table cell spans.

`DocumentFormat` currently allows only `plain_text`, `markdown`, and `pdf`. Phase 34 must extend that contract additively and preserve all existing ingestion behavior.

## Boundary and Mapping Policy

Phase 34 must preserve the three evidence layers introduced in Phase 33:

1. Immutable source identity: source path, source byte length, source SHA-256, and stable `doc_id`.
2. Extracted-text identity: `Document.text`, text SHA-256, exact character offsets, exact UTF-8 byte offsets, page or logical section map, layout spans, table spans when available, and metadata.
3. Raw source-byte backing: `SourceMapSegment.kind == "source"` with source byte offsets into the original file.

The first two layers are required for each new format. The third layer is allowed only when implementation and tests prove stable offsets into the original source bytes. When a parser decodes zipped XML, HTML entities, MIME transfer encodings, or charset conversions, the extracted text should be represented as `unmapped` unless exact raw source byte mapping is proven.

Generated text remains allowed only when explicit. Examples include paragraph breaks, heading separators, email header labels, MIME part separators, table delimiters, and adapter-inserted newlines. Generated segments must have no source byte offsets and must not be accepted by `require_source_backed_span(...)`.

## DOCX Ingestion

The DOCX adapter should:

- Support `.docx` files that are valid OpenXML ZIP packages.
- Extract text from `word/document.xml` in deterministic document order.
- Preserve paragraph boundaries with generated newline separators.
- Preserve table text when table cells can be aligned into `Document.text`; reuse existing `table_spans` and `table_cell` layout roles rather than adding DOCX-specific contracts.
- Populate metadata from available core properties such as title, creator, created time, modified time, and source name when present.
- Populate layout spans for paragraphs, headings, list items, tables, and table cells when the XML structure provides enough information without guessing.
- Keep DOCX extracted text `unmapped` unless exact byte ranges into the original `.docx` source bytes are proven.
- Fail explicitly with `IngestionError` for malformed ZIP files, missing `word/document.xml`, empty extracted text, unsupported encrypted/protected packages, or unalignable emitted table cells.

The first implementation should prefer Python standard-library ZIP/XML parsing unless the approved board pins a parser dependency. If a dependency is required, it must be justified on the board before implementation.

## HTML Ingestion

The HTML adapter should:

- Support `.html` and `.htm` files.
- Decode source bytes using a declared charset when safely available, otherwise UTF-8.
- Extract visible text in deterministic DOM order.
- Represent headings, paragraphs, list items, tables, and table cells with existing layout/table boundary contracts when alignable.
- Preserve generated separators for block boundaries, list items, rows, and cells.
- Populate metadata such as title, declared charset, source name, MIME type, parser name, and selected meta tags when present.
- Treat decoded text as `unmapped` unless exact raw source byte mapping is proven, especially when entities or whitespace normalization are involved.
- Fail explicitly for empty visible text, unsupported encodings, parser failures, or tables/cells the adapter claims to emit but cannot align exactly into `Document.text`.

HTML ingestion must not fetch external resources, execute scripts, follow links, crawl websites, or resolve remote images/stylesheets.

## Email Ingestion

The email adapter should:

- Support `.eml` files parsed as RFC 5322 messages through the Python standard-library email parser unless the approved board pins a different parser.
- Extract a deterministic text view containing selected headers and the preferred body text.
- Prefer `text/plain` body parts when present; fall back to `text/html` body extraction through the HTML adapter when no plain text body exists.
- Preserve generated header labels and section separators in source-map segments.
- Populate metadata for source name, MIME type, parser name, message ID, subject, from, to, cc, date, content type, and declared charsets when present.
- Keep decoded headers and body text `unmapped` unless exact raw source byte ranges are proven.
- Allow multipart alternatives only when they represent alternative views of the same body content.
- Fail explicitly for attachments, unsupported body parts, nested messages, empty body text, unsupported encodings, or ambiguous multipart structures.

Email ingestion should not extract attachments, recurse into attached documents, download remote images, or treat inline binary parts as text.

## Contract Changes

Allowed:

- Extend `DocumentFormat` additively with `docx`, `html`, and `email`.
- Add focused adapter modules under `src/extractor/ingestion/`, such as `docx.py`, `html.py`, and `email.py`.
- Add ingestion-only helper functions for deterministic text assembly and text-range alignment.
- Add additive validation helpers if Phase 32 boundary validation is insufficient for these formats.
- Add small repo-safe fixtures under `tests/fixtures/` or `evals/fixtures/` when they are auditable and do not require external state.
- Add tests for metadata, logical section maps, generated/unmapped source maps, layout spans, table spans, explicit failures, audit readback, and source-support rejection.

Required compatibility:

- Existing `.txt`, `.md`, and `.pdf` ingestion tests must keep passing without changed expected hashes, IDs, text, byte lengths, or page maps.
- Existing public imports from `extractor.ingestion` and `extractor.contracts` must remain valid.
- Existing audit document payloads must remain readable without a schema migration.
- Existing Phase 29, Phase 30, and Phase 31 evaluation suites must remain passing.

Disallowed:

- Removing or renaming existing `Document`, `PageSpan`, `SourceMapSegment`, `LayoutSpan`, `TableSpan`, `TableCellSpan`, `Chunk`, or `SourceSpan` fields.
- Replacing the public `ingest_document(...)` interface.
- Adding format-specific runtime LLM behavior.
- Marking decoded parser text as source-backed solely because it appears in `Document.text`.
- Adding parser dependencies without a board-pinned rationale and tests.

## Validation Rules

Phase 34 must enforce at least these rules:

- Every page or logical section range is within `Document.text` and `text_byte_length`.
- Ranges are ordered and non-overlapping.
- Every populated layout span references a known page or logical section and a valid text range.
- Every populated table span references a known page or logical section and a valid text range.
- Every table cell range is within its parent table range and within `Document.text`.
- Table and cell IDs are unique within a document.
- Generated source-map segments have no source byte offsets.
- Decoded parser text remains `unmapped` unless raw source-byte mapping is proven.
- `require_source_backed_span(...)` continues to reject generated or unmapped ranges for all new formats.
- Empty text, unsupported protected/encrypted files, unsupported email parts, attachments, malformed source files, and unalignable supported structures fail explicitly.

If a parser output would require guessing offsets or silently dropping supported content, the adapter must fail closed with an explicit `IngestionError`.

## Stage and Module Boundaries

### Expected Code Areas

- `src/extractor/contracts/base.py`
- `src/extractor/ingestion/documents.py`
- `src/extractor/ingestion/docx.py`
- `src/extractor/ingestion/html.py`
- `src/extractor/ingestion/email.py`
- `src/extractor/contracts/ingestion.py` only if additive validation helpers are required
- `src/extractor/contracts/documents.py` only if additive document validation is required
- `src/extractor/source_support.py` only if tests expose a generated/unmapped support gap
- `tests/unit/test_ingestion.py`
- `tests/unit/test_ingestion_docx_html_email.py`
- `tests/unit/test_audit_document_boundaries.py` if audit readback coverage needs format-specific assertions

Do not edit runtime LLM stages for Phase 34.

### Tests

Expected test coverage:

- Existing text, Markdown, and PDF ingestion compatibility.
- Format detection for `.docx`, `.html`, `.htm`, and `.eml`.
- DOCX text extraction, metadata, paragraphs, headings, list items, table cells, generated separators, and explicit malformed/empty failures.
- HTML visible-text extraction, metadata, headings, paragraphs, lists, tables, generated separators, and explicit empty/unsupported failures.
- EML header/body extraction, plain-text preference, HTML-body fallback, metadata, generated separators, and explicit attachment/unsupported multipart failures.
- Audit readback of each new format's metadata, source map, layout spans, and table spans where populated.
- Source-support rejection for generated and unmapped ranges in each new format.

## Audit and Provenance Effects

Phase 34 should improve non-PDF provenance representation without changing the audit database schema unless implementation proves an indexed field is required.

Required properties:

- Document payload JSON includes metadata, page or logical section maps, source maps, layout spans, and table spans for supported fixtures.
- Audit readback preserves all populated boundary fields.
- Generated and unmapped source-map regions remain visible in payload JSON.
- Unsupported, malformed, protected, attachment-bearing, or unalignable parser outputs are rejected explicitly; they are not silently dropped.
- Existing audit idempotency and conflicting-document detection remain intact.

## Invariant Impact

Do not weaken I1-I9.

Phase 34 strengthens provenance for additional real-world formats by populating the existing boundary model. Required protections:

- Existing exact text, Markdown, and PDF behavior remains unchanged.
- Extracted-text offsets are exact in `Document.text`.
- Parser-introduced text is generated, not source-backed.
- Decoded DOCX, HTML, and email text is not marked raw source-backed unless proven by tests.
- Table cells carry exact extracted-text ranges when emitted.
- Existing Phase 29, Phase 30, and Phase 31 evaluation gates remain passing.
- No prompt body, runtime config, domain-pack behavior, runtime LLM stage, or architecture rule is changed.

## Configuration Changes

Expected configuration work: none.

Runtime tuning values must remain in `config/`. Parser constants used only to interpret format structure should live near the adapter and be covered by tests.

## Prompt Changes

No prompt body should be changed in Phase 34.

Allowed prompt-related work:

- Run prompt-no-change verification.

Disallowed prompt-related work:

- Prompt instructions about DOCX, HTML, email, attachments, target domains, parser behavior, or table extraction.
- Free-text JSON parsing.

## Tests and Evaluation Gates

Required narrow tests:

- New format detection and unsupported-format behavior.
- DOCX ingestion populates metadata, generated/unmapped source maps, layout spans, and table spans from deterministic fixtures.
- HTML ingestion populates metadata, generated/unmapped source maps, layout spans, and table spans from deterministic fixtures.
- EML ingestion populates metadata, generated/unmapped source maps and layout spans from deterministic fixtures.
- Attachments and unsupported multipart email structures fail with explicit `IngestionError`.
- Empty or malformed source files fail explicitly.
- Audit readback preserves each new format's boundary fields.
- `require_source_backed_span(...)` rejects generated and unmapped ranges for each new format.
- Plain text, Markdown, and PDF ingestion identity remains unchanged.

Required broader verification before Phase 34 completion:

```bash
python3 -m pytest tests/unit/test_ingestion.py tests/unit/test_ingestion_boundaries.py tests/unit/test_source_support.py tests/unit/test_audit_document_boundaries.py tests/unit/test_ingestion_pdf_tables.py tests/unit/test_ingestion_docx_html_email.py -q
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

1. Add failing format-detection and compatibility tests for `DocumentFormat`, suffix routing, and existing `.txt`/`.md`/`.pdf` behavior.
2. Add DOCX adapter tests with deterministic repo-safe fixtures for paragraphs, headings, lists, tables, metadata, and failure cases.
3. Implement the focused DOCX adapter and wire it through `ingest_document(...)`.
4. Add HTML adapter tests with deterministic fixtures for visible text, headings, lists, tables, metadata, charset handling, and failure cases.
5. Implement the focused HTML adapter and wire it through `ingest_document(...)`.
6. Add `.eml` adapter tests with deterministic fixtures for plain-text body, HTML fallback, metadata, generated separators, attachment rejection, and multipart failures.
7. Implement the focused email adapter and wire it through `ingest_document(...)`.
8. Add audit readback and source-support regression coverage for DOCX, HTML, and email generated/unmapped ranges.
9. Run narrow tests.
10. Run project-level and evaluation verification.
11. Update the Phase 34 board and `PROGRESS.md`.
12. Commit the completed step or hand off explicitly.

## Expected Board Steps

When the board is created after spec approval, use these steps unless implementation planning exposes a better equivalent split:

1. Add format-detection and compatibility tests.
2. Add DOCX ingestion fixtures, adapter, metadata, layout, table, and failure handling.
3. Add HTML ingestion fixtures, adapter, metadata, layout, table, and failure handling.
4. Add EML ingestion fixtures, adapter, metadata, body selection, and failure handling.
5. Add audit readback, source-support regression, and prompt-neutrality verification.
6. Add final project and evaluation verification.

## Gate Criteria

Phase 34 is complete only when:

- `DocumentFormat` supports DOCX, HTML, and email additively.
- Public `ingest_document(...)` supports `.docx`, `.html`, `.htm`, and `.eml` while preserving existing `.txt`, `.md`, and `.pdf` behavior.
- Supported fixtures produce stable source hashes, text hashes, document IDs, text, page or logical section maps, source maps, metadata, layout spans, and table spans where applicable.
- Generated parser text is explicit and cannot be accepted as source-backed evidence.
- Decoded parser text is not marked raw source-backed unless source byte offsets are proven by tests.
- Unsupported attachments, malformed source files, protected packages, unsupported encodings, unsupported MIME parts, and unalignable structures fail explicitly.
- Audit document persistence round-trips all new populated boundary fields.
- Existing Phase 29, Phase 30, and Phase 31 eval gates remain passing.
- No OCR, `.msg`, spreadsheet, prompt, runtime LLM, domain-pack runtime, config, or architecture-rule change is added.
- Relevant narrow tests pass.
- `make test`, `make lint`, `make smoke`, `git diff --check`, and `git diff --exit-code -- prompts` pass when feasible.
- All Phase 34 board issues are resolved or explicitly deferred.
- `PROGRESS.md` is updated.

## Board Decisions to Pin at Opening

1. Use Python standard-library ZIP/XML parsing for the first DOCX adapter unless implementation exposes a board-logged need for a parser dependency.
2. Use Python standard-library HTML parsing for the first HTML adapter unless implementation exposes a board-logged need for a parser dependency.
3. Support `.eml` only for Phase 34 email ingestion; keep `.msg` out of scope.
4. Reject non-alternative email attachments explicitly rather than silently omitting them.
5. Keep decoded DOCX, HTML, and email text `unmapped` unless source byte ranges into the original source bytes are proven.

## Open Questions

_(None.)_
