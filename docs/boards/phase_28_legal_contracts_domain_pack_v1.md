# Phase 28 - Legal Contracts Domain Pack v1

## Current Status

Step: 2 of 4
Branch: main
Started: 2026-05-10
Last session: 2026-05-10
Spec: `docs/specs/phase_28_legal_contracts_domain_pack_v1.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:Target Domains, Non-Targets, and Market Sizing`; `docs/PROJECT_OVERVIEW.md:Planner`; `docs/phase_26_plus_roadmap.md`

Phase 28 spec approved by the operator on 2026-05-10. Steps 1-2 are complete and committed after verification. Next step is Step 3: add legal-contract evaluation fixture and report-schema coverage.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add legal-contract domain-pack artifact and loader coverage.
- [x] Step 2: Add approved legal schema registry fixture and schema-selection coverage.
- [ ] Step 3: Add legal-contract evaluation fixture and report-schema coverage.
- [ ] Step 4: Add source-neutrality guard and final verification.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Keep the legal approved schema fixture under `tests/fixtures/schema_registry/`; do not introduce a repo-tracked `config/schema_registry/` directory in Phase 28. | Phase 28 proves the mechanism with test fixtures while avoiding a runtime registry governance surface before it is needed. |
| Q2 | Use `legal_contract` as the first document class. | The first pack should prove a reusable domain class rather than overfit to one contract subtype; domain hints can carry narrower commercial-contract semantics. |
| Q3 | Keep the first legal schema small but include limited definitions and notices alongside operational terms. | Parties, dates, obligations, payment, termination, governing law, notices, conditions, exceptions, definitions, and renewal terms exercise legal-contract structure without creating an exhaustive clause taxonomy. |
| Q4 | Do not add duplicate `pack_id` rejection unless Step 1 exposes an existing generic loader gap that blocks reliable pack loading. | Phase 28 should minimize runtime source changes; multi-pack governance can handle broader duplicate-pack policy later. |

---

## Gate Interpretations

- Legal-domain terms may appear in config artifacts, schema registry fixtures, evaluation fixtures, tests, docs, board, and progress logs.
- Runtime `src/` implementation must not add legal-domain branching, legal category constants, clause labels, or legal prompt text.
- Strict approved-schema policy tests may point at fixture registry paths; default local config must not require a real `.veritext/schema_registry` directory.
- The legal fixture is synthetic and must preserve exact source spans, byte offsets, character offsets, and schema metadata.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_28_legal_contracts_domain_pack_v1.md:1` | Approved Phase 28 spec. | Board opening |
| `docs/boards/README.md:1` | Active phase status and board link. | Board opening |
| `docs/boards/phase_28_legal_contracts_domain_pack_v1.md:1` | Active Phase 28 board. | Board opening |
| `PROGRESS.md:1` | Current gate and board-opening session log. | Board opening |
| `tests/unit/test_domain_pack_loader.py:11` | Added config-domain-pack fixture path and loader assertions for the legal contracts pack. | Step 1 |
| `config/domain_packs/legal_contracts.yaml:1` | Added the legal-contract domain-pack artifact and core schema template metadata. | Step 1 |
| `tests/unit/test_schema_registry_loader.py:17` | Added legal schema-registry fixture loading and selection assertions. | Step 2 |
| `tests/fixtures/schema_registry/legal_contract_core_v1.yaml:1` | Added approved legal-contract schema registry fixture with canonical schema hash. | Step 2 |

---

## Issues

_(No issues yet.)_

<!--
### ISS-001 - <short title>
**Status:** OPEN | **Severity:** high/medium/low | **Found:** Step K, YYYY-MM-DD
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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_28_legal_contracts_domain_pack_v1.md docs/boards/README.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md`; `rg -n "phase_28_legal_contracts_domain_pack_v1.md|approved|BOARD OPEN|Step 1" docs/boards/README.md PROGRESS.md docs/specs/phase_28_legal_contracts_domain_pack_v1.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md`; `cmp -s AGENTS.md CLAUDE.md` | PASS | 2026-05-10 |
| 1 | `python3 -m pytest tests/unit/test_domain_pack_loader.py -q` first failed with missing `legal-contracts-v1` pack; `python3 -m pytest tests/unit/test_domain_pack_loader.py -q`; `python3 -m pytest tests/unit/test_domain_pack_loader.py tests/unit/test_config.py tests/unit/test_orchestrator.py -q`; `git diff --check` | PASS | 2026-05-10 |
| 2 | `python3 -m pytest tests/unit/test_schema_registry_loader.py -q` first failed with missing `schema:legal-contract-core-v1` fixture; `python3 -m pytest tests/unit/test_schema_registry_loader.py -q`; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_planner_schema_fit_policy.py -q`; `git diff --check` | PASS | 2026-05-10 |

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

### 2026-05-10 - Session 1

- Resumed after operator approved the Phase 28 spec with `continue`.
- Completed: opened this board, pinned Phase 28 implementation open-question resolutions, updated tracking references, added the legal-contract config domain-pack artifact, added loader coverage for that artifact, added the approved legal schema-registry fixture, and added registry loading and candidate-selection coverage for it.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_28_legal_contracts_domain_pack_v1.md docs/boards/README.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md` returned no matches; `rg -n "phase_28_legal_contracts_domain_pack_v1.md|approved|BOARD OPEN|Step 1" docs/boards/README.md PROGRESS.md docs/specs/phase_28_legal_contracts_domain_pack_v1.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed; `python3 -m pytest tests/unit/test_domain_pack_loader.py -q` first failed with missing `legal-contracts-v1` pack, then passed with 5 passed; `python3 -m pytest tests/unit/test_domain_pack_loader.py tests/unit/test_config.py tests/unit/test_orchestrator.py -q` passed with 29 passed; `python3 -m pytest tests/unit/test_schema_registry_loader.py -q` first failed with missing `schema:legal-contract-core-v1` fixture, then passed with 11 passed; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_planner_schema_fit_policy.py -q` passed with 20 passed; `git diff --check` passed.
- Next: Step 3 - add legal-contract evaluation fixture and report-schema coverage.

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
