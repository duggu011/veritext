# Phase 42 - Static Provenance Artifact

Status: approved for implementation.

Date drafted: 2026-05-30
Date approved: 2026-05-30

Roadmap sources: `docs/PROJECT_OVERVIEW.md` section `9. Reporter`,
`docs/PROJECT_OVERVIEW.md` highest-leverage item 5,
`docs/phase_26_plus_roadmap.md`, `docs/boards/README.md`, `PROGRESS.md`, and
Phase 41 board/spec/commits through `50fdd34`.

## Goal

Add a deterministic static provenance artifact that makes audit review practical
without changing extraction behavior.

Phase 42 should produce a local static HTML report artifact for existing
single-document extraction reports. The artifact must let a reviewer inspect
each reported data point, exact source span, schema identity, prompt/config
hash identities when available through signed manifests, confidence bucket, and
rejection/run-diff trail without running a web server or calling an LLM.

The artifact is a reporter-side view over existing typed report, manifest, and
audit data. It must not become an alternate extraction path, a browser app, a
review UI, or a source of new facts.

## Non-Goals

- Do not add a web UI, web server, REST API, dynamic browser app, client-side
  data fetching, persistent browser/local state, Docker, deployment packaging,
  vector databases, embeddings, fine-tuning hooks, agent frameworks, local
  model serving, external services, or open-web crawling.
- Do not change extraction behavior, prompt bodies, LLM calls, schema-fit
  policy, critic/verifier/reconciler behavior, or evaluation thresholds.
- Do not replace `report.v2`, `refusal.v1`, `cross_document_report.v1`,
  `signed_report_manifest.v1`, or `run_diff_report.v1`.
- Do not hide low-confidence, conflicted, or rejected material to make the
  artifact look cleaner.
- Do not infer provenance from rendered text when typed `SourceSpan` or audited
  document offsets are missing. Missing provenance must be explicit.
- Do not add domain-specific labels, colors, grouping, or copy tied to legal,
  financial, clinical, insurance, standards, scientific, procurement, or audit
  evidence documents.
- Do not add JavaScript that fetches data, mutates state, stores decisions, or
  changes artifact meaning after generation.

## Domain-Scope Alignment

Phase 42 remains domain-neutral. The static artifact must work from the shared
kernel's typed outputs: data point IDs, categories, field names, values,
canonical values, source spans, confidence, conflict metadata, schema metadata,
signed manifest identities, and audit records.

Domain packs may affect the categories and fields present in a report, but they
must not affect how provenance is rendered or validated. The same rules should
apply across legal contracts, SEC filings, clinical protocols, FDA labels,
insurance policies, standards, scientific reviews, patents, procurement files,
and audit evidence.

## Current State

The reporter currently writes deterministic JSON for:

- `report.v2` through `write_report(...)`
- `refusal.v1` through `write_refusal_report(...)`
- `cross_document_report.v1` through `write_cross_document_report(...)`

Phase 40 added:

- `SignedReportManifest` sidecars with report/source/text/schema/prompt/config
  hashes and confidence buckets
- `AuditIntegrityEvent` persistence and chain-head tracking
- deterministic `RunDiffReport` artifacts
- `veritext-report diff`, `veritext-report sign`, and `veritext-report verify`

The existing `ExtractionReport` contains ordered `DataPoint` records, and every
`DataPoint` includes a typed `SourceSpan` with document ID, chunk ID, character
offsets, UTF-8 byte offsets, and exact source text. The audit store can read the
audited `Document` for source text, source hash, text hash, and page map.

There is no static provenance artifact, no HTML rendering module, and no CLI
command that turns a report plus audit state into a reviewer-friendly local
file.

## Artifact Policy

Phase 42 must generate self-contained, deterministic local files. The primary
artifact is static HTML written by reporter code. The implementation may add a
small CSS file only if it is embedded or copied deterministically next to the
HTML with a content hash reference. Prefer a single self-contained HTML file
unless tests show that a sibling static asset is simpler and more auditable.

