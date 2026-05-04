# Phase 26+ Roadmap Proposal

Status: proposal only. This file is not a phase spec, not a board, and does not open Phase 26.

Date: 2026-05-04

Sources:

- `AGENTS.md`
- `WORKFLOW.md`
- `docs/boards/README.md`
- `docs/PROJECT_OVERVIEW.md`
- `PROGRESS.md`

## Purpose

Turn the Phase 26+ roadmap into a board-ready phase plan while preserving the Veritext rules:

- Keep the extraction kernel domain-neutral.
- Prioritize accuracy, provenance, generalization, and evaluation before deployment economics.
- Do not add LangChain, LlamaIndex, agent frameworks, web UI, REST API, Docker, CI/CD, vector DBs, embeddings, or fine-tuning hooks unless an explicit architecture-rule amendment phase approves the change first.
- Route every LLM call through `src/extractor/llm/client.py`.
- Preserve Pydantic v2 stage contracts, SQLite audit state, forced tool use, exact span/offset provenance, and invariants I1-I9.
- Keep `PROGRESS.md` as history. Boards remain primary for active and future tracking.

## Recommended Board Index Amendment

The current `docs/boards/README.md` Phase Index is directionally right but too coarse from Phase 26 onward.

Recommended amendment:

- Split current Phase 26 into three phases: schema/pack foundation, planner reuse/refusal, and first legal domain pack.
- Split current Phase 27 into evaluation harness, diverse fixture corpus, and adversarial/calibration evaluation.
- Split current Phase 28 into ingestion contracts, PDF/table ingestion, DOCX/HTML/email ingestion, and layout-aware chunking.
- Split current Phase 29 into lens/normalization contracts, expanded lenses, and dedup/reconciliation normalization.
- Split current Phase 30 into signed reports/run diffs, architecture-rule amendment, and viewer work only if approved.
- Split current Phase 31 into cost observability, stage model comparison, and measured cost-cut implementation.
- Leave deployment-economics work after measurement and accuracy gates.

Do not edit `docs/boards/README.md` until this roadmap is accepted.

## Phase Roadmap

