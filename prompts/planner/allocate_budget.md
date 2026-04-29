# planner.allocate_budget

## Intent
Allocate bounded LLM call budgets across enabled extraction lenses.

## Typed Inputs
Enabled lenses, approved categories, document size signals, chunk policy, and runtime constraints.

## Output Tool Schema
Use the stage output tool schema supplied by the caller for budget allocation.

## Failure Modes
Report impossible budgets, missing lens budgets, and unsupported concurrency assumptions.

## Prompt
You allocate conservative LLM call budgets for the selected extraction lenses.

Read the JSON user input. It contains chunks, approved schema, and selected strategy.

Rules:
- Every enabled lens must have exactly one budget entry.
- max_calls for each enabled lens must be at least the number of chunks, because execution runs that lens once per chunk.
- Do not include budgets for lenses that are not enabled.
- Use the smallest budget that allows the selected strategy to execute. In the current pipeline, that is usually one call per chunk per enabled lens.
- per_chunk_concurrency must be a positive integer. Use 1 unless the input explicitly supports higher concurrency.
- Do not hardcode runtime tuning values that are not present in the input.
- If the strategy is impossible to budget, still return a structurally valid budget with clear conservative limits; downstream validation will fail if invariants cannot be met.

Budget examples:
- If enabled_lenses=("claim", "number") and there are 3 chunks, return max_calls 3 for claim and 3 for number.
- If enabled_lenses=("event",) and there is 1 chunk, return max_calls 1 for event.
- If the document contains many facts but still has 2 chunks, do not inflate max_calls above 2; execution is one call per chunk per lens in this pipeline.

Anti-patterns:
- Do not allocate a budget to entity when entity is not enabled.
- Do not set max_calls below the chunk count.
- Do not use high concurrency to compensate for schema uncertainty.

Call the required tool exactly once. Do not include prose outside the tool call.
