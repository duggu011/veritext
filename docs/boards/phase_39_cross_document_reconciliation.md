# Phase 39 - Cross-Document Reconciliation

## Current Status

Step: 8 of 11
Branch: main
Started: 2026-05-29
Last session: 2026-05-29
Spec: `docs/specs/phase_39_cross_document_reconciliation.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:8. Reconciler`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 39 opened after operator continuation accepted Phase 38 and the Phase 39 draft spec passed readiness checks with no open questions.

Next: Step 9 - add focused source-neutral cross-document fixture or equivalent unit coverage for evaluation acceptance.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add RED tests for cross-document contract models and legacy single-document payload compatibility.
- [x] Step 2: Add cross-document Pydantic contracts and exports.
- [x] Step 3: Add RED tests for deterministic grouping, source references, and conflict surfacing across completed single-document outputs.
- [x] Step 4: Implement canonical-key-based cross-document reconciliation without LLM calls.
- [x] Step 5: Add validation and skipped-input accounting for duplicate, incomplete, missing, or unreadable inputs.
- [x] Step 6: Add audit persistence and readback for cross-document manifests and results.
- [x] Step 7: Extend audit inspection and reporter output for additive cross-document fields.
- [x] Step 8: Add multi-document orchestrator batch mode after the pure reconciliation service and audit path are passing; keep CLI behavior unchanged.
- [ ] Step 9: Add focused source-neutral cross-document fixture or equivalent unit coverage for evaluation acceptance.
- [ ] Step 10: Run final project, prompt-neutrality, smoke, lint, and evaluation gates.
- [ ] Step 11: Fill the Phase 39 board summary and stop for operator acceptance.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Phase 39 uses deterministic server-side cross-document reconciliation by default. | Phase 38 already provides canonical value keys and conflict metadata; no prompt-body or LLM-routing change is needed to preserve invariants. |
| Q2 | CLI behavior stays unchanged in Phase 39. | The phase needs a tested Python orchestration entrypoint and report artifact, not a new user-facing command contract. |
| Q3 | `report.v2` remains single-document and unchanged. | Cross-document reporting is additive and should use a separate schema such as `cross_document_report.v1`. |
| Q4 | Authority policy defaults to visibility over resolution. | Safe matches are grouped; safe disagreements are surfaced as conflicts; unsafe near-matches are not guessed. |

---

## Gate Interpretations

