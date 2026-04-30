# Progress

Running log for repository sessions and accepted phase gates.

## Current Gate

- Last completed phase: Phase 18 — Multi-provider LLM Client
- Current status: awaiting explicit `continue` before Phase 19
- Next required work: Phase 19 scope is not yet defined in repository docs

## Session Log

### 2026-04-30 — Medium Research Output Comparison

- Compared `outputs/medium-research.json` against `evals/fixtures/medium_research_brief/source.md` and verified the reported SHA-256/byte length match the run summary.
- Found all 12 emitted data points are source-backed and come from the first Headlines paragraph, with no distractor extraction from the rejected CleanTech Daily or Northwind/Sunbelt statements.
- Found major recall loss outside Headlines: executor generated candidates for Operations, Acquisition, Guidance, Risk, and Personnel, but most were rejected as `invalid_source_offsets`/`invented_span` before critic/verifier because claimed offsets did not match chunk text.
- Confirmed the approved extraction plan covered seven categories, so the missed later-section facts were not caused by planner schema scope.
- Reviewed `docs/extraction-quality-strategy.md`; the chunk-wide unique-span locator strategy matches the audit failure, but the run-status wording, retry-loop placement, and call-scaling formula need correction before implementation.
- Shipped the executor locator fix: after a claimed offset miss, executor span resolution now searches the whole chunk and only auto-corrects exact `source_text` when it occurs uniquely.
- Hardened executor span resolution further with whitespace-normalized unique matching that rewrites provenance to the exact chunk substring, plus typed `ambiguous_source_span` rejection for short repeated snippets even when the claimed offset lands on one occurrence.
- Added executor coverage for far-off unique offset correction, ambiguous repeated-span rejection, exact claimed short ambiguity rejection, and newline/space normalized correction; verified `python3 -m pytest tests/unit/test_executor.py`, `python3 -m pytest tests/unit/test_executor.py tests/unit/test_contracts.py tests/unit/test_orchestrator.py`, and `make lint`.
- Investigated the follow-up live rerun that failed at `2026-04-30T08:54:12Z` with Anthropic 429 input-token rate limiting; the DB shows executor produced 137 candidates with no executor offset rejections, critic completed 9 batches / 90 reports, and no verifier or report output was reached.

### 2026-04-30 — Executor Offset Prompt Hardening

- Updated all executor prompts to spell out absolute offset arithmetic as `start_char = chunk.start_char + chunk_relative_index`.
- Added explicit instructions to avoid estimated offsets, byte/token/line/markdown offsets, and forbidden offset keys such as `start_text`, `end_char`, `start_byte`, and `end_byte`.
- Added prompt regression coverage so the stricter offset algorithm and forbidden-key rules remain present in the executor prompt pack.
- Added a gitignored local OpenAI override for a `gpt-5.4-mini` global trial with medium-effort `gpt-5.2` on planner, executor, and reconciler, and made the canonical default config test ignore local developer overrides.

### 2026-04-29 — Moonshot Kimi Tool Compatibility

- Fixed Moonshot Kimi structured requests by explicitly disabling Kimi thinking whenever Veritext sends a forced named function `tool_choice`.
- Preserved the forced-tool invariant, strict OpenAI-compatible function schemas, `max_tokens`, and `parallel_tool_calls=False` behavior.
- Updated README/config comments and LLM client unit coverage to document Moonshot's specified-tool/thinking incompatibility.
- Hardened executor payload validation against Kimi returning `start_text` as a typo for the integer `start_char` offset while keeping the advertised tool schema strict and preserving exact-span validation.
- Lowered the canonical Moonshot stage concurrency from 4 to 2 to stay below the observed organization concurrency cap of 3 requests and avoid repeated 429 failures.

### 2026-04-29 — Moonshot Kimi Configuration