The artifact may include minimal inline JavaScript only for deterministic local
interactions such as toggling rows or jumping between anchors. Any JavaScript
must be embedded in the generated file, must not fetch data, must not persist
state, must not contact a network, and must not compute facts that are absent
from the typed inputs. A no-JavaScript artifact remains acceptable if all
required provenance is visible through anchors and sections.

All generated output must be deterministic for the same typed inputs. If a
timestamp is included, it must come from an explicit `generated_at` parameter or
from the input report/manifest timestamp, not from hidden global state in tests.

## Provenance Rendering Requirements

For `report.v2`, the static artifact must show:

- report identity: run ID, document ID, report schema version, generated time,
  output data point count, and ordered data point IDs
- schema identity: schema ID, schema hash, source kind, version when available,
  and approved categories/fields without rewriting their meaning
- signed manifest identity when supplied: artifact hash, source/text hashes,
  prompt hashes, config hash, audit digest, audit chain head, signature key ID,
  and confidence bucket membership
- source document identity from the audit store when supplied: source path,
  source hash, text hash, source byte length, text byte length, and page spans
- each data point: category, field name, value, canonical value, value kind,
  confidence, conflict status/reason, source span offsets, exact source text,
  contributing candidate IDs, critic report IDs, verifier report IDs, and
  reconciliation decision ID
- source text context for each data point, using audited document text and exact
  character offsets when available
- explicit warnings for missing audit document text, missing manifest data,
  source-span/document mismatches, and offset/text mismatches

The artifact must not silently repair or normalize mismatched spans. If
`SourceSpan.text` does not equal the audited document slice at
`start_char:end_char`, the artifact must render the mismatch as an artifact
warning and preserve both values for review.

## Rejection and Diff Trail

Phase 42 should expose the rejection and diff trail without changing their
source contracts.

For the single-document report artifact:

- If an audit store is provided, include a deterministic rejection summary by
  stage/reason when available for the report run.
- If a `RunDiffReport` is provided, include a linked diff section that preserves
  entry IDs, diff kinds, old/new refs, source spans, values, canonical values,
  confidence, and reason codes.
- If a signed manifest is provided, include its artifact reference and
  confidence buckets.
- If any optional trail input is absent, render that absence explicitly rather
  than pretending the trail is empty.

Refusal and cross-document static artifacts are deferred unless their support
falls out naturally from the same renderer without broadening scope. The first
implementation must prioritize `report.v2` because it is the artifact that
links individual data points to exact source spans.

## Contract Changes

Expected additive Pydantic contracts:

- `StaticProvenanceWarning`
  - warning code, severity, message, affected data point ID when applicable,
    and affected source span when applicable
- `StaticProvenanceSourceContext`
  - data point ID, source span, prefix text, highlighted text, suffix text,
    offset-match status, and any mismatch details
- `StaticProvenanceDataPointView`
  - data point identity, display-safe value fields, confidence bucket, conflict
    metadata, source context, provenance IDs, and warnings
- `StaticProvenanceArtifact`
  - artifact schema version such as `static_provenance_artifact.v1`
  - report artifact ref when available
  - run/document/schema identities
  - manifest identities when supplied
  - source document summary when supplied
  - data point views
  - rejection summary
  - diff summary
  - warnings

Contracts must use Pydantic v2, frozen models, `extra="forbid"`, stable IDs,
and deterministic ordering. They must not embed raw untyped dictionaries as
stage-boundary data.

## Reporter Effects

Phase 42 may add focused reporter modules rather than growing
`src/extractor/reporter/service.py`.

Expected modules:

- `src/extractor/reporter/static_provenance.py` for typed view construction,
  source-context validation, HTML escaping, deterministic rendering, and file
  writing.
- Optional `src/extractor/reporter/static_assets.py` only if shared CSS or
  rendering constants would otherwise make the renderer unfocused.

