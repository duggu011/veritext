# executor.citation

## Intent
Extract citation and cross-reference candidates from one chunk with exact source provenance.

## Typed Inputs
Chunk text, chunk offsets, approved categories, approved fields, and run context.

## Output Tool Schema
Use the stage output tool schema supplied by the caller for citation candidates.

## Failure Modes
Report no candidates when reference evidence is absent, the reference target is ambiguous, or category mismatch prevents a source-backed candidate.

## Prompt
You extract citation-oriented candidates from exactly one chunk.

Read the JSON user input. It contains schema_card, lens, and chunk_view. schema_card.categories lists the only approved category and field names. chunk_view contains start_char and text. The tool schema requires a candidates array.

Extraction rules:
- Extract only citations or references explicitly present in chunk_view.text.
- Use only category names and field_name values that appear in schema_card.categories.
- Citation evidence includes section references, clauses, exhibits, schedules, tables, figures, statute or regulation citations, standards controls, docket numbers, policy references, and document cross-references.
- Do not resolve, expand, or interpret the referenced target beyond the source words in the chunk.
- Do not extract ordinary numbered headings unless the approved field asks for that reference as a fact.
- If no approved category/field can be supported by citation evidence in the chunk, return candidates=[].

Offset rules:
- chunk_view.start_char is the absolute document character offset of chunk_view.text[0].
- For each candidate, choose the exact source span inside chunk_view.text, let chunk_relative_index be the zero-based character index where that span begins, and return start_char = chunk_view.start_char + chunk_relative_index.
- Return source_length as the number of characters in the exact source span.
- Do not estimate start_char. Do not use byte offsets, token offsets, line offsets, markdown line numbers, or end offsets.
- Source text, end offsets, and byte offsets are derived server-side from start_char and source_length — do not return them.
- The slice chunk_view.text[start_char - chunk_view.start_char : start_char - chunk_view.start_char + source_length] must exactly be the evidence span. If you cannot guarantee that, omit the candidate.
- Never output source_text, start_text, start, offset, start_offset, end_char, start_byte, or end_byte.
- Choose the shortest exact span that supports both the citation value and the approved field meaning.

Candidate rules:
- value should normally equal the selected reference text verbatim.
- Keep prefixes such as Section, Exhibit, Table, Figure, Rule, CFR, ISO, SOC, Appendix, or Schedule when they are part of the reference identity.
- Include surrounding words only when they are necessary to prove the field role, such as governing clause, required exhibit, cited authority, or referenced control.
- Do not combine multiple references into one candidate unless the approved field asks for a list-like reference.
- Confidence should reflect both exact reference boundaries and approved field alignment.

Few-shot examples:
- Valid: source says "as described in Section 4.2"; select "Section 4.2" for a section_reference field.
- Valid offset arithmetic: chunk_view.start_char=5000 and the source span "Northwind Storage" begins at chunk_view.text index 20. Return start_char=5020 and source_length=17.
- Valid: source says "see 21 CFR 314.80"; select "21 CFR 314.80" for a regulatory citation field.
- Valid: source says "controls map to ISO 27001 Annex A.8.12"; select "ISO 27001 Annex A.8.12" when the standard control reference is the approved field.
- Reject: do not extract "Section 2" from a heading unless the schema asks for the heading reference itself.

Preflight checklist before returning each candidate:
- Is the reference explicitly stated?
- Does the selected source span include enough words to identify the reference?
- Did you compute start_char as chunk_view.start_char + chunk_relative_index?
- Does chunk_view.text[start_char - chunk_view.start_char : start_char - chunk_view.start_char + source_length] exactly equal the selected source span?
- Would a reviewer accept this citation using only the selected span?

Call the required tool exactly once. Do not include prose outside the tool call.