- Added `openai_compatible` as a first-class LLM provider with configurable `base_url` and `api_key_env` fields.
- Updated the OpenAI SDK client creation path to support OpenAI-compatible endpoints such as Moonshot while preserving forced tool calls, strict schemas, and effective-model audit logging.
- Switched canonical `config/default.yaml` to Moonshot Kimi K2.6 through `https://api.moonshot.ai/v1`, using `MOONSHOT_API_KEY` and `kimi-k2.6` by default.
- Omitted normal OpenAI `temperature` and `reasoning_effort` request parameters for Kimi model IDs so Moonshot can apply Kimi K2.6 defaults, including thinking enabled by default.
- Removed references to unavailable `kimi-k2-thinking`; Kimi configuration now uses `kimi-k2.6` only.
- Aligned Kimi request parameters with Moonshot docs by sending `max_tokens`, explicit `thinking: {"type": "enabled"}` through the OpenAI SDK `extra_body` escape hatch, and no `temperature` or OpenAI-only `reasoning_effort`.
- Reworked `.env` and `.env.example` so they contain API keys only, with `MOONSHOT_API_KEY` as the active key name and provider/model settings kept in YAML.
- Updated README and config tests for the Moonshot Kimi setup.
- Cleaned up `src/extractor/llm/client.py` by centralizing OpenAI-compatible provider routing and extracting OpenAI/Kimi request construction into focused helper functions without changing forced-tool behavior.

### 2026-04-29 — Medium Research Recall Config Adjustment

- Reviewed the `medium-research-1` live audit run after the final report returned 25 high-precision data points but missed later document sections.
- Confirmed chunking and executor scheduling ran across two chunks with all four executor lenses called on each chunk.
- Found chunk 0 produced 75 executor candidates while chunk 1 produced zero candidates across `entity`, `event`, `claim`, and `number` despite clean `tool_calls` completions.
- Confirmed the approved extraction schema covered the missed later-section fact types, including operational metrics, segment revenue, risk disclosures, commercial contract terms, capital allocation, personnel changes, and project milestones.
- Raised the canonical OpenAI completion budget from 16,384 to 32,768 tokens and restored `reasoning_effort` from `low` to `medium` to improve recall on dense later chunks while preserving forced tool-use behavior.
- Switched the local OpenAI runtime override and example docs from `gpt-5.2` to `gpt-5-mini` for lower-cost development runs.
- Added typed per-stage LLM overrides keyed by stage group (`planner`, `executor`, `critic`, `verifier`, `reconciler`) and routed both Anthropic/OpenAI requests through the resolved stage settings.
- Configured local/example OpenAI runs to use `gpt-5-mini` globally while promoting `executor` and `reconciler` calls to `gpt-5.2`, with audit logs recording the effective model used for each call.
- Documented cheap, balanced, and highest-quality model presets in `.env.example`, README, and local `.env` comments so stage-specific model choices are easy to switch without code changes.
- Updated the balanced model preset to promote `planner` alongside `executor` and `reconciler`, reflecting the stage quality priority of executor recall first, planner schema quality second, and reconciler merge quality third.
- Added `llm.stage_overrides: {}` to canonical `config/default.yaml` and created `config/local.example.yaml` with the OpenAI balanced preset so YAML config users can switch models without relying on environment variables.
- Promoted the OpenAI balanced preset into canonical `config/default.yaml`: `gpt-5-mini` globally with `gpt-5.2` overrides for planner, executor, and reconciler.

### 2026-04-29 — OpenAI Live Smoke Offset Rejection

- Investigated a live OpenAI smoke run that reached `executor.event` and failed on malformed candidate offset validation.
- Moved executor LLM boundary handling so internally inconsistent source offsets are recorded as explicit `invalid_source_offsets` candidate rejections instead of aborting the batch with a raw Pydantic validation error.
- Added focused executor test coverage for malformed payload offsets and verified related executor, contract, audit, and LLM-client tests.
- Added OpenAI strict-tool schema adaptation so nullable optional fields are still included in each object schema's `required` list, fixing the `critic.corrected_candidate` 400 response without weakening Pydantic contracts.

### 2026-04-29 — Phase 0 Bootstrap

- Created the required repository layout under `src/extractor/`, `prompts/`, `tests/`, `config/`, and `evals/`.
- Added `pyproject.toml` with required runtime and test dependencies.
- Added `.gitignore`, `README.md` skeleton, and `Makefile` with `test`, `lint`, and `smoke` targets.
- Added minimal bootstrap tests for scaffold integrity and package importability.
- Verified `make test`, `make lint`, and `make smoke` all pass.
- Decision recorded: selected `pdfplumber` over `pypdf` for higher-fidelity PDF extraction in later ingestion work.

