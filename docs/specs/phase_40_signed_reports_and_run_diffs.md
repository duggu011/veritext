# Phase 40 - Signed Reports and Run Diffs

Status: draft.

Date drafted: 2026-05-30

Roadmap sources: `docs/PROJECT_OVERVIEW.md` section `9. Reporter`,
`docs/PROJECT_OVERVIEW.md` section `11. Audit and observability`,
`docs/PROJECT_OVERVIEW.md` highest-leverage item 5,
`docs/phase_26_plus_roadmap.md`, `docs/boards/README.md`, `PROGRESS.md`, and
Phase 39 board/spec/commits through `a26dc4c`.

## Goal

Add non-UI audit surfaces that make report artifacts tamper-evident and make
re-extraction changes reviewable.

Phase 40 should produce deterministic signed report manifests for existing
single-document reports, refusal reports, and cross-document reports. The
signature manifest must bind the report bytes to audit identities, source
hashes, schema hashes, prompt hashes, config hashes, output hashes, and the
current audit integrity-chain head.

Phase 40 should also add deterministic run diff reports so a reviewer can
compare two extraction outputs and see added, removed, changed, unchanged, and
ambiguous facts without a web UI and without hiding provenance changes.

## Non-Goals

- Do not implement the HTML provenance viewer, review UI, web UI, REST API,
  Docker, CI/CD, vector databases, embeddings, fine-tuning hooks, agent
  frameworks, local model serving, external signing services, or open-web
  crawling.
- Do not change prompt bodies or add LLM calls for signing, verification, or
  diffing.
- Do not mutate historical audit rows to retrofit a hash chain. Phase 40 may
  add new audit integrity records and digest existing rows into signed
  manifests.
- Do not replace `report.v2`, `refusal.v1`, or `cross_document_report.v1`.
- Do not remove, rename, or weaken any existing report fields.
- Do not store signing secrets in config files, audit rows, reports, or source
  code.
- Do not use filename, document title, company name, sector, or fixture text as
  diff identity policy.
- Do not make confidence buckets reduce or hide extracted data points.

## Domain-Scope Alignment

Phase 40 remains domain-neutral. Signing, verification, confidence bucketing,
and run diffing must work from typed report fields, audit identities, source
hashes, schema metadata, prompt hashes, config hashes, normalized value
metadata, source spans, and data point provenance.

The same logic should apply to legal contracts, SEC filings, clinical
protocols, FDA labels, insurance policies, standards, scientific reviews,
patents, procurement files, and audit evidence. Domain packs may influence the
schema fields being extracted, but they must not influence signing, hash-chain,
or diff verification rules.

## Current State

The reporter writes deterministic JSON for:

- `report.v2` through `write_report(...)`
- `refusal.v1` through `write_refusal_report(...)`
- `cross_document_report.v1` through `write_cross_document_report(...)`

`ReportWriteResult` returns the output path, output SHA-256, byte length, and
completed manifest. The single-source CLI prints these values in its JSON
summary. The cross-document Python entrypoint writes a cross-document report,
but the public CLI remains single-source.

The audit store persists run manifests, documents, chunks, plans, LLM call
logs, candidates, critic reports, verifier reports, data points, rejections,
stage states, cross-document manifests, and cross-document results. Audit rows
store typed payload JSON, but there is no signed report manifest, report
artifact table, audit integrity-chain table, or run diff report table.

`LLMCallLog` records `prompt_sha256`. `Document` records `source_sha256` and
`text_sha256`. `ApprovedSchemaMetadata` records `schema_hash`. The loaded
runtime config is not currently recorded as a signed identity. `RunManifest`
does not currently expose report artifact hashes, signature IDs, or config
hashes.

The audit CLI only inspects a database. There is no report verification command
and no run diff command.

## Signing Policy

Phase 40 uses detached signed manifests rather than mutating report payloads.
This keeps existing report schemas readable and makes signing additive.

The default signing algorithm is `hmac-sha256` over a canonical JSON signing
payload. The signing key is supplied through an environment variable named by
configuration, and only a non-secret `key_id` is persisted. If signing is
requested and the key is missing, verification or writing must fail explicitly.
There is no unsigned fallback for a requested signature.

Public-key signatures and external key-management systems are deferred because
they require deployment and governance decisions outside Phase 40. The Phase 40
contracts should include `signature_algorithm` and `key_id` fields so a later
phase can add a public-key algorithm without changing existing signed-manifest
meaning.

The signed manifest should include:

- report artifact path, byte length, and SHA-256
- report run identity or cross-document run identity
- report, source, schema, prompt, and config hash identities
- output data point, group, and conflict IDs
- confidence bucket summary
- audit integrity digest and chain head
- signature algorithm, key ID, signed payload SHA-256, and signature

