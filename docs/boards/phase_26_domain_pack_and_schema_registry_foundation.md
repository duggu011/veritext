# Phase 26 - Domain Pack and Schema Registry Foundation

## Current Status

Step: 4 of 6
Branch: main
Started: 2026-05-04
Last session: 2026-05-05
Spec: `docs/specs/phase_26_domain_pack_and_schema_registry_foundation.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:Improvement Roadmap - Accuracy, Generalization, and Provenance`; `docs/phase_26_plus_roadmap.md`

Step 4 complete. Domain-pack YAML artifacts are validated explicitly, missing optional pack directories remain safe, and orchestrator startup validates configured artifacts without using them for planner selection or schema reuse. Next: Step 5 - propagate schema metadata through reporter, audit payloads, orchestrator, and CLI summary.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add schema metadata contracts and deterministic hashing.
- [x] Step 2: Add config surface for domain packs and schema registry.
- [x] Step 3: Attach neutral planner-generated schema metadata to extraction plans.
- [x] Step 4: Add domain-pack loader validation without planner selection or reuse.
- [ ] Step 5: Propagate schema metadata through reporter, audit payloads, orchestrator, and CLI summary.
- [ ] Step 6: Run final verification, update board and `PROGRESS.md`, and commit/handoff cleanly.

---

## Open Question Resolutions

| # | Decision | Rationale |
|---|---|---|
| Q1 | Use `schema:<hash-prefix>` for planner-generated schema IDs. | The source kind already records whether a schema is planner-generated; the ID should stay short, deterministic, and source-neutral. |
| Q2 | Accept YAML domain-pack artifacts only in Phase 26. | Veritext already uses YAML for canonical config. JSON support can be added later if a real integration needs it. |
| Q3 | Put synthetic loader fixtures under `tests/fixtures/domain_packs/`. | Test fixtures should not be confused with canonical runtime packs under `config/`. |
| Q4 | Include schema identity in the CLI JSON summary. | Operators should see the schema ID/version/hash without opening the report or audit DB. |

---

## Gate Interpretations

- "Existing extraction behavior is unchanged" means categories, fields, enabled lenses, candidates, data points, and rejection behavior stay decision-equivalent except for added schema metadata.
- "Schema metadata visible in audit" means visible through existing `ExtractionPlan` and report payload JSON; no new audit DB tables are allowed in Phase 26.
- "Deterministic hash" means unchanged across run IDs, timestamps, local absolute paths, LLM call IDs, and data point IDs; changed by approved category or field semantic changes.
- "Invalid domain-pack artifacts fail explicitly" applies to loader validation tests. The default absence of a domain-pack directory must not break existing local extraction runs.

---

## References

Every file this phase creates or modifies. Updated as work happens.