### 2026-04-29 — Project Operating Docs

- Added `AGENTS.md` with short conventions for phase discipline, architecture, configuration, prompts, invariants, testing, and auditability.
- Added this `PROGRESS.md` file to track completed phases and session updates.
- Phase 1 has not started.

### 2026-04-29 — Phase 1 Data Contracts

- Added Pydantic v2 contracts for documents, chunks, source spans, extraction plans, lens candidates, critic reports, verifier reports, data points, run manifests, and LLM call logs.
- Added supporting contract types for page spans, category fields, lens budgets, chunk policy, critic issues, and rejection reasons.
- Enforced strict validation for confidence ranges, offsets, UTF-8 byte ranges, non-blank identifiers, immutable models, duplicate schema entries, candidate/source identity, verifier rejection reasons, run completion timing, and LLM call metrics.
- Added unit tests covering all Phase 1 contract validation behavior.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Agent Convention Update

- Updated `AGENTS.md` with stricter coding conventions for typed stage functions, stage-boundary models, comments, explicit errors, stable provenance, and focused tests.
- Added modification discipline rules requiring agents to avoid unrelated edits, avoid opportunistic refactors, preserve local changes, and ask before edits that could affect invariants.
- Phase 2 has not started.

### 2026-04-29 — Phase 2 Configuration & Logging

- Added canonical `config/default.yaml` for runtime tuning values.
- Added frozen Pydantic config models for LLM, chunking, execution, audit, logging, prompt paths, and run context values.
- Added configuration loading with `default.yaml` as the base, optional `local.yaml` overrides, and `VERITEXT_*` nested environment overrides.
- Added explicit configuration errors for missing/malformed YAML and conflicting environment override paths.
- Added structlog JSON logging setup with timestamp, level, logger name, and context variable merging.
- Added contextvars-based run context helpers that propagate `run_id`, `doc_id`, and `audit_db_path` through async tasks and structured logs.
- Added Phase 2 unit tests covering config precedence, validation failures, canonical default loading, JSON log output, and async run context propagation.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 3 Audit Storage

- Added an async `aiosqlite` audit store with schema initialization and schema version tracking.
- Added SQLite tables for run manifests, documents, chunks, extraction plans, LLM call logs, lens candidates, critic reports, verifier reports, data points, and candidate rejections.
- Stored each audited contract as full Pydantic JSON payload while also indexing stable IDs, run/doc IDs, status, stage, and ordering fields for retrieval.
- Added explicit duplicate and provenance protection through primary keys, unique constraints, and foreign keys.
- Added run manifest update support that fails loudly when the target run does not exist.
- Added `CandidateRejection` audit records so rejected candidates can be persisted with non-empty typed reasons.
- Added Phase 3 unit tests covering schema creation, contract round-trips, duplicate failures, orphaned provenance failures, manifest updates, and rejected-candidate logging.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 4 LLM Client

- Added documented placeholder prompt files for every declared LLM stage under `prompts/`.
- Added prompt loading that maps stages to prompt files, requires intent, typed inputs, output tool schema, failure modes, and prompt sections, and preserves prompt text for hashing.
- Added `max_output_tokens` to LLM configuration so Anthropic output limits remain configured rather than hardcoded.
- Added a direct Anthropic SDK client wrapper in `src/extractor/llm/client.py`.
- Enforced forced tool use by sending Anthropic `tool_choice` and rejecting responses without exactly one matching `tool_use` block.
- Validated structured tool input with caller-supplied Pydantic output models and added tests proving free-text JSON responses are not parsed.
- Added LLM call audit logging with prompt hash, token metrics, cache metrics, latency, stop reason, stage, model, and tool name.
- Added Phase 4 unit tests covering prompt loading, default prompt placeholders, forced tool-use request shape, structured output validation, audit logging, free-text rejection, and wrong-tool rejection.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 5 Ingestion

