# Veritext - Agent Operating Rules

This file is kept **byte-identical** between `AGENTS.md` and `CLAUDE.md`. Edit both together in the same commit. Drift between them is a bug.

Veritext is a research-grade document extraction engine. Optimize for extraction accuracy, auditability, and invariant enforcement. Speed, elegance, token cost, and convenience are secondary.

Where this file conflicts with `WORKFLOW.md`, this file wins.

---

## Session Start

Every session, before implementation work:

1. Read `docs/boards/README.md`.
2. Read the active board listed there, if it exists.
3. Read the active spec listed by the board, if it exists.
4. Read the relevant `docs/PROJECT_OVERVIEW.md` roadmap/domain section for the active phase.
5. Check the active board for OPEN issues.
6. Tell the operator: `Phase NN, Step K of N. Open issues: N. Next up: <description>. Ready?`
7. Wait for operator confirmation before implementation.

If the active board does not exist, read `WORKFLOW.md` and follow the board/spec creation process. Do not infer phase scope from chat alone.

---

## Session Goal

For long-running Codex sessions, the operator may set `/goal` after the session-start read and before implementation begins. Use this as advisory steering only:

```text
Advance Veritext one approved board phase at a time into a provenance-first extraction engine for high-stakes documents. Preserve domain-neutral runtime behavior, exact source/offset provenance, Pydantic contracts, auditability, and invariants I1-I9. Use the active board/spec as source of truth, stop at gates, avoid fixture-specific fixes, and prioritize measurable extraction trust over speed, UI, cost, or convenience. Current focus: Phase NN <active phase>.
```

Update `Current focus` from `docs/boards/README.md` at session start. A session goal never overrides this file, the active board/spec, `docs/PROJECT_OVERVIEW.md`, `PROGRESS.md`, or invariants I1-I9. Do not treat `/goal` state as a durable project artifact; durable scope belongs in boards, specs, and progress logs.

---

## Operator Trust Resume

This repository currently runs in operator-trust resume mode unless the operator says `gated mode`, `manual approval mode`, `pause`, or `stop`.

In operator-trust resume mode, after completing the Session Start reads and reporting `Phase NN, Step K of N. Open issues: N. Next up: <description>.`, continue automatically instead of waiting for a separate `Ready?` confirmation when all of these are true:

- The next action is already defined by the active board, approved spec, or board/spec creation workflow.
- The action stays inside the active phase or the operator's explicit request.
- There are no OPEN high-severity issues.
- The action does not weaken I1-I9, change architecture rules, or require a product/design decision with multiple valid options.
- Required verification and commits will still be performed.

If the active phase has a draft spec but no board, operator-trust resume mode is standing permission to perform spec-readiness checks, mark the spec approved, create the board, update tracking files, commit the board-opening change, and proceed to the first board step. Stop instead if the draft contains open questions, placeholders outside allowed prompt blocks, architecture-rule changes, invariant risk, or unclear gate interpretations.

Operator-trust resume mode never overrides Hard Stops. It also does not accept a completed phase, start the next phase after a phase gate, or approve architecture-rule amendments unless the operator explicitly says so.

---

## Session End

Before ending a session:

1. Update the active board Current Status.
2. Add a Work Log entry with what changed, verification, issues, and next step.
3. Update References for every created or modified file.
4. Update Tests with exact commands and results.
5. Update `PROGRESS.md` for the session or accepted phase.
6. Run `git status --short` and `git log --oneline -10`.
7. Commit completed board steps unless the operator explicitly says not to.
8. Tell the operator where the next session picks up.

If a board marks a step DONE, a matching commit must exist or the uncommitted state must be handed back explicitly.

---

## Mission

Optimize for high-stakes, audit-heavy document workflows where exact provenance is mandatory: legal contracts, SEC filings, e-discovery/litigation review, clinical trial documents, FDA labels, regulatory rulings, insurance policies, standards documents, SOC 2/ISO evidence, patents, scientific review papers, and government procurement.

Do not optimize behavior for one fixture, document, company, proper noun, sentence, market sector, or evaluation answer. A fix must be a reusable extraction, provenance, schema, reconciliation, or invariant rule.

If a proposed guardrail depends on document-specific tokens, named entities, industry nouns, or one-off phrasing, stop and redesign around source role, schema semantics, typed contracts, offsets, or auditable invariants.

Non-targets include chatbot RAG, generic summarization, sentiment/opinion extraction, predictive synthesis, search/indexing, low-stakes high-volume content, real-time user-facing pipelines, primary image/audio/video extraction, already-structured data, and open-web crawling.

---

## Pipeline

```text
ingestion -> chunker -> planner -> executor -> dedup -> critic -> verifier -> reconciler -> reporter -> audit store
```

Source lives under `src/extractor/<stage>/`. Tests live under `tests/{unit,integration,smoke}/`.

---

## Phase Discipline

