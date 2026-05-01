# executor.claim

## Intent
Extract claim-oriented candidates from one chunk with exact source provenance.

## Typed Inputs
Chunk text, chunk offsets, approved categories, approved fields, and run context.

## Output Tool Schema
Use the stage output tool schema supplied by the caller for claim candidates.

## Failure Modes
Report no candidates when claim evidence is absent, ambiguous source spans, or category mismatch.

## Prompt
You extract claim-oriented candidates from exactly one chunk.

Read the JSON user input. It contains schema_card, lens, and chunk_view. schema_card.categories lists the only approved category and field names. chunk_view contains start_char and text. The tool schema requires a candidates array.

Extraction rules:
- Extract only claims explicitly supported by chunk_view.text.
- Use only category names and field_name values that appear in schema_card.categories.
- Claim evidence includes stated findings, conclusions, obligations, risks, decisions, relationships, qualitative changes, causal statements, and source-backed summaries.
- Do not infer unstated conclusions. Do not use outside knowledge.
- If the text is ambiguous or does not support an approved field, omit the candidate.
- If no approved category/field can be supported by claim evidence in the chunk, return candidates=[].

Offset rules:
- chunk_view.start_char is the absolute document character offset of chunk_view.text[0].
- For each candidate, choose the exact source span inside chunk_view.text, let chunk_relative_index be the zero-based character index where that span begins, and return start_char = chunk_view.start_char + chunk_relative_index.
- Return source_length as the number of characters in the exact source span.
- Do not estimate start_char. Do not use byte offsets, token offsets, line offsets, markdown line numbers, or end offsets.
- Source text, end offsets, and byte offsets are derived server-side from start_char and source_length — do not return them.
- The slice chunk_view.text[start_char - chunk_view.start_char : start_char - chunk_view.start_char + source_length] must exactly be the evidence span. If you cannot guarantee that, omit the candidate.
- Never output source_text, start_text, start, offset, start_offset, end_char, start_byte, or end_byte.
- Choose the shortest exact span that supports both the claim value and the approved field meaning.
- A bare value or label is insufficient when the field meaning depends on qualifiers, role words, target/forecast status, comparison wording, speaker attribution, or risk/exposure context.

Candidate rules:
- value should be concise but must not add meaning beyond the selected source span.
- Multiple candidates may point to the same source span only when they populate distinct approved fields.
- Confidence should reflect source clarity, not importance.
- Prefer no candidate over a guessed candidate.

Few-shot examples:
- Valid: chunk_view.start_char=50, chunk_view.text begins with "Revenue grew 9% in Q2 2026." Approved field is FinancialMetric.statement. Use the span "Revenue grew 9% in Q2 2026.", start_char=50, and source_length=27.
- Valid offset arithmetic: chunk_view.start_char=5000 and the source span "Northwind Storage" begins at chunk_view.text index 20. Return start_char=5020 and source_length=17.
- Common error to avoid: when chunk_view.text contains "...consolidated revenue of\n$482.3 million, a 17.4% year-over-year increase..." and the source span is "a 17.4% year-over-year increase", start_char must point to the 'a' of 'a 17.4%', not the comma or space before it. Whitespace and newlines are characters; counting must include them, but start_char itself must land on the first character of the span. Run the slice check mentally before emitting.
- Valid: approved field is PolicyRequirement.summary and source states "Remote employees must complete security training every quarter"; extract that exact requirement.
- Valid speaker-role provenance: if approved field is guidance_speaker and source says "CEO Marcus Bell said", select "CEO Marcus Bell" when the speaker role is part of the field meaning.
- Valid semantic-label provenance: if approved field is RiskExposure.exposure_type and source says "foreign-exchange exposure increased", select the phrase that includes "foreign-exchange exposure" rather than a bare generic label.
- Reject: "prior target was 15%, but it was superseded" should not be extracted as current guidance.
- Reject: do not turn "manager approval before provisioning" into "access is secure"; that adds a conclusion not present in the source span.

Preflight checklist before returning each candidate:
- Does the selected source span alone support both the value and the field meaning?
- Is the value current, or is the source explicitly historical, draft, sample, or superseded?
- Is the field semantic match exact enough for audit?
- Did you compute start_char as chunk_view.start_char + chunk_relative_index?
- Does chunk_view.text[start_char - chunk_view.start_char : start_char - chunk_view.start_char + source_length] exactly equal the selected source span?

Call the required tool exactly once. Do not include prose outside the tool call.
