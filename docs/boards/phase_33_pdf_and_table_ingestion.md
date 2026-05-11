# Phase 33 - PDF and Table Ingestion

## Current Status

Step: 0 of 6
Branch: main
Started: 2026-05-11
Last session: 2026-05-11
Spec: `docs/specs/phase_33_pdf_and_table_ingestion.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:1. Ingestion`; `docs/PROJECT_OVERVIEW.md:2. Chunker`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 33 approved for implementation after operator continuation. Board opened; implementation has not started.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [ ] Step 1: Add PDF/table ingestion tests and parser fixture strategy.
- [ ] Step 2: Split and harden the PDF adapter boundary.
- [ ] Step 3: Populate PDF metadata, page maps, and layout spans.
- [ ] Step 4: Populate table spans and table cell provenance.
- [ ] Step 5: Add unalignable-cell failure handling and audit readback coverage.
- [ ] Step 6: Add prompt-neutrality verification and final project verification.

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

### 2026-05-11 - Session 1

- Resumed after operator continued from the Phase 33 spec draft.
- Completed: approved the Phase 33 spec for implementation, opened this board, pinned Phase 33 open-question resolutions, and updated active phase tracking.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_33_pdf_and_table_ingestion.md docs/boards/README.md docs/boards/phase_33_pdf_and_table_ingestion.md` returned no matches; `rg -n "Phase 33|phase_33_pdf_and_table_ingestion.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_33_pdf_and_table_ingestion.md docs/boards/phase_33_pdf_and_table_ingestion.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed.
- Next: Step 1 - add PDF/table ingestion tests and parser fixture strategy.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: _(pending)_
- Deferred: _(pending)_
- Added beyond spec: _(pending)_

### Lessons for downstream phases

- _(pending)_