| Phase | Name | Goal | Why Here | Source Roadmap Items | Expected Deliverables | Non-Goals | Gate / Acceptance Criteria | Primary Files Likely Involved | Risk |
|---|---|---|---|---|---|---|---|---|---|
| 26 | Domain Pack and Schema Registry Foundation | Define typed, versioned, hashed domain-pack and schema metadata contracts. | Current Phase 26 is too broad; this creates the substrate before planner behavior changes. | Highest-leverage item 1; Planner schema registry/cache; Target Domains configurable/non-configurable split. | Pack/schema Pydantic models; stable hash rules; config hooks; schema metadata in plan/report/audit. | No domain-specific extraction logic; no schema-fit refusal yet; no Phase 26 board/spec opening in this file. | Invalid packs fail explicitly; schema hash is stable; existing smoke/unit tests pass; no invariant weakening. | `src/extractor/contracts/`, `src/extractor/planner/`, `src/extractor/config/`, `src/extractor/reporter/`, `config/default.yaml`, `tests/unit/` | Medium |
| 27 | Planner Schema Reuse and Schema-Fit Refusal | Make planner select/reuse approved schemas or refuse with reason codes. | Depends on schema metadata from Phase 26. | Planner schema registry/cache; explicit no-fitting-schema path; coverage estimation; schema versioning. | Refusal contract; coverage threshold; registry lookup; audited refusal trail; report-level refusal artifact. | No new domain pack corpus; no silent fallback to invented schema. | Out-of-scope docs produce structured, audited refusal instead of extraction; no invariant weakening. | `src/extractor/planner/`, `src/extractor/orchestrator/`, `src/extractor/audit/`, `src/extractor/reporter/`, `prompts/planner/`, `tests/unit/test_planner.py` | High |
| 28 | Legal Contracts Domain Pack v1 | Prove pack mechanism with the first domain pack while keeping the kernel neutral. | Legal contracts are the overview's first proving ground. | Target Domains first-domain-pack proving ground; Planner domain packs. | Legal pack artifact; pack-loader tests; legal fixture coverage; domain assumptions as config/artifacts. | Not a contract-specific fork; no source-code contract nouns; no legal UI/export. | Pack changes config/artifacts only; fixture passes without source hardcoding. | `config/domain_packs/`, `evals/fixtures/`, `src/extractor/planner/`, `tests/unit/` | Medium |
| 29 | Evaluation Harness: Per-Field Gates | Upgrade scoring before broader feature work. | Prevents future phases from optimizing one fixture. | Highest-leverage item 2; Evaluation per-category and per-field metrics. | Suite manifest; per-category and per-field metrics; provenance and invariant breakdowns. | No CI integration because current architecture rules ban CI/CD. | Eval output reports precision, recall, F1, provenance recall, false positives, false negatives, and invariant violations by field/category. | `src/extractor/evals/`, `evals/`, `tests/unit/test_evals.py` | Medium |
| 30 | Diverse Fixture Corpus Round 1 | Add cross-domain fixtures with annotation discipline. | Uses Phase 29 metrics to measure generalization. | Evaluation diverse fixtures; Target Domains Tier 1 and Tier 2. | Legal, SEC, clinical, regulatory, insurance, standards, scientific, and procurement fixtures. | No one-off fixes to pass fixtures; no implementation tuning. | All fixtures score with explicit gates and zero invariant violations. | `evals/fixtures/`, `docs/annotation-conventions.md`, `docs/boards/` | High |
| 31 | Adversarial, Mutation, and Calibration Evaluation | Measure robustness, confidence calibration, and source sensitivity. | Follows baseline corpus. | Evaluation adversarial fixtures, calibration test, mutation testing. | Adversarial fixture pairs; mutation scorer; confidence reliability report. | No model routing changes yet. | Mutations change expected outputs; calibration report is reproducible; gates remain source-grounded. | `src/extractor/evals/`, `evals/fixtures/`, `tests/unit/` | High |
| 32 | Boundary-Preserving Ingestion Model | Extend document/span contracts for layout, tables, metadata, and confidence. | Needed before real PDF/DOCX/email support. | Ingestion; Chunker; Highest-leverage item 3. | Layout/page/table span contracts; metadata contract; offset-map rules; OCR confidence field shape if deferred. | No full PDF/DOCX/email parser yet. | Existing text ingestion remains byte/char exact; new contracts reject lossy or unmapped spans. | `src/extractor/contracts/`, `src/extractor/ingestion/`, `tests/unit/test_ingestion.py` | High |
| 33 | PDF and Table Ingestion | Add layout-aware PDF text/table extraction. | Depends on boundary model. | Ingestion layout-aware PDF; table extraction as first-class lens. | PDF parser; page geometry; table cell provenance; PDF/table fixtures. | No OCR fallback yet unless explicitly included. | PDF fixture preserves source hash, text hash, offsets, page map, and cell maps. | `src/extractor/ingestion/`, `src/extractor/chunker/`, `tests/unit/`, `evals/fixtures/` | High |
| 34 | DOCX, HTML, and Email Ingestion | Support target workflow formats. | After common layout/span model exists. | Ingestion DOCX, HTML, EML/MSG, encoding detection, document metadata. | Format-specific ingestion modules and fixtures; metadata extraction. | No already-structured XLSX analytics; no web crawling. | Fixtures preserve offsets and metadata; unsupported formats fail explicitly. | `src/extractor/ingestion/`, `src/extractor/contracts/`, `tests/unit/` | High |
| 35 | Layout-Aware Chunking | Stop splitting mid-section, mid-sentence, or mid-table. | Ingestion now exposes boundaries. | Chunker semantic/layout-aware chunking; hierarchical chunks; cross-chunk reference markers; per-provider tokenizer. | Section/paragraph/table-aware chunks; cross-chunk references; provider tokenizer policy. | No embeddings or vector DB. | Chunk tests prove boundary preservation, offset continuity, and no mid-table splits. | `src/extractor/chunker/`, `src/extractor/contracts/`, `config/default.yaml`, `tests/unit/test_chunker.py` | High |
| 36 | Lens Taxonomy and Normalization Contracts | Add source-grounded lens/value contracts before prompt/executor expansion. | Avoids ad hoc lens additions. | Highest-leverage item 4; Executor more lenses; Reconciler canonical plus verbatim values. | Lens registry; `value_verbatim`/`value_canonical`; normalization policy contracts. | No new extraction prompts yet. | Existing lenses still pass; new contracts reject unsupported normalization. | `src/extractor/contracts/`, `src/extractor/executor/`, `src/extractor/reconciler/`, `tests/unit/` | High |
| 37 | Expanded Lenses Round 1 | Implement definition, citation, temporal, and quantity-with-unit lenses. | Start with lower-risk deterministic/source-grounded roles. | Executor more lenses. | Lens prompts; executor materialization; validation; tests; fixtures. | No obligation/condition/exception logic yet. | Fixtures show recall gain without false-positive or invariant regression. | `prompts/executor/`, `src/extractor/executor/`, `tests/unit/test_executor.py`, `evals/fixtures/` | High |
| 38 | Dedup, Canonical Values, and Conflict Preservation | Preserve clusters, canonicalize values, and surface conflicts. | Needed before cross-document reconciliation. | Dedup normalized-value dedup, number/date/entity normalization, cluster preservation; Reconciler conflict surfacing and canonical/verbatim values. | Cross-chunk dedup; normalized number/date/entity keys; provenance arrays; conflict output. | No cross-document grouping yet. | Duplicates merge without losing spans; conflicts are emitted instead of dropped. | `src/extractor/executor/dedup.py`, `src/extractor/reconciler/`, `src/extractor/contracts/`, `tests/unit/` | High |
| 39 | Cross-Document Reconciliation | Group facts across documents with separate provenance and conflict policy. | After single-doc normalization/conflict rules. | Reconciler cross-document reconciliation; orchestration multi-document batch mode. | Multi-document run model; deterministic authority policies; conflict surfacing. | No REST service or vector search. | Same fact across docs groups deterministically; unresolved conflicts remain visible. | `src/extractor/orchestrator/`, `src/extractor/reconciler/`, `src/extractor/audit/`, `tests/unit/` | High |
| 40 | Signed Reports and Run Diffs | Add non-UI audit surfaces first. | Improves provenance without violating the web UI ban. | Reporter run diffs, confidence-stratified output, cryptographic signing; Audit hash-chained entries. | Run diff CLI/report; confidence buckets; signed manifest/hash chain. | No HTML provenance viewer yet. | Re-extraction diff is reproducible; manifest verifies hashes and schema/prompt/config/source identities. | `src/extractor/reporter/`, `src/extractor/audit/`, `src/extractor/cli/`, `tests/unit/` | Medium |
| 41 | Architecture Rule Amendment for Viewer, Governance, and CI | Decide whether to allow static HTML viewer, review UI, or CI. | Required before roadmap UI/CI items. | Reporter HTML provenance viewer; Human review/governance; Evaluation CI integration. | Explicit `AGENTS.md`/`CLAUDE.md` amendment or explicit deferral. | No implementation. | Byte-identical agent files; scope distinguishes static generated HTML from web UI and REST API. | `AGENTS.md`, `CLAUDE.md`, `WORKFLOW.md`, `docs/boards/README.md` | Medium |
| 42 | HTML Provenance Viewer, If Approved | Make audit review practical. | Only after amendment. | Highest-leverage item 5; Reporter HTML provenance viewer. | Static provenance viewer or approved UI; source highlighting; run diff links. | No REST API unless separately approved. | Viewer proves every data point links to exact source span, schema version, prompt hash, config hash, and rejection trail. | `src/extractor/reporter/`, possible `templates/`, `tests/` | High |
| 43 | Cost Observability and Cost-per-Correct-Fact | Add measurement before cost cuts. | Cost work must be measurement-gated. | Cost observability prerequisite; LLM client cost reporter. | Per-call cost; per-stage/run/data-point/correct-fact metrics; configured model rates. | No routing or cost-reduction behavior yet. | Fixture report includes cost-per-correct-fact; no quality gate is weakened. | `src/extractor/audit/`, `src/extractor/llm/`, `src/extractor/evals/`, `config/default.yaml` | Medium |
| 44 | Stage Model Comparison | Measure safe cheaper-model routing by stage. | Uses Phase 43 metrics and Phase 29-31 evaluation gates. | Cost playbook tiered models per stage caution. | Stage comparison harness; routing recommendations; evidence table. | No global model downgrade. | Any cheaper route must meet accuracy/provenance gates by stage and fixture. | `src/extractor/llm/`, `config/default.yaml`, `src/extractor/evals/`, `tests/unit/` | High |
| 45 | Deployment-Economics Cost Cuts | Implement proven cost cuts only. | After accuracy/provenance/evaluation and measurement. | Cost playbook top cuts; batch APIs; chunk truncation; caps; prompt caching. | Batch mode; token caps; safe critic/verifier slimming; cache improvements. | No local models, fine-tuning, vector DB, or framework additions. | Cost improves without eval, provenance, or invariant regression. | `src/extractor/llm/`, `src/extractor/critic/`, `src/extractor/verifier/`, `config/default.yaml` | High |

