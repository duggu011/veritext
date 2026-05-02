# Evaluation case-file annotation conventions

These rules govern every `case.json` under `evals/fixtures/`. They are
domain-agnostic and apply to any future fixture. Their goal is to make the
provenance gate (`min_provenance_recall: 1.0`) mathematically achievable by
removing per-instance ambiguity from the ground truth, without weakening the
pipeline's byte-exact provenance bar.

## Why these rules exist

The pipeline scores a data point as exact-provenance only when its source span
matches the case file byte-for-byte. If the same `(category, field_name)` pair
is annotated with different span widths across instances — sometimes the bare
value, sometimes the full sentence — no extractor can satisfy the gate, because
no rule the model could derive at inference time would pick the right width
for each instance.

These conventions make the choice mechanical and consistent.

## Span-text rule (universal)

For every expected entry:

- **`source_text` MUST equal the source byte slice `[start_char, end_char)`
  exactly.** No leading or trailing whitespace, no punctuation reshaping.
- **`start_byte` / `end_byte` MUST equal the UTF-8 byte offsets of the chosen
  character range.**
- **`value` MUST either equal `source_text` byte-for-byte, or be a
  normalization of `source_text` that differs only in casing, noun-form, or
  controlled-vocabulary substitution.** When `value` differs from `source_text`,
  every content word in `value` must trace to a word inside `source_text`.

Under this rule, the matcher (`(category, field_name, normalize(value))`)
remains insensitive to casing, but the provenance check sees a unique span
slice for every instance.

## Field-type span widths

Classify each field into exactly one of four types. The type determines span
width.

### Type A — atomic value / qualifier / attribute

The field names a discrete quantity, identifier, date, percentage, currency,
duration, named entity, qualifier, attribute, or short label whose entire
textual form fits in one contiguous source token sequence.

Examples by intent: numeric values, dates, named parties, named facilities,
issuing authorities, transaction amounts, change percentages with their
direction word, prior-period values that carry a period suffix, metric
qualifiers, and operational profile details.

**Span = the smallest contiguous source slice that contains the value's text
verbatim** (after case-fold normalization).

- The span MUST NOT include the field's own role qualifier when the field name
  already carries that role. Drop "forecast" from `forecast_value` spans,
  "margin" from `margin` spans, "target" from `target_value` spans, "from" or
  "to" prepositions from `prior_rate` / `new_rate` spans.
- The span MAY include directional or sign wording when that wording is part
  of the value's textual identity in the source (e.g. `"up 17.4%"` for a
  signed change percentage where `value="up 17.4%"`).
- The span MUST include period-of-time wording when the field's name does not
  carry the period (e.g. `prior_period_value="$410.8 million in Q1 2025"`
  keeps "in Q1 2025" because no field name encodes the prior period itself).
- For effective timing fields, the span MUST include an immediately attached
  named event context when the action becomes effective at that named event,
  e.g. `effective_date="June 18, 2026 Annual Meeting"` keeps "Annual Meeting"
  because the source timing is the meeting, not just the calendar date.
- For qualifier fields such as `notable_qualifier`, span is the qualifier
  phrase or clause itself, not the whole metric sentence.
- For attribute/detail fields such as `asset_detail`, span is the tight
  attribute phrase when the source states a static profile like
  `"Northwind operates 1.85 gigawatt-hours across seven U.S. states."`;
  the span is `"1.85 gigawatt-hours across seven U.S. states"`.

### Type B — label / category term

The field names a labelling concept (`metric_name`, `event_type`,
`change_type`, `exposure_type`, `risk_type`, etc.) where the value is a noun
or noun-phrase classifying the surrounding statement.

**Span = the smallest contiguous source slice whose words map to every content
word in the value.**

- When the value is verbatim in the source, span equals that verbatim
  occurrence.
- When the value is a normalization (different capitalization, different
  noun-form, controlled vocabulary), span equals the source phrase that maps
  to it word-for-word — never the surrounding sentence.
- The span MUST NOT include the surrounding clause, the value's measurement,
  or the action's date even when they sit in the same sentence.

Examples:
- `metric_name="Adjusted EBITDA"` (verbatim source) → span `"Adjusted EBITDA"`
- `metric_name="Revenue"` (source has lowercase `"revenue"`) → span `"revenue"`
- `change_type="appointment"` (source has `"appointed"`) → span `"appointed"`
- `event_type="Acquisition approval"` (source has `"approved acquiring"`) →
  span `"approved acquiring"`

### Type C — entity / role / title

The field names a person, organization, asset, or title held by a person.

**Span = the bare entity name or title.**

- For person and party fields, span is the bare name without surrounding
  action verbs, role prefixes, or locations.
- For role / title fields, span is the bare title without the appointing verb
  and without the named holder.
- For named-entity fields (facility, party, issuing authority), span is the
  bare entity without any "in <location>" qualifier appended in the source.

Exception: when the field's name explicitly bundles role + name (for example
a hypothetical `speaker_with_role` field), the span includes both. The default
is bare name.

### Type D — sentence / statement / event detail clause

The field names a free-text statement (`summary`, `statement`,
`description`, `condition`) or an event detail field whose source support is
the whole event sentence rather than a detachable attribute.

**Span = a contiguous source slice that begins at the first non-whitespace
character of a sentence (or stand-alone clause) and ends at the closing
punctuation, inclusive.**

- `value` MUST equal `source_text` verbatim. No paraphrase. No leading-article
  trimming. No trailing-period trimming.
- One sentence supports one Type D datapoint per field. If the source sentence
  contains two distinct events the schema asks about (for example two separate
  asset-detail events in one sentence), split into two contiguous clauses and
  emit two datapoints, each with its own clause-bounded span.
- `asset_detail` is Type D only when the field captures an event-level asset
  detail whose support is the whole sentence or standalone clause, such as an
  asset commencing operation and contributing output. Static operational
  profiles remain Type A attribute spans.

## Mechanical procedure for annotating a fixture

For each datapoint:

1. Identify the field's type (A / B / C / D) from the field's intent.
2. Locate the value's textual occurrence(s) in the source.
3. Apply the Type's span rule.
4. Set `start_char` / `end_char` to the chosen char range.
5. Compute `start_byte` / `end_byte` as the UTF-8 byte offsets of that range
   (`start_byte = len(source[:start_char].encode("utf-8"))`, similarly for
   end).
6. Set `source_text = source[start_char:end_char]`.
7. Set `value`: equal to `source_text` for Type D; equal to the chosen
   normalization for Types A / B / C.
8. Verify `source_text` decodes the same byte slice and that `value` either
   equals `source_text` or normalizes to it case-fold-equal with all content
   words mapped.

## What this rule does NOT do

- It does not change the pipeline's byte-exact provenance bar.
- It does not change the eval gate threshold (still `1.0`).
- It does not change the executor prompt's "shortest exact span supporting
  field meaning" rule — the conventions align with that prompt.
- It does not paper over genuine extractor errors. A pipeline that emits a
  span crossing section headers, including unrelated context, or omitting
  required value words still fails the gate.

## Auditing existing fixtures

When a fixture predates these conventions, audit each entry against the four
types and rewrite spans that violate the type's width rule. Keep value text
unchanged when the value already case-fold-matches the corrected span; rewrite
value to the verbatim normalization when it does not.

After re-annotation, re-score the most recent pipeline output against the
new case file with no LLM calls. Any entry that newly fails was either an
extractor bug masked by the prior inconsistency or an annotator choice that
needs a second look. Do not rerun the pipeline for re-annotation alone.
