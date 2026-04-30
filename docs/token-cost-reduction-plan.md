# Token-Cost Reduction Plan

Phase-wise implementation plan to reduce per-run cost on `medium_research_brief`
from ~$1.49 (projected, end-to-end) to ~$0.50 without weakening I1–I9, exact
source-span enforcement, audit-DB completeness, or typed contracts.

Source review: see audit DB inspection of `medium-research-1` —
`126,078 in / 33,809 out` across 18 calls before the Anthropic 429, with
`cache_read_tokens=0` on every call.

Work is partitioned into six independently shippable phases. Each phase has a
single LLM-cost lever and is independently revertible. Land in order: caching
first (highest leverage, smallest blast radius), payload trimming next, dedup
and reconciler last.

---

## Phase 19 — Anthropic prompt caching on stable prefixes

**Goal.** Cache the system prompt, tool schema, and stable user-message prefix
(plan + chunk) across repeated critic/verifier/executor/planner calls. Cache
reads bill at 0.1× input rate.

**Why first.** No payload changes, no contract changes, no behavioral changes —
purely a request-shape change in `LLMClient`. Lifts the 429 by collapsing
input-tokens-per-minute on the critic stage.

### Scope

- `LLMClient._complete_anthropic` request shape moves from string `system` and
  string user content to **list-of-blocks** form so each block can carry
  `cache_control={"type": "ephemeral"}`.
- `StructuredLLMRequest` gains an optional `stable_user_prefix: str | None`
  field. When set, the user message becomes two text blocks:
  `[{text: stable_user_prefix, cache_control: ephemeral}, {text: user_content}]`.
  When omitted, request shape is unchanged.
- `system` and `tools` always carry `cache_control` for stages that send
  identical system text and tool schemas across multiple calls (critic,
  verifier, planner.* family).
- New `LLMConfig.prompt_cache_enabled: bool = True` flag in
  `src/extractor/config/models.py` and `config/default.yaml` so the change is
  reversible without code rollback.

### Cache breakpoint plan (max 4 per request)

| Stage | tools | system | user prefix (cached) | user tail (variable) |
|---|---|---|---|---|
| `executor.{lens}` | ✓ | ✓ | plan + chunk JSON | (none — plan+chunk is the whole user msg) |
| `critic` | ✓ | ✓ | plan + chunk JSON | candidates batch JSON |
| `verifier` | ✓ | ✓ | plan + chunk JSON | items batch JSON |
| `reconciler` | ✓ | ✓ | plan + candidates JSON | (rejection list, if any) |
| `planner.classify_document` | ✓ | ✓ | document + chunks | (none) |
| `planner.propose_schema` ... `allocate_budget` | ✓ | ✓ | document + chunks | prior-stage outputs |

### Concurrency / priming

`Semaphore(max_stage_concurrency=4)` causes the first 4 critic batches to fire
in parallel, all paying cache-write rates. To prime the cache deterministically:

- **Critic / verifier:** acquire a one-shot priming lock around the first
  batch. Release the full semaphore once the first call returns (cache populated).
  Implementation: `asyncio.Event` set after batch 0 completes; batches 1..N
  await the event before entering the semaphore.
- **Executor:** 4 calls per chunk, sequential within `Semaphore(max_chunk_concurrency=2)` already — accept ~1 cache miss per concurrent chunk pair.
- **Planner:** already sequential by `await` chain — natural priming.

### Files

- `src/extractor/llm/client.py` — request construction, `cache_control` blocks,
  `LLMCallLog` continues to capture `cache_read_tokens` /
  `cache_creation_tokens` from the existing usage path.
- `src/extractor/llm/__init__.py` — export updated `StructuredLLMRequest`.
- `src/extractor/config/models.py` — add `prompt_cache_enabled`.
- `config/default.yaml` — set `llm.prompt_cache_enabled: true`.
- `src/extractor/critic/service.py` — split user content; add priming
  `asyncio.Event`; pass `stable_user_prefix`.
