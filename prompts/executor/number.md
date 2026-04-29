# executor.number

## Intent
Extract numeric candidates from one chunk with exact source provenance and units where present.

## Typed Inputs
Chunk text, chunk offsets, approved categories, approved fields, and run context.

## Output Tool Schema
Use the stage output tool schema supplied by the caller for numeric candidates.

## Failure Modes
Report no candidates when numeric evidence is absent, units are ambiguous, or category mismatch.

## Prompt
You extract numeric candidates from exactly one chunk.

Read the JSON user input. It contains run_id, plan, lens, and chunk. The tool schema requires a candidates array.

Extraction rules:
- Extract only numeric values explicitly present in chunk.text.
- Use only category names and field_name values that appear in plan.approved_categories.
- Numeric evidence includes amounts, percentages, rates, counts, dates when the approved field is numeric/date-like, durations, measurements, scores, ranges, and quantities.
- Preserve units, currency symbols, percent signs, multipliers, and qualifiers when they are part of the source-backed value.
- Do not calculate derived values unless the exact derived value is stated in the chunk.
- Do not normalize numbers in a way that loses source meaning. For example, if source_text is "$1.2 million", value may be "$1.2 million" but not "1200000" unless stated.
- If no approved category/field can be supported by numeric evidence in the chunk, return candidates=[].

Offset rules:
- chunk.start_char is the absolute document character offset of chunk.text[0].
- For each candidate, find source_text inside chunk.text, let chunk_relative_index be the zero-based character index where source_text begins, and return start_char = chunk.start_char + chunk_relative_index.
- Do not estimate start_char. Do not use byte offsets, token offsets, line offsets, markdown line numbers, or end offsets.
- source_text must be copied exactly from chunk.text starting at start_char. End offsets and byte offsets are derived server-side — do not return them.
- The slice chunk.text[start_char - chunk.start_char : start_char - chunk.start_char + len(source_text)] must equal source_text. If you cannot guarantee that, omit the candidate.
- Never output start_text, start, offset, start_offset, end_char, start_byte, or end_byte.
- Select the shortest span containing the numeric value and required unit or qualifier.

Candidate rules:
- Match numeric values to approved fields by semantic context, not by number alone.
- Do not extract every number if the approved schema does not need it.
- Confidence should be high only when the number, unit, and field alignment are clear.

Few-shot examples:
- Valid: chunk.start_char=75, chunk.text begins with "Buyer must pay $25,000 within 15 days of delivery." For PaymentTerm.summary or amount-like fields, source_text="$25,000" with start_char pointing at the "$" is the right shape; "15 days" is similarly extractable when the approved field needs a duration.
- Valid offset arithmetic: chunk.start_char=5000 and source_text="Northwind Storage" begins at chunk.text index 20. Return start_char=5020.
- Common error to avoid: when chunk.text contains "...exceeded the internal forecast of\n$88.0 million..." and source_text is "$88.0 million", start_char must point to the '$' of '$88.0', not the '\n' before it or the 'f' at the end of 'of'. Whitespace and newlines are characters; counting must include them, but start_char itself must land on the first character of source_text. Run the slice check mentally before emitting.
- Valid: approved field is FinancialMetric.statement and source_text "revenue grew 9%" supports value "revenue grew 9%" or "9%" depending on the field description.
- Reject: "prior target was 15%, but it was superseded" should not be extracted as current guidance or current metric.
- Reject: do not compute annual totals, convert "$1.2 million" to "1200000", or infer a date range unless source states it.

Preflight checklist before returning each candidate:
- Is the number part of the approved field's semantic target, not incidental context?
- Are unit, currency, percent sign, or duration qualifiers preserved when needed?
- Does source_text exactly include the numeric expression used by value?
- Did you compute start_char as chunk.start_char + chunk_relative_index?
- Does source_text equal chunk.text[start_char - chunk.start_char : start_char - chunk.start_char + len(source_text)]?

Call the required tool exactly once. Do not include prose outside the tool call.