- Added an async document ingestion API for plain text, Markdown, and PDF sources.
- Added suffix-based format detection with explicit unsupported-format errors.
- Added stable document IDs derived from source SHA-256 bytes.
- Preserved source path, source SHA-256, text SHA-256, source byte length, text byte length, extracted text, and page maps in the `Document` contract.
- Added UTF-8 validation for text and Markdown inputs with explicit errors for invalid sources.
- Added PDF extraction through lazy `pdfplumber` loading, with page text joined by stable separators and page-level character/UTF-8 byte offsets preserved.
- Added empty-extraction failures for empty text inputs and PDFs with no extracted page text.
- Added optional audit persistence via `AuditStore.record_document`.
- Added Phase 5 unit tests covering text hashing and offsets, stable IDs, Markdown detection, audit persistence, PDF page offsets, unsupported formats, empty sources, and invalid UTF-8.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 6 Chunking

- Added an async token-aware chunking API using configured `tiktoken` encodings.
- Added stable chunk IDs derived from document identity, text hash, chunk index, byte offsets, and token offsets.
- Preserved source character offsets, UTF-8 byte offsets, token offsets, document ID, chunk index, and exact chunk text in the `Chunk` contract.
- Added configured window and overlap handling with deterministic token-window advancement.
- Added UTF-8 boundary protection for tokenizer cases where one character spans multiple tokens.
- Added optional audit persistence via `AuditStore.record_chunk`.
- Added explicit chunking errors for unknown tokenizers, missing `tiktoken`, tokenizer byte reconstruction mismatches, and non-advancing windows.
- Added Phase 6 unit tests covering token windows, overlap, stable IDs, Unicode boundary preservation, audit persistence, and unknown-tokenizer failures.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 7 Planning

- Added typed planner output models for document classification, schema proposal, schema critique, strategy selection, and budget allocation.
- Added an async `create_extraction_plan` planner service that runs five forced-tool LLM calls in order.
- Built planner stage inputs from typed document, chunk, domain-hint, and prior-stage output models.
- Enforced schema critique acceptance before strategy and budget planning continue.
- Built final `ExtractionPlan` from approved categories, selected lenses, configured chunk policy, and allocated budget.
- Preserved configured chunk window/overlap values instead of allowing prompt output to hardcode runtime tuning.
- Merged caller-provided and classifier-produced domain hints while preserving order and removing duplicates.
- Added validation that all chunks belong to the planned document before any LLM calls run.
- Added optional audit persistence for LLM call logs and final extraction plans.
- Added Phase 7 unit tests covering planner call order, forced-tool request names, prompt/user content, LLM audit logs, final plan persistence, failed schema critique handling, missing lens budget rejection, and chunk/document identity checks.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 8 Executor

- Added typed executor models for per-chunk stage input, extracted candidate payloads, candidate batches, task results, and aggregate execution results.
- Added an async `execute_plan` service that runs forced-tool executor LLM calls for each enabled lens over each chunk.
- Added configured chunk-level concurrency via `ExecutionConfig.max_chunk_concurrency`.
- Enforced executor budgets before LLM calls so lens call limits cannot be silently exceeded.
- Added validation that all executor chunks belong to the extraction plan document.
- Converted LLM tool outputs into stable `LensCandidate` records with deterministic candidate IDs, exact source spans, confidence, lens, category, field, and executor call provenance.
- Validated candidate categories and fields against the approved extraction plan schema.
- Validated candidate source spans against chunk character and UTF-8 byte offsets.
- Persisted both accepted and rejected candidates to the audit store, with rejected candidates logged as `CandidateRejection(stage="executor")` and explicit rejection reasons.
- Added `executor` as a first-class candidate rejection stage.
- Added Phase 8 unit tests covering accepted/rejected candidate persistence, forced-tool request names, LLM audit logs, invented-span rejection, category rejection, insufficient-budget failure, and chunk/document identity checks.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 9 Critic

