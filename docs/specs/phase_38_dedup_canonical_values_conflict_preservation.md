# Phase 38 - Dedup, Canonical Values, and Conflict Preservation

Status: draft, not approved.

Date drafted: 2026-05-29
Date approved: not approved.

Roadmap sources: `docs/PROJECT_OVERVIEW.md` sections `5. Dedup` and
`8. Reconciler`, `docs/PROJECT_OVERVIEW.md` highest-leverage item 4,
`docs/phase_26_plus_roadmap.md`, `docs/boards/README.md`, `PROGRESS.md`, and
Phase 36-37 board/spec/commits through `9975129`.

## Goal

Improve single-document duplicate handling and conflict auditability by adding
deterministic canonical value keys, cross-chunk duplicate merging, preserved
dedup clusters, data-point provenance arrays, and explicit unresolved conflict
metadata.

The central outcome is that duplicate candidates merge without losing source
spans, canonical and verbatim values remain visible, and conflicting verified
candidates are surfaced as conflict-marked outputs or explicit invariant
failures instead of disappearing through silent rejection.

## Non-Goals

- Do not implement cross-document reconciliation in Phase 38.
- Do not add REST APIs, web UI, Docker, CI/CD, vector databases, embeddings,
  fine-tuning hooks, or agent frameworks.
- Do not route normalization through an LLM.
- Do not use document-specific tokens, company names, fixture strings, market
  sectors, or proper nouns as dedup or conflict rules.
- Do not weaken exact source spans, byte offsets, character offsets, source
  hashes, Pydantic contracts, audit logging, forced tool use, or no-silent-drop
  rejection accounting.
- Do not change report output by removing existing fields or changing
  `report.v2`.
- Do not make `relation`, `obligation`, `condition`, or `exception` executable.

## Domain-Scope Alignment

Phase 38 remains domain-neutral. Canonical value keys may normalize general
forms such as whitespace, case, punctuation, numbers, dates, quantities,
entities, and citations only when the transformation is deterministic and
auditable from the source-backed value metadata.

Conflict preservation is source-role and schema-role based, not industry based.
The same category/field conflict rules should work for legal deadlines, SEC
amounts, clinical dosage values, insurance limits, procurement dates, standards
controls, and scientific findings.

## Current State

Dedup currently lives in `src/extractor/executor/dedup.py` and groups by:

```text
(chunk_id, category, field_name, source_span.text, value)
```

That means an overlapping chunk can preserve the same candidate twice because
`chunk_id` differs. It also misses deterministic canonical duplicates such as
case, punctuation, quote, dash, numeric, or canonical label differences.

The reconciler currently returns ID-only `groups` and `rejected` decisions. The
server materializes final `DataPoint` values from the selected source
candidate. Phase 36 added `value_verbatim`, `value_canonical`, `value_kind`,
and normalization metadata to `LensCandidate` and `DataPoint`. Phase 37 added
new executable lenses without changing dedup or reconciler semantics.

`DataPoint` currently preserves one selected `source_span` and the contributing
candidate IDs, but it does not expose all contributor source spans as a typed
provenance array. It also has no conflict metadata for unresolved same-field
disagreements.

## Contract Changes

Expected additive changes:

- Add a typed canonical value key contract that records:
  - `kind`
  - `key`
  - `source`
  - optional `policy_id`
  - optional `policy_version`
- Add a typed dedup cluster contract that records:
  - `primary_candidate_id`
  - `merged_candidate_ids`
  - `all_candidate_ids`
  - `canonical_key`
  - `source_span_count`
- Preserve the existing `deduplicate_candidates()` return shape unless tests
  prove a split helper is necessary; new cluster detail may be exposed through
  a separate helper to avoid breaking existing callers.
- Add additive `DataPoint` fields with legacy-safe defaults:
  - `supporting_source_spans: tuple[SourceSpan, ...] = ()`
  - `conflict_status: "none" | "unresolved" = "none"`
  - `conflict_group_id: str | None = None`
  - `conflict_reason: str | None = None`
- Preserve `source_span` as the selected primary source span for backward
  compatibility.
- Preserve `contributing_candidate_ids`, `critic_report_ids`, and
  `verifier_report_ids` as existing audit join keys.
- Add no new required fields to existing audit payloads.

## Canonical Value Rules

Canonical keys must be deterministic and auditable:

- Use `value_canonical` when `normalization_status == "canonicalized"`.
- Use `value_verbatim` when `normalization_status == "verbatim_only"`.
- Otherwise use `value`.
- Collapse internal whitespace.
- Case-fold text.
- Normalize Unicode compatibility forms.
- Normalize simple surrounding punctuation, quote variants, and dash variants.
- Preserve exact `value_verbatim` and source span text even when the key
  normalizes the value.
- Reject or fall back to text keys for ambiguous number, date, duration, or
  quantity forms rather than guessing.

Numeric/date/quantity canonicalization may be conservative in Phase 38. The
minimum acceptable behavior is deterministic equivalence for values already
canonicalized by Phase 36 metadata and safe text normalization for raw values.

## Dedup Behavior

Dedup must:

- Merge exact duplicates across overlapping chunks when category, field, lens,
  selected canonical key, and absolute source span identity agree.
- Merge deterministic canonical duplicates when category, field, lens, and
  selected canonical key agree and the values are safely comparable.
