# Phase 34 - DOCX, HTML, and Email Ingestion

## Current Status

Step: 0 of 6
Branch: main
Started: 2026-05-29
Last session: 2026-05-29
Spec: `docs/specs/phase_34_docx_html_email_ingestion.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:1. Ingestion`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 34 was approved for implementation and the board was opened on 2026-05-29. Next up: Step 1 - add format-detection and compatibility tests.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [ ] Step 1: Add format-detection and compatibility tests.
- [ ] Step 2: Add DOCX ingestion fixtures, adapter, metadata, layout, table, and failure handling.
- [ ] Step 3: Add HTML ingestion fixtures, adapter, metadata, layout, table, and failure handling.
- [ ] Step 4: Add EML ingestion fixtures, adapter, metadata, body selection, and failure handling.
- [ ] Step 5: Add audit readback, source-support regression, and prompt-neutrality verification.
- [ ] Step 6: Add final project and evaluation verification.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Use Python standard-library ZIP/XML parsing for the first DOCX adapter unless implementation exposes a board-logged need for a parser dependency. | Keeps Phase 34 inside current dependency and architecture boundaries while proving deterministic extracted-text provenance. |
| Q2 | Use Python standard-library HTML parsing for the first HTML adapter unless implementation exposes a board-logged need for a parser dependency. | Avoids a parser dependency until tests prove one is required for correctness. |
| Q3 | Support `.eml` only for Phase 34 email ingestion; keep `.msg` out of scope. | `.msg` needs a separate parser decision and should not expand this phase. |
| Q4 | Reject non-alternative email attachments explicitly rather than silently omitting them. | Prevents partial email records and preserves no-silent-drop behavior. |
| Q5 | Keep decoded DOCX, HTML, and email text `unmapped` unless source byte ranges into the original source bytes are proven. | Decoding zipped XML, entities, MIME encodings, and charsets does not automatically provide raw source-byte provenance. |

---

## Gate Interpretations

- Phase 34 may extend `DocumentFormat` additively and add focused DOCX, HTML, and EML ingestion adapters.
- Phase 34 must not add OCR, `.msg`, spreadsheet ingestion, attachment extraction, web crawling, prompt changes, runtime LLM behavior, domain-pack runtime behavior, config changes, or architecture-rule changes.
- Decoded parser text remains `unmapped` unless a test-proven raw source byte mapping exists.
- Generated separators, header labels, and block delimiters are allowed only when represented as generated source-map segments.
- Tables are accepted only when cells can be aligned exactly into `Document.text`.
- Empty, malformed, protected, attachment-bearing, unsupported multipart, unsupported encoding, or unalignable inputs fail explicitly with `EmptyDocumentError` or `IngestionError`.
- Existing plain text, Markdown, and PDF ingestion identity must remain hash- and offset-compatible.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_34_docx_html_email_ingestion.md:1` | Approved Phase 34 spec. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_34_docx_html_email_ingestion.md:1` | Active Phase 34 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |

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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_34_docx_html_email_ingestion.md docs/boards/README.md docs/boards/phase_34_docx_html_email_ingestion.md`; `rg -n "Phase 34|phase_34_docx_html_email_ingestion.md|BOARD OPEN|Step 1|approved" docs/boards/README.md PROGRESS.md docs/specs/phase_34_docx_html_email_ingestion.md docs/boards/phase_34_docx_html_email_ingestion.md`; `cmp -s AGENTS.md CLAUDE.md` returned `1` because of pre-existing local `AGENTS.md` drift unrelated to this phase. | PASS with noted unrelated drift | 2026-05-29 |

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

### 2026-05-29 - Session 1

- Resumed after operator continued from the Phase 34 spec draft.
- Completed: approved the Phase 34 spec for implementation, opened this board, pinned Phase 34 open-question resolutions, and updated active phase tracking.
- Issues found: none for Phase 34 board opening.
- Tests: board-opening verification passed as recorded above, with the known unrelated `AGENTS.md`/`CLAUDE.md` drift preserved outside this phase.
- Next: Step 1 - add format-detection and compatibility tests.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: _(pending implementation)_
- Deferred: _(pending implementation)_
- Added beyond spec: _(pending implementation)_

### Lessons for downstream phases

- _(pending implementation)_
