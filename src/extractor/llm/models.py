from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extractor.contracts import LLMCallLog
from extractor.contracts.models import LLMStage
from extractor.llm.prompts import PromptTemplate


OutputModelT = TypeVar("OutputModelT", bound=BaseModel)
NonEmptyStr = Annotated[str, Field(strict=True, min_length=1)]


@dataclass(frozen=True)
class ItemComplaint:
    identifier: str
    message: str


@dataclass(frozen=True)
class Accepted(Generic[OutputModelT]):
    output: OutputModelT


@dataclass(frozen=True)
class Complaints:
    complaints: tuple[ItemComplaint, ...]


class StructuredLLMRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(strict=True, min_length=1)
    stage: LLMStage
    prompt: PromptTemplate
    user_content: str = Field(strict=True)
    stable_user_prefix: NonEmptyStr | None = None
    prompt_cache_allowed: bool = Field(default=True, strict=True)
    tool_name: str = Field(strict=True, min_length=1)
    tool_description: str = Field(strict=True, min_length=1)

    @model_validator(mode="after")
    def validate_user_content(self) -> StructuredLLMRequest:
        if not self.user_content and self.stable_user_prefix is None:
            raise ValueError("user_content must be non-empty unless stable_user_prefix is set")
        return self

    @property
    def full_user_content(self) -> str:
        return f"{self.stable_user_prefix or ''}{self.user_content}"


class StructuredLLMResult(BaseModel, Generic[OutputModelT]):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output: OutputModelT
    call_log: LLMCallLog


__all__ = [
    "Accepted",
    "Complaints",
    "ItemComplaint",
    "OutputModelT",
    "StructuredLLMRequest",
    "StructuredLLMResult",
]
