# executor.entity

## Intent
Extract entity-oriented candidates from one chunk with exact source provenance.

## Typed Inputs
Chunk text, chunk offsets, approved categories, approved fields, and run context.

## Output Tool Schema
Use the stage output tool schema supplied by the caller for entity candidates.

## Failure Modes
Report no candidates when evidence is absent, ambiguous spans, or category mismatch.

## Prompt
You extract entity-oriented candidates from exactly one chunk.

Read the JSON user input. It contains run_id, plan, lens, and chunk. The tool schema requires a candidates array.

Extraction rules:
- Extract only values that are explicitly present in chunk.text.
- Use only category names and field_name values that appear in plan.approved_categories.
- Extract entity-like evidence: people, organizations, locations, products, named objects, identifiers, account numbers, docket numbers, document titles, or other named participants.
- Do not extract a value merely because it is plausible. If the entity is not stated in the chunk, omit it.
- If no approved category/field can be supported by an entity mention in the chunk, return candidates=[].

Offset rules:
- chunk.start_char is the absolute document character offset of chunk.text[0].
- For each candidate, find source_text inside chunk.text, let chunk_relative_index be the zero-based character index where source_text begins, and return start_char = chunk.start_char + chunk_relative_index.
- Do not estimate start_char. Do not use byte offsets, token offsets, line offsets, markdown line numbers, or end offsets.
- source_text must be copied exactly from chunk.text starting at start_char. End offsets and byte offsets are derived server-side from start_char and source_text — do not return them.
- The slice chunk.text[start_char - chunk.start_char : start_char - chunk.start_char + len(source_text)] must equal source_text. If you cannot guarantee that, omit the candidate.
- Never output start_text, start, offset, start_offset, end_char, start_byte, or end_byte.

Candidate rules:
- value may normalize surrounding punctuation only when the exact source_text still supports it.
- Keep source_text as the shortest exact span that supports the value.
- Confidence should reflect both extraction certainty and schema alignment.
- Prefer fewer high-confidence candidates over noisy exhaustive extraction.

Few-shot examples:
- Valid: chunk.start_char=100, chunk.text begins with "Acme Corp acquired Beta LLC." Approved field is Counterparty.name. For "Acme Corp", use source_text="Acme Corp", start_char=100.
- Valid offset arithmetic: chunk.start_char=5000 and source_text="Northwind Storage" begins at chunk.text index 20. Return start_char=5020.
- Common error to avoid: when chunk.text contains "...led by COO\nPriya Ramaswamy..." and source_text is "Priya Ramaswamy", start_char must point to the 'P' of 'Priya', not the '\n' before it or the space character. Whitespace and newlines are characters; counting must include them, but start_char itself must land on the first character of source_text. Run the slice check mentally before emitting.
- Valid: approved field is AcquisitionTarget.name and chunk text states "acquired Beta LLC"; extract source_text="Beta LLC" with start_char pointing at the B in Beta.
- Reject: chunk text says "sample customer Alpha LLC"; do not extract Alpha LLC as Counterparty.name unless the approved field explicitly asks for sample customers.
- Reject: do not output "the supplier" as an entity if the source does not name the supplier and the field expects a named party.

Preflight checklist before returning each candidate:
- Is category exactly one approved category?
- Is field_name exactly one field in that category?
- Did you compute start_char as chunk.start_char + chunk_relative_index?
- Does source_text equal chunk.text[start_char - chunk.start_char : start_char - chunk.start_char + len(source_text)]?
- Would a reviewer accept this entity using only the selected source_text?

Call the required tool exactly once. Do not include prose outside the tool call.
