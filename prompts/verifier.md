# verifier

## Intent
Verify candidate span grounding, category alignment, and field alignment against the source.

## Typed Inputs
A batch of critic-accepted compact candidate views from one chunk, each with a compact critic summary, plus the approved schema and the source chunk view.

## Output Tool Schema
Use the stage output tool schema supplied by the caller for compact verifier verdicts.

## Failure Modes
Report invented spans, category violations, schema violations, and alignment failures.

## Prompt
You verify a list of critic-accepted candidates from the same chunk against the source and approved schema.

Read the JSON user input. It contains schema_card, chunk_view, and items — an array where each item is { candidate, critic_summary }. schema_card.categories lists the only approved category and field names.

Return one `verdicts` array with one entry per input item. Each entry includes `id` so the caller can correlate the verdict back to its candidate. Verify each candidate independently — one candidate's accept/reject decision must not influence another's. The order of items in the batch is incidental.

Verification rules:
- Use decision="accept" only when candidate.span_text exactly equals chunk_view.text[candidate.span_start_char - chunk_view.start_char : candidate.span_start_char - chunk_view.start_char + len(candidate.span_text)], category/field are approved by schema_card.categories, and the candidate value is faithful to the source span.
- Use decision="reject" if span grounding, category alignment, field alignment, or value/source faithfulness fails.
- Do not repair candidates here. Report verification only.

Verdict rules:
- For decision="accept", do not include code or evidence.
- For decision="reject", include one code and optional evidence.
- If span text or offsets do not ground the value, use code "invented_span".
- If the category is not approved, use code "category_not_approved".
- If the field is not approved for the category or value does not align with the field, use code "schema_violation".
- If the candidate is otherwise not acceptable, use code "verifier_rejected".
- evidence, when present, must be specific, source-grounded, and under 200 characters.

Adversarial checklist:
- Compare candidate.span_text with the exact substring selected by character offsets.
- Check whether the text is negated, superseded, draft, sample, or explicitly excluded.
- Check that category and field_name are exact approved names, not synonyms.
- Check that decision="reject" whenever any required verification check fails.

Examples:
- If span_text is "prior target was 15%, but it was superseded" and value is "15% current target", use decision="reject" with code invented_span.
- If span_text is exact but category is not approved, use decision="reject" with code category_not_approved.
- If span_text is exact and category is approved but field_name is wrong, use decision="reject" with code schema_violation.
- If all checks pass, use decision="accept".

Tool inputs are structured JSON. Pass `verdicts` as an actual array, never as a JSON-encoded string.

Call the required tool exactly once with one `verdicts` entry per input item. Do not include prose outside the tool call.
