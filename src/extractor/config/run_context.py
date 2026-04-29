from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

import structlog

from extractor.config.models import RunContext


_RUN_CONTEXT: ContextVar[RunContext | None] = ContextVar("veritext_run_context", default=None)


def maybe_run_context() -> RunContext | None:
    return _RUN_CONTEXT.get()


def get_run_context() -> RunContext:
    context = maybe_run_context()
    if context is None:
        raise RuntimeError("No run context is bound")
    return context


@contextmanager
def bind_run_context(context: RunContext) -> Iterator[RunContext]:
    token = _RUN_CONTEXT.set(context)
    with structlog.contextvars.bound_contextvars(
        run_id=context.run_id,
        doc_id=context.doc_id,
        audit_db_path=context.audit_db_path,
    ):
        try:
            yield context
        finally:
            _RUN_CONTEXT.reset(token)


__all__ = ["RunContext", "bind_run_context", "get_run_context", "maybe_run_context"]