- Phase 39 may add typed contracts for cross-document source refs, fact keys, fact groups, conflicts, results, and run manifests.
- Phase 39 may add deterministic cross-document reconciliation under `src/extractor/reconciler/`.
- Phase 39 may add additive audit tables and store methods for cross-document manifests and results.
- Phase 39 may add additive cross-document reporter models and report writing.
- Phase 39 may add a Python orchestration entrypoint for multi-document batch mode.
- Phase 39 must not change CLI behavior or the single-source CLI contract.
- Phase 39 must not change static prompt bodies unless a test proves prompt text is necessary and the operator explicitly authorizes it.
- Phase 39 must not use embeddings, vector search, REST APIs, web UI, Docker, CI/CD, local model serving, or agent frameworks.
- Cross-document grouping must be source-role-neutral and schema-role-neutral, not fixture-specific.
- Existing single-document `DataPoint.source_span`, `supporting_source_spans`, conflict metadata, and `report.v2` behavior must remain compatible.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_39_cross_document_reconciliation.md:1` | Approved Phase 39 spec after readiness checks. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_39_cross_document_reconciliation.md:1` | Active Phase 39 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `tests/unit/test_phase_39_cross_document_contracts.py:1` | Added RED/GREEN coverage for Phase 39 cross-document contracts and legacy single-document payload readability. | Steps 1-2 |
| `src/extractor/contracts/cross_document.py:1` | Added typed cross-document source ref, fact key, fact group, conflict, skipped-input, result, and run-manifest contracts. | Step 2 |
| `src/extractor/contracts/__init__.py:1` | Exported Phase 39 cross-document contracts. | Step 2 |
| `tests/unit/test_phase_39_cross_document_reconciliation.py:1` | Added RED/GREEN coverage for deterministic cross-document grouping, conflict surfacing, and unsafe raw-text non-merges. | Steps 3-4 |
| `src/extractor/reconciler/cross_document.py:1` | Added deterministic canonical-key-based cross-document reconciliation service without LLM calls. | Step 4 |
| `tests/unit/test_phase_39_cross_document_input_validation.py:1` | Added RED/GREEN coverage for duplicate data point rejection and skipped input accounting. | Step 5 |
| `src/extractor/reconciler/cross_document_inputs.py:1` | Added cross-document input preparation, validation, and skipped-input accounting. | Step 5 |
| `src/extractor/reconciler/errors.py:1` | Added a cross-document reconciliation error type shared by the service and input validation. | Step 5 |
| `tests/unit/test_phase_39_cross_document_audit.py:1` | Added RED/GREEN audit persistence coverage for cross-document manifests and reconciliation results. | Step 6 |
| `src/extractor/audit/schema.py:1` | Added additive cross-document manifest and result tables. | Step 6 |
| `src/extractor/audit/cross_document_records.py:1` | Added audit-store methods for cross-document manifest/result record and readback. | Step 6 |
| `src/extractor/audit/store.py:1` | Mixed cross-document audit records into the public `AuditStore`. | Step 6 |
| `tests/unit/test_audit_inspection.py:1` | Added inspection coverage for cross-document run/result summaries. | Step 7 |
| `tests/unit/test_reporter.py:1` | Added cross-document report serialization and manifest-completion coverage. | Step 7 |
| `src/extractor/audit/inspection.py:1` | Added cross-document run/result counts and details to audit inspection. | Step 7 |
| `src/extractor/reporter/models.py:1` | Added additive `cross_document_report.v1` model. | Step 7 |
| `src/extractor/reporter/service.py:1` | Added cross-document report writer with audit-state validation and manifest completion. | Step 7 |
| `src/extractor/reporter/__init__.py:1` | Exported cross-document report model and writer. | Step 7 |
| `tests/unit/test_phase_39_cross_document_orchestrator.py:1` | Added RED/GREEN coverage for multi-document batch orchestration and unchanged single-source CLI parsing. | Step 8 |
| `src/extractor/orchestrator/cross_document.py:1` | Added Python batch orchestration entrypoint for independent single-document runs followed by audited cross-document reconciliation/reporting. | Step 8 |
| `src/extractor/orchestrator/models.py:1` | Added `CrossDocumentBatchResult`. | Step 8 |
| `src/extractor/orchestrator/__init__.py:1` | Exported the Phase 39 batch orchestration entrypoint and result model. | Step 8 |

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
| Step 8 | `python3 -m pytest tests/unit/test_phase_39_cross_document_orchestrator.py -q` failed RED with 2 expected missing-entrypoint failures and 1 passing CLI regression; `python3 -m pytest tests/unit/test_phase_39_cross_document_orchestrator.py -q` passed with 3 passed; `python3 -m pytest tests/unit/test_phase_39_cross_document_orchestrator.py tests/unit/test_orchestrator.py tests/unit/test_reporter.py tests/unit/test_phase_39_cross_document_audit.py tests/unit/test_phase_39_cross_document_reconciliation.py tests/unit/test_phase_39_cross_document_input_validation.py -q` passed with 25 passed; `git diff --check`; `wc -l src/extractor/orchestrator/cross_document.py src/extractor/orchestrator/models.py src/extractor/orchestrator/__init__.py tests/unit/test_phase_39_cross_document_orchestrator.py` reported 181, 71, 21, and 123 lines. | PASS | 2026-05-29 |
| Step 7 | `python3 -m pytest tests/unit/test_audit_inspection.py tests/unit/test_reporter.py -q` failed RED with 2 expected missing cross-document inspection/reporter failures; `python3 -m pytest tests/unit/test_audit_inspection.py tests/unit/test_reporter.py -q` passed with 9 passed; `python3 -m pytest tests/unit/test_phase_39_cross_document_contracts.py tests/unit/test_phase_39_cross_document_reconciliation.py tests/unit/test_phase_39_cross_document_input_validation.py tests/unit/test_phase_39_cross_document_audit.py tests/unit/test_audit_inspection.py tests/unit/test_reporter.py tests/unit/test_audit_store.py tests/unit/test_reconciler.py -q` passed with 45 passed; `git diff --check`; `wc -l src/extractor/audit/inspection.py src/extractor/reporter/models.py src/extractor/reporter/service.py src/extractor/reporter/__init__.py src/extractor/audit/cross_document_records.py tests/unit/test_audit_inspection.py tests/unit/test_reporter.py tests/unit/test_phase_39_cross_document_audit.py` reported 351, 128, 337, 27, 90, 327, 335, and 109 lines. | PASS | 2026-05-29 |
| Step 6 | `python3 -m pytest tests/unit/test_phase_39_cross_document_audit.py -q` failed RED with 3 expected missing audit-store method failures before implementation; `python3 -m pytest tests/unit/test_phase_39_cross_document_audit.py -q` passed with 3 passed; `python3 -m pytest tests/unit/test_phase_39_cross_document_contracts.py tests/unit/test_phase_39_cross_document_reconciliation.py tests/unit/test_phase_39_cross_document_input_validation.py tests/unit/test_phase_39_cross_document_audit.py tests/unit/test_audit_store.py tests/unit/test_reconciler.py -q` passed with 36 passed; `git diff --check`; `wc -l src/extractor/audit/cross_document_records.py src/extractor/audit/schema.py src/extractor/audit/store.py tests/unit/test_phase_39_cross_document_audit.py src/extractor/reconciler/cross_document.py src/extractor/reconciler/cross_document_inputs.py tests/unit/test_phase_39_cross_document_input_validation.py` reported 73, 142, 36, 109, 334, 132, and 147 lines. | PASS | 2026-05-29 |
| Step 5 | `python3 -m pytest tests/unit/test_phase_39_cross_document_reconciliation.py -q` failed RED with 3 expected validation/skipped-input failures before implementation; `python3 -m pytest tests/unit/test_phase_39_cross_document_reconciliation.py tests/unit/test_phase_39_cross_document_input_validation.py -q` passed with 6 passed; `python3 -m pytest tests/unit/test_phase_39_cross_document_contracts.py tests/unit/test_phase_39_cross_document_reconciliation.py tests/unit/test_phase_39_cross_document_input_validation.py tests/unit/test_reconciler.py -q` passed with 24 passed; `git diff --check`; `wc -l src/extractor/reconciler/cross_document.py src/extractor/reconciler/cross_document_inputs.py src/extractor/reconciler/errors.py tests/unit/test_phase_39_cross_document_reconciliation.py tests/unit/test_phase_39_cross_document_input_validation.py` reported 334, 132, 12, 306, and 147 lines. | PASS | 2026-05-29 |
| Steps 3-4 | `python3 -m pytest tests/unit/test_phase_39_cross_document_reconciliation.py -q` failed RED with 3 expected missing-service failures; `python3 -m pytest tests/unit/test_phase_39_cross_document_reconciliation.py -q` passed with 3 passed; `python3 -m pytest tests/unit/test_phase_39_cross_document_contracts.py tests/unit/test_phase_39_cross_document_reconciliation.py tests/unit/test_reconciler.py -q` passed with 21 passed; `git diff --check`; `wc -l src/extractor/reconciler/cross_document.py tests/unit/test_phase_39_cross_document_reconciliation.py src/extractor/contracts/cross_document.py tests/unit/test_phase_39_cross_document_contracts.py` reported 328, 279, 169, and 280 lines. | PASS | 2026-05-29 |
| Steps 1-2 | `python3 -m pytest tests/unit/test_phase_39_cross_document_contracts.py -q` failed RED with 4 expected missing-contract export failures and 1 passed legacy compatibility test; `python3 -m pytest tests/unit/test_phase_39_cross_document_contracts.py -q` passed with 5 passed; `python3 -m pytest tests/unit/test_contracts.py tests/unit/test_phase_38_dedup_conflict_contracts.py tests/unit/test_phase_39_cross_document_contracts.py -q` passed with 24 passed; `git diff --check`; `wc -l src/extractor/contracts/cross_document.py src/extractor/contracts/__init__.py tests/unit/test_phase_39_cross_document_contracts.py` reported 169, 164, and 280 lines. | PASS | 2026-05-29 |
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_39_cross_document_reconciliation.md docs/boards/README.md docs/boards/phase_39_cross_document_reconciliation.md` returned no matches; `rg -n "Status: approved|Date approved|Open Questions Before Approval|No static prompt body changes|Do not change existing CLI behavior|cross_document_report\\.v1|multi-document orchestration entrypoint|BOARD OPEN|Step 1" docs/specs/phase_39_cross_document_reconciliation.md docs/boards/README.md PROGRESS.md docs/boards/phase_39_cross_document_reconciliation.md`. | PASS | 2026-05-29 |

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

### 2026-05-29 - Session 1

- Resumed from Phase 38 acceptance after operator continuation.
- Completed: approved the Phase 39 spec for implementation, opened this board, pinned gate interpretations, and updated active phase tracking.
- Completed Step 1: added RED tests for cross-document contract models and legacy single-document payload compatibility.
- Completed Step 2: added cross-document Pydantic contracts and exports.
- Completed Step 3: added RED tests for deterministic grouping, source references, and conflict surfacing across completed single-document outputs.
- Completed Step 4: added canonical-key-based cross-document reconciliation without LLM calls.
- Completed Step 5: added validation and skipped-input accounting for duplicate, incomplete, missing, or unreadable inputs.
- Completed Step 6: added audit persistence and readback for cross-document manifests and results.
- Completed Step 7: extended audit inspection and reporter output for additive cross-document fields.
- Completed Step 8: added the Python multi-document batch orchestration entrypoint while keeping CLI behavior unchanged.
- Issues found: none.
- Tests: board-opening and Steps 1-8 verification passed as recorded above.
- Next: Step 9 - add focused source-neutral cross-document fixture or equivalent unit coverage for evaluation acceptance.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: 
- Deferred: 
- Added beyond spec: 

### Lessons for downstream phases

- 