- `src/extractor/verifier/service.py` — same shape as critic.
- `src/extractor/executor/service.py` — pass `stable_user_prefix` (plan + chunk).
- `src/extractor/planner/service.py` — pass `stable_user_prefix` (document +
  chunks); the per-stage prior-output deltas remain in `user_content`.

### Tests

- `tests/unit/test_llm_client.py`
  - new test: when `prompt_cache_enabled=True` and `stable_user_prefix` is set,
    Anthropic request payload contains `cache_control` on `system[0]`,
    `tools[0]`, and the first user content block.
  - new test: when `prompt_cache_enabled=False`, payload is byte-identical to
    today (regression guard).
  - existing forced-tool tests continue to pass.
- `tests/unit/test_critic.py` — assert second batch in a multi-batch run sees
  `cache_read_tokens > 0` against a mock client that echoes
  `cache_read_input_tokens` in usage.
- `tests/unit/test_orchestrator.py` — extend the end-to-end mock to assert
  every stage with >1 call has at least one `cache_read_tokens > 0` call log.

### Acceptance criteria

- Live rerun of `medium-research-1` shows `cache_read_tokens > 0` on critic
  batches 2..N and verifier batches 2..N.
- No change to accepted/rejected counts or final data points vs a non-cached
  reference run on `minimal_financial_update`.
- Critic input billed cost falls ≥50% on the medium fixture.

### Estimated reduction

Critic input cost: ~60% (mostly cache reads at 0.1× after first batch).
Planner input cost: ~50%.
Executor input cost: ~30%.

---

## Phase 20 — Compact LLM-boundary view models

**Goal.** Stop sending fields the model cannot use: byte offsets,
`run_id`/`doc_id`/`chunk_id`/`executor_call_id`, chunk indexes, budget,
chunk_policy, domain_hints. Audit DB still stores the full strict contracts.

### New view models — `src/extractor/llm/views.py`

```python
class LLMSchemaCard(BaseModel):
    categories: tuple[LLMCategoryCard, ...]   # name, description, fields
    enabled_lenses: tuple[LensName, ...]

class LLMCategoryCard(BaseModel):
    name: str
    description: str
    fields: tuple[LLMFieldCard, ...]

class LLMFieldCard(BaseModel):
    name: str
    value_type: str
    description: str

class LLMChunkView(BaseModel):
    start_char: int
    text: str

class LLMCandidateView(BaseModel):
    id: str                       # short stable token, first 12 hex of candidate_id
    lens: LensName
    category: str
    field_name: str
    value: str
    span_start_char: int
    span_text: str
    confidence: float
```

Each consuming stage builds a `dict[str, LensCandidate]` mapping `id → full
candidate` so server-side expansion is keyed by the short ID.

### Stage-by-stage updates

- **Executor (`src/extractor/executor/service.py`).** `ExecutorStageInput`
  user-content payload uses `LLMSchemaCard` + `LLMChunkView` + `lens`.
  Output schema unchanged. `start_char` arithmetic in the prompt is unchanged
  because `LLMChunkView.start_char` is the same field name.
- **Critic (`src/extractor/critic/service.py`).** `CriticBatchStageInput` →
  `{schema_card, chunk_view, candidates: tuple[LLMCandidateView, ...]}`.
  Server expands the per-`id` decision back to `candidate_id` via the
  view→full mapping.
- **Verifier (`src/extractor/verifier/service.py`).** `VerifierBatchStageInput`
  → `{schema_card, chunk_view, items: tuple[{candidate: LLMCandidateView,
  critic_summary: {accepted: bool}}, ...]}`. Drop `CriticReport` from the
  payload — the model only needs to know the candidate already passed critic.
- **Reconciler (`src/extractor/reconciler/service.py`).** See Phase 23.

### Compact correction shape (critic only)

`RawCorrectedCandidate` (currently 11 fields) compresses to:

```python
class CompactCorrection(BaseModel):
    value: str | None = None
    category: str | None = None
    field_name: str | None = None
    source_start_char: int | None = None
    source_text: str | None = None
```

