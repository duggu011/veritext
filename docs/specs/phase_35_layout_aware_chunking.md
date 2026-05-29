# Phase 35 - Layout-Aware Chunking

Status: approved for implementation.

Date drafted: 2026-05-29
Date approved: 2026-05-29

Roadmap sources: `docs/PROJECT_OVERVIEW.md` sections `2. Chunker`,
`Highest-leverage accuracy/provenance improvements, ranked`, `Target domains
(ranked by fit)`, `Configurable surface`, and `Non-configurable core`;
`docs/phase_26_plus_roadmap.md`; `docs/boards/README.md`; `PROGRESS.md`;
Phase 34 board and completed commits through `125432e`.

## Goal

Replace fixed token-window chunking with boundary-aware chunking that uses the
layout, page, source-map, and table boundaries produced by Phases 32-34.

Phase 35 should stop routine chunk splits in the middle of sections,
paragraphs, sentences, and tables while preserving exact `Document.text`
slices, UTF-8 byte offsets, token offsets, stable audit payloads, and
mechanical span enforcement. Chunking must remain domain-neutral: the behavior
is driven by typed document boundaries and generic text structure, not by
customer, sector, vendor, or fixture-specific language.

## Non-Goals

- Do not add embeddings, vector databases, retrieval indexes, search products,
  REST APIs, web UI, Docker, CI/CD, fine-tuning hooks, or agent frameworks.
- Do not add parser changes for PDF, DOCX, HTML, email, or other source
  formats except test fixtures needed to exercise existing boundaries.
- Do not add runtime LLM calls or route any chunking decision through an LLM.
- Do not change planner, executor, critic, verifier, reconciler, reporter,
  domain-pack, or prompt semantics.
- Do not inject cross-chunk marker text into `Chunk.text`. Markers must be
  metadata so source offsets remain exact.
- Do not split tables to satisfy a token target. Oversized tables must remain
  atomic and be flagged explicitly.
- Do not silently discard page ranges, layout spans, table spans, source-map
  segments, or chunk intervals that cannot be reconciled.
- Do not tune behavior for one fixture, document title, proper noun, insurance
  form, contract type, or market sector.

## Domain-Scope Alignment

Layout-aware chunking directly supports high-stakes document workflows where a
single fact may depend on a heading, clause lead-in, table header, or previous
paragraph. This phase remains a domain-neutral runtime improvement for legal
contracts, procurement packages, SEC filings, clinical and regulatory
documents, insurance policies, standards, SOC 2/ISO evidence, patents, and
scientific review papers.

Configurable in Phase 35: chunk target token window and overlap,
boundary-aware mode and tokenizer policy, oversized atomic chunk handling for
tables and unusually long text blocks, and generic sentence/paragraph boundary
preferences.

Non-configurable in Phase 35:

- Exact `Document.text` slicing.
- `Chunk.start_char`, `Chunk.end_char`, `Chunk.start_byte`, `Chunk.end_byte`,
  `Chunk.start_token`, and `Chunk.end_token` validation.
- Source hash, text hash, and document identity.
- Audit storage of chunk payload JSON.
- Pydantic stage contracts and frozen model behavior.
- No-silent-drop behavior for invalid boundaries.
- Architecture bans listed in `AGENTS.md` and `CLAUDE.md`.

## Current State

`src/extractor/chunker/tokenizer.py` currently tokenizes the entire document
with the configured `tiktoken` encoding and emits fixed windows using
`window_tokens` and `overlap_tokens`. It preserves source character, UTF-8 byte,
and token offsets, and it records chunks to the audit store when requested.

`src/extractor/contracts/models.py` defines `Chunk` with identity, text,
character offsets, byte offsets, and token offsets only. Downstream source-span
validation relies on each chunk text being an exact contiguous slice of
`Document.text`.

`src/extractor/contracts/documents.py` now exposes `page_map`, `source_map`,
`layout_spans`, `table_spans`, and OCR confidence spans on `Document`. Phases
33 and 34 populate layout and table boundaries for PDF, DOCX, HTML, and email.
Phase 35 should consume those boundaries; it should not add new ingestion
semantics.

