# CLAUDE.md

Veritext: research-grade document extraction engine. Optimize for accuracy, auditability, and invariant enforcement. Speed/elegance/cost are secondary.

## Pipeline

`ingestion -> chunker -> planner -> executor -> critic -> verifier -> reconciler -> reporter -> audit store`

Source under `src/extractor/<stage>/`. Tests under `tests/{unit,integration,smoke}/`.

## Hard Rules

- Python 3.11+. Direct Anthropic / OpenAI SDK calls only. **No** LangChain, LlamaIndex, CrewAI, AutoGen, Haystack, DSPy, agent frameworks, web UI, REST API, Docker, CI/CD, vector DBs, embeddings, fine-tuning.
- Every LLM call routes through `src/extractor/llm/client.py`. Use forced tool use for structured output; never parse free-text JSON.
- Pydantic v2 models at every stage boundary. No loose dicts between stages.
- SQLite via `aiosqlite` for audit state. `asyncio` for stage-level parallelism.
- Preserve stable IDs, source offsets, and provenance through every transform.
- No silent drops. Log rejected candidates with reasons.
- Do not weaken invariants I1-I9. Enforce in code; cover with tests.

## Phase Discipline

- Follow phases in `PROGRESS.md` in order. Stop after each phase report.
- Do not start the next phase without explicit `continue` from the operator.
- Do not merge phases. Update `PROGRESS.md` after each session.

## Modification Discipline

- Touch only files in the active phase or explicit request.
- No drive-by refactors. Do not change behavior unless the phase requires it or a test exposes a defect.
- Leave unrelated local changes intact and work around them.
- Ask before editing if a change could affect an invariant.

## Configuration

- Tuning values live in `config/`. Never hardcode in source or tests.
- `config/default.yaml` is canonical; `config/local.yaml` and env vars override.
- Secrets only in `.env` (see `.env.example`). Provider/model settings in YAML.

## Prompts

- All prompts in `prompts/`. Each documents intent, typed inputs, output tool schema, failure modes.
- Prompt bodies stay as placeholders until a human fills them. Unfinished-work markers are only allowed inside fenced placeholder blocks.

## Coding

- Small, typed, async functions with explicit inputs/outputs. No hidden global state.
- Comment only non-obvious logic, invariant enforcement, audit decisions, accuracy tradeoffs. Never restate code.
- Errors explicit and specific. Do not catch broad exceptions to skip past invariant failures.

## Testing

```bash
make test    # python3 -m pytest
make lint    # compileall src tests
make smoke   # pytest tests/smoke
```

Run the narrowest relevant tests during development. Run all three before closing major work. No skipped tests in final completion.

## Audit Inspection

```bash
PYTHONPATH=src python3 -m extractor.audit .veritext/audit.sqlite3 --run-id <id> --details
```

