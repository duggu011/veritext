# Veritext Extraction Quality & Cost Strategy

Snapshot of known issues observed across the Sonnet 4.6 runs on the 274-word `medium_research_brief` fixture, the fixes already shipped, and the open work ranked by leverage.

## Run baseline (latest interrupted run, `medium-research-1`)

| Metric | Value |
|---|---|
| Doc size | 274 words, 1 chunk |
| Executor candidates emitted | 144 |
| Executor-stage offset rejections | **119 (83%)** |
| Reached critic | 25 |
| Critic-accepted | 23 |
| Verifier-accepted | 23 |
| Final data points | 12 |
| LLM calls | 15 (5 planner + 3 executor + 3 critic + 3 verifier + 1 reconciler) |
| Approx cost | ~$0.10-0.15 (down from ~$0.50 pre-batching) |

---

## Problem 1 — Executor offset hallucinations (CRITICAL, blocks recall)

**Symptom.** 83% of executor candidates rejected with `invalid_source_offsets` / `invented_span`. The model claims `start_char=383` for `"Fleet generation"` but the actual chunk slice at 383 is `"st time in eight"`. Off by 30 to 200+ chars, not 1-2.

**Root cause.** Sonnet (and likely all LLMs) cannot reliably count UTF-8 character positions in long text. The current `_locate_source_text` corrects within a ±32-char window — fine for whitespace boundary drift, useless when the model invents the position outright.

**Why bumping the window further fails.** At ±100+ chars on rich text, multiple substrings collide (e.g., `"Q1 2026"` appears in five places). Uniqueness constraint then rejects the candidate anyway, and we burn more CPU on every search.

**Fix (planned, not shipped).** Invert the locator priority in `src/extractor/executor/service.py:_locate_source_text`:
1. Try `source_text` at claimed `start_char` first (cheap path when the model is right).
2. On miss, search the **entire chunk** for `source_text`.
3. If exactly one match → accept that absolute offset.
4. If 0 or 2+ matches → reject with a typed reason.

This makes the model responsible only for emitting an exact `source_text`. Offset arithmetic moves fully server-side. Expected outcome: rejection rate drops from 83% to <10%, executor → critic flow opens up, final data points jump from ~12 to ~25-35 on the same input.

**Risk.** Ambiguous spans (`"Q1 2026"` × 5 occurrences) get rejected uniformly — that is correct: the model must disambiguate by emitting wider unique spans.

---

## Problem 2 — Reconciler payload stringification (HIGH, run-killer)

**Symptom.** Pydantic crash:
```
data_points: input_value='[{"category":"FinancialM...rejected_candidates":[]', input_type=str
rejected_candidates: Field required
```
Sonnet returned the full output object as a JSON-encoded *string* in the `data_points` field instead of as an array. One bad call kills the entire run.

**Fix (shipped).** Added `mode="before"` validator on `ReconciliationBatch` in `src/extractor/reconciler/models.py` that JSON-decodes string-valued payloads or fields. Also tightened `prompts/reconciler.md` and `prompts/verifier.md` with: *"Tool inputs are structured JSON. Pass `data_points` and `rejected_candidates` as actual arrays, never as JSON-encoded strings."*

**Open follow-up.** Same defensive `mode="before"` coercion should be added to other top-level batch payloads (`CriticBatchReviewPayload`, `VerifierBatchReviewPayload`) — Sonnet has demonstrated the bug, the fix is a 6-line copy-paste.

---

## Problem 3 — No retry on Pydantic ValidationError (MEDIUM)

**Symptom.** `ExecutionConfig.max_llm_attempts` exists in the config but is never read. The Anthropic SDK's `max_retries=3` only fires on transient HTTP errors, not on tool-input validation failures. So Sonnet's stringification bug (Problem 2) crashes the run on the first occurrence even though a single retry would likely succeed.

**Fix (not shipped).** In `src/extractor/llm/client.py:complete_structured`, wrap the inner call in a retry loop bounded by `execution_config.max_llm_attempts` that catches `pydantic.ValidationError` and re-issues the request (with a slightly nudged user_content reminding the model the prior response was malformed). Log each retry as its own `LLMCallLog` row with `attempt=n`.