- Added typed critic models for per-candidate stage input, LLM critic payloads, task results, and aggregate critic results.
- Added an async `review_candidates` critic service that runs forced-tool critic LLM calls for each executor-accepted candidate.
- Added configured candidate-level concurrency via `ExecutionConfig.max_stage_concurrency`.
- Validated critic inputs against extraction plan run/document identity, approved schema, provided chunk context, and exact source spans before any LLM calls run.
- Converted critic tool outputs into stable `CriticReport` records with call provenance, plausibility score, issues, acceptance state, and optional corrected candidates.
- Validated corrected candidates before acceptance, preserving stable candidate/run/document/chunk/lens/executor provenance, approved schema membership, and exact chunk-backed source spans.
- Rejected invalid corrections without silent drops by recording failed critic reports and `CandidateRejection(stage="critic")` records with explicit typed reasons.
- Persisted critic LLM call logs, critic reports, and critic-stage candidate rejections to the audit store.
- Added Phase 9 unit tests covering accepted/rejected critic persistence, forced-tool request names, LLM audit logs, valid correction acceptance, invalid correction rejection, and candidate/plan identity checks.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 10 Verifier

- Added typed verifier models for per-candidate stage input, LLM verifier payloads, task results, and aggregate verification results.
- Added an async `verify_candidates` service that runs forced-tool verifier LLM calls for each critic-accepted candidate.
- Required each verifier candidate to have exactly one accepted critic report before any verifier LLM call runs.
- Validated candidate run/document identity, provided chunk context, and accepted critic corrections before verification.
- Built verifier stage inputs from the extraction plan, candidate, accepted critic report, and source chunk context.
- Converted verifier tool outputs into stable `VerifierReport` records with call provenance, span/category verification flags, alignment score, acceptance state, and rejection reasons.
- Added deterministic source-span and schema alignment checks that can override an accepted LLM output when invariants fail.
- Persisted verifier LLM call logs, verifier reports, and `CandidateRejection(stage="verifier")` records with explicit typed reasons.
- Added Phase 10 unit tests covering accepted/rejected verifier persistence, forced-tool request names, LLM audit logs, source-span override rejection, missing critic acceptance, and critic correction mismatch checks.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 11 Reconciler

- Added typed reconciler models for whole-run stage input, reconciled data point payloads, rejected candidate payloads, reconciliation batches, and aggregate reconciliation results.
- Added an async `reconcile_candidates` service that runs one forced-tool reconciler LLM call over verifier-accepted candidates.
- Required every reconciler candidate to have exactly one accepted critic report and exactly one accepted verifier report before the LLM call runs.
- Validated candidate run/document identity, duplicate candidate IDs, accepted critic corrections, and report/run provenance before reconciliation.
- Converted reconciliation output into stable `DataPoint` records with source spans derived from selected source candidates rather than model-supplied offsets.
- Preserved contributing candidate IDs, accepted critic report IDs, accepted verifier report IDs, and stable reconciliation decision IDs on each data point.
- Added conflict handling for explicit candidate rejection, contradictory contribute/reject output, duplicate data point assignment, schema mismatches, and unknown candidate references.
- Ensured no verified candidate is silently dropped by logging omitted candidates as `CandidateRejection(stage="reconciler")` with explicit typed reasons.
- Persisted reconciler LLM call logs, final data points, and reconciler-stage candidate rejections to the audit store.
- Added Phase 11 unit tests covering data point persistence, explicit conflict rejection, omitted candidate rejection, missing verifier provenance, unknown output candidate IDs, forced-tool request names, and LLM audit logs.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 12 Reporter

- Added typed reporter models for final extraction reports and report write results.
- Added an async `write_report` service that validates final reconciled data points before output serialization.
- Added deterministic JSON report rendering with stable data point ordering, output data point IDs, report schema version, generated timestamp, and full `DataPoint` payloads.
- Added output SHA-256 and byte-length reporting for auditable artifact verification.
- Added audit readback checks requiring the run manifest and every serialized data point to match the audit store before writing output.
- Added atomic local report writes through a temporary file and replace operation.
- Added run manifest completion with `status="completed"`, `completed_at`, and serialized output data point IDs after the report is written.
- Added explicit reporter errors for failed manifests, run/document identity mismatches, duplicate data point IDs, missing audited data points, stale audit manifest state, and directory output paths.
- Added Phase 12 unit tests covering JSON serialization, manifest completion, output hash/byte metadata, audit-store readback, missing audited data points without output writes, manifest/data point mismatch, and failed-run rejection.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 13 Orchestrator

