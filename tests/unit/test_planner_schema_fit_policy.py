import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from extractor.audit import AuditStore
from extractor.config import ChunkingConfig, LLMConfig
from extractor.contracts import (
    ApprovedSchemaArtifact,
    ApprovedSchemaMetadata,
    CategoryDefinition,
    Chunk,
    Document,
    PageSpan,
    RunManifest,
    SchemaSelectionPolicy,
    canonical_schema_hash,
)
from extractor.llm import LLMClient, PromptLoader
from extractor.planner import (
    PlanningRefusalError,
    create_extraction_plan,
)


ROOT = Path(__file__).resolve().parents[2]
HASH = "a" * 64
STARTED = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)


class QueuedMessages:
    def __init__(self, tool_payloads: list[tuple[str, dict[str, object]]]) -> None:
        self.tool_payloads = tool_payloads
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        tool_name, payload = self.tool_payloads.pop(0)
        return SimpleNamespace(
            content=[SimpleNamespace(type="tool_use", name=tool_name, input=payload)],
            stop_reason="tool_use",
            usage=SimpleNamespace(
                input_tokens=10 + len(self.calls),
                output_tokens=5,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            ),
        )


class QueuedAnthropicClient:
    def __init__(self, tool_payloads: list[tuple[str, dict[str, object]]]) -> None:
        self.messages = QueuedMessages(tool_payloads)


def make_document() -> Document:
    text = "Revenue increased in Q1. Margin declined."
    text_bytes = text.encode("utf-8")
    return Document(
        doc_id="doc-1",
        source_path="/tmp/doc.txt",
        format="plain_text",
        text=text,
        source_sha256=HASH,
        text_sha256="b" * 64,
        source_byte_length=len(text_bytes),
        text_byte_length=len(text_bytes),
        page_map=(
            PageSpan(
                page_number=1,
                start_char=0,
                end_char=len(text),
                start_byte=0,
                end_byte=len(text_bytes),
            ),
        ),
    )


def make_chunks() -> tuple[Chunk, ...]:
    document = make_document()
    return (
        Chunk(
            chunk_id="chunk-1",
            doc_id=document.doc_id,
            chunk_index=0,
            text=document.text,
            start_char=0,
            end_char=len(document.text),
            start_byte=0,
            end_byte=len(document.text.encode("utf-8")),
            start_token=0,
            end_token=8,
        ),
    )


def make_run_manifest() -> RunManifest:
    return RunManifest(
        run_id="run-1",
        doc_id="doc-1",
        audit_db_path="/tmp/audit.sqlite3",
        status="created",
        started_at=STARTED,
        output_data_point_ids=(),
    )


def make_llm_config() -> LLMConfig:
    return LLMConfig(
        provider="anthropic",
        model="configured-model",
        max_retries=0,
        timeout_seconds=30,
        max_output_tokens=512,
        temperature=0.0,
    )


def strict_policy(threshold: float = 0.65) -> SchemaSelectionPolicy:
    return SchemaSelectionPolicy(
        require_approved_schema=True,
        minimum_schema_coverage=threshold,
        allow_planner_generated_fallback=False,
    )


def fallback_policy(threshold: float = 0.65) -> SchemaSelectionPolicy:
    return SchemaSelectionPolicy(
        require_approved_schema=False,
        minimum_schema_coverage=threshold,
        allow_planner_generated_fallback=True,
    )


def make_registry_artifact() -> ApprovedSchemaArtifact:
    category = CategoryDefinition.model_validate(
        {
            "name": "FinancialMetric",
            "description": "Registry-approved financial metric semantics.",
            "fields": (
                {
                    "name": "summary",
                    "description": "Registry-approved source-backed metric summary.",
                    "value_type": "text",
                    "required": True,
                },
            ),
        }
    )
    schema_hash = canonical_schema_hash(
        approved_categories=(category,),
        source_kind="schema_registry",
        schema_version="1.0.0",
        domain_hints=("finance",),
        document_class="financial_update",
    )
    return ApprovedSchemaArtifact(
        schema_metadata=ApprovedSchemaMetadata(
            schema_id="schema:financial-metrics-v1",
            schema_version="1.0.0",
            schema_hash=schema_hash,
            source_kind="schema_registry",
            domain_pack_id=None,
            document_class="financial_update",
            created_from="schema_registry",
            refined_from_schema_id=None,
        ),
        approved_categories=(category,),
        document_class="financial_update",
        domain_hints=("finance",),
        match_basis=("document_class", "domain_hints"),
    )


def classify_payload(confidence: float = 0.9) -> tuple[str, dict[str, object]]:
    return (
        "classify_document",
        {
            "document_type": "financial_update",
            "summary": "Revenue increased in Q1 while margin declined.",
            "domain_hints": ("finance",),
            "confidence": confidence,
        },
    )


