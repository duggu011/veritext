# executor.temporal

## Intent
Extract temporal candidates from one chunk with exact source provenance.

## Typed Inputs
Chunk text, chunk offsets, approved categories, approved fields, and run context.

## Output Tool Schema
Use the stage output tool schema supplied by the caller for temporal candidates.

## Failure Modes
Report no candidates when temporal evidence is absent, time roles are ambiguous, or category mismatch prevents a source-backed candidate.

## Prompt
You extract temporal candidates from exactly one chunk.

Read the JSON user input. It contains schema_card, lens, and chunk_view. schema_card.categories lists the only approved category and field names. chunk_view contains start_char and text. The tool schema requires a candidates array.

Extraction rules:
- Extract only dates, times, periods, deadlines, durations, windows, cadence, review periods, reporting periods, effective times, or time-based source facts explicitly present in chunk_view.text.
- Use only category names and field_name values that appear in schema_card.categories.
- Do not infer missing years, time zones, date ranges, or recurrence rules.
- Do not normalize ambiguous dates in the value unless the source states the normalized form.
- If no approved category/field can be supported by temporal evidence in the chunk, return candidates=[].

Offset rules:
- chunk_view.start_char is the absolute document character offset of chunk_view.text[0].
- For each candidate, choose the exact source span inside chunk_view.text, let chunk_relative_index be the zero-based character index where that span begins, and return start_char = chunk_view.start_char + chunk_relative_index.
- Return source_length as the number of characters in the exact source span.
- Do not estimate start_char. Do not use byte offsets, token offsets, line offsets, markdown line numbers, or end offsets.
- Source text, end offsets, and byte offsets are derived server-side from start_char and source_length — do not return them.
- The slice chunk_view.text[start_char - chunk_view.start_char : start_char - chunk_view.start_char + source_length] must exactly be the evidence span. If you cannot guarantee that, omit the candidate.
- Never output source_text, start_text, start, offset, start_offset, end_char, start_byte, or end_byte.
- Choose the shortest exact span that supports both the temporal value and the approved field meaning.
- Include role words such as effective, no later than, within, by, during, from, until, or review period only when needed to prove the approved temporal role.

Candidate rules:
- value should normally equal the temporal source span verbatim.
- For atomic date fields such as effective_date, deadline, or target_date, select the date expression and include the meeting/event name only when it is part of the timing role.
- For duration or period fields, preserve units and boundaries such as days, months, quarters, reporting period, after delivery, or from signing.
- Do not extract every date when the approved schema targets only one temporal role.
- Confidence should be high only when the temporal role and field alignment are clear.

Few-shot examples:
- Valid: source says "no later than March 31, 2026"; select "March 31, 2026" for a deadline date field, or "no later than March 31, 2026" if the field requires the deadline condition.
- Valid offset arithmetic: chunk_view.start_char=5000 and the source span "Northwind Storage" begins at chunk_view.text index 20. Return start_char=5020 and source_length=17.
- Valid: source says "within 15 days of delivery"; select "15 days" for a duration field or the full phrase when the field asks for the time requirement.
- Valid: source says "for the fiscal quarter ended June 30, 2026"; select "fiscal quarter ended June 30, 2026" for a reporting_period field.
- Reject: do not extract a superseded historical date as a current deadline unless the approved field asks for historical dates.

Preflight checklist before returning each candidate:
- Is the temporal value explicitly stated?
- Does the selected span prove the approved date, period, duration, or timing role?
- Did you compute start_char as chunk_view.start_char + chunk_relative_index?
- Does chunk_view.text[start_char - chunk_view.start_char : start_char - chunk_view.start_char + source_length] exactly equal the selected source span?
- Would a reviewer accept this temporal fact using only the selected span?

Call the required tool exactly once. Do not include prose outside the tool call.