| File | Change | Step |
|---|---|---|
| `docs/specs/phase_26_domain_pack_and_schema_registry_foundation.md` | Approved Phase 26 spec. | Board opening |
| `docs/boards/README.md` | Active phase status and board link. | Board opening |
| `docs/boards/phase_26_domain_pack_and_schema_registry_foundation.md` | Active Phase 26 board. | Board opening |
| `PROGRESS.md` | Current gate and board-opening session log. | Board opening |
| `src/extractor/contracts/schema_metadata.py:1` | Added strict domain-pack, schema-template, and approved-schema metadata contracts plus canonical schema hashing helpers. | Step 1 |
| `src/extractor/contracts/__init__.py:1` | Exported schema metadata contracts and hashing helpers from the public contracts package. | Step 1 |
| `tests/unit/test_schema_metadata.py:1` | Added unit coverage for metadata validation, deterministic sorted hashing, semantic hash changes, and planner-generated schema IDs. | Step 1 |
| `src/extractor/config/models.py:1` | Added typed domain-pack and schema-registry path config sections to `ExtractorConfig`. | Step 2 |
| `src/extractor/config/__init__.py:1` | Exported domain-pack and schema-registry config models. | Step 2 |
| `config/default.yaml:1` | Added canonical default directories for domain packs and schema registry. | Step 2 |
| `tests/unit/test_config.py:1` | Added config loader and strict-model coverage for the new config sections and environment overrides. | Step 2 |
| `tests/unit/test_cli.py:1` | Updated CLI test config fixture with required domain-pack and schema-registry sections. | Step 2 |
| `tests/unit/test_orchestrator.py:1` | Updated direct `ExtractorConfig` construction with the new required config sections. | Step 2 |
| `src/extractor/contracts/base.py:1` | Split shared contract primitives from `contracts/models.py` so schema metadata can be imported without circular dependencies. | Step 3 |
| `src/extractor/contracts/models.py:1` | Added `ExtractionPlan.schema_metadata` derivation and canonical hash validation. | Step 3 |
| `src/extractor/contracts/schema_metadata.py:1` | Updated schema metadata hashing imports to depend on shared contract primitives. | Step 3 |
| `tests/unit/test_contracts.py:1` | Added coverage proving extraction plans carry planner-generated schema metadata and ignore run/doc IDs in hashes. | Step 3 |
| `tests/unit/test_planner.py:1` | Added planner coverage proving stored plans include neutral schema metadata without changing existing plan decisions. | Step 3 |
| `src/extractor/planner/domain_packs.py:1` | Added YAML-only domain-pack artifact loader and validation errors. | Step 4 |
| `src/extractor/planner/__init__.py:1` | Exported domain-pack loader utilities. | Step 4 |
| `src/extractor/orchestrator/service.py:1` | Validates configured domain-pack artifacts before runs without feeding them into planner decisions. | Step 4 |
| `tests/fixtures/domain_packs/generic_metadata_pack.yaml:1` | Added synthetic generic pack fixture for loader validation. | Step 4 |
| `tests/unit/test_domain_pack_loader.py:1` | Added loader validation tests for valid YAML, missing directories, template drift, and non-YAML rejection. | Step 4 |
| `tests/unit/test_orchestrator.py:1` | Added orchestrator boundary coverage for invalid configured pack artifacts. | Step 4 |

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
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_26_domain_pack_and_schema_registry_foundation.md docs/boards/phase_26_domain_pack_and_schema_registry_foundation.md`; `rg -n "phase_26_domain_pack_and_schema_registry_foundation.md|approved|BOARD OPEN" docs/boards/README.md PROGRESS.md docs/specs/phase_26_domain_pack_and_schema_registry_foundation.md` | PASS | 2026-05-04 |
| 1 | `python3 -m pytest tests/unit/test_schema_metadata.py -q`; `python3 -m pytest tests/unit/test_contracts.py tests/unit/test_schema_metadata.py -q` | PASS | 2026-05-05 |
| 2 | `python3 -m pytest tests/unit/test_config.py -q`; `python3 -m pytest tests/unit/test_config.py tests/unit/test_cli.py tests/unit/test_orchestrator.py -q` | PASS | 2026-05-05 |
| 3 | `python3 -m pytest tests/unit/test_contracts.py tests/unit/test_schema_metadata.py tests/unit/test_planner.py tests/unit/test_audit_store.py tests/unit/test_audit_inspection.py tests/unit/test_llm_views.py -q`; `python3 -m pytest tests/unit/test_executor.py tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_reconciler.py tests/unit/test_orchestrator.py -q` | PASS | 2026-05-05 |
| 4 | `python3 -m pytest tests/unit/test_domain_pack_loader.py -q`; `python3 -m pytest tests/unit/test_domain_pack_loader.py tests/unit/test_schema_metadata.py tests/unit/test_config.py tests/unit/test_planner.py tests/unit/test_orchestrator.py -q` | PASS | 2026-05-05 |

### Final Gate

- [ ] Narrow relevant tests pass
- [ ] `make test` passes when feasible
- [ ] `make lint` passes
- [ ] `make smoke` passes when feasible
- [ ] `git diff --check` passes
- [ ] Extraction behavior remains decision-equivalent except for added schema metadata
- [ ] All OPEN issues are resolved or explicitly deferred
- [ ] Phase Summary filled in
- [ ] `PROGRESS.md` updated

---

## Work Log

Reverse chronological. Log every session.

### 2026-05-05 - Session 2

- Resumed at step 1 after operator confirmation.
- Completed: added strict schema/domain-pack metadata contracts and deterministic canonical schema hashing helpers; added typed domain-pack and schema-registry config sections with default YAML and environment override coverage; attached neutral planner-generated schema metadata to extraction plans; added YAML-only domain-pack loader validation without planner selection/reuse.
- Issues found: none.
- Tests: `python3 -m pytest tests/unit/test_schema_metadata.py -q` passed; `python3 -m pytest tests/unit/test_contracts.py tests/unit/test_schema_metadata.py -q` passed; `python3 -m pytest tests/unit/test_config.py -q` passed; `python3 -m pytest tests/unit/test_config.py tests/unit/test_cli.py tests/unit/test_orchestrator.py -q` passed after allowing tiktoken to populate its tokenizer cache; `python3 -m pytest tests/unit/test_contracts.py tests/unit/test_schema_metadata.py tests/unit/test_planner.py tests/unit/test_audit_store.py tests/unit/test_audit_inspection.py tests/unit/test_llm_views.py -q` passed; `python3 -m pytest tests/unit/test_executor.py tests/unit/test_critic.py tests/unit/test_verifier.py tests/unit/test_reconciler.py tests/unit/test_orchestrator.py -q` passed; `python3 -m pytest tests/unit/test_domain_pack_loader.py -q` passed; `python3 -m pytest tests/unit/test_domain_pack_loader.py tests/unit/test_schema_metadata.py tests/unit/test_config.py tests/unit/test_planner.py tests/unit/test_orchestrator.py -q` passed.
- Next: step 5 - propagate schema metadata through reporter, audit payloads, orchestrator, and CLI summary.

### 2026-05-04 - Session 1

- Resumed after operator approved the Phase 26 spec.
- Completed: opened this board, pinned implementation open-question resolutions, and updated tracking references.
- Issues found: none.
- Tests: board-opening documentation checks listed above.
- Next: Step 1 - add schema metadata contracts and deterministic hashing.

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
