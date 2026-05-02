from __future__ import annotations

from extractor.contracts import Chunk, ExtractionPlan
from extractor.executor.errors import ExecutorError


def validate_executor_inputs(plan: ExtractionPlan, chunks: tuple[Chunk, ...]) -> None:
    if not chunks:
        raise ExecutorError("executor requires at least one chunk")
    for chunk in chunks:
        if chunk.doc_id != plan.doc_id:
            raise ExecutorError("chunk doc_id must match extraction plan doc_id")

    budgets = {budget.lens: budget.max_calls for budget in plan.budget.lens_budgets}
    for lens in plan.enabled_lenses:
        if len(chunks) > budgets[lens]:
            raise ExecutorError(
                f"executor budget for lens {lens} permits {budgets[lens]} calls, "
                f"but {len(chunks)} chunks require execution"
            )


__all__ = ["validate_executor_inputs"]