The reporter should export explicit functions such as:

- `build_static_provenance_artifact(...)`
- `render_static_provenance_html(...)`
- `write_static_provenance_html(...)`

The renderer must escape all source and value text with Python standard-library
HTML escaping. It must not use a templating engine unless the repository already
has one by the time implementation begins.

Existing `write_report(...)`, `write_refusal_report(...)`,
`write_cross_document_report(...)`, signing, diffing, and verification behavior
must remain compatible.

## CLI Effects

Phase 42 may extend `veritext-report` with a static artifact command such as:

```text
veritext-report provenance REPORT_JSON --audit-db AUDIT_DB --output REPORT_HTML
```

Allowed optional inputs:

- `--manifest SIGNED_MANIFEST_JSON`
- `--diff RUN_DIFF_JSON`

The command must fail explicitly when `REPORT_JSON` is not `report.v2`, the
audit DB is missing required run/document state for mandatory checks, the
output path is a directory, or the typed input contracts fail validation.

The command must print a JSON summary containing outcome type, run ID, document
ID, output path, output SHA-256, byte length, data point count, warning count,
and optional manifest/diff identities.

## Audit Effects

Phase 42 should read audit records but should avoid new audit persistence unless
a narrow verification need appears during implementation.

Allowed audit reads:

- run manifest for the report run
- audited document for source text and source/page hashes
- candidate rejections for rejection summaries
- audit integrity events for chain-head display when relevant

If new audit methods are required, they must be additive, typed, and covered by
unit tests. Do not mutate historical audit rows.

## Configuration Impact

No new runtime tuning is expected.

If implementation needs display context size, keep it in `config/default.yaml`
under `reporting` and validate it through `ExtractorConfig`. Do not hardcode
tuning values in source or tests.

## Prompt Impact

No prompt files may change in Phase 42.

## Invariant Impact

Phase 42 must not weaken I1-I9.

Specific invariant effects:

- Exact source text, character offsets, byte offsets, source hashes, and schema
  hashes must be preserved from typed inputs.
- Missing or inconsistent provenance must create explicit warnings, not
  silent omission or repair.
- The static artifact must be deterministic and auditable from local typed
  inputs.
- No LLM call may be added for rendering, source-context selection, warnings,
  rejection summaries, or diffs.

If implementation finds that existing contracts cannot prove a required
provenance relationship, stop and log an issue instead of inferring from
filename, document title, domain nouns, or fixture text.

## Tests and Verification Gates

Required narrow tests:

- contract validation tests for static provenance view models
- renderer tests proving HTML escapes source/value text, preserves exact source
  spans, renders offsets, and emits mismatch warnings
- writer tests proving deterministic output bytes and output hash reporting
- CLI tests for `veritext-report provenance`
- source-neutral acceptance coverage using generic categories and fields

Required phase gates:

- narrow relevant tests pass
- `git diff --check`
- `git diff --exit-code -- prompts`
- draft-marker and open-question scan on the Phase 42 spec and board
- `make test`, `make lint`, and `make smoke` before closing the phase when
  feasible
- relevant evaluation suites only if implementation changes extraction
  behavior, which Phase 42 should not do

## Implementation Order

1. Approve this spec and open the Phase 42 board.
2. Add static provenance view contracts and source-context validation tests.
3. Implement typed artifact construction from `ExtractionReport`, optional
   `SignedReportManifest`, optional `RunDiffReport`, and optional audited
   `Document`/rejections.
4. Add deterministic HTML rendering and escaping tests.
5. Implement static HTML writing with output hash and byte-length reporting.
6. Extend `veritext-report` with the provenance command and CLI tests.
7. Add source-neutral acceptance coverage.
8. Run final gates, fill the board summary, and stop for operator acceptance.

## Open Questions Before Approval

_(None; resolved by operator approval to begin Phase 42 under the Phase 41
static-artifact allowance on 2026-05-30.)_