## Phases That Are Too Broad

Current Phase 26 combines domain packs, registry, and refusal. Split it into:

- Phase 26: domain-pack and schema-registry foundation.
- Phase 27: planner schema reuse and schema-fit refusal.
- Phase 28: first legal contracts domain pack.

Current Phase 27 combines evaluation framework and corpus. Split it into:

- Phase 29: evaluation harness with per-field gates.
- Phase 30: diverse fixture corpus.
- Phase 31: adversarial, mutation, and calibration evaluation.

Current Phase 28 combines all real-world ingestion. Split it into:

- Phase 32: boundary-preserving ingestion model.
- Phase 33: PDF and table ingestion.
- Phase 34: DOCX, HTML, and email ingestion.
- Phase 35: layout-aware chunking.

Current Phase 29 combines lens expansion, normalization, dedup, and reconciliation. Split it into:

- Phase 36: lens taxonomy and normalization contracts.
- Phase 37: expanded lenses round 1.
- Phase 38: dedup, canonical values, and conflict preservation.
- Phase 39: cross-document reconciliation.

Current Phase 30 combines reports, diffs, signing, and UI. Split it into:

- Phase 40: signed reports and run diffs.
- Phase 41: architecture-rule amendment for viewer/governance/CI.
- Phase 42: HTML provenance viewer only if approved.

