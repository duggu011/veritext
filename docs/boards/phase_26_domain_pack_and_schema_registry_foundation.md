# Phase 26 - Domain Pack and Schema Registry Foundation

## Current Status

Step: 0 of 6
Branch: main
Started: 2026-05-04
Last session: 2026-05-04
Spec: `docs/specs/phase_26_domain_pack_and_schema_registry_foundation.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:Improvement Roadmap - Accuracy, Generalization, and Provenance`; `docs/phase_26_plus_roadmap.md`

Spec approved by operator on 2026-05-04. Board opened. Implementation has not started.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [ ] Step 1: Add schema metadata contracts and deterministic hashing.
- [ ] Step 2: Add config surface for domain packs and schema registry.
- [ ] Step 3: Attach neutral planner-generated schema metadata to extraction plans.
- [ ] Step 4: Add domain-pack loader validation without planner selection or reuse.
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