## Confidence Buckets

Phase 40 adds deterministic confidence bucket summaries for report artifacts and
run diffs. Buckets do not change acceptance rules and do not suppress data
points.

Default bucket names:

- `verified`
- `probable`
- `tentative`

Thresholds are runtime tuning values and must live in `config/default.yaml`.
The default thresholds should be explicit, validated, and ordered. Existing
`DataPoint.confidence` remains the source value. A report manifest may list data
point IDs per bucket and counts per bucket. Cross-document reports may bucket
source refs or groups only when confidence can be derived from contributing data
points without inventing a new confidence value.

## Audit Integrity Chain

Phase 40 should add an additive audit integrity-chain table rather than
rewriting existing audit tables.

Each integrity event should include:

- stable event ID
- event kind
- run ID or cross-document run ID
- artifact and payload SHA-256 values
- previous chain hash, if any
- chain hash
- created timestamp
- typed payload JSON

The chain hash should be derived deterministically from the previous chain hash
and current payload hash. Verification must recompute event hashes and fail on
missing links, mismatched hashes, or out-of-order events.

The signed manifest should also include a deterministic digest over the relevant
existing audit payloads for the reported run. For single-document reports, this
includes the run manifest, document, plan, LLM call logs, data points, and
rejections needed to prove the final report. For cross-document reports, this
includes the cross-document manifest/result plus the input run/document
identities available in the same audit DB.

## Run Diff Policy

Run diffs must be deterministic and conservative. They should compare two
completed single-document reports, two refusal reports, or two cross-document
reports only when the schema pair is supported by explicit typed rules.

For `report.v2`, the primary comparison identity should use typed fields, not
source-specific nouns:

- schema hash when both reports have one
- document source SHA-256 and text SHA-256 when available
- category
- field name
- value kind
- normalization policy ID and version
- canonical value when it is safely available
- source span identity as a tie-breaker for duplicate fields

Diff output should classify facts as:

`added`, `removed`, `changed_value`, `changed_provenance`,
`changed_confidence`, `unchanged`, and `ambiguous_match`.

When multiple old and new data points share the same partial key and cannot be
paired safely, the diff must emit `ambiguous_match` entries rather than guessing
or silently dropping either side. Every diff entry must preserve old and new
report refs, data point IDs, source spans, values, canonical values, confidence,
and conflict metadata where applicable.

For `cross_document_report.v1`, Phase 40 may compare group and conflict IDs and
their source references. It must not invent cross-document semantic equivalence
beyond the deterministic keys already produced by Phase 39.

## Contract Changes

Expected additive Pydantic contracts:

- `ReportArtifactRef`: artifact path, report schema version, artifact SHA-256,
  byte length, and run identity fields.
- `ReportConfidenceBucketSummary`: bucket name, data point IDs or group IDs,
  count, and threshold metadata.
- `AuditIntegrityEvent`: event ID, event kind, artifact SHA-256, payload
  SHA-256, previous chain hash, chain hash, created timestamp, and payload JSON.
- `SignedReportManifest`
  - manifest schema version such as `signed_report_manifest.v1`
  - report artifact ref
  - source identities
  - schema identities
  - prompt hashes
  - config hash
  - confidence bucket summary
  - audit digest and chain head
  - signature envelope
- `RunDiffFactRef`: report side, run/doc IDs, data point or group/conflict ID,
  category, field name, values, source span refs, confidence, and conflict
  metadata.
- `RunDiffEntry`: diff entry ID, diff kind, old refs, new refs, and reason code.
- `RunDiffReport`
  - report schema version such as `run_diff_report.v1`
  - base artifact ref
  - candidate artifact ref
  - generated timestamp
  - entries by kind
  - summary counts
  - signed manifest refs, if available

All contracts must use Pydantic v2, frozen models, `extra="forbid"`, stable IDs,
and deterministic ordering.

## Reporter Effects

Phase 40 may add sibling modules such as `src/extractor/reporter/integrity.py`,
`src/extractor/reporter/signing.py`, and `src/extractor/reporter/diff.py` rather
than growing the existing `service.py` catch-all.

The reporter should be able to:

- compute canonical report artifact hashes
- compute canonical config hashes without including secret values
- collect prompt/schema/source identities from the audit store
- write a detached signed manifest sidecar
- verify a report against a detached signed manifest
- write deterministic run diff reports
- optionally sign diff reports using the same manifest mechanism

Existing `write_report(...)`, `write_refusal_report(...)`, and
`write_cross_document_report(...)` behavior must remain compatible. If their
signatures change, new parameters must be optional with legacy-safe defaults.