- Added typed orchestrator result models for full pipeline outputs from document ingestion through final report writing.
- Added an async `run_extraction_pipeline` service that wires ingestion, chunking, planning, execution, critic review, verification, reconciliation, and reporting in order.
- Added audit store lifecycle management around the full pipeline using configured audit database paths.
- Added run manifest creation, transition to running, completion through reporter output, and failed status updates when later stages raise.
- Bound run context after document ingestion so downstream stage work has run/document/audit identifiers.
- Passed configured chunking, execution, prompt, audit, and LLM settings through each stage without hardcoded runtime tuning values.
- Preserved optional caller-provided run IDs and domain hints while generating run IDs when omitted.
- Added Phase 13 unit tests covering an end-to-end deterministic pipeline run, full stage audit log ordering, final report output, completed manifest persistence, and failed manifest persistence on planner rejection.
- Verified `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 14 CLI

- Added an `argparse` command-line entrypoint for running the orchestrated extraction pipeline.
- Added support for source document paths, required report output paths, optional config directories, local config suppression, stable run IDs, and repeated domain hints.
- Added package module execution via `python -m extractor.cli`.
- Added a `veritext` console script entrypoint in `pyproject.toml`.
- Loaded canonical configuration through the existing config loader and initialized configured logging before pipeline execution.
- Surfaced successful runs as deterministic JSON summaries containing run ID, document ID, status, audit database path, report path, output SHA-256, output byte length, data point count, and output data point IDs.
- Added explicit CLI errors for missing source documents and non-zero process returns for command failures.
- Added Phase 14 unit tests covering summary rendering, config-driven pipeline invocation, domain hint forwarding, missing-source failure, and console script registration.
- Verified `PYTHONPATH=src python3 -m extractor.cli --help`, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 15 Evaluations

- Added a typed `extractor.evals` package for source-backed evaluation cases, expected data points, thresholds, metric results, data point matches, and invariant violations.
- Added evaluation loading that resolves fixture-relative source paths, computes source SHA-256 values, validates UTF-8 source text, and rejects bad expected provenance before scoring.
- Added a scoring harness that separates extraction precision/recall/F1 from exact provenance recall and records source-span invariant violations for text, byte, and bounds mismatches.
- Added `python -m extractor.evals` and `veritext-eval` entrypoints that emit deterministic JSON results and return non-zero status for failed evaluations.
- Added a minimal financial-update fixture with source text, expected data points, strict thresholds, and a passing example report.
- Updated README evaluation usage and package scaffold tests.
- Added Phase 15 unit tests covering passing fixtures, missing/false-positive scoring, source-span invariant failures, fixture provenance validation, eval CLI output, and console script registration.
- Verified `python3 -m pytest tests/unit/test_evals.py`, `PYTHONPATH=src python3 -m extractor.evals evals/fixtures/minimal_financial_update/expected.json evals/fixtures/minimal_financial_update/report.example.json`, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 16 Prompt Pack v1

- Replaced placeholder prompt bodies for all planner, executor, critic, verifier, and reconciler stages with operational prompt instructions.
- Kept required prompt contract sections intact while adding stage-specific rules for conservative extraction, approved schema usage, forced tool calls, explicit rejection behavior, and exact provenance.
- Added executor prompt rules requiring absolute document character offsets, absolute UTF-8 byte offsets, exact `source_text` copying, and candidate omission when offsets are uncertain.
- Added verifier prompt rules for accepted/rejected consistency, exact span grounding, schema alignment, and typed rejection reason codes.
- Added reconciler prompt rules requiring every verified candidate to be accounted for exactly once as a data point contributor or explicit rejection.
- Added contract-obligation and policy-control eval fixtures with source text, expected data points, strict thresholds, and passing example reports.
- Updated prompt tests to assert active prompts are non-placeholder operational prompts and include required provenance/accounting rules.
- Updated eval tests to score all included example fixtures.
- Updated README status, evaluation fixture coverage, and prompt pack notes.
- Verified `python3 -m pytest tests/unit/test_evals.py tests/unit/test_llm_client.py`, all three `PYTHONPATH=src python3 -m extractor.evals ...` fixture checks, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 17 Prompt Hardening

- Added concrete decision examples and anti-patterns to planner prompts for classification, schema proposal, schema critique, lens selection, and budget allocation.
- Added few-shot examples to all executor prompts, including valid extraction examples and explicit rejection examples for sample, superseded, historical, inferred, and schema-mismatched evidence.
- Added executor preflight checklists requiring approved category/field names, exact `source_text`, exact absolute character offsets, exact UTF-8 byte offsets, and reviewer-verifiable source support.
- Added adversarial checklists and examples to critic and verifier prompts for invented evidence, wrong schema, overbroad spans, superseded facts, sample entities, negation, and accepted/rejected consistency.
- Added reconciler duplicate-merge, conflict-rejection, separate-fact, and no-silent-drop examples plus a final audit checklist requiring every input candidate to be accounted for exactly once.
- Added a hard mixed-distractor eval fixture containing superseded numeric guidance and a sample entity that should not be extracted.
- Updated eval tests to score the new hard fixture and assert its distractors are not expected outputs.
- Updated prompt tests to require few-shot examples, rejection examples, adversarial checklists, and reconciler audit checklists.
- Updated README status and prompt/eval fixture notes for the hardened prompt pack.
- Verified `python3 -m pytest tests/unit/test_evals.py tests/unit/test_llm_client.py`, all four `PYTHONPATH=src python3 -m extractor.evals ...` fixture checks, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Phase 18 Multi-provider LLM Client

- Added `openai` as a supported `LLMConfig.provider` value while keeping Anthropic as the canonical default provider.
- Updated `LLMClient` to route requests by provider while preserving the existing public `complete_structured` API used by every pipeline stage.
- Preserved direct SDK usage only: Anthropic calls use `AsyncAnthropic`; OpenAI calls use `AsyncOpenAI`.
- Implemented OpenAI Chat Completions forced function tool calls with `tool_choice`, `strict` function schema parameters, `parallel_tool_calls=False`, and Pydantic validation of decoded tool arguments.
- Preserved Anthropic forced tool-use behavior and audit logging unchanged for existing tests and pipeline stages.
- Added OpenAI usage accounting to `LLMCallLog` for prompt tokens, completion tokens, cached prompt tokens, finish reason, prompt hash, model, latency, and tool name.
- Added explicit OpenAI tool-call errors for missing tool calls, wrong function names, malformed tool argument JSON, and non-object tool argument payloads.
- Added `openai` as a project dependency and updated architecture docs to allow direct Anthropic and OpenAI SDK calls.
- Added README configuration example for `llm.provider: openai` with a GPT model.
- Added unit tests covering OpenAI config loading, dependency declaration, forced OpenAI tool call request shape, audit logging, missing-tool rejection, wrong-tool rejection, and malformed-argument rejection.
- Verified `python3 -m pytest tests/unit/test_llm_client.py tests/unit/test_config.py tests/unit/test_bootstrap.py`, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Environment File Support

- Added `.env.example` with OpenAI defaults for `VERITEXT_LLM__PROVIDER=openai`, `VERITEXT_LLM__MODEL=gpt-5.2`, and SDK key placeholders.
- Updated `.gitignore` so `.env` and `.env.*` stay local while `.env.example` remains trackable.
- Added `.env` loading to `load_config()` for normal runtime configuration while keeping explicit test env mappings isolated from local files.
- Applied `.env` values as `VERITEXT_*` configuration overrides and exposed SDK keys such as `OPENAI_API_KEY` through `os.environ` without overriding values already present in the shell.
- Added explicit `.env` parse errors for malformed entries.
- Updated README local provider setup notes.
- Verified `python3 -m pytest tests/unit/test_config.py tests/unit/test_cli.py tests/unit/test_bootstrap.py`, `make test`, `make lint`, and `make smoke` all pass.

### 2026-04-29 — Audit Rerun Idempotency Fix

- Fixed reruns over the same source document by making exact duplicate document and chunk audit writes idempotent.
- Preserved audit integrity by still rejecting conflicting payloads for stable document IDs and chunk IDs.
- Kept run manifests strict, so reusing the same `run_id` still fails rather than overwriting a prior run.
- Added audit-store tests covering idempotent document/chunk writes and conflicting stable-ID payload rejection.
- Verified `python3 -m pytest tests/unit/test_audit_store.py`, `make test`, `make lint`, and `make smoke` all pass.
