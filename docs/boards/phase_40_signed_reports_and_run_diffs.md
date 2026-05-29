# Phase 40 - Signed Reports and Run Diffs

## Current Status

Step: 0 of 11
Branch: main
Started: 2026-05-30
Last session: 2026-05-30
Spec: `docs/specs/phase_40_signed_reports_and_run_diffs.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:9. Reporter`; `docs/PROJECT_OVERVIEW.md:11. Audit and observability`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 40 opened after operator continuation accepted Phase 39 and the Phase 40 draft spec passed readiness checks with no open questions.

Next: Step 1 - add RED tests for Phase 40 signing, confidence bucket, audit integrity, and run diff contracts.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [ ] Step 1: Add RED tests for Phase 40 signing, confidence bucket, audit integrity, and run diff contracts.
- [ ] Step 2: Add additive Pydantic contracts and exports.
- [ ] Step 3: Add reporting config models/defaults for signing and confidence buckets.
- [ ] Step 4: Implement canonical hashing, config hashing, HMAC signing, and verification helpers without external signing services.
- [ ] Step 5: Add audit integrity-chain persistence and readback.
- [ ] Step 6: Extend reporter services with detached signed manifest writing and verification for existing report schemas.
- [ ] Step 7: Add deterministic run diff service and report writer.
- [ ] Step 8: Add CLI surface for sign, verify, and diff while preserving existing CLI behavior.
- [ ] Step 9: Add focused source-neutral run diff/signature acceptance coverage.
- [ ] Step 10: Run final project, prompt-neutrality, smoke, lint, and evaluation gates.
- [ ] Step 11: Fill the Phase 40 board summary and stop for operator acceptance.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Phase 40 uses detached signed manifests with canonical hashes plus `hmac-sha256`. | This provides a deterministic tamper-evident surface with stdlib cryptography primitives and no external signing service or key-management dependency. |
| Q2 | Public-key signatures are deferred. | They require deployment and governance choices outside the active extraction-kernel phase. Contracts include algorithm/key metadata so a later phase can add them. |
| Q3 | Signing is disabled by default and explicit signing fails if the configured key environment variable is missing. | Existing extraction, smoke, and local runs must not require a secret, but requested signing must never silently downgrade to unsigned output. |
| Q4 | The CLI surface is a new `veritext-report` command with `sign`, `verify`, and `diff` subcommands. | Existing `veritext` and `veritext-audit` argument parsing remains compatible. |
| Q5 | Confidence buckets are additive report-manifest summaries only. | Buckets help review triage without changing `DataPoint.confidence`, acceptance rules, or extracted output visibility. |
| Q6 | Audit integrity chaining is additive. | Existing audit rows stay readable and are digested into signed manifests rather than rewritten. |

---

## Gate Interpretations

- Phase 40 may add typed contracts for report artifact refs, confidence bucket summaries, signed report manifests, audit integrity events, and run diff reports.
- Phase 40 may add `reporting` config models/defaults for signing and confidence buckets.
- Phase 40 may add additive audit integrity-chain tables and store methods.
- Phase 40 may add reporter modules for canonical hashing, signing, verification, and run diffs.
- Phase 40 may add a new `veritext-report` console script.
- Phase 40 must not change existing `veritext` or `veritext-audit` behavior except for additive exports or shared helpers required by tests.
- Phase 40 must not change static prompt bodies, add LLM calls, or route signing/diffing through an LLM.
- Phase 40 must not add HTML viewer work, REST APIs, web UI, Docker, CI/CD, vector DBs, embeddings, local model serving, external signing services, or agent frameworks.
- Report signing must preserve `report.v2`, `refusal.v1`, and `cross_document_report.v1` compatibility by using detached manifests.
- Run diff identity must be source-neutral and typed-field based, not fixture-, filename-, organization-, or sector-specific.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_40_signed_reports_and_run_diffs.md:1` | Approved Phase 40 spec after readiness checks. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_40_signed_reports_and_run_diffs.md:1` | Active Phase 40 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |

---

## Issues

_(No issues yet.)_

<!--
### ISS-NNN - <short title>
**Status:** <OPEN|RESOLVED|DEFERRED> | **Severity:** high/medium/low | **Found:** Step K, 2026-05-30
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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_40_signed_reports_and_run_diffs.md docs/boards/README.md docs/boards/phase_40_signed_reports_and_run_diffs.md`; `rg -n "Status: approved|Date approved|Open Questions Before Approval|No static prompt body changes|hmac-sha256|signed_report_manifest\\.v1|run_diff_report\\.v1|BOARD OPEN|Step 1|veritext-report" docs/specs/phase_40_signed_reports_and_run_diffs.md docs/boards/README.md PROGRESS.md docs/boards/phase_40_signed_reports_and_run_diffs.md`; `cmp -s AGENTS.md CLAUDE.md`; `wc -l docs/specs/phase_40_signed_reports_and_run_diffs.md docs/boards/phase_40_signed_reports_and_run_diffs.md`. | PASS | 2026-05-30 |

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

### 2026-05-30 - Session 1

- Resumed from Phase 39 acceptance after operator continuation.
- Completed: approved the Phase 40 spec for implementation, opened this board, pinned gate interpretations, and updated active phase tracking.
- Issues found: none.
- Tests: board-opening verification passed as recorded above.
- Next: Step 1 - add RED tests for Phase 40 signing, confidence bucket, audit integrity, and run diff contracts.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

_(Filled in when phase is complete.)_

### What shipped vs spec

- Built as specified: ...
- Deferred: ...
- Added beyond spec: ...

### Lessons for downstream phases

- ...
