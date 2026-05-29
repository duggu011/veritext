# Phase 38 - Dedup, Canonical Values, and Conflict Preservation

## Current Status

Step: 4 of 11
Branch: main
Started: 2026-05-29
Last session: 2026-05-29
Spec: `docs/specs/phase_38_dedup_canonical_values_conflict_preservation.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:5. Dedup`; `docs/PROJECT_OVERVIEW.md:8. Reconciler`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 38 opened after operator continuation accepted Phase 37 and the Phase 38 draft spec passed readiness checks with no open questions.

Next: Step 4 - add RED tests for `DataPoint.supporting_source_spans` and additive conflict metadata.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add RED tests for canonical key contracts, legacy payload readability, cross-chunk dedup, canonical duplicate dedup, and no-merge conflict cases.
- [x] Step 2: Add canonical value key helpers and dedup cluster contracts.
- [x] Step 3: Extend dedup to drop `chunk_id` from duplicate identity where safe, use canonical keys, preserve deterministic clusters, and keep stable rejection trails.
- [ ] Step 4: Add RED tests for `DataPoint.supporting_source_spans` and additive conflict metadata.
- [ ] Step 5: Extend `DataPoint` and reconciler materialization to populate supporting source spans from contributing candidates.
- [ ] Step 6: Add reconciler conflict detection and stable unresolved conflict metadata.
- [ ] Step 7: Add validation or retry complaints for silent rejection of otherwise valid conflicting candidates.
- [ ] Step 8: Extend audit inspection and report/eval tests for additive fields.
- [ ] Step 9: Add focused source-neutral dedup/conflict fixture coverage if needed for evaluation acceptance.
- [ ] Step 10: Run final project, prompt-neutrality, smoke, lint, and evaluation gates.
- [ ] Step 11: Fill the Phase 38 board summary and stop for operator acceptance.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Phase 38 stays single-document. | Cross-document reconciliation is Phase 39 and depends on single-document conflict preservation. |
| Q2 | No static prompt body changes are approved for Phase 38. | The spec keeps conflict preservation in deterministic server validation and materialization; prompt edits are a stop condition. |
| Q3 | `DataPoint` changes must be additive with legacy-safe defaults. | Existing audit/report payloads must remain readable and `report.v2` must not be broken. |
| Q4 | Canonical value keys are conservative and deterministic. | Ambiguous values must not be guessed or normalized with document-specific heuristics. |

---

## Gate Interpretations

- Phase 38 may add typed contracts for canonical value keys, dedup clusters, supporting source spans, and conflict metadata.
- Phase 38 may modify `src/extractor/executor/dedup.py`, `src/extractor/reconciler/`, `src/extractor/contracts/`, `src/extractor/audit/inspection.py`, reporter/eval tests, and focused fixtures.
- Phase 38 must not change static prompt bodies unless a test proves prompt text is necessary and the operator explicitly authorizes it.
- Phase 38 must not implement cross-document grouping.
- Phase 38 must not change architecture rules or add UI/API/CI/Docker/vector/embedding/framework behavior.
- Phase 38 must preserve exact selected `source_span` fields while adding any supporting provenance arrays.
- New conflict behavior must be source-role-neutral and schema-role-neutral, not fixture-specific.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_38_dedup_canonical_values_conflict_preservation.md:1` | Approved Phase 38 spec after readiness checks. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_38_dedup_canonical_values_conflict_preservation.md:1` | Active Phase 38 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `src/extractor/contracts/dedup.py:1` | Added typed canonical value key and dedup cluster contracts. | Steps 2-3 |
| `src/extractor/contracts/__init__.py:1` | Exported Phase 38 dedup contracts. | Steps 2-3 |
| `src/extractor/contracts/models.py:304` | Added legacy-safe additive `DataPoint` provenance and conflict defaults. | Steps 1-3 |
| `src/extractor/executor/dedup.py:1` | Added canonical value key helpers, cross-chunk dedup identity, canonical duplicate merging, and cluster detail. | Steps 2-3 |
| `tests/unit/test_phase_38_dedup_conflict_contracts.py:1` | Added RED/GREEN coverage for Phase 38 dedup contracts and behavior. | Step 1 |