- Follow phases in `docs/boards/README.md` order.
- Stop after each phase report or board gate.
- Do not begin the next phase without an explicit `continue` from the operator.
- Do not merge phases, even when a phase looks small.
- Keep `PROGRESS.md` as the historical phase/session archive.
- Keep the active board current during every working session.
- After completing an accepted phase or task, commit scoped changes with a clear descriptive message unless the operator explicitly says not to.
- Prefer multiple logical commits over one mixed commit when work spans distinct phases or concerns.

---

## Architecture Rules

- Use Python 3.11+ with direct Anthropic and OpenAI Python SDK calls only.
- Do not add LangChain, LlamaIndex, CrewAI, AutoGen, Haystack, DSPy, agent frameworks, web UI, REST API, Docker, CI/CD, vector DBs, embeddings, or fine-tuning hooks.
- Use Pydantic v2 models for all inter-stage contracts.
- Use SQLite through `aiosqlite` for audit state.
- Use `asyncio` for stage-level parallelism.
- Route every LLM call through `src/extractor/llm/client.py`.
- Use forced tool use for structured output; never parse free-text JSON.

---

## Coding Conventions

- Prefer small, typed, async functions with explicit inputs and outputs.
- Use Pydantic models at stage boundaries; do not pass loose dictionaries between stages.
- Keep stage functions independently testable with no hidden global state.
- Do not create new files over 400 lines. If a change would exceed that size, split it into focused modules or subpackages before committing.
- Avoid growing existing oversized files further. When working in a large `service.py`, prefer moving cohesive helper logic into a named sibling module or subpackage such as `validation.py`, `materialization.py`, `routing.py`, or `policies.py`, while preserving public stage interfaces.
- Keep modules cohesive and single-purpose: orchestration, validation, normalization, model materialization, and persistence should not be mixed into one catch-all file when a clean folder/subfolder service structure would make the code easier to test and audit.
- Add concise comments for non-obvious logic, invariant enforcement, audit-chain decisions, and accuracy tradeoffs.
- Do not add comments that merely restate obvious code.
- Keep errors explicit and specific; do not catch broad exceptions to continue past invariant failures.
- Preserve stable IDs, source offsets, and provenance fields whenever transforming data.
- Keep tests close to the behavior being enforced.

---

## Modification Discipline

- Do not modify files outside the active phase or explicit user request.
- Do not refactor unrelated code while implementing a phase.
- Do not change existing behavior unless the phase requires it or a test exposes a defect.
- Do not add document-specific patches to make one run or fixture pass.
- If unrelated local changes exist, leave them intact and work around them.
- If a requested change is unclear and could affect an invariant, ask before editing.

---

## Configuration

- Keep runtime tuning values in `config/`.
- Do not hardcode tuning values in source or tests.
- `config/default.yaml` is canonical.
- `config/local.yaml` and environment variables may override local runs.
- Secrets belong in `.env`; provider/model settings belong in YAML.

---

## Prompt Rules

- Prompt files live in `prompts/`.
- Prompt bodies must remain placeholders until a human fills them.
- The only allowed unfinished-work markers are inside clearly fenced prompt placeholder blocks.
- Each prompt must document intent, typed inputs, output tool schema, and failure modes.

---

## Invariants

Do not weaken I1-I9. Every invariant must be enforced in code and covered by tests when its phase is implemented.

---

## Testing

Run the narrowest relevant tests during development.

Before closing major work when feasible:

```bash
make test
make lint
make smoke
git diff --check
```

No skipped tests are acceptable for final completion unless an approved phase explicitly changes that rule.

---

## Auditability

- No silent drops.
- Log rejected candidates with reasons.
- Preserve provenance from ingestion through final data point output.
- Every LLM call, rejection, stage transition, and final output should remain auditable.

---

## Hard Stops

Stop and ask the operator when:

- A test failure suggests the spec is wrong.
- A change might weaken I1-I9.
- A file does not match what the spec or board says.
- A design decision has multiple valid options.
- You are tempted to patch around a symptom instead of fixing the root cause.
- You find a high-severity issue. Log it on the board, then ask.
- A future roadmap item requires changing architecture rules such as the current web UI, REST API, Docker, CI/CD, vector DB, embedding, or framework bans.

---

## Source Of Truth

| Priority | Source | Purpose |
|---|---|---|
| 0 | `AGENTS.md` / `CLAUDE.md` | Agent operating rules. Must stay byte-identical. |
| 1 | `docs/boards/phase_NN_*.md` | Active phase state, issues, references, tests, and work log. |
| 2 | `docs/boards/README.md` | Active phase pointer, roadmap index, and board template. |
| 3 | `WORKFLOW.md` | Process manual. |
| 4 | `docs/PROJECT_OVERVIEW.md` | Roadmap, target domains, non-targets, and market scope. |
| 5 | `PROGRESS.md` | Historical accepted gate and session archive. |
| 6 | `config/default.yaml` | Canonical runtime configuration. |