Service merges the correction over the original candidate keyed by `id`,
then runs the existing `_materialize_correction` validation path against the
strict `LensCandidate` contract. **No span-validation shortcuts.** Identity
fields (`candidate_id`, `run_id`, `doc_id`, `chunk_id`, `lens`,
`executor_call_id`) are preserved by construction.

### Invariant impact

None. `LensCandidate`, `Chunk`, `ExtractionPlan`, `CriticReport` audit shapes
unchanged; views are LLM-boundary projections only.

### Files

- `src/extractor/llm/views.py` (new)
- `src/extractor/executor/{service.py,models.py}`
- `src/extractor/critic/{service.py,models.py}`
- `src/extractor/verifier/{service.py,models.py}`
- `prompts/critic.md`, `prompts/verifier.md`, `prompts/executor/*.md` —
  rewrite the "Read the JSON user input" section to reference the compact
  field names.

### Tests

- `tests/unit/test_llm_views.py` (new) — round-trip view ↔ full contract,
  short-ID stability, candidate map collision rejection.
- `tests/unit/test_executor.py` — assert user_content JSON does NOT contain
  `chunk_id`, `doc_id`, `run_id`, `start_byte`, `end_byte`, `chunk_policy`,
  `budget`, `domain_hints`.
- `tests/unit/test_critic.py` — same payload assertions plus correction
  expansion test.
- `tests/unit/test_verifier.py` — same payload assertions plus
  critic-summary-only assertion.

### Acceptance criteria

- Per-batch non-cached payload size for critic falls from ~2.5k → ~1.4k tokens.
- Existing eval fixtures (`minimal_financial_update`, `contract_obligation`,
  `policy_control`, `mixed_distractor_hard`) all pass with no recall change.

### Estimated reduction

Critic + verifier non-cached tail: ~45% smaller. Compounds with Phase 19's
caching multiplier.

---

## Phase 21 — Compact critic / verifier output schema

**Goal.** Replace verbose model-authored prose with `{id, decision, code,
evidence?}` records. Server-side expansion rebuilds full `CriticReport` /
`VerifierReport` so audit DB stays unchanged.

### New output schema

```python
class CriticVerdict(BaseModel):
    id: str
    decision: Literal["accept", "reject", "correct"]
    code: RejectionReasonCode | None = None     # required when decision != "accept"
    evidence: str | None = Field(None, max_length=200)
    correction: CompactCorrection | None = None  # required iff decision == "correct"

class CriticBatchVerdicts(BaseModel):
    verdicts: tuple[CriticVerdict, ...]

class VerifierVerdict(BaseModel):
    id: str
    decision: Literal["accept", "reject"]
    code: RejectionReasonCode | None = None
    evidence: str | None = Field(None, max_length=200)
```

Cross-field validators enforce: `code` required iff `decision != "accept"`;
`correction` required iff `decision == "correct"`.

### Server-side expansion to existing contracts

- **Accepted critic verdict** → `CriticReport(plausibility_score=1.0,
  issues=(), corrected_candidate=None, accepted=True)`.
- **Rejected critic verdict** → `CriticReport(plausibility_score=0.0,
  issues=(CriticIssue(code=verdict.code, severity=_severity_for(code),
  message=verdict.evidence or _default_message(verdict.code)),),
  accepted=False)`.
- **Corrected critic verdict** → reuse current `_materialize_correction` path
  on the `CompactCorrection` merged onto the original candidate; on success
  emit `CriticReport(corrected_candidate=..., accepted=True)`; on failure emit
  the existing `invalid_correction` rejection path unchanged.
- **Verifier verdict** → `VerifierReport(span_verified=..., category_verified=...,
  alignment_score=1.0 if accepted else 0.0, accepted=..., rejection_reasons=...)`.
  `span_verified` and `category_verified` are derived deterministically from
  the existing `_deterministic_rejection_reasons` and the LLM `decision`,
  preserving the current LLM/deterministic merge behavior in `_build_report`.