**Why this matters.** With Problem 1 fixed, the run's surface area expands (more candidates → more critic batches → more verifier batches → more chances for a single bad response to nuke everything). Defense-in-depth.

---

## Problem 4 — Cost (MEDIUM, partially addressed)

**Before batching.** ~80 LLM calls per 274-word run on Sonnet 4.6, ~$0.50.

**After critic + verifier batching.** ~15 calls per run, ~$0.10-0.15. **5× reduction shipped.**

| Stage | Calls per run | Status |
|---|---|---|
| Planner | 5 (sequential) | Not yet batched |
| Executor | 4 × N_chunks | Structural; one call per lens per chunk |
| Critic | ceil(accepted/10) per chunk | **Batched** |
| Verifier | ceil(accepted/10) per chunk | **Batched** |
| Reconciler | 1 | Already single |

**Open opportunity (planner collapse).** Two moves:
- **Safe (5 → 4):** Merge `select_strategy` + `allocate_budget` into one tool call. They're mechanical, sequentially dependent, and feed each other directly. Saves one round-trip per run.
- **Aggressive (4 → 3):** Merge `propose_schema` + `critique_schema` into a "propose-and-critique" call. **Risk:** a model self-reviewing its own proposal loses adversarial skepticism that catches schema bloat. Don't ship without measuring quality regression.

**Not worth touching.** Executor lens fan-out — the 4 lenses (claim, entity, event, number) each have tailored prompts and adversarial checklists. Merging into one "extract everything" call empirically degrades recall, especially on `number` and `event`.

**Scaling formula post-batching.** `~6 + 14 × N_chunks` calls per run.
- 274-word doc (1 chunk): ~15 calls, ~$0.10
- 1000-word doc (2 chunks): ~30-35 calls, ~$0.20-0.35
- 5000-word doc (6 chunks): ~90 calls, ~$0.80-1.20

---

## Problem 5 — Hidden run failure modes (LOW, hygiene)

**Symptom.** Latest run shows `status='running'` with no `completed_at` — possibly killed mid-stream, possibly still in progress. The DB doesn't distinguish.

**Fix (not shipped).** Add a heartbeat or last-activity timestamp on `run_manifests`. On startup, the CLI could detect stale `running` runs and either resume or mark them `failed` with an `interrupted` reason.

---

## Problem 6 — Single-chunk cap on per-call efficiency (informational)

The current batching groups by `chunk_id` — so the maximum batch size is bounded by candidates *per chunk*. On the small fixture this is fine (one chunk → one large batch). On a multi-chunk doc with 4 candidates per chunk, batching gives no benefit because each batch already fits in one call.

**Not a bug.** Cross-chunk batching would force the model to juggle multiple chunk contexts in one call, hurting accuracy. Keep this contract.

---

## Suggested order of next work

1. **Ship Problem 1 fix** (chunk-wide search in `_locate_source_text`). Single biggest quality win available. ~30 lines of code.
2. **Apply Problem 2 defensive coercion** to critic + verifier batch payloads. ~12 lines, prevents future run-killers.
3. **Wire Problem 3 retry loop** for `ValidationError`. ~25 lines, defense-in-depth.
4. **Run on the 274-word fixture**, expect ~25-35 data points and ~15 LLM calls.
5. **Run on a 1000-word doc**, expect ~30-35 calls and confirm scaling formula.
6. **Then** consider planner collapse (Problem 4 safe move) if cost still matters.

## Out of scope (intentionally not pursued)

- Verifier deterministic short-circuit (skip LLM when span match is exact, category is approved, alignment is trivially clean) — would cut verifier calls further but breaks the audit invariant of "every candidate got an LLM-reviewed verifier report." Not worth the audit complication.
- Cross-chunk critic/verifier batching — sacrifices grounding accuracy.
- Switching providers mid-run for cost — operational complexity, marginal savings at current scale.
- Document-level caching of planner output across re-runs — useful for evals, premature for production.