Current Phase 31 combines measurement and cost-reduction behavior. Split it into:

- Phase 43: cost observability.
- Phase 44: stage model comparison.
- Phase 45: measured deployment-economics cost cuts.

## Dependencies

- Phase 27 depends on Phase 26.
- Phase 28 depends on Phases 26-27.
- Phase 30 depends on Phase 29.
- Phase 31 depends on Phases 29-30.
- Phases 33-35 depend on Phase 32.
- Phase 37 depends on Phase 36.
- Phase 38 depends on Phase 36 and should benefit from Phase 37 fixture coverage.
- Phase 39 depends on Phase 38.
- Phase 42 depends on Phase 41 approval.
- Phase 44 depends on Phase 43 and the evaluation gates from Phases 29-31.
- Phase 45 depends on Phase 44.

## Architecture-Rule Conflicts

These roadmap items conflict with current architecture rules and need an explicit amendment phase before implementation:

- HTML provenance viewer or marginal-candidate review UI, unless Phase 41 explicitly narrows approval to static generated HTML and keeps REST/web-server behavior banned.
- CI integration for evaluation gates.
- Local model support via vLLM or llama.cpp.
- Postgres or another non-SQLite audit backend.
- Docker or deployment packaging.
- REST API.
- Fine-tuning hooks or active-learning loops that train models rather than producing labeled fixtures or prompt examples.
- Vector DBs, embeddings, retrieval/indexing, or open-web crawling.

These items do not need an architecture amendment if implemented within existing constraints:

- Batch APIs through direct Anthropic/OpenAI SDK calls in `src/extractor/llm/client.py`.
- Provider failover through the existing LLM client/provider boundary.
- Stage model routing using configured Anthropic/OpenAI/OpenAI-compatible providers.
- Classical deterministic normalization or parsing libraries, provided they do not become agent frameworks or retrieval systems.

## Exact Next Phase To Open

Open Phase 26 as:

- Spec: `docs/specs/phase_26_domain_pack_and_schema_registry_foundation.md`
- Board: `docs/boards/phase_26_domain_pack_and_schema_registry_foundation.md`

Recommended Phase 26 implementation steps:

1. Write the Phase 26 spec from this roadmap and `docs/PROJECT_OVERVIEW.md`.
2. Define typed domain-pack and approved-schema metadata contracts.
3. Add canonical schema hashing and versioning rules with unit tests.
4. Add config hooks for pack locations and registry behavior.
5. Add schema metadata to `ExtractionPlan` without changing planner decisions.
6. Add schema metadata to reporter output and audit payloads.
7. Add pack-loader validation tests using generic test fixtures.
8. Verify existing extraction behavior still passes.
9. Update board references, tests, work log, and `PROGRESS.md`.
10. Commit the completed board step or explicitly hand back uncommitted work.

Final Phase 26 gate:

- Domain-pack and schema metadata contracts are Pydantic v2 models.
- Schema hashes are deterministic and stable across repeated loads.
- Invalid pack/schema artifacts fail with explicit errors.
- Existing `.txt`/`.md` extraction behavior is unchanged except for additional schema metadata.
- Schema metadata is visible in report and audit output.
- No domain-specific source-code patch is introduced.
- No prompt body is filled with implementation-specific domain content outside an approved prompt phase.
- No architecture-rule amendment is made in Phase 26.
- Relevant unit tests pass.
- `make test`, `make lint`, `make smoke`, and `git diff --check` pass when feasible.

## Open Questions Before Writing The Phase 26 Spec

1. Should Phase 26 include audit DB schema changes now, or keep schema registry metadata embedded in existing plan/report payloads until a later schema-migration phase?
2. Should the first approved domain pack be legal contracts, as the overview recommends, or SEC filings?
3. What is the minimum legal-pack fixture gate for Phase 28: one representative contract fixture or multiple contract genres?
4. Should schema-fit refusal block the whole run, or emit a structured refusal report artifact?
5. What coverage threshold should trigger `coverage_below_threshold` refusal?
6. Is static generated HTML acceptable under current rules, or does any HTML provenance viewer require an architecture-rule amendment first?