`plausibility_score` and `alignment_score` are not consumed downstream beyond
the reconciler's `min()` of confidences. Setting them to 1.0/0.0 deterministically
is safe; document this explicitly in the audit metadata.

### Severity mapping (`_severity_for`)

| Code | Severity |
|---|---|
| `invented_span`, `category_not_approved`, `schema_violation` | high |
| `invalid_source_offsets`, `ambiguous_source_span` | high |
| `critic_rejected`, `verifier_rejected`, `reconciler_rejected` | medium |

### Files

- `src/extractor/critic/{service.py,models.py}` — new output payload, new
  expansion helpers `_expand_to_critic_report`, `_severity_for`,
  `_default_message`.
- `src/extractor/verifier/{service.py,models.py}` — same.
- `prompts/critic.md` — rewrite output instructions; keep the adversarial
  checklist.
- `prompts/verifier.md` — rewrite output instructions; keep verification rules.

### Tests

- `tests/unit/test_critic.py`
  - accepted verdict expansion preserves `accepted=True`, empty issues.
  - rejected verdict expansion produces typed `CriticIssue` matching the
    `code`.
  - correction verdict triggers existing `_materialize_correction` validation
    on success and on failure (invalid span).
  - audit DB row for `CriticReport` contains all current columns.
- `tests/unit/test_verifier.py` — analogous.

### Acceptance criteria

- Critic output tokens 14,437 → ≤6,000 on the medium fixture.
- Verifier output similarly compressed.
- All four eval fixtures unchanged.

### Estimated reduction

Critic output cost: ~60%. Verifier output cost: ~60%.

---

## Phase 22 — Pre-critic candidate deduplication

**Goal.** Collapse exact duplicates emitted by overlapping lenses before they
reach critic. ≥20 of 137 candidates in `medium-research-1` are exact duplicates
by `(chunk_id, category, field_name, source_span.text, value)`.

### Dedup algorithm

```python
def deduplicate_candidates(
    candidates: tuple[LensCandidate, ...],
) -> tuple[tuple[LensCandidate, ...], dict[str, str]]:
    by_key: dict[tuple, list[LensCandidate]] = {}
    for c in candidates:
        key = (c.chunk_id, c.category, c.field_name, c.source_span.text, c.value)
        by_key.setdefault(key, []).append(c)
    canonical: list[LensCandidate] = []
    merged_into: dict[str, str] = {}   # duplicate_id → primary_id
    for group in by_key.values():
        primary, *rest = sorted(group, key=lambda c: c.candidate_id)
        canonical.append(primary)
        for dup in rest:
            merged_into[dup.candidate_id] = primary.candidate_id
    return tuple(canonical), merged_into
```

Conservative key: byte-identical `source_span.text`, `value`, `category`,
`field_name`, `chunk_id`. Different span widths for the same fact (e.g.
`"September 30, 2026"` vs `"Closing expected by September 30, 2026"`) do NOT
merge — those distinct provenance choices remain for the critic.

### No silent drops (I9)

For each duplicate, persist:

```python
CandidateRejection(
    rejection_id=...,
    run_id=plan.run_id,
    candidate_id=duplicate.candidate_id,
    stage="dedup",
    reasons=(RejectionReason(
        code="duplicate_candidate",
        message=f"merged_into:{primary.candidate_id}",
    ),),
    created_at=...,
)
```

After critic runs on canonical, propagate the critic decision to each merged
duplicate so reconciler invariants (one accepted critic report per candidate)
still hold. Implementation: persist a stub `CriticReport` for each duplicate
with the same `accepted`, `corrected_candidate`, and a synthetic
`report_id` derived from the primary's report ID + duplicate's candidate ID
(stable hash). The reconciler then naturally accepts both into one
`DataPoint` via `contributing_candidate_ids`.

### Contract / audit changes

- `src/extractor/contracts/models.py` — add `"duplicate_candidate"` to
  `RejectionReasonCode`.