---

## Issues

_(No issues yet.)_

<!--
### ISS-NNN - <short title>
**Status:** <OPEN|RESOLVED|DEFERRED> | **Severity:** high/medium/low | **Found:** Step K, 2026-05-29
**Files:** `path/to/file.py:line`
**What is wrong:** <expected vs actual>
**How to reproduce:** <command or scenario>
**Root cause:** _(filled when diagnosed)_
**Resolution:** _(filled when fixed or deferred)_
**Resolved:** _(date + step, or "deferred to Phase NN")_
-->

---

## Tests

### Per-Step Results

| Step | Tests | Result | Date |
|---|---|---|---|
| Steps 1-3 | `python3 -m pytest tests/unit/test_phase_38_dedup_conflict_contracts.py` failed RED with 6 expected failures before production changes; `python3 -m pytest tests/unit/test_phase_38_dedup_conflict_contracts.py tests/unit/test_dedup.py tests/unit/test_phase_36_lens_normalization_contracts.py`; `git diff --check`. | PASS | 2026-05-29 |
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_38_dedup_canonical_values_conflict_preservation.md docs/boards/README.md docs/boards/phase_38_dedup_canonical_values_conflict_preservation.md`; `rg -n "Phase 38|phase_38_dedup_canonical_values_conflict_preservation.md|BOARD OPEN|approved|Step 1|Prompt Changes|Open Questions" docs/boards/README.md PROGRESS.md docs/specs/phase_38_dedup_canonical_values_conflict_preservation.md docs/boards/phase_38_dedup_canonical_values_conflict_preservation.md`. | PASS | 2026-05-29 |

### Final Gate

- [ ] Narrow relevant tests pass
- [ ] `make test` passes when feasible
- [ ] `make lint` passes
- [ ] `make smoke` passes when feasible
- [ ] `git diff --check` passes
- [ ] Evaluation gates pass, if this phase changes extraction behavior
- [ ] All OPEN issues are resolved or explicitly deferred
- [ ] Phase Summary filled in
- [ ] `PROGRESS.md` updated

---

## Work Log

Reverse chronological. Log every session.

### 2026-05-29 - Session 2

- Completed Steps 1-3.
- Added RED tests for canonical value key contracts, dedup cluster contracts, legacy `DataPoint` additive defaults, cross-chunk duplicate merging, canonical duplicate merging, and distinct conflict preservation.
- Added typed `CanonicalValueKey` and `DedupCluster` contracts.
- Updated dedup to drop `chunk_id` from duplicate identity where absolute source span identity or canonicalized value identity makes a merge safe, preserve deterministic primary selection, expose cluster details, and keep duplicate rejection trails stable.
- Added legacy-safe default `DataPoint` provenance and conflict fields for old payload readability.
- Issues found: none.
- Tests: Step 1 RED and Steps 1-3 GREEN verification passed as recorded above.
- Next: Step 4 - add RED tests for `DataPoint.supporting_source_spans` and additive conflict metadata.

### 2026-05-29 - Session 1

- Resumed from Phase 37 acceptance after operator continuation.
- Completed: accepted Phase 37, drafted the Phase 38 spec, ran spec readiness checks, approved the Phase 38 spec under operator-trust resume mode, opened this board, pinned gate interpretations, and updated active phase tracking.
- Issues found: none.
- Tests: board-opening verification passed as recorded above.
- Next: Step 1 - add RED tests for canonical key contracts, legacy payload readability, cross-chunk dedup, canonical duplicate dedup, and no-merge conflict cases.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: pending.
- Deferred: pending.
- Added beyond spec: pending.

### Lessons for downstream phases

- Pending.
