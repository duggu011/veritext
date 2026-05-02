from __future__ import annotations


class LLMClientError(RuntimeError):
    """Base class for LLM client failures."""


class LLMToolUseError(LLMClientError):
    """Raised when the model response does not contain the required tool call."""


class LLMRetryMergeError(LLMClientError):
    """Raised when a retry response cannot be reconciled with the prior batch."""


__all__ = ["LLMClientError", "LLMRetryMergeError", "LLMToolUseError"]