def generated_schema_payloads() -> list[tuple[str, dict[str, object]]]:
    category = {
        "name": "FinancialMetric",
        "description": "Financial performance metric stated in the document.",
        "fields": (
            {
                "name": "summary",
                "description": "The exact metric statement.",
                "value_type": "text",
                "required": True,
            },
        ),
    }
    return [
        classify_payload(),
        (
            "propose_schema",
            {
                "categories": (category,),
                "rationale": "FinancialMetric captures source-backed financial statements.",
            },
        ),
        (
            "critique_schema",
            {
                "accepted": True,
                "approved_categories": (category,),
                "issues": (),
            },
        ),
        (
            "select_strategy",
            {
                "enabled_lenses": ("claim", "number"),
                "rationale": "Claim covers statements and number covers numeric values.",
            },
        ),
        (
            "allocate_budget",
            {
                "budget": {
                    "per_chunk_concurrency": 2,
                    "lens_budgets": (
                        {"lens": "claim", "max_calls": 4},
                        {"lens": "number", "max_calls": 3},
                    ),
                },
            },
        ),
    ]


async def create_plan_with(
    *,
    anthropic_client: QueuedAnthropicClient,
    tmp_path: Path,
    policy: SchemaSelectionPolicy,
    artifacts: tuple[ApprovedSchemaArtifact, ...] = (),
):
    document = make_document()
    chunks = make_chunks()
    llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

    async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
        await audit_store.record_run_manifest(make_run_manifest())
        await audit_store.record_document(document)
        for chunk in chunks:
            await audit_store.record_chunk(chunk)

        return await create_extraction_plan(
            run_id="run-1",
            document=document,
            chunks=chunks,
            chunking_config=ChunkingConfig(
                tokenizer="cl100k_base",
                window_tokens=1200,
                overlap_tokens=120,
            ),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
            approved_schema_artifacts=artifacts,
            schema_selection_policy=policy,
            audit_store=audit_store,
        )


def test_strict_policy_refuses_when_no_approved_schema_candidates(tmp_path: Path) -> None:
    async def run_check() -> None:
        anthropic_client = QueuedAnthropicClient([classify_payload()])

        with pytest.raises(PlanningRefusalError) as exc_info:
            await create_plan_with(
                anthropic_client=anthropic_client,
                tmp_path=tmp_path,
                policy=strict_policy(),
            )

        refusal = exc_info.value.refusal
        assert refusal.reason_codes == ("no_approved_schema_candidates",)
        assert refusal.candidate_schema_ids == ()
        assert refusal.document_class == "financial_update"
        assert refusal.domain_hints == ("finance",)
        assert [call["tool_choice"] for call in anthropic_client.messages.calls] == [
            {"type": "tool", "name": "classify_document"},
        ]

    asyncio.run(run_check())


def test_strict_policy_refuses_when_schema_fit_coverage_is_below_threshold(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        anthropic_client = QueuedAnthropicClient([classify_payload(confidence=0.4)])

        with pytest.raises(PlanningRefusalError) as exc_info:
            await create_plan_with(
                anthropic_client=anthropic_client,
                tmp_path=tmp_path,
                artifacts=(make_registry_artifact(),),
                policy=strict_policy(threshold=0.75),
            )

        refusal = exc_info.value.refusal
        assert refusal.reason_codes == ("coverage_below_threshold",)
        assert refusal.candidate_schema_ids == ("schema:financial-metrics-v1",)
        assert refusal.fit_assessments[0].overall_coverage == 0.4
        assert refusal.fit_assessments[0].coverage_estimates[0].category_name == "FinancialMetric"
        assert [call["tool_choice"] for call in anthropic_client.messages.calls] == [
            {"type": "tool", "name": "classify_document"},
        ]

    asyncio.run(run_check())


def test_fallback_policy_uses_generated_schema_when_no_approved_schema_fits(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        anthropic_client = QueuedAnthropicClient(generated_schema_payloads())

        plan = await create_plan_with(
            anthropic_client=anthropic_client,
            tmp_path=tmp_path,
            policy=fallback_policy(),
        )

        assert plan.schema_metadata.source_kind == "planner_generated"
        assert [call["tool_choice"] for call in anthropic_client.messages.calls] == [
            {"type": "tool", "name": "classify_document"},
            {"type": "tool", "name": "propose_schema"},
            {"type": "tool", "name": "critique_schema"},
            {"type": "tool", "name": "select_strategy"},
            {"type": "tool", "name": "allocate_budget"},
        ]

    asyncio.run(run_check())