- Drop `chunk_id` from the primary dedup identity so overlapping chunks do not
  prevent a merge.
- Preserve every merged candidate ID in a cluster record.
- Emit dedup rejections for merged duplicate candidates with
  `duplicate_candidate` reasons that name the selected primary candidate.
- Keep the stable primary selection deterministic.
- Avoid merging candidates that differ by category or field.
- Avoid merging unresolved conflicting values. Those belong to reconciler
  conflict preservation, not dedup.

## Reconciler Conflict Preservation

The reconciler must:

- Continue using ID-only LLM output for normal groups and rejections.
- Continue deriving final values, source spans, confidence, normalization
  metadata, critic report IDs, and verifier report IDs on the server.
- Build `supporting_source_spans` from all contributing candidates in a kept
  group.
- Detect unresolved same-category/same-field conflicts using canonical keys
  after materialization.
- Mark all unresolved conflicting data points with the same stable
  `conflict_group_id`.
- Set `conflict_status` to `unresolved` and `conflict_reason` to an explicit
  reason when same-field verified values cannot be safely merged or resolved.
- Reject reconciler output that silently rejects a verified candidate when it
  conflicts with a kept same-category/same-field value and the candidate is
  otherwise schema-valid.
- Keep schema violations explicit as rejections.
- Preserve existing omitted-candidate rejection behavior for non-conflicting
  candidates.

Conflict preservation should use deterministic server validation and
materialization. Phase 38 should not change the static reconciler prompt body
unless a test proves the current ID-only prompt prevents invariant-safe
preservation. If such a prompt change becomes necessary, stop and ask the
operator before editing prompt text.

## Audit and Provenance Effects

- Existing audit rows and report payloads from old runs must remain readable.
- New `DataPoint` fields must serialize into audit and report payloads without
  requiring audit schema migrations.
- Compact audit inspection should show conflict status, conflict group IDs,
  supporting source span count, and normalization metadata for data points.
- Dedup inspection counts should distinguish merged duplicate candidates from
  canonical candidates without losing candidate rejection trails.
- Every merged duplicate or conflict-marked value must remain traceable to
  exact source spans.

## Configuration Changes

No new runtime tuning keys are planned for Phase 38.

If tests show canonical key behavior needs configuration, it must be typed,
defaulted, and stored under `config/default.yaml`; it must not be hardcoded in
source or tests as fixture-specific behavior.

## Prompt Changes

No static prompt body changes are planned for Phase 38.

The current reconciler prompt already requires every candidate to be accounted
for and uses ID-only output. Phase 38 should enforce conflict preservation in
server validation and materialization. Prompt edits are a stop condition unless
the operator explicitly authorizes them.

## Tests and Evaluation Gates

Narrow tests:

- Contract tests proving new `DataPoint` and canonical-key fields are additive
  and legacy payloads remain readable.
- Dedup tests proving cross-chunk duplicates merge without losing source spans.
- Dedup tests proving deterministic canonical keys merge safe duplicates and
  do not merge distinct conflicts.
- Dedup rejection tests proving merged candidates record stable
  `duplicate_candidate` trails.
- Reconciler tests proving `supporting_source_spans` includes every contributor
  span in a kept group.
- Reconciler tests proving same-field unresolved conflicts become
  conflict-marked data points.
- Reconciler validation tests proving silent rejection of otherwise valid
  conflicting verified candidates is rejected or retried.
- Audit inspection tests proving conflict and provenance fields are visible.
- Reporter/eval tests proving additive `DataPoint` fields do not break reports
  or existing static fixtures.

Regression and final gates:

- Existing unit tests for contracts, dedup, reconciler, audit store, audit
  inspection, reporter, orchestrator, and evaluation scoring.
- `git diff --exit-code -- prompts`
- `make test`
- `make lint`
- `make smoke`
- `git diff --check`
- Phase 29 and Phase 30 evaluation suites.
- Phase 31 adversarial, mutation, and calibration suites.
- Phase 37 expanded-lens evaluation suite.

Evaluation acceptance:

- No regression in Phase 29, Phase 30, Phase 31, or Phase 37 precision, recall,
  F1, provenance recall, false positives, false negatives, or invariant
  violations.
- New dedup/conflict fixtures or tests must demonstrate duplicate merging and
  conflict preservation without document-specific source patches.

## Implementation Order

1. Add RED tests for canonical key contracts, legacy payload readability,
   cross-chunk dedup, canonical duplicate dedup, and no-merge conflict cases.
2. Add canonical value key helpers and dedup cluster contracts.
3. Extend dedup to drop `chunk_id` from duplicate identity where safe, use
   canonical keys, preserve deterministic clusters, and keep stable rejection
   trails.
4. Add RED tests for `DataPoint.supporting_source_spans` and additive conflict
   metadata.
5. Extend `DataPoint` and reconciler materialization to populate supporting
   source spans from contributing candidates.
6. Add reconciler conflict detection and stable unresolved conflict metadata.
7. Add validation or retry complaints for silent rejection of otherwise valid
   conflicting candidates.
8. Extend audit inspection and report/eval tests for additive fields.
9. Add focused source-neutral dedup/conflict fixture coverage if needed for
   evaluation acceptance.
10. Run final project, prompt-neutrality, smoke, lint, and evaluation gates.
11. Fill the Phase 38 board summary and stop for operator acceptance.

## Open Questions Before Approval

_(None.)_