- `src/extractor/audit/models.py` — add `"dedup"` to `CandidateRejection.stage`
  literal. SQLite `candidate_rejections.stage` column is already TEXT so no
  schema migration is required.

### Files

- `src/extractor/executor/dedup.py` (new)
- `src/extractor/orchestrator/service.py` — call `deduplicate_candidates`
  between `execute_plan` and `review_candidates`; persist `dedup` rejections
  via `audit_store.record_candidate_rejection`.
- `src/extractor/critic/service.py` — accept an optional
  `merged_into: dict[str, str]` parameter; after critic returns, mirror each
  primary's `CriticReport` to its merged duplicates with stable derived IDs.
- `src/extractor/contracts/models.py`
- `src/extractor/audit/models.py`

### Tests

- `tests/unit/test_dedup.py` (new) — exact-duplicate grouping; distinct-value
  preservation; distinct-source-text preservation; stable primary selection.
- `tests/unit/test_orchestrator.py` — assert duplicates produce
  `CandidateRejection(stage="dedup")` rows in audit; assert critic only sees
  canonical candidates; assert each merged duplicate has a mirrored
  `CriticReport` row.

### Acceptance criteria

- `medium-research-1` rerun produces ≤120 canonical candidates from 137 raw.
- Every duplicate appears in `candidate_rejections` with `stage='dedup'`.
- Final `data_points` count unchanged vs non-dedup baseline.

### Estimated reduction

~20% fewer critic LLM calls on the medium fixture.

---

## Phase 23 — Reconciler input slim

**Goal.** Stop shipping `critic_reports` and `verifier_reports` to the
reconciler LLM. The service has already enforced the one-accepted-report
invariant before constructing the payload, and the reports are noise to the
LLM (~13k tokens on this fixture).

### Changes

- `ReconcilerStageInput` becomes:

```python
class ReconcilerStageInput(BaseModel):
    schema_card: LLMSchemaCard
    candidates: tuple[LLMCandidateView, ...]
```

  Drop `run_id`, `plan` (replaced by schema card), `critic_reports`,
  `verifier_reports`.

- Server-side, `_build_data_point` continues to look up
  `critic_reports_by_candidate_id` and `verifier_reports_by_candidate_id` for
  `critic_report_ids` / `verifier_report_ids` on the final `DataPoint` — that
  join is already in the service layer, not the LLM payload.