## Audit Effects

Allowed audit changes:

- Additive table or tables for audit integrity-chain events.
- Additive audit store methods to record, fetch, and list integrity events.
- Audit inspection output that summarizes report manifest counts, latest chain
  head, and verification status when available.
- Optional report artifact records if the implementation needs them for
  reproducible verification.

Required compatibility:

- Existing audit DBs must remain readable.
- Existing audit schema version behavior must remain compatible with prior DBs.
- Existing single-document and cross-document tables must remain unchanged.
- Existing run-resume behavior must keep passing.

## CLI Effects

Phase 40 may add a non-UI command surface for report verification and run diffs.
The safest shape is a new console script such as `veritext-report` with
subcommands for `sign`, `verify`, and `diff`, or an additive subcommand surface
that preserves current `veritext` and `veritext-audit` behavior.

CLI output should be JSON and include artifact paths, hashes, verification
status, signature metadata without secrets, and diff summary counts. Existing
single-source `veritext` extraction arguments and existing `veritext-audit`
inspection behavior must remain compatible.

## Configuration Changes

Expected additive config:

- `reporting.signing.enabled`
- `reporting.signing.algorithm`
- `reporting.signing.key_id`
- `reporting.signing.key_env`
- `reporting.signing.manifest_suffix`
- `reporting.confidence_buckets`

Signing secrets must not be stored in YAML. The YAML config stores only the
environment variable name and non-secret key ID. Confidence thresholds must be
validated as ordered numeric values.

## Prompt Changes

No static prompt body changes are planned for Phase 40.

Signing, verification, confidence bucketing, hash-chain events, and run diffing
must be deterministic server-side behavior. If a test appears to require an LLM
to interpret a diff, stop before adding that behavior and redesign around typed
contracts.

## Tests and Verification Gates

Narrow tests:

- Contract tests for signed manifests, signature envelopes, report artifact
  refs, confidence bucket summaries, audit integrity events, run diff refs,
  diff entries, and diff reports.
- Canonical hashing tests proving stable JSON output across key order and
  process runs.
- Signing tests proving HMAC verification passes for exact bytes and fails for
  tampered report bytes, tampered manifests, wrong key IDs, missing keys, and
  mismatched audit digests.
- Confidence bucket tests proving configured thresholds are validated and data
  point IDs are bucketed without changing `DataPoint.confidence`.
- Audit persistence tests for integrity-chain event record, readback, chain-head
  listing, and tamper detection.
- Reporter tests for signed manifest writing and verification for `report.v2`,
  `refusal.v1`, and `cross_document_report.v1`.
- Run diff tests for added, removed, changed value, changed provenance, changed
  confidence, unchanged, and ambiguous-match outputs.
- CLI tests proving new sign/verify/diff commands produce stable JSON and
  existing `veritext` and `veritext-audit` behavior remains compatible.
- Source-neutral tests proving diff identity does not depend on fixture-specific
  nouns, filenames, market sectors, or company names.

Regression and final gates:

- Existing unit tests for config, contracts, reporter, audit store, audit
  inspection, CLI, orchestrator, and cross-document reporting.
- `git diff --exit-code -- prompts`
- `make test`
- `make lint`
- `make smoke`
- `git diff --check`
- Phase 29 and Phase 30 evaluation suites.
- Phase 31 adversarial, mutation, and calibration suites.
- Phase 37 expanded-lens evaluation suite.

Evaluation acceptance:

- No regression in existing precision, recall, F1, provenance recall, false
  positives, false negatives, or invariant violations.
- Signed manifests verify report bytes, source hashes, schema hashes, prompt
  hashes, config hashes, and audit digest identities.
- Run diffs are reproducible and preserve exact old/new provenance for every
  changed or ambiguous entry.

## Implementation Order

1. Add RED tests for Phase 40 signing, confidence bucket, audit integrity, and
   run diff contracts.
2. Add additive Pydantic contracts and exports.
3. Add reporting config models/defaults for signing and confidence buckets.
4. Implement canonical hashing, config hashing, HMAC signing, and verification
   helpers without external signing services.
5. Add audit integrity-chain persistence and readback.
6. Extend reporter services with detached signed manifest writing and
   verification for existing report schemas.
7. Add deterministic run diff service and report writer.
8. Add CLI surface for sign, verify, and diff while preserving existing CLI
   behavior.
9. Add focused source-neutral run diff/signature acceptance coverage.
10. Run final project, prompt-neutrality, smoke, lint, and evaluation gates.
11. Fill the Phase 40 board summary and stop for operator acceptance.

## Open Questions Before Approval

_(None.)_