`config/default.yaml` sets `chunking.tokenizer: cl100k_base`,
`window_tokens: 1200`, and `overlap_tokens: 120`. The default LLM provider is
currently Anthropic, so Phase 35 must make tokenizer policy explicit instead of
pretending one encoding is provider-exact in all cases.

## Boundary-Aware Chunking Policy

Chunk text must always be an exact contiguous slice of `Document.text`. The
chunker may move chunk start and end positions to better boundaries, but it must
not rewrite, normalize, prepend, append, or annotate source text.

Boundary priority:

1. Document start and end.
2. Page or logical section boundaries from `Document.page_map`.
3. Heading starts from `layout_spans` with role `heading`.
4. Table starts and ends from `Document.table_spans`.
5. Paragraph and list-item spans from `layout_spans`.
6. Sentence ends detected deterministically inside prose spans.
7. Token-safe UTF-8 character boundaries as the final overflow fallback.

Rules:

- Prefer starting a new chunk at a heading rather than attaching the heading to
  the previous section.
- Keep a table in one chunk even if it exceeds the target token window. Mark
  the chunk as oversized instead of splitting inside the table.
- Keep paragraph and list-item spans intact when they fit within the target
  window.
- Avoid splitting inside a sentence when a sentence boundary exists within the
  allowed window.
- If a single sentence, paragraph, or list item exceeds the target window, split
  at token-safe character boundaries and flag the split reason explicitly.
- Preserve overlap only when it does not force a split inside a table. If the
  configured overlap would bisect a table, shorten or drop that overlap and
  record the reason in chunk metadata.
- After removing configured overlap, the primary chunk intervals must cover
  `Document.text` in order with no gaps.

## Hierarchy and Cross-Chunk Metadata

Phase 35 should add metadata to `Chunk` rather than changing chunk text.

Allowed additive fields include:

- `chunk_kind`: a literal value such as `document`, `section`, `paragraph`,
  `list_item`, `table`, `mixed`, or `overflow`.
- `section_path`: the ordered generic heading text or generated section labels
  that place the chunk inside the document hierarchy.
- `layout_span_ids`: layout spans covered by the chunk.
- `table_ids`: table spans covered by the chunk.
- `page_numbers`: pages or logical sections touched by the chunk.
- `parent_chunk_id`: an optional parent or section-leader chunk ID.
- `depends_on_chunk_ids`: previous chunks needed for local context.
- `split_reason`: a literal reason such as `boundary`, `token_window`,
  `atomic_table_overflow`, `oversized_sentence`, `oversized_paragraph`, or
  `overlap_adjusted`.

All new fields must have defaults so older audited chunk payloads remain
readable. Existing required fields must not be removed or renamed.

Cross-chunk reference markers must be metadata-only. The first implementation
should mark dependencies through structural evidence first: a chunk that begins
inside a section whose heading was emitted in an earlier chunk depends on that
section-leader chunk; a table chunk split away from its heading depends on the
heading chunk; a chunk whose overlap was shortened because of an atomic table
depends on the previous chunk when context was intentionally separated.

Generic discourse cues such as references to previous, following, above, or
foregoing material may be used only as a deterministic secondary signal. The
signal must be domain-neutral, tested, and never required for correctness.

## Tokenizer Policy

Phase 35 should centralize tokenizer loading and policy decisions inside the
chunker rather than scattering assumptions through runtime stages.

- Preserve the current `cl100k_base` path for existing OpenAI-compatible
  token-window behavior.
- Keep `Chunk.start_token` and `Chunk.end_token` deterministic for the selected
  tokenizer policy.
- Add explicit configuration and validation for tokenizer policy if needed,
  while preserving the existing default config values unless the approved board
  pins a migration.
- When an exact local provider tokenizer is unavailable, use the configured
  tokenizer as an explicit approximation and expose that policy through chunk
  metadata or audit-visible configuration.
- Raise `ChunkingError` for unknown tokenizer policies, missing tokenizer
  dependencies, tokenizer byte reconstruction mismatches, or non-advancing
  windows.

Phase 35 must not call provider APIs to count tokens.

## Contract Changes

- Extend `Chunk` additively with hierarchy, boundary, dependency, page, table,
  tokenizer-policy, and split-reason metadata.
- Add small literal types or Pydantic models near existing chunk contracts when
  they keep the contract auditable and typed.