- `prompts/reconciler.md` — drop references to `accepted critic reports` and
  `accepted verifier reports`; keep the accounting rule ("every input
  candidate must be accounted for exactly once").

### Invariant impact

None. Reconciler still enforces:
- one accepted critic report per candidate (service-side validation in
  `_validate_reconciler_inputs`)
- one accepted verifier report per candidate (same)
- no silent drops (final `for candidate_id in candidates_by_id` loop)

### Files

- `src/extractor/reconciler/{service.py,models.py}`
- `prompts/reconciler.md`

### Tests

- `tests/unit/test_reconciler.py` — assert user_content JSON does NOT contain
  `critic_reports` or `verifier_reports` keys; existing accounting tests
  unchanged.

### Estimated reduction

Reconciler input: ~28k → ~6k tokens.

---

## Phase 24 — Batch-size tuning and observability

**Goal.** Once Phases 19–23 land, raise `critic_batch_size` and
`verifier_batch_size` from 10 to 20 to halve call counts. Add a tiny audit
helper to surface effective per-stage cache hit rate so regressions are
visible.

### Changes

- `config/default.yaml` — `execution.critic_batch_size: 20`,
  `execution.verifier_batch_size: 20`.
- New `audit_store.summarize_run(run_id)` returns per-stage totals for
  `input_tokens`, `output_tokens`, `cache_read_tokens`,
  `cache_creation_tokens`, `calls`. Used by CLI to print a usage summary at
  end of `run_extraction_pipeline`.
- `src/extractor/cli/main.py` — append `usage_summary` to the existing JSON
  summary object (does not change existing keys).

### Risk and mitigation

Larger batches increase output tokens per call. With `max_output_tokens=32768`
this is well within budget; the OpenAI `finish_reason=length` hint already
exists for safety.

### Files

- `config/default.yaml`
- `src/extractor/audit/store.py`
- `src/extractor/cli/main.py`
- `src/extractor/orchestrator/service.py` — call `summarize_run` after
  reporter completes.

### Tests

- `tests/unit/test_audit_store.py` — new test for `summarize_run` aggregation.
- `tests/unit/test_cli.py` — assert summary includes `usage_summary` with
  per-stage breakdown.

### Acceptance criteria

- `medium-research-1` rerun completes with ≤6 critic batches and ≤5 verifier
  batches.
- CLI summary shows non-zero `cache_read_tokens` for critic and verifier.

### Estimated reduction

40% fewer critic and verifier round-trips → fewer 429 retry windows.

---

## Phase order, dependencies, rollout

```
P19 prompt caching          (no deps)                  -> ship first
P20 boundary view models    (deps: none, but compounds with P19)
P21 compact verdict output  (deps: none, independent)
P23 reconciler slim         (deps: P20 for LLMCandidateView)
P22 pre-critic dedup        (deps: P21 for stub CriticReport mirroring)
P24 batch tuning + obs      (deps: P19; safest to land last)
```

Each phase ships behind no feature flag except P19 (`prompt_cache_enabled`).
Each PR keeps existing behavior on the unchanged paths so a single
revert restores the prior phase.

After each phase, rerun the four eval fixtures plus a live
`medium-research-{N}` against Sonnet 4.6 and record the audit summary in
`PROGRESS.md`.

---

## Estimated end-to-end before / after on `medium_research_brief`

| Stage | Before in/out | Before $ | After in/out (billed-equivalent) | After $ |
|---|---|---|---|---|
| Planner (5)        | 29,084 / 7,616  | $0.202 | 10,000 / 5,000 | $0.105 |
| Executor (4)       | 20,956 / 11,756 | $0.239 | 8,000 / 7,000  | $0.129 |
| Critic (5 @20)     | 88,000 / 17,000 | $0.519 | 12,000 / 5,000 | $0.111 |
| Verifier (5 @20)   | 70,000 / 12,000 | $0.390 | 10,000 / 4,000 | $0.090 |
| Reconciler (1)     | 28,000 / 4,000  | $0.144 | 6,000 / 3,000  | $0.063 |
| **Total**          | **236k / 52k**  | **~$1.49** | **46k / 24k** | **~$0.50** |

Net: ~67% cost reduction, ~80% reduction in input tokens-per-minute (the 429
trigger).

---

## Must-not list (carried forward across all phases)

- Do not drop `source_span.text` or `start_char` from any LLM input.
- Do not let any LLM emit byte offsets — keep server-side derivation
  (`_build_candidate`, `_materialize_correction`).
- Do not bypass critic or verifier on "high-confidence" candidates — I9
  requires independent verification.
- Do not merge critic and verifier into one LLM call.
- Do not relax `tool_choice` forcing or Pydantic strict validation.
- Do not silently drop duplicates — every dedup writes a
  `CandidateRejection(stage="dedup")`.
- Do not loosen `_materialize_correction` span re-validation. Compact
  correction shape is fine; the rebuilt `LensCandidate` must still pass
  `_span_matches_chunk`.
- Do not remove `cache_read_tokens` / `cache_creation_tokens` from
  `LLMCallLog` — required for $ reconciliation and cache-regression detection.
- Do not switch any stage to free-text JSON parsing.
- Do not raise `max_chunk_concurrency` to "amortize" 429 wait — it worsens
  TPM bursts.
- Do not lower `max_output_tokens` to force shorter outputs — risks
  `finish_reason=length` mid-tool-call.
- Do not collapse the 4 lens executor calls into one prompt — lens-specific
  rejection rules degrade if merged.
