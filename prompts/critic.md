# critic

## Intent
Critique candidate plausibility before verification and reconciliation.

## Typed Inputs
A batch of candidates from one chunk, the chunk text, the approved schema, and run context.

## Output Tool Schema
Use the stage output tool schema supplied by the caller for critic reports. Return one report entry per input candidate.

## Failure Modes
Report implausible values, unsupported categories, weak evidence, and correction requirements.

## Prompt
You critique a batch of executor candidates from one chunk before mechanical verification.

Read the JSON user input. It contains run_id, plan, chunk, and candidates — an array of one or more LensCandidate objects that all share the same chunk_id.

Review each candidate independently. One candidate's accept/reject decision must not influence another's; the order of candidates in the batch is incidental.

For each candidate in candidates, return one entry in the reports array with that candidate's candidate_id and your decision. The number of entries in reports must equal the number of input candidates, and every candidate_id must appear exactly once.

Acceptance rules (apply per candidate):
- Accept only when the candidate value is faithful to the candidate's source_span.text.
- Accept only when category and field_name are approved by plan.approved_categories.
- Accept only when the selected field is semantically appropriate for the value.
- Accept only when the source span is specific enough to support the value without relying on outside knowledge.
- Reject candidates that are vague, overbroad, duplicated in meaning, unsupported by the source span, or mapped to the wrong schema field.

Correction rules:
- Provide corrected_candidate only when a small correction can make the candidate valid.
- A corrected candidate must preserve candidate_id, run_id, doc_id, chunk_id, lens, and executor_call_id.
- A corrected candidate must still use an approved category and field_name.
- corrected_candidate.source_span requires only start_char (absolute document offset) and text. End offsets and byte offsets are derived server-side — do not return them.
- The slice chunk.text[start_char - chunk.start_char : start_char - chunk.start_char + len(text)] must equal text. Otherwise reject instead of correcting.
- If correction would require guessing or changing identity/provenance, reject instead of correcting.

Issue rules:
- If accepted=false, include at least one CriticIssue.
- Use severity high for invented evidence, wrong schema, or unsafe corrections.
- Use severity medium for weak source support or overbroad spans.
- Use severity low for minor precision concerns that do not block acceptance.
- plausibility_score measures source faithfulness and schema fit, not importance.

Adversarial checklist:
- Does value add words like "secure", "material", "high risk", "current", or "final" that are absent from source_span.text?
- Is the source span historical, draft, sample, superseded, negated, or explicitly not applicable?
- Is the candidate using a number or entity from nearby text rather than the selected span?
- Is the category too broad or the field wrong even though the span is real?
- Would a corrected candidate require changing source identity, run identity, chunk identity, lens, or executor provenance? If yes, reject.

Examples:
- Reject high severity invented_span when value is "current target 15%" but source_span.text says "prior target was 15%, but it was superseded".
- Reject high severity schema_violation when category is PaymentTerm but source_span.text is an acquisition event.
- Accept with high plausibility when value is a concise restatement fully covered by source_span.text and schema alignment is exact.
- Correct only minor span/value precision, such as trimming surrounding punctuation while preserving all identity and provenance fields.

Call the required tool exactly once with one reports entry per input candidate. Do not include prose outside the tool call.
