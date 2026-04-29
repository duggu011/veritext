# AGENTS.md

Project conventions for autonomous coding agents working on this repository.

## Mission

Optimize for extraction accuracy, auditability, and invariant enforcement. Speed, elegance, token cost, and convenience are secondary.

## Phase Discipline

- Follow the project phases in order.
- Stop after each phase report.
- Do not begin the next phase without an explicit `continue` from the operator.
- Do not merge phases, even when a phase looks small.
- Keep `PROGRESS.md` current after each working session or accepted phase.

## Architecture Rules

- Use Python 3.11+ with direct Anthropic and OpenAI Python SDK calls only.
- Do not add LangChain, LlamaIndex, CrewAI, AutoGen, Haystack, DSPy, agent frameworks, web UI, REST API, Docker, CI/CD, vector DBs, embeddings, or fine-tuning hooks.
- Use Pydantic v2 models for all inter-stage contracts.
- Use SQLite through `aiosqlite` for audit state.
- Use `asyncio` for stage-level parallelism.
- Route every LLM call through `src/extractor/llm/client.py`.
- Use forced tool use for structured output; never parse free-text JSON.

## Coding Conventions

- Prefer small, typed, async functions with explicit inputs and outputs.
- Use Pydantic models at stage boundaries; do not pass loose dictionaries between stages.
- Keep stage functions independently testable with no hidden global state.
- Add concise comments for non-obvious logic, invariant enforcement, audit-chain decisions, and accuracy tradeoffs.
- Do not add comments that merely restate obvious code.
- Keep errors explicit and specific; do not catch broad exceptions to continue past invariant failures.
- Preserve stable IDs, source offsets, and provenance fields whenever transforming data.
- Keep tests close to the behavior being enforced.

## Modification Discipline

- Do not modify files outside the active phase or explicit user request.
- Do not refactor unrelated code while implementing a phase.
- Do not change existing behavior unless the phase requires it or a test exposes a defect.
- If unrelated local changes exist, leave them intact and work around them.
- If a requested change is unclear and could affect an invariant, ask before editing.

## Configuration

- Keep runtime tuning values in `config/`.
- Do not hardcode those values in source or tests.
- `config/default.yaml` is canonical; `config/local.yaml` and env vars may override it.

## Prompt Rules

- Prompt files live in `prompts/`.
- Prompt bodies must remain placeholders until a human fills them.
- The only allowed unfinished-work markers are inside clearly fenced prompt placeholder blocks.
- Each prompt must document intent, typed inputs, output tool schema, and failure modes.

## Invariants

Do not weaken I1-I9. Every invariant must be enforced in code and covered by tests when its phase is implemented.

## Testing

- Run the narrowest relevant tests during development.
- Run `make test`, `make lint`, and `make smoke` before closing major work when feasible.
- No skipped tests are acceptable for final completion.

## Auditability

- No silent drops.
- Log rejected candidates with reasons.
- Preserve provenance from ingestion through final data point output.
