from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


NonEmptyStr = Annotated[str, Field(strict=True, min_length=1, pattern=r".*\S.*")]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
Temperature = Annotated[float, Field(ge=0.0, le=1.0)]
SchemaCoverageThreshold = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]
LLMProvider = Literal["anthropic", "openai", "openai_compatible"]
ReasoningEffort = Literal["minimal", "low", "medium", "high"]
LLMStageGroup = Literal["planner", "executor", "critic", "verifier", "reconciler"]
ChunkBoundaryMode = Literal["token_window", "layout_aware"]
ChunkTokenizerPolicy = Literal["tiktoken"]
ReportSignatureAlgorithm = Literal["hmac-sha256"]
ConfidenceBucketName = Literal["verified", "probable", "tentative"]


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LLMStageOverrideConfig(ConfigModel):
    model: NonEmptyStr | None = None
    max_output_tokens: PositiveInt | None = None
    reasoning_effort: ReasoningEffort | None = None


class LLMConfig(ConfigModel):
    provider: LLMProvider
    model: NonEmptyStr
    base_url: NonEmptyStr | None = None
    api_key_env: NonEmptyStr | None = None
    max_retries: NonNegativeInt
    min_request_interval_seconds: NonNegativeInt = 0
    timeout_seconds: PositiveInt
    max_output_tokens: PositiveInt
    temperature: Temperature
    reasoning_effort: ReasoningEffort = "medium"
    prompt_cache_enabled: bool = True
    stage_overrides: dict[LLMStageGroup, LLMStageOverrideConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_provider_settings(self) -> LLMConfig:
        if self.provider == "openai_compatible":
            if self.base_url is None:
                raise ValueError("base_url is required for openai_compatible provider")
            if self.api_key_env is None:
                raise ValueError("api_key_env is required for openai_compatible provider")
        if self.provider == "anthropic" and self.base_url is not None:
            raise ValueError("base_url is only supported for OpenAI-compatible providers")
        return self


class ChunkingConfig(ConfigModel):
    tokenizer: NonEmptyStr
    window_tokens: PositiveInt
    overlap_tokens: NonNegativeInt
    boundary_mode: ChunkBoundaryMode = "token_window"
    tokenizer_policy: ChunkTokenizerPolicy = "tiktoken"
    allow_oversized_atomic_chunks: bool = Field(default=True, strict=True)

    @model_validator(mode="after")
    def validate_overlap(self) -> ChunkingConfig:
        if self.overlap_tokens >= self.window_tokens:
            raise ValueError("overlap_tokens must be less than window_tokens")
        return self


class ExecutionConfig(ConfigModel):
    max_stage_concurrency: PositiveInt
    max_chunk_concurrency: PositiveInt
    max_llm_attempts: PositiveInt
    critic_batch_size: PositiveInt = 20
    verifier_batch_size: PositiveInt = 20


class AuditConfig(ConfigModel):
    database_path: Path


class LoggingConfig(ConfigModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    format: Literal["json"]


class PromptConfig(ConfigModel):
    directory: Path


class DomainPacksConfig(ConfigModel):
    directory: Path


class SchemaRegistryConfig(ConfigModel):
    directory: Path
    require_approved_schema: bool = Field(default=False, strict=True)
    minimum_schema_coverage: SchemaCoverageThreshold = 0.65


class ReportSigningConfig(ConfigModel):
    enabled: bool = Field(default=False, strict=True)
    algorithm: ReportSignatureAlgorithm = "hmac-sha256"
    key_id: NonEmptyStr = "local-dev"
    key_env: NonEmptyStr = "REPORT_SIGNING_KEY"
    manifest_suffix: NonEmptyStr = ".manifest.json"


class ConfidenceBucketConfig(ConfigModel):
    bucket_name: ConfidenceBucketName
    minimum_confidence: SchemaCoverageThreshold


def default_confidence_buckets() -> tuple[ConfidenceBucketConfig, ...]:
    return (
        ConfidenceBucketConfig(bucket_name="verified", minimum_confidence=0.85),
        ConfidenceBucketConfig(bucket_name="probable", minimum_confidence=0.65),
        ConfidenceBucketConfig(bucket_name="tentative", minimum_confidence=0.0),
    )


class ReportingConfig(ConfigModel):
    signing: ReportSigningConfig = Field(default_factory=ReportSigningConfig)
    static_provenance_context_radius: NonNegativeInt = 80
    confidence_buckets: tuple[ConfidenceBucketConfig, ...] = Field(
        default_factory=default_confidence_buckets
    )

    @model_validator(mode="after")
    def validate_confidence_buckets(self) -> ReportingConfig:
        expected_names = ("verified", "probable", "tentative")
        names = tuple(bucket.bucket_name for bucket in self.confidence_buckets)
        if names != expected_names:
            raise ValueError("confidence_buckets must be ordered verified, probable, tentative")

        thresholds = tuple(bucket.minimum_confidence for bucket in self.confidence_buckets)
        if thresholds != tuple(sorted(thresholds, reverse=True)):
            raise ValueError("confidence_buckets thresholds must be descending")
        return self


class ExtractorConfig(ConfigModel):
    llm: LLMConfig
    chunking: ChunkingConfig
    execution: ExecutionConfig
    audit: AuditConfig
    logging: LoggingConfig
    prompts: PromptConfig
    domain_packs: DomainPacksConfig
    schema_registry: SchemaRegistryConfig
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)


class RunContext(ConfigModel):
    run_id: NonEmptyStr
    doc_id: NonEmptyStr
    audit_db_path: NonEmptyStr


__all__ = [
    "AuditConfig",
    "ConfidenceBucketConfig",
    "ConfidenceBucketName",
    "ChunkBoundaryMode",
    "ChunkingConfig",
    "ChunkTokenizerPolicy",
    "DomainPacksConfig",
    "ExecutionConfig",
    "ExtractorConfig",
    "LLMConfig",
    "LLMProvider",
    "LLMStageGroup",
    "LLMStageOverrideConfig",
    "LoggingConfig",
    "PromptConfig",
    "ReportSignatureAlgorithm",
    "ReportSigningConfig",
    "ReportingConfig",
    "RunContext",
    "SchemaRegistryConfig",
    "SchemaCoverageThreshold",
]
