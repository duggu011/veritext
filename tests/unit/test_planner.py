import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from extractor.audit import AuditStore
from extractor.config import ChunkingConfig, LLMConfig
from extractor.contracts import Chunk, Document, PageSpan, RunManifest
from extractor.llm import LLMClient, PromptLoader
from extractor.planner import PlanningError, create_extraction_plan


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


def call_user_text(call: dict[str, object]) -> str:
    content = call["messages"][0]["content"]  # type: ignore[index]
    if isinstance(content, str):
        return content
    return "".join(str(block["text"]) for block in content)


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
    split = document.text.index(" Margin")
    first = document.text[:split]
    second = document.text[split:]
    return (
        Chunk(
            chunk_id="chunk-1",
            doc_id=document.doc_id,
            chunk_index=0,
            text=first,
            start_char=0,
            end_char=len(first),
            start_byte=0,
            end_byte=len(first.encode("utf-8")),
            start_token=0,
            end_token=5,
        ),
        Chunk(
            chunk_id="chunk-2",
            doc_id=document.doc_id,
            chunk_index=1,
            text=second,
            start_char=split,
            end_char=len(document.text),
            start_byte=len(first.encode("utf-8")),
            end_byte=len(document.text.encode("utf-8")),
            start_token=4,
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


def valid_tool_payloads() -> list[tuple[str, dict[str, object]]]:
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
        (
            "classify_document",
            {
                "document_type": "financial_update",
                "summary": "Revenue increased in Q1 while margin declined.",
                "domain_hints": ("finance",),
                "confidence": 0.9,
            },
        ),
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


def test_create_extraction_plan_runs_planner_calls_and_persists_audit(tmp_path: Path) -> None:
    async def run_check() -> None:
        document = make_document()
        chunks = make_chunks()
        anthropic_client = QueuedAnthropicClient(valid_tool_payloads())
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_run_manifest(make_run_manifest())
            await audit_store.record_document(document)
            for chunk in chunks:
                await audit_store.record_chunk(chunk)

            plan = await create_extraction_plan(
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
                domain_hints=("user-hint",),
                audit_store=audit_store,
            )
            stored_plan = await audit_store.get_extraction_plan("run-1")
            logs = await audit_store.list_llm_call_logs("run-1")

        assert stored_plan == plan
        assert plan.run_id == "run-1"
        assert plan.doc_id == "doc-1"
        assert plan.domain_hints == ("user-hint", "finance")
        assert plan.approved_category_names == frozenset({"FinancialMetric"})
        assert plan.enabled_lenses == ("claim", "number")
        assert plan.chunk_policy.window_tokens == 1200
        assert plan.chunk_policy.overlap_tokens == 120
        assert {budget.lens for budget in plan.budget.lens_budgets} == {"claim", "number"}
        assert len(logs) == 5
        assert [log.stage for log in logs] == [
            "planner.classify_document",
            "planner.propose_schema",
            "planner.critique_schema",
            "planner.select_strategy",
            "planner.allocate_budget",
        ]
        assert [call["tool_choice"] for call in anthropic_client.messages.calls] == [
            {"type": "tool", "name": "classify_document"},
            {"type": "tool", "name": "propose_schema"},
            {"type": "tool", "name": "critique_schema"},
            {"type": "tool", "name": "select_strategy"},
            {"type": "tool", "name": "allocate_budget"},
        ]
        assert all(isinstance(call["system"], str) for call in anthropic_client.messages.calls)
        assert all(
            "cache_control" not in call["tools"][0]
            for call in anthropic_client.messages.calls
        )
        assert "Revenue increased" in call_user_text(anthropic_client.messages.calls[0])

    asyncio.run(run_check())


def test_create_extraction_plan_generalizes_over_specific_schema_descriptions() -> None:
    async def run_check() -> None:
        corporate_event = {
            "name": "CorporateEvent",
            "description": (
                "A board-approved corporate transaction or significant business event, "
                "specifically the acquisition of Northwind Storage."
            ),
            "fields": (
                {
                    "name": "event_type",
                    "description": "The type of corporate event as stated, e.g. 'Acquisition'.",
                    "value_type": "text",
                    "required": True,
                },
                {
                    "name": "asset_detail",
                    "description": "Descriptive details about the acquired asset.",
                    "value_type": "text",
                    "required": False,
                },
            ),
        }
        operational_metric = {
            "name": "OperationalMetric",
            "description": "Non-financial operational metrics.",
            "fields": (
                {
                    "name": "facility",
                    "description": (
                        "The name and location of a specific asset or facility, "
                        "e.g. 'Atacama-1 in Chile'."
                    ),
                    "value_type": "text",
                    "required": False,
                },
            ),
        }
        personnel_change = {
            "name": "PersonnelChange",
            "description": "Personnel changes.",
            "fields": (
                {
                    "name": "change_type",
                    "description": "The nature of the personnel change as stated.",
                    "value_type": "text",
                    "required": True,
                },
            ),
        }
        categories = (corporate_event, operational_metric, personnel_change)
        payloads = valid_tool_payloads()
        payloads[1] = (
            "propose_schema",
            {
                "categories": categories,
                "rationale": "The schema captures source-backed event and operational facts.",
            },
        )
        payloads[2] = (
            "critique_schema",
            {
                "accepted": True,
                "approved_categories": categories,
                "issues": (),
            },
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=QueuedAnthropicClient(payloads))

        plan = await create_extraction_plan(
            run_id="run-1",
            document=make_document(),
            chunks=make_chunks(),
            chunking_config=ChunkingConfig(
                tokenizer="cl100k_base",
                window_tokens=1200,
                overlap_tokens=120,
            ),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
        )

        categories_by_name = {category.name: category for category in plan.approved_categories}
        corporate_description = categories_by_name["CorporateEvent"].description
        assert "facility commencements or operation starts" in corporate_description
        assert "one named event or transaction" in corporate_description
        assert "Northwind" not in corporate_description

        facility_field = categories_by_name["OperationalMetric"].fields[0]
        assert facility_field.description.startswith("The bare source-stated facility")
        assert "facility plus location" in facility_field.description

        type_field = categories_by_name["PersonnelChange"].fields[0]
        assert "noun-form normalization is allowed and preferred" in type_field.description
        assert "provenance stays on the supporting source words" in type_field.description

    asyncio.run(run_check())


def test_create_extraction_plan_adds_optional_operational_metric_facility() -> None:
    async def run_check() -> None:
        operational_metric = {
            "name": "OperationalMetric",
            "description": "Non-financial operational metrics in physical units.",
            "fields": (
                {
                    "name": "metric_name",
                    "description": "The operational metric name.",
                    "value_type": "text",
                    "required": True,
                },
                {
                    "name": "value",
                    "description": "The stated operational metric value.",
                    "value_type": "text",
                    "required": True,
                },
            ),
        }
        payloads = valid_tool_payloads()
        payloads[1] = (
            "propose_schema",
            {
                "categories": (operational_metric,),
                "rationale": "OperationalMetric captures source-backed operational facts.",
            },
        )
        payloads[2] = (
            "critique_schema",
            {
                "accepted": True,
                "approved_categories": (operational_metric,),
                "issues": (),
            },
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=QueuedAnthropicClient(payloads))

        plan = await create_extraction_plan(
            run_id="run-1",
            document=make_document(),
            chunks=make_chunks(),
            chunking_config=ChunkingConfig(
                tokenizer="cl100k_base",
                window_tokens=1200,
                overlap_tokens=120,
            ),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
        )

        fields = {field.name: field for field in plan.approved_categories[0].fields}
        assert set(fields) == {"metric_name", "value", "facility"}
        assert fields["facility"].required is False
        assert fields["facility"].description.startswith(
            "The bare source-stated facility or asset name associated with a "
            "facility-specific operational metric."
        )

    asyncio.run(run_check())


def test_create_extraction_plan_rejects_failed_schema_critique() -> None:
    async def run_check() -> None:
        payloads = valid_tool_payloads()
        payloads[2] = (
            "critique_schema",
            {
                "accepted": False,
                "approved_categories": (),
                "issues": ("No source-backed category definitions were proposed.",),
            },
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=QueuedAnthropicClient(payloads))

        with pytest.raises(PlanningError, match="Schema critique rejected"):
            await create_extraction_plan(
                run_id="run-1",
                document=make_document(),
                chunks=make_chunks(),
                chunking_config=ChunkingConfig(
                    tokenizer="cl100k_base",
                    window_tokens=1200,
                    overlap_tokens=120,
                ),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
            )

    asyncio.run(run_check())


def test_create_extraction_plan_rejects_budget_missing_enabled_lens() -> None:
    async def run_check() -> None:
        payloads = valid_tool_payloads()
        payloads[4] = (
            "allocate_budget",
            {
                "budget": {
                    "per_chunk_concurrency": 2,
                    "lens_budgets": ({"lens": "claim", "max_calls": 4},),
                },
            },
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=QueuedAnthropicClient(payloads))

        with pytest.raises(PlanningError, match="Invalid extraction plan"):
            await create_extraction_plan(
                run_id="run-1",
                document=make_document(),
                chunks=make_chunks(),
                chunking_config=ChunkingConfig(
                    tokenizer="cl100k_base",
                    window_tokens=1200,
                    overlap_tokens=120,
                ),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
            )

    asyncio.run(run_check())


def test_create_extraction_plan_rejects_chunks_from_other_document() -> None:
    async def run_check() -> None:
        bad_chunk = make_chunks()[0].model_copy(update={"doc_id": "doc-2"})
        llm_client = LLMClient(
            make_llm_config(),
            anthropic_client=QueuedAnthropicClient(valid_tool_payloads()),
        )

        with pytest.raises(PlanningError, match="chunk doc_id must match"):
            await create_extraction_plan(
                run_id="run-1",
                document=make_document(),
                chunks=(bad_chunk,),
                chunking_config=ChunkingConfig(
                    tokenizer="cl100k_base",
                    window_tokens=1200,
                    overlap_tokens=120,
                ),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
            )

    asyncio.run(run_check())
