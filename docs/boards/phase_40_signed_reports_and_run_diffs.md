# Phase 40 - Signed Reports and Run Diffs

## Current Status

Step: 11 of 11
Branch: main
Started: 2026-05-30
Last session: 2026-05-30
Spec: `docs/specs/phase_40_signed_reports_and_run_diffs.md`
Roadmap source: `docs/PROJECT_OVERVIEW.md:9. Reporter`; `docs/PROJECT_OVERVIEW.md:11. Audit and observability`; `docs/PROJECT_OVERVIEW.md:Highest-leverage accuracy/provenance improvements, ranked`; `docs/phase_26_plus_roadmap.md`

Phase 40 opened after operator continuation accepted Phase 39 and the Phase 40 draft spec passed readiness checks with no open questions.

Accepted by operator continuation on 2026-05-30.

Next: Phase 41 spec readiness and architecture-rule amendment questions.

---

## Implementation Steps

From the approved spec. Check off only after verification and commit or explicit handoff.

- [x] Step 1: Add RED tests for Phase 40 signing, confidence bucket, audit integrity, and run diff contracts.
- [x] Step 2: Add additive Pydantic contracts and exports.
- [x] Step 3: Add reporting config models/defaults for signing and confidence buckets.
- [x] Step 4: Implement canonical hashing, config hashing, HMAC signing, and verification helpers without external signing services.
- [x] Step 5: Add audit integrity-chain persistence and readback.
- [x] Step 6: Extend reporter services with detached signed manifest writing and verification for existing report schemas.
- [x] Step 7: Add deterministic run diff service and report writer.
- [x] Step 8: Add CLI surface for sign, verify, and diff while preserving existing CLI behavior.
- [x] Step 9: Add focused source-neutral run diff/signature acceptance coverage.
- [x] Step 10: Run final project, prompt-neutrality, smoke, lint, and evaluation gates.
- [x] Step 11: Fill the Phase 40 board summary and stop for operator acceptance.

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
| `docs/boards/phase_40_signed_reports_and_run_diffs.md:1` | Active Phase 40 board, final gates, and phase summary. | Board opening; Steps 10-11 |
| `PROGRESS.md:1` | Current gate, board-opening session log, final gates, and phase-summary handoff. | Board opening; Steps 10-11 |
| `tests/unit/test_phase_40_report_integrity_contracts.py:1` | Added RED/GREEN coverage for signed report, audit integrity, and run diff contracts. | Steps 1-2 |
| `src/extractor/contracts/report_integrity.py:1` | Added Phase 40 report artifact, confidence bucket, signature, integrity event, signed manifest, and run diff contracts. | Step 2 |
| `src/extractor/contracts/__init__.py:1` | Exported Phase 40 report integrity contracts. | Step 2 |
| `tests/unit/test_phase_40_reporting_config.py:1` | Added RED/GREEN reporting signing and confidence bucket config coverage. | Step 3 |
| `src/extractor/config/models.py:1` | Added reporting signing and confidence bucket config models/defaults. | Step 3 |
| `src/extractor/config/__init__.py:1` | Exported reporting config models. | Step 3 |
| `config/default.yaml:1` | Added canonical reporting signing and confidence bucket defaults. | Step 3 |
| `tests/unit/test_phase_40_report_signing.py:1` | Added RED/GREEN coverage for canonical JSON hashing, file hashing, config hashing, HMAC signing, and verification. | Step 4 |
| `src/extractor/reporter/signing.py:1` | Added canonical hashing, config hashing, file hashing, HMAC signing, and verification helpers. | Step 4 |
| `src/extractor/reporter/__init__.py:1` | Exported report signing helpers. | Step 4 |
| `tests/unit/test_phase_40_audit_integrity.py:1` | Added RED/GREEN audit integrity-chain persistence and readback coverage. | Step 5 |
| `src/extractor/audit/schema.py:1` | Added additive `audit_integrity_events` table. | Step 5 |
| `src/extractor/audit/integrity_records.py:1` | Added audit-store methods for integrity event record, readback, listing, and latest chain hash. | Step 5 |
| `src/extractor/audit/store.py:1` | Mixed integrity audit records into the public `AuditStore`. | Step 5 |
| `tests/unit/test_phase_40_signed_report_manifest.py:1` | Added RED/GREEN coverage for detached signed report manifest writing, audit identity binding, integrity event recording, and tamper verification. | Step 6 |
| `src/extractor/reporter/signing.py:1` | Added signed report manifest writing and verification on top of the Step 4 signing helpers. | Step 6 |
| `src/extractor/reporter/__init__.py:1` | Exported signed report manifest writer and verifier. | Step 6 |
| `tests/unit/test_phase_40_run_diff.py:1` | Added RED/GREEN coverage for deterministic report diffs and run diff JSON writing. | Step 7 |
| `src/extractor/reporter/diff.py:1` | Added deterministic `report.v2` diff service and run diff report writer. | Step 7 |
| `src/extractor/reporter/__init__.py:1` | Exported run diff service and writer. | Step 7 |
| `tests/unit/test_phase_40_report_cli.py:1` | Added RED/GREEN coverage for `veritext-report diff`, `sign`, `verify`, and pyproject script registration. | Step 8 |
| `src/extractor/reporter/cli.py:1` | Added `veritext-report` CLI with `diff`, `sign`, and `verify` subcommands. | Step 8 |
| `src/extractor/reporter/__main__.py:1` | Added module entrypoint for the report CLI. | Step 8 |
| `pyproject.toml:1` | Registered the `veritext-report` console script. | Step 8 |
| `src/extractor/config/models.py:1` | Updated default signing key env name so report signing secrets are not parsed as `VERITEXT_` config overrides. | Step 8 |
| `config/default.yaml:1` | Updated canonical signing key env default to `REPORT_SIGNING_KEY`. | Step 8 |
| `tests/unit/test_phase_40_reporting_config.py:1` | Updated reporting config expectations for the non-`VERITEXT_` signing secret env var. | Step 8 |
| `tests/unit/test_phase_40_report_signing.py:1` | Updated config-hash signing-secret test for the non-`VERITEXT_` signing secret env var. | Step 8 |
| `tests/unit/test_phase_40_signed_report_manifest.py:1` | Updated signed manifest test env for the non-`VERITEXT_` signing secret env var. | Step 8 |
| `tests/unit/test_phase_40_report_acceptance.py:1` | Added source-neutral acceptance coverage combining signed manifests, verification, confidence buckets, source hashes, and run diffs. | Step 9 |

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
| Step 10 | `make test` passed with 387 passed and 2 skipped; `make lint`; `make smoke` passed with 1 passed; `git diff --check`; `git diff --exit-code -- prompts`; `git diff --exit-code e32a359..HEAD -- prompts`; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_29_core.json` passed with 21 expected/actual data points, 21 exact provenance matches, and zero invariant violations; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 expected/actual data points, 49 exact provenance matches, and zero invariant violations; `PYTHONPATH=src python3 -m extractor.evals --suite evals/suites/phase_37_expanded_lenses_round_1.json` passed with 4 expected/actual data points, 4 exact provenance matches, and zero invariant violations; `PYTHONPATH=src python3 -m extractor.evals --adversarial-suite evals/suites/phase_31_adversarial.json` passed; `PYTHONPATH=src python3 -m extractor.evals --mutation-suite evals/suites/phase_31_mutation.json` passed with source sensitivity 1.0; `PYTHONPATH=src python3 -m extractor.evals --calibration-suite evals/suites/phase_30_diverse_corpus_round_1.json` passed with 49 matched, 0 unmatched, expected calibration error 0.048979591836734754, and provenance calibration error 0.048979591836734754. | PASS | 2026-05-30 |
| Step 9 | `python3 -m pytest tests/unit/test_phase_40_report_acceptance.py -q` passed with 1 passed; `python3 -m pytest tests/unit/test_phase_40_report_acceptance.py tests/unit/test_phase_40_report_cli.py tests/unit/test_phase_40_run_diff.py tests/unit/test_phase_40_signed_report_manifest.py tests/unit/test_phase_40_report_signing.py tests/unit/test_phase_40_audit_integrity.py tests/unit/test_phase_40_report_integrity_contracts.py tests/unit/test_phase_40_reporting_config.py -q` passed with 19 passed; `git diff --check`; `wc -l tests/unit/test_phase_40_report_acceptance.py` reported 137 lines. | PASS | 2026-05-30 |
| Step 8 | `python3 -m pytest tests/unit/test_phase_40_report_cli.py -q` failed RED with expected missing `extractor.reporter.cli`, then initially exposed report JSON datetime loading and `VERITEXT_` signing-secret env collision gaps; `python3 -m pytest tests/unit/test_phase_40_report_cli.py -q` passed with 3 passed; `python3 -m pytest tests/unit/test_phase_40_report_cli.py tests/unit/test_phase_40_run_diff.py tests/unit/test_phase_40_signed_report_manifest.py tests/unit/test_phase_40_report_signing.py tests/unit/test_phase_40_reporting_config.py tests/unit/test_cli.py tests/unit/test_reporter.py -q` passed with 24 passed; `git diff --check`; `wc -l tests/unit/test_phase_40_report_cli.py src/extractor/reporter/cli.py src/extractor/reporter/__main__.py pyproject.toml src/extractor/config/models.py config/default.yaml` reported 123, 195, 5, 41, 185, and 61 lines. | PASS | 2026-05-30 |
| Step 7 | `python3 -m pytest tests/unit/test_phase_40_run_diff.py -q` failed RED with expected missing `diff_reports` export, then passed with 2 passed after correcting the test fixture to satisfy existing normalization invariants; `python3 -m pytest tests/unit/test_phase_40_run_diff.py tests/unit/test_phase_40_report_integrity_contracts.py tests/unit/test_phase_40_report_signing.py tests/unit/test_phase_40_signed_report_manifest.py tests/unit/test_reporter.py -q` passed with 16 passed; `git diff --check`; `wc -l tests/unit/test_phase_40_run_diff.py src/extractor/reporter/diff.py src/extractor/reporter/__init__.py` reported 134, 228, and 57 lines. | PASS | 2026-05-30 |
| Step 6 | `python3 -m pytest tests/unit/test_phase_40_signed_report_manifest.py -q` failed RED with expected missing `verify_signed_report_manifest` export, then passed with 1 passed; `python3 -m pytest tests/unit/test_phase_40_signed_report_manifest.py tests/unit/test_phase_40_report_signing.py tests/unit/test_phase_40_audit_integrity.py tests/unit/test_reporter.py tests/unit/test_audit_store.py tests/unit/test_config.py -q` passed with 39 passed; `git diff --check`; `wc -l tests/unit/test_phase_40_signed_report_manifest.py src/extractor/reporter/signing.py src/extractor/reporter/__init__.py` reported 99, 376, and 47 lines. | PASS | 2026-05-30 |
| Step 5 | `python3 -m pytest tests/unit/test_phase_40_audit_integrity.py -q` failed RED with 2 expected missing `AuditStore` method failures, then passed with 2 passed; `python3 -m pytest tests/unit/test_phase_40_audit_integrity.py tests/unit/test_phase_40_report_signing.py tests/unit/test_audit_store.py tests/unit/test_phase_39_cross_document_audit.py tests/unit/test_reporter.py -q` passed with 24 passed; `git diff --check`; `wc -l tests/unit/test_phase_40_audit_integrity.py src/extractor/audit/integrity_records.py src/extractor/audit/schema.py src/extractor/audit/store.py` reported 77, 78, 155, and 42 lines. | PASS | 2026-05-30 |
| Step 4 | `python3 -m pytest tests/unit/test_phase_40_report_signing.py -q` failed RED with expected missing `extractor.reporter.signing`, then passed with 4 passed; `python3 -m pytest tests/unit/test_phase_40_report_signing.py tests/unit/test_phase_40_report_integrity_contracts.py tests/unit/test_phase_40_reporting_config.py tests/unit/test_reporter.py tests/unit/test_config.py -q` passed with 33 passed; `git diff --check`; `wc -l tests/unit/test_phase_40_report_signing.py src/extractor/reporter/signing.py src/extractor/reporter/__init__.py` reported 81, 114, and 43 lines. | PASS | 2026-05-30 |
| Steps 1-3 | `python3 -m pytest tests/unit/test_phase_40_report_integrity_contracts.py -q` failed RED with 3 expected missing-contract export failures, then passed with 3 passed; `python3 -m pytest tests/unit/test_config.py::test_default_config_file_loads tests/unit/test_config.py::test_reporting_settings_support_env_overrides tests/unit/test_config.py::test_domain_pack_and_schema_registry_config_sections_are_strict tests/unit/test_config.py::test_reporting_config_rejects_invalid_signing_and_bucket_thresholds -q` failed RED during collection with missing `ConfidenceBucketConfig`, then the focused config tests were moved to `tests/unit/test_phase_40_reporting_config.py`; `python3 -m pytest tests/unit/test_phase_40_report_integrity_contracts.py tests/unit/test_phase_40_reporting_config.py tests/unit/test_config.py -q` passed with 23 passed; `python3 -m pytest tests/unit/test_contracts.py tests/unit/test_phase_39_cross_document_contracts.py tests/unit/test_phase_40_report_integrity_contracts.py tests/unit/test_phase_40_reporting_config.py tests/unit/test_config.py -q` passed with 41 passed; `git diff --check`; `wc -l tests/unit/test_phase_40_report_integrity_contracts.py tests/unit/test_phase_40_reporting_config.py src/extractor/contracts/report_integrity.py src/extractor/contracts/__init__.py src/extractor/config/models.py src/extractor/config/__init__.py config/default.yaml tests/unit/test_config.py` reported 254, 100, 203, 196, 185, 59, 61, and 361 lines. | PASS | 2026-05-30 |
| Board opening | `git diff --check`; `rg -n "T[B]D|T[O]DO|i[m]plement later|f[i]ll in|place[h]older|\\?\\?" docs/specs/phase_40_signed_reports_and_run_diffs.md docs/boards/README.md docs/boards/phase_40_signed_reports_and_run_diffs.md`; `rg -n "Status: approved|Date approved|Open Questions Before Approval|No static prompt body changes|hmac-sha256|signed_report_manifest\\.v1|run_diff_report\\.v1|BOARD OPEN|Step 1|veritext-report" docs/specs/phase_40_signed_reports_and_run_diffs.md docs/boards/README.md PROGRESS.md docs/boards/phase_40_signed_reports_and_run_diffs.md`; `cmp -s AGENTS.md CLAUDE.md`; `wc -l docs/specs/phase_40_signed_reports_and_run_diffs.md docs/boards/phase_40_signed_reports_and_run_diffs.md`. | PASS | 2026-05-30 |

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

### 2026-05-30 - Session 1

- Resumed from Phase 39 acceptance after operator continuation.
- Completed: approved the Phase 40 spec for implementation, opened this board, pinned gate interpretations, and updated active phase tracking.
- Completed Step 1: added RED tests for Phase 40 signed report, audit integrity, run diff, and reporting config contracts.
- Completed Step 2: added additive Phase 40 report integrity Pydantic contracts and exports.
- Completed Step 3: added reporting signing and confidence bucket config models/defaults.
- Completed Step 4: added canonical JSON hashing, config hashing, file hashing, HMAC signing, and verification helpers without external signing services.
- Completed Step 5: added additive audit integrity-chain persistence and readback.
- Completed Step 6: added detached signed report manifest writing and verification with audit integrity event recording.
- Completed Step 7: added deterministic `report.v2` run diff service and JSON writer.
- Completed Step 8: added `veritext-report` CLI subcommands for diff, sign, and verify while preserving existing `veritext` and `veritext-audit` behavior.
- Completed Step 9: added source-neutral acceptance coverage for signed manifest verification, confidence buckets, source hashes, and run diffs.
- Completed Step 10: ran final project, prompt-neutrality, smoke, lint, and evaluation gates.
- Completed Step 11: filled the Phase 40 summary and prepared the operator acceptance handoff.
- Issues found: none.
- Tests: board-opening and Steps 1-10 verification passed as recorded above.
- Accepted by operator continuation on 2026-05-30.
- Next: Phase 41 spec readiness and architecture-rule amendment questions.

---

## Deferred Issues

_(None yet.)_

---

## Phase Summary

### What shipped vs spec

- Built as specified: additive report integrity contracts, reporting signing/confidence-bucket config, canonical JSON/config/file hashing, `hmac-sha256` signing and verification helpers, additive audit integrity-chain persistence, detached signed report manifests for existing report artifacts, deterministic `report.v2` run diffs, `veritext-report diff/sign/verify`, and source-neutral acceptance coverage.
- Deferred: public-key signatures and external key management remain deferred by spec; HTML viewer, REST API, web UI, CI/CD, Docker, vector DBs, embeddings, and agent frameworks remain out of scope and gated by later approved phases.
- Added beyond spec: no scope expansion. The configured signing key environment variable default is `REPORT_SIGNING_KEY` so signing secrets are not parsed as `VERITEXT_` runtime config overrides.

### Lessons for downstream phases

- Detached manifests let downstream review tools verify report bytes and audit identity without mutating `report.v2`, `refusal.v1`, or `cross_document_report.v1`.
- Run diffs are intentionally conservative and source-neutral. Ambiguous matching remains visible rather than guessed, so any future richer diff must preserve typed refs, exact source spans, confidence, and conflict metadata.
- Phase 41 must handle architecture-rule amendments before any viewer, governance UI, or CI work. Phase 40 added the non-UI integrity surface those later phases can consume.
