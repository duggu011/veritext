from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from extractor.contracts.models import LLMStage


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]

REQUIRED_SECTIONS = (
    "Intent",
    "Typed Inputs",
    "Output Tool Schema",
    "Failure Modes",
    "Prompt",
)

PROMPT_STAGES: tuple[LLMStage, ...] = (
    "planner.classify_document",
    "planner.propose_schema",
    "planner.critique_schema",
    "planner.select_strategy",
    "planner.allocate_budget",
    "executor.entity",
    "executor.event",
    "executor.claim",
    "executor.number",
    "critic",
    "verifier",
    "reconciler",
)


class PromptLoadError(ValueError):
    """Raised when a prompt file is missing or does not document its contract."""


class PromptTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: LLMStage
    path: Path
    text: NonEmptyStr
    intent: NonEmptyStr
    typed_inputs: NonEmptyStr
    output_tool_schema: NonEmptyStr
    failure_modes: NonEmptyStr
    body: NonEmptyStr

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


class PromptLoader:
    def __init__(self, prompt_dir: str | Path) -> None:
        self.prompt_dir = Path(prompt_dir)

    def load(self, stage: LLMStage) -> PromptTemplate:
        path = self._path_for_stage(stage)
        if not path.exists():
            raise PromptLoadError(f"Missing prompt file for stage {stage}: {path}")

        text = path.read_text(encoding="utf-8")
        sections = _parse_sections(text, path)
        return PromptTemplate(
            stage=stage,
            path=path,
            text=text,
            intent=sections["Intent"],
            typed_inputs=sections["Typed Inputs"],
            output_tool_schema=sections["Output Tool Schema"],
            failure_modes=sections["Failure Modes"],
            body=sections["Prompt"],
        )

    def load_all(self) -> tuple[PromptTemplate, ...]:
        return tuple(self.load(stage) for stage in PROMPT_STAGES)

    def _path_for_stage(self, stage: LLMStage) -> Path:
        return self.prompt_dir / Path(*stage.split(".")).with_suffix(".md")


def _parse_sections(text: str, path: Path) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)

    parsed: dict[str, str] = {}
    for section in REQUIRED_SECTIONS:
        if section not in sections:
            raise PromptLoadError(f"Prompt {path} is missing required section: {section}")
        body = "\n".join(sections[section]).strip()
        if not body:
            raise PromptLoadError(f"Prompt {path} has an empty required section: {section}")
        parsed[section] = body
    return parsed


__all__ = [
    "PROMPT_STAGES",
    "PromptLoadError",
    "PromptLoader",
    "PromptTemplate",
    "REQUIRED_SECTIONS",
]