- Extend `ChunkingConfig` additively for boundary-aware mode, tokenizer policy,
  and oversized atomic chunk handling.
- Add chunker helper modules under `src/extractor/chunker/` for boundary
  collection, sentence-boundary selection, token offset utilities, and chunk
  materialization.
- Add audit compatibility tests for older chunk payload JSON without new fields.
- Add focused fixtures that exercise existing `Document` boundary contracts.

- Preserve the public `chunk_document(document, config, audit_store=None)`
  interface.
- Preserve exact slice validation: `chunk.text == document.text[start:end]`.
- Preserve downstream executor source-span validation semantics.
- Keep existing audit schema readable without a SQLite migration unless an
  approved board pins a schema change.
- Preserve existing public imports from `extractor.chunker` and
  `extractor.contracts`.

- Removing or renaming existing `Chunk`, `SourceSpan`, `Document`, `PageSpan`,
  `SourceMapSegment`, `LayoutSpan`, `TableSpan`, or `TableCellSpan` fields.
- Passing loose dictionaries between stage boundaries.
- Adding hidden global state to the chunker.
- Adding prompt, LLM view, or runtime extraction changes to consume dependency
  metadata in this phase.

If new chunk metadata changes payload JSON for the same document and offsets,
the implementation must avoid audit idempotency conflicts. Acceptable solutions
include a deterministic layout-aware chunk ID policy version or compatibility
serialization that keeps legacy token-window payloads byte-identical when no
new metadata is emitted.

## Validation Rules

Phase 35 must enforce at least these rules:

- Every chunk range is within `Document.text` and `text_byte_length`.
- Every chunk text exactly matches its document character and byte range.
- Chunk indexes are contiguous and ordered.
- Primary chunk coverage has no gaps after accounting for configured overlap.
- Overlaps do not split through a table.
- Table chunks fully contain each referenced table span.
- No table span is split across chunks unless the chunker raises
  `ChunkingError` before returning chunks.
- Layout span and table IDs referenced by chunks exist on the source document.
- Page numbers referenced by chunks exist in `Document.page_map`.
- `parent_chunk_id` and `depends_on_chunk_ids` reference emitted chunk IDs.
- Oversized atomic chunks are flagged and explain why the target token window
  was exceeded.
- Unknown tokenizer policies, missing tokenizer dependencies, invalid document
  boundaries, impossible non-advancing windows, and unreconciled coverage gaps
  raise explicit `ChunkingError`.

## Stage and Module Boundaries

Expected code areas:

- `src/extractor/chunker/tokenizer.py`
- `src/extractor/chunker/__init__.py`
- `src/extractor/contracts/models.py`
- `src/extractor/contracts/__init__.py`
- `src/extractor/config/models.py`
- `config/default.yaml`
- `src/extractor/audit/core_records.py` only if audit compatibility requires a
  narrow serialization adjustment
- `src/extractor/orchestrator/state.py` only if resume validation must verify
  new chunk metadata
- `src/extractor/llm/views.py` only if tests prove that compact chunk views
  must expose non-text chunk metadata without changing prompts
- `tests/unit/test_chunker.py`
- `tests/unit/test_contracts.py`
- New focused chunker tests under `tests/unit/` if `test_chunker.py` would
  exceed the file-size rule

Do not edit runtime LLM stages for Phase 35.

## Audit and Provenance Effects

Phase 35 should make audit chunk payloads more informative without weakening
source provenance.

- Stored chunks include the exact text slice and additive boundary metadata.
- Audit readback preserves new chunk metadata.
- Old chunk payload JSON without new fields remains readable.
- Resume validation still rejects chunks whose text no longer matches document
  offsets.
- Chunk metadata never claims raw source-byte backing; raw source support
  remains governed by `Document.source_map` and `require_source_backed_span`.
- Re-running with existing audited chunks must not silently replace old chunks
  with incompatible payloads.

## Invariant Impact

Do not weaken I1-I9.

Phase 35 strengthens invariant enforcement by reducing chunk splits that make
provenance harder for executor, critic, and verifier stages to reason about.

