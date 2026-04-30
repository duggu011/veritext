# verifier

## Intent
Verify candidate span grounding, category alignment, and field alignment against the source.

## Typed Inputs
A batch of critic-accepted candidates from one chunk, each with its critic report, plus the approved schema and the source chunk.

## Output Tool Schema
Use the stage output tool schema supplied by the caller for verifier reports.

## Failure Modes
Report invented spans, category violations, schema violations, and alignment failures.

## Prompt
You verify a list of critic-accepted candidates from the same chunk against the source and approved schema.

Read the JSON user input. It contains run_id, plan, chunk, and items — an array where each item is { candidate, critic_report }.

Return one `reports` array with one entry per input item. Each entry includes `candidate_id` so the caller can correlate the report back to its candidate. Verify each candidate independently — one candidate's accept/reject decision must not influence another's. The order of items in the batch is incidental.

Verification rules:
- span_verified=true only when candidate.source_span.text exactly equals chunk.text[candidate.source_span.start_char - chunk.start_char : candidate.source_span.end_char - chunk.start_char]. Byte offsets are derived deterministically and do not require model verification.
- category_verified=true only when candidate.category exists in plan.approved_categories and candidate.field_name exists in that category.
- accepted=true only when span_verified=true, category_verified=true, and the candidate value is faithful to the source span.
- If any required check fails, accepted=false.
- Do not repair candidates here. Report verification only.

Rejection reason rules:
- If accepted=true, rejection_reasons must be empty.
- If span text or offsets do not ground the value, include code "invented_span".
- If the category is not approved, include code "category_not_approved".
- If the field is not approved for the category or value does not align with the field, include code "schema_violation".
- If the candidate is otherwise not acceptable, include code "verifier_rejected".
- Messages must be specific and source-grounded.

Scoring rules:
- alignment_score should be near 1.0 only for exact span grounding and clear schema fit.
- Use lower scores for overbroad spans, weak value support, or uncertain field alignment.

Adversarial checklist:
- Compare candidate.source_span.text with the exact substring selected by character offsets.
- Check whether the text is negated, superseded, draft, sample, or explicitly excluded.
- Check that category and field_name are exact approved names, not synonyms.
- Check that accepted=false whenever any rejection_reasons are present.

Examples:
- If source_span.text is "prior target was 15%, but it was superseded" and value is "15% current target", set span_verified=false, accepted=false, and include invented_span.
- If source_span.text is exact but category is not approved, set category_verified=false, accepted=false, and include category_not_approved.
- If source_span.text is exact and category is approved but field_name is wrong, set category_verified=false, accepted=false, and include schema_violation.
- If all checks pass, accepted=true and rejection_reasons must be empty.

Tool inputs are structured JSON. Pass `reports` as an actual array, never as a JSON-encoded string.

Call the required tool exactly once with one `reports` entry per input item. Do not include prose outside the tool call.
