import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from extractor.audit import AuditStore
from extractor.config import ExecutionConfig, LLMConfig
from extractor.contracts import (
    CategoryDefinition,
    Chunk,
    ChunkPolicy,
    Document,
    ExtractionBudget,
    ExtractionPlan,
    FieldDefinition,
    LensBudget,
    PageSpan,
    RunManifest,
)
from extractor.contracts.lens_taxonomy import default_lens_registry
from extractor.executor import execute_plan
from extractor.llm import LLMClient, PROMPT_STAGES, PromptLoader
from extractor.planner.models import BudgetAllocation, StrategySelection


ROOT = Path(__file__).resolve().parents[2]
HASH = "a" * 64
STARTED = datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc)
PHASE37_LENSES = ("definition", "citation", "temporal", "quantity_with_unit")


class QueuedMessages:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    id="toolu_1",
                    name=kwargs["tool_choice"]["name"],
                    input=self.payload,
                )
            ],
            stop_reason="tool_use",
            usage=SimpleNamespace(
                input_tokens=20,
                output_tokens=8,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            ),
        )


class QueuedAnthropicClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.messages = QueuedMessages(payload)


def make_document() -> Document:
    text = "Section 1. Defined Term means a source-backed value."
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


def make_chunk() -> Chunk:
    text = make_document().text
    text_bytes = text.encode("utf-8")
    return Chunk(
        chunk_id="chunk-1",
        doc_id="doc-1",
        chunk_index=0,
        text=text,
        start_char=0,
        end_char=len(text),
        start_byte=0,
        end_byte=len(text_bytes),
        start_token=0,
        end_token=10,
    )


def make_plan(lens: str) -> ExtractionPlan:
    return ExtractionPlan(
        run_id="run-1",
        doc_id="doc-1",
        domain_hints=("generic",),
        approved_categories=(
            CategoryDefinition(
                name="Finding",
                description="A source-backed finding.",
                fields=(
                    FieldDefinition(
                        name="summary",
                        description="A source-backed summary.",
                        value_type="text",
                        required=True,
                    ),
                ),
            ),
        ),
        enabled_lenses=(lens,),  # type: ignore[arg-type]
        chunk_policy=ChunkPolicy(window_tokens=100, overlap_tokens=10),
        budget=ExtractionBudget(
            per_chunk_concurrency=1,
            lens_budgets=(
                LensBudget(lens=lens, max_calls=1),  # type: ignore[arg-type]
            ),
        ),
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


def make_execution_config() -> ExecutionConfig:
    return ExecutionConfig(
        max_stage_concurrency=1,
        max_chunk_concurrency=1,
        max_llm_attempts=1,
    )


async def seed_audit_store(audit_store: AuditStore, plan: ExtractionPlan) -> None:
    document = make_document()
    await audit_store.record_run_manifest(
        RunManifest(
            run_id="run-1",
            doc_id="doc-1",
            audit_db_path="/tmp/audit.sqlite3",
            status="created",
            started_at=STARTED,
            output_data_point_ids=(),
        )
    )
    await audit_store.record_document(document)
    await audit_store.record_chunk(make_chunk())
    await audit_store.record_extraction_plan(plan)


def test_phase37_round1_lenses_are_executable_contracts() -> None:
    registry = default_lens_registry()

    for lens in PHASE37_LENSES:
        assert registry.definition_for(lens).runtime_status == "executable"  # type: ignore[arg-type]
        assert make_plan(lens).enabled_lenses == (lens,)

    assert registry.definition_for("relation").runtime_status == "contract_only"
    assert registry.definition_for("obligation").runtime_status == "contract_only"
    assert registry.definition_for("condition").runtime_status == "contract_only"
    assert registry.definition_for("exception").runtime_status == "contract_only"


def test_prompt_loader_knows_phase37_executor_stages() -> None:
    expected_stages = tuple(f"executor.{lens}" for lens in PHASE37_LENSES)

    for stage in expected_stages:
        assert stage in PROMPT_STAGES

    prompts = {prompt.stage: prompt for prompt in PromptLoader(ROOT / "prompts").load_all()}
    for stage in expected_stages:
        assert stage in prompts
        assert "Call the required tool exactly once" in prompts[stage].body


def test_planner_models_accept_phase37_lens_selection_and_budget() -> None:
    selection = StrategySelection(
        enabled_lenses=PHASE37_LENSES,  # type: ignore[arg-type]
        rationale="Approved schema needs definitions, citations, temporal facts, and quantities.",
    )
    budget = BudgetAllocation(
        budget=ExtractionBudget(
            per_chunk_concurrency=1,
            lens_budgets=tuple(
                LensBudget(lens=lens, max_calls=2)  # type: ignore[arg-type]
                for lens in selection.enabled_lenses
            ),
        )
    )

    assert selection.enabled_lenses == PHASE37_LENSES
    assert tuple(entry.lens for entry in budget.budget.lens_budgets) == PHASE37_LENSES


def test_planner_prompts_describe_phase37_lens_selection_and_budgeting() -> None:
    prompts = {prompt.stage: prompt.body for prompt in PromptLoader(ROOT / "prompts").load_all()}
    strategy = prompts["planner.select_strategy"]
    allocation = prompts["planner.allocate_budget"]

    for phrase in (
        "definition: defined terms",
        "citation: source references",
        "temporal: dates, deadlines, periods, or durations",
        "quantity_with_unit: quantities whose unit or scope is part of the field meaning",
        "enabled_lenses must be unique and contain only supported executable lenses",
    ):
        assert phrase in strategy

    for lens in PHASE37_LENSES:
        assert lens in allocation


def test_execute_plan_routes_phase37_lenses_through_existing_audit_path(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        for lens in PHASE37_LENSES:
            plan = make_plan(lens)
            source_text = "Defined Term means a source-backed value"
            payload = {
                "candidates": (
                    {
                        "category": "Finding",
                        "field_name": "summary",
                        "value": source_text,
                        "source_length": len(source_text),
                        "start_char": make_chunk().text.index(source_text),
                        "confidence": 0.9,
                    },
                )
            }
            anthropic_client = QueuedAnthropicClient(payload)
            llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

            async with AuditStore(tmp_path / f"{lens}.sqlite3") as audit_store:
                await seed_audit_store(audit_store, plan)
                result = await execute_plan(
                    plan=plan,
                    chunks=(make_chunk(),),
                    prompt_loader=PromptLoader(ROOT / "prompts"),
                    llm_client=llm_client,
                    execution_config=make_execution_config(),
                    audit_store=audit_store,
                )
                logs = await audit_store.list_llm_call_logs("run-1")
                stored_candidates = await audit_store.list_lens_candidates("run-1")

            assert len(result.accepted_candidates) == 1
            assert result.rejected_candidates == ()
            assert result.accepted_candidates[0].lens == lens
            assert stored_candidates[0].lens == lens
            assert logs[0].stage == f"executor.{lens}"
            assert anthropic_client.messages.calls[0]["tool_choice"] == {
                "type": "tool",
                "name": f"extract_{lens}_candidates",
            }

    asyncio.run(run_check())
