# Phase 41 - Architecture Rule Amendment for Viewer, Governance, and CI

## Current Status

Step: 8 of 8
Branch: main
Started: 2026-05-30
Last session: 2026-05-30
Spec: `docs/specs/phase_41_architecture_rule_amendment_for_viewer_governance_and_ci.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:9. Reporter`; `docs/PROJECT_OVERVIEW.md:13. Evaluation`; `docs/PROJECT_OVERVIEW.md:14. Human review and governance`; `docs/phase_26_plus_roadmap.md`

Phase 41 opened after explicit operator approval of the conservative architecture-rule amendment default and is ready for operator acceptance.

Next: operator acceptance of Phase 41; Phase 42 remains gated.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Resolve operator decisions for deterministic static HTML artifacts, deterministic CI, non-UI governance records, exact amendment text, and the Phase 42 name.
- [x] Step 2: Approve the Phase 41 spec and open this board.
- [x] Step 3: Capture RED-style documentation checks for the selected policy outcome.
- [x] Step 4: Apply the selected architecture-rule amendment to `AGENTS.md` and `CLAUDE.md`.
- [x] Step 5: Keep `AGENTS.md` and `CLAUDE.md` byte-identical.
- [x] Step 6: Update `WORKFLOW.md`, `docs/boards/README.md`, and `PROGRESS.md` as needed to reflect the approved policy decision.
- [x] Step 7: Run the Phase 41 documentation gates.
- [x] Step 8: Fill the Phase 41 summary and stop for operator acceptance.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Allow deterministic static HTML report artifacts only in later approved reporter phases, as local files. | This unblocks source-span review artifacts without allowing a web server, REST API, dynamic browser app, client-side fetching, persistent browser/local state, or extraction behavior changes. |
| Q2 | Allow repository CI only in later approved phases for deterministic verification checks. | Unit tests, lint, smoke, prompt-neutrality checks, and explicit evaluation suites are gate automation, not deployment. Secret-dependent services and deployment packaging remain banned. |
| Q3 | Allow non-UI governance records only in later approved phases. | Reviewer IDs, decisions, timestamps, and review status can be audited without approving a human review UI or active-learning/fine-tuning behavior. |
| Q4 | Add an explicit narrow Phase 41 allowance block to `AGENTS.md` and `CLAUDE.md`. | The architecture-rule exception must be byte-identical in both agent files and must not be implied from roadmap language. |
| Q5 | Rename Phase 42 to "Static Provenance Artifact, If Approved". | The new name keeps the next phase aligned with static generated artifacts and avoids web UI ambiguity. |

---

## Gate Interpretations