- Source spans remain mechanical document/chunk slices.
- Chunk text remains exact and contiguous.
- Generated or unmapped source-map semantics remain unchanged.
- Table and layout boundaries are consumed only as typed evidence.
- No document-specific lexical patches are allowed.
- Existing Phase 29, Phase 30, and Phase 31 evaluation suites remain passing.
- No prompt body, runtime LLM call path, domain-pack runtime behavior, or
  architecture rule changes.

## Configuration Changes

Allowed additive configuration under `chunking`: `boundary_mode`,
`tokenizer_policy`, `allow_oversized_atomic_chunks`, and a generic sentence
boundary threshold if tests show it is needed to avoid pathological tiny chunks.
Defaults must preserve current behavior unless the approved board pins a
migration.

All tuning values must live in `config/default.yaml` and the config models.
Do not hardcode runtime tuning values in source or tests.

## Prompt Changes

No prompt body should be changed in Phase 35.

- Run prompt-no-change verification.
- Keep LLM chunk views source-text-compatible if metadata is surfaced through
  existing compact view models.

- New instructions about layout-aware chunking, tables, headings, cross-chunk
  dependencies, target domains, or extraction strategy.
- Free-text JSON parsing.
- LLM calls for chunking decisions.

## Tests and Evaluation Gates

Required narrow tests:

- Existing token-window behavior stays deterministic for documents without
  usable layout boundaries or for the legacy boundary mode.
- UTF-8 boundary preservation still holds when tokens split multi-byte
  characters.
- Paragraph and sentence boundary tests prove normal chunks do not split
  mid-sentence when a valid boundary exists.
- Heading tests prove headings start a new section chunk and are not attached
  to the previous section when avoidable.
- Table tests prove table spans are never split across chunks.
- Oversized table tests prove atomic overflow chunks are emitted or rejected
  according to approved config, with explicit metadata.
- Overlap tests prove overlap never bisects a table and coverage remains
  gap-free.
- Hierarchy metadata tests prove section paths, page numbers, layout span IDs,
  table IDs, parent chunk IDs, and dependency IDs are valid.
- Audit readback tests prove new chunk metadata persists.
- Backward-compatibility tests prove older chunk payload JSON without new
  metadata fields remains readable.
- Resume validation tests prove mismatched chunk text or invalid dependency
  metadata fails explicitly.
- Prompt-neutrality verification proves files under `prompts/` did not change.

Required broader verification before Phase 35 completion:

```bash
python3 -m pytest tests/unit/test_chunker.py tests/unit/test_contracts.py -q
make test
make lint
make smoke
git diff --check
git diff --exit-code -- prompts
PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json
PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json
PYTHONPATH=src python3 -m extractor.evals --adversarial-suite evals/suites/phase_31_adversarial.json
PYTHONPATH=src python3 -m extractor.evals --mutation-suite evals/suites/phase_31_mutation.json
PYTHONPATH=src python3 -m extractor.evals --calibration-suite evals/suites/phase_30_diverse_corpus_round_1.json
```

If layout-aware chunking changes expected chunk counts in evaluation fixtures,
record the before/after chunk counts and extraction metrics on the Phase 35
board. Do not accept a metric regression without a board issue and operator
decision.

## Implementation Order

1. Add contract and config tests for additive chunk metadata, legacy chunk
   payload readback, tokenizer-policy validation, and unchanged public imports.
2. Split reusable token-offset helpers from the current fixed-window chunker and
   keep the legacy path green.
3. Add boundary collection and validation from page maps, layout spans, and
   table spans.
4. Add boundary-aware packing that preserves headings, paragraphs, sentences,
   and tables, including explicit oversized atomic chunk handling.
5. Add hierarchy and dependency metadata, audit readback coverage, resume
   validation coverage, and prompt-neutrality verification.
6. Run final project, smoke, lint, prompt-neutrality, and evaluation gates; fill
   the board summary and stop for operator acceptance.

## Open Questions

None. This draft pins the main design decisions so the implementation board can
open cleanly after operator approval:

- Cross-chunk markers are metadata, not injected text.
- Tables are atomic; oversized table chunks are explicit.
- Long prose overflow is allowed only when no safe boundary fits.
- Tokenizer policy is explicit and local; no provider API calls count tokens.
- Consuming dependency metadata in executor or planner context is outside this
  phase.
