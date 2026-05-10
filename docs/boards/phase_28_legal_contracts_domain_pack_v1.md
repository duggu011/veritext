# Phase 28 - Legal Contracts Domain Pack v1

## Current Status

Step: 4 of 4
Branch: main
Started: 2026-05-10
Last session: 2026-05-10
Spec: `docs/specs/phase_28_legal_contracts_domain_pack_v1.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:Target Domains, Non-Targets, and Market Sizing`; `docs/PROJECT_OVERVIEW.md:Planner`; `docs/phase_26_plus_roadmap.md`

Phase 28 accepted by the operator on 2026-05-10. Matching commits exist through `47a350d`. Phase 29 spec draft is opened; do not begin Phase 29 implementation until its spec is approved and a board is created.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add legal-contract domain-pack artifact and loader coverage.
- [x] Step 2: Add approved legal schema registry fixture and schema-selection coverage.
- [x] Step 3: Add legal-contract evaluation fixture and report-schema coverage.
- [x] Step 4: Add source-neutrality guard and final verification.

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
| `tests/unit/test_evals.py:15` | Added the legal-contract fixture to exact fixture scoring and asserted approved schema metadata in its example report. | Step 3 |
| `evals/fixtures/legal_contracts_core/source.txt:1` | Added synthetic legal-contract source text with multiple contract-style clauses. | Step 3 |
| `evals/fixtures/legal_contracts_core/expected.json:1` | Added exact expected legal data points with character and byte offsets. | Step 3 |
| `evals/fixtures/legal_contracts_core/report.example.json:1` | Added deterministic example report using the approved legal schema metadata. | Step 3 |
| `tests/unit/test_phase28_source_neutrality.py:1` | Added guard scanning runtime source and prompt files for Phase 28-specific legal identifiers. | Step 4 |
| `tests/fixtures/source_neutrality/phase_28_forbidden_runtime_terms.txt:1` | Added Phase 28 forbidden runtime identifier list for the source-neutrality guard. | Step 4 |
| `docs/boards/README.md:1` | Updated active Phase 28 status to final-gate-ready. | Step 4 |
| `docs/specs/phase_29_evaluation_harness_per_field_gates.md:1` | Opened draft Phase 29 spec after operator acceptance. | Acceptance |
| `docs/boards/README.md:1` | Marked Phase 28 complete and Phase 29 active in spec-draft state. | Acceptance |
| `PROGRESS.md:1` | Recorded Phase 28 acceptance and Phase 29 spec-draft handoff. | Acceptance |

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
| 3 | `python3 -m pytest tests/unit/test_evals.py -q` first failed with missing `legal_contracts_core` fixture files; `python3 -m pytest tests/unit/test_evals.py -q`; `python3 -m pytest tests/unit/test_evals.py tests/unit/test_reporter.py tests/unit/test_schema_registry_loader.py tests/unit/test_domain_pack_loader.py -q`; `git diff --check` | PASS | 2026-05-10 |
| 4 | `python3 -m pytest tests/unit/test_phase28_source_neutrality.py -q` first failed with missing forbidden-terms fixture; `python3 -m pytest tests/unit/test_phase28_source_neutrality.py -q`; `python3 -m pytest tests/unit/test_domain_pack_loader.py tests/unit/test_schema_registry_loader.py tests/unit/test_evals.py tests/unit/test_phase28_source_neutrality.py -q`; `git diff --exit-code -- prompts`; `git diff --check`; `make test`; `make lint`; `make smoke` | PASS | 2026-05-10 |
| Acceptance | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/README.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md`; `rg -n "Phase 29|phase_29_evaluation_harness_per_field_gates.md|SPEC DRAFT|COMPLETE \\(2026-05-10\\)" docs/boards/README.md PROGRESS.md docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md`; `cmp -s AGENTS.md CLAUDE.md` | PASS | 2026-05-10 |

### Final Gate

- [x] Narrow relevant tests pass
- [x] `make test` passes when feasible
- [x] `make lint` passes
- [x] `make smoke` passes when feasible
- [x] `git diff --check` passes
- [x] Evaluation gates pass, if this phase changes extraction behavior
- [x] All OPEN issues are resolved or explicitly deferred
- [x] Phase Summary filled in
- [x] `PROGRESS.md` updated

---

## Work Log

Reverse chronological. Log every session.

### 2026-05-10 - Session 2

- Resumed after operator accepted Phase 28 with `continue`.
- Completed: marked Phase 28 complete in the board index, opened the draft Phase 29 spec for Evaluation Harness: Per-Field Gates, and updated `PROGRESS.md`.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/README.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md` returned no matches; `rg -n "Phase 29|phase_29_evaluation_harness_per_field_gates.md|SPEC DRAFT|COMPLETE \\(2026-05-10\\)" docs/boards/README.md PROGRESS.md docs/specs/phase_29_evaluation_harness_per_field_gates.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed.
- Next: operator review of `docs/specs/phase_29_evaluation_harness_per_field_gates.md`. Phase 29 implementation must not begin until the spec is approved and a board is created.

### 2026-05-10 - Session 1

- Resumed after operator approved the Phase 28 spec with `continue`.
- Completed: opened this board, pinned Phase 28 implementation open-question resolutions, updated tracking references, added the legal-contract config domain-pack artifact, added loader coverage for that artifact, added the approved legal schema-registry fixture, added registry loading and candidate-selection coverage for it, added the legal-contract evaluation fixture, added report-schema metadata coverage, added source-neutrality guard coverage, and ran final verification.
- Issues found: none.
- Tests: `git diff --check` passed; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_28_legal_contracts_domain_pack_v1.md docs/boards/README.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md` returned no matches; `rg -n "phase_28_legal_contracts_domain_pack_v1.md|approved|BOARD OPEN|Step 1" docs/boards/README.md PROGRESS.md docs/specs/phase_28_legal_contracts_domain_pack_v1.md docs/boards/phase_28_legal_contracts_domain_pack_v1.md` found the expected pointers; `cmp -s AGENTS.md CLAUDE.md` passed; `python3 -m pytest tests/unit/test_domain_pack_loader.py -q` first failed with missing `legal-contracts-v1` pack, then passed with 5 passed; `python3 -m pytest tests/unit/test_domain_pack_loader.py tests/unit/test_config.py tests/unit/test_orchestrator.py -q` passed with 29 passed; `python3 -m pytest tests/unit/test_schema_registry_loader.py -q` first failed with missing `schema:legal-contract-core-v1` fixture, then passed with 11 passed; `python3 -m pytest tests/unit/test_schema_registry_loader.py tests/unit/test_schema_registry_contracts.py tests/unit/test_planner_schema_registry_reuse.py tests/unit/test_planner_schema_fit_policy.py -q` passed with 20 passed; `python3 -m pytest tests/unit/test_evals.py -q` first failed with missing `legal_contracts_core` fixture files, then passed with 12 passed; `python3 -m pytest tests/unit/test_evals.py tests/unit/test_reporter.py tests/unit/test_schema_registry_loader.py tests/unit/test_domain_pack_loader.py -q` passed with 32 passed; `python3 -m pytest tests/unit/test_phase28_source_neutrality.py -q` first failed with missing forbidden-terms fixture, then passed with 1 passed; `python3 -m pytest tests/unit/test_domain_pack_loader.py tests/unit/test_schema_registry_loader.py tests/unit/test_evals.py tests/unit/test_phase28_source_neutrality.py -q` passed with 29 passed; `git diff --exit-code -- prompts` passed; `make test` passed with 252 passed and 2 skipped; `make lint` passed; `make smoke` passed with 1 passed; `git diff --check` passed.
- Next: operator review and acceptance of Phase 28. Phase 29 must not open until the operator explicitly continues.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

### What shipped vs spec

- Built as specified: legal-contract domain pack artifact; approved legal schema registry fixture with canonical hash enforcement; schema-selection coverage; legal-contract evaluation fixture with exact provenance; report-schema metadata coverage; source-neutrality guard; final verification.
- Deferred: broad per-field evaluation gates, diverse fixture corpus, legal-specific runtime logic, prompt-body legal customization, UI/export, and ingestion-format expansion remain outside Phase 28 as specified.
- Added beyond spec: source-neutrality guard terms are fixture-backed so future legal-pack identifiers can be added without editing runtime source.

### Lessons for downstream phases

- Phase 29 can use `legal_contracts_core` as one strict fixture, but should add per-field gates before expanding this into a broader legal corpus.
- Domain-pack assumptions remain auditable as YAML/test/eval artifacts; no runtime source branch was needed for the first pack.