- Phase 41 may change only documentation and workflow policy files.
- Phase 41 may approve deterministic static HTML report files but not web UI, a web server, REST API, dynamic browser app, client-side fetching, persistent browser/local state, or extraction behavior changes.
- Phase 41 may approve deterministic repository CI checks but not deployment packaging, Docker, secret-backed external services, or broad CI/CD.
- Phase 41 may approve non-UI governance records but not human review UI, active-learning loops, or fine-tuning behavior.
- Phase 41 must keep `AGENTS.md` and `CLAUDE.md` byte-identical.
- Phase 41 must not change executable code, prompt bodies, runtime config, report schemas, audit schemas, or evaluation thresholds.
- Phase 42 remains gated by operator acceptance of this phase.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_41_architecture_rule_amendment_for_viewer_governance_and_ci.md:1` | Approved the Phase 41 spec and recorded operator-selected resolutions. | Steps 1-2 |
| `docs/boards/phase_41_architecture_rule_amendment_for_viewer_governance_and_ci.md:1` | Active Phase 41 board, decision resolutions, gates, and handoff tracking. | Steps 2-8 |
| `AGENTS.md:1` | Added narrow Phase 41 architecture-rule allowances and adjusted hard-stop wording. | Steps 4-5 |
| `CLAUDE.md:1` | Added byte-identical narrow Phase 41 architecture-rule allowances and adjusted hard-stop wording. | Steps 4-5 |
| `WORKFLOW.md:1` | Updated roadmap policy to reference the narrow Phase 41 allowances. | Step 6 |
| `docs/boards/README.md:1` | Updated active phase pointer, Phase 41 board/spec status, and renamed Phase 42. | Step 6 |
| `PROGRESS.md:1` | Updated current gate and session log for Phase 41. | Steps 6-8 |

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
| Step 7 | `cmp -s AGENTS.md CLAUDE.md`; `git diff --check`; `git diff --exit-code -- prompts`; `rg -n "T[B]D\|T[O]DO\|i[m]plement later\|f[i]ll in\|place[h]older\|\\?\\?" docs/specs/phase_41_architecture_rule_amendment_for_viewer_governance_and_ci.md docs/boards/phase_41_architecture_rule_amendment_for_viewer_governance_and_ci.md docs/boards/README.md WORKFLOW.md` returned no matches; `rg -n "Phase 41 allowances\|Deterministic static HTML report artifacts may be generated as local files\|Repository CI may run deterministic verification\|Non-UI governance records may be file-based\|Static Provenance Artifact\|Status: approved\|Date approved\|BOARD OPEN" AGENTS.md CLAUDE.md docs/specs/phase_41_architecture_rule_amendment_for_viewer_governance_and_ci.md docs/boards/phase_41_architecture_rule_amendment_for_viewer_governance_and_ci.md docs/boards/README.md WORKFLOW.md`; `wc -l docs/specs/phase_41_architecture_rule_amendment_for_viewer_governance_and_ci.md docs/boards/phase_41_architecture_rule_amendment_for_viewer_governance_and_ci.md AGENTS.md CLAUDE.md WORKFLOW.md docs/boards/README.md PROGRESS.md` reported 220, 139, 227, 227, 270, 192, and 3313 lines before final tracking updates. | PASS | 2026-05-30 |

### Final Gate

- [x] Narrow relevant tests pass
- [x] `make test` optional for doc-only Phase 41; not run because no executable code changed
- [x] `make lint` optional for doc-only Phase 41; not run because no executable code changed
- [x] `make smoke` optional for doc-only Phase 41; not run because no executable code changed
- [x] `git diff --check` passes
- [x] Evaluation gates optional; not run because no extraction behavior changed
- [x] All OPEN issues are resolved or explicitly deferred
- [x] Phase Summary filled in
- [x] `PROGRESS.md` updated

---

## Work Log

Reverse chronological. Log every session.

### 2026-05-30 - Session 1

- Resumed from Phase 41 spec approval.
- Completed Step 1: resolved the Phase 41 architecture-rule decisions from the operator-approved conservative default.
- Completed Step 2: approved the Phase 41 spec and opened this board.
- Completed Step 3: captured RED-style documentation checks for the selected policy outcome.
- Completed Step 4: applied the selected architecture-rule amendment to `AGENTS.md` and `CLAUDE.md`.
- Completed Step 5: kept `AGENTS.md` and `CLAUDE.md` byte-identical.
- Completed Step 6: updated `WORKFLOW.md`, `docs/boards/README.md`, and `PROGRESS.md` to reflect the approved policy decision.
- Completed Step 7: ran the Phase 41 documentation gates.
- Completed Step 8: filled the Phase 41 summary and prepared the operator acceptance handoff.
- Issues found: none.
- Tests: Step 7 documentation gates passed as recorded above.
- Next: operator acceptance of Phase 41.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

### What shipped vs spec

- Built as specified: explicit Phase 41 architecture-rule amendments in byte-identical `AGENTS.md` and `CLAUDE.md`, board/index tracking, workflow policy alignment, and a renamed Phase 42 plan.
- Allowed for later approved phases: deterministic static HTML report files, deterministic repository CI checks, and non-UI governance records.
- Still banned unless a later architecture-rule phase approves them: web UI, web servers, REST APIs, dynamic browser apps, Docker, deployment packaging, vector DBs, embeddings, local model serving, broad CI/CD, secret-backed external services, agent frameworks, active-learning loops, and fine-tuning behavior.
- Deferred: all actual static artifact, CI, and governance implementation remains deferred to later approved phases.

### Lessons for downstream phases

- Phase 42 should consume existing report/audit contracts and generate static local artifacts only; it must not become an alternate extraction path or introduce a server.
- Any CI phase should automate existing deterministic gates without deployment packaging or secret-backed external services.
- Governance records can be modeled as auditable files or SQLite/audit-DB records before any UI is reconsidered.
