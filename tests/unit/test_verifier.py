import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from extractor.audit import AuditStore
from extractor.config import ExecutionConfig, LLMConfig
from extractor.contracts import (
    CategoryDefinition,
    Chunk,
    ChunkPolicy,
    CriticReport,
    Document,
    ExtractionBudget,
    ExtractionPlan,
    FieldDefinition,
    LensBudget,
    LensCandidate,
    PageSpan,
    RejectionReason,
    RunManifest,
    SourceSpan,
)
from extractor.llm import LLMClient, PromptLoader, short_candidate_id
from extractor.verifier import VerifierError, verify_candidates
from extractor.verifier.models import VerifierBatchVerdicts


ROOT = Path(__file__).resolve().parents[2]
HASH = "a" * 64
STARTED = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)


class QueuedMessages:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self.payloads = payloads
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    name=kwargs["tool_choice"]["name"],
                    input=self.payloads.pop(0),
                )
            ],
            stop_reason="tool_use",
            usage=SimpleNamespace(
                input_tokens=40 + len(self.calls),
                output_tokens=11,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
            ),
        )


class QueuedAnthropicClient:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self.messages = QueuedMessages(payloads)


def call_user_text(call: dict[str, object]) -> str:
    content = call["messages"][0]["content"]  # type: ignore[index]
    if isinstance(content, str):
        return content
    return "".join(str(block["text"]) for block in content)


def make_document() -> Document:
    text = "Revenue increased. Margin declined."
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
            end_token=3,
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
            start_token=2,
            end_token=5,
        ),
    )


def make_plan() -> ExtractionPlan:
    return ExtractionPlan(
        run_id="run-1",
        doc_id="doc-1",
        domain_hints=("finance",),
        approved_categories=(
            CategoryDefinition(
                name="Finding",
                description="A source-backed finding.",
                fields=(
                    FieldDefinition(
                        name="summary",
                        description="Short finding summary.",
                        value_type="text",
                        required=True,
                    ),
                ),
            ),
        ),
        enabled_lenses=("claim",),
        chunk_policy=ChunkPolicy(window_tokens=100, overlap_tokens=10),
        budget=ExtractionBudget(
            per_chunk_concurrency=1,
            lens_budgets=(LensBudget(lens="claim", max_calls=2),),
        ),
    )


def make_corporate_asset_detail_plan() -> ExtractionPlan:
    return make_plan().model_copy(
        update={
            "approved_categories": (
                CategoryDefinition(
                    name="CorporateEvent",
                    description="Source-backed corporate events from audited records.",
                    fields=(
                        FieldDefinition(
                            name="asset_detail",
                            description=(
                                "Source-stated asset or facility details involved "
                                "in the event."
                            ),
                            value_type="text",
                            required=False,
                        ),
                    ),
                ),
            ),
            "enabled_lenses": ("event",),
            "budget": ExtractionBudget(
                per_chunk_concurrency=1,
                lens_budgets=(LensBudget(lens="event", max_calls=1),),
            ),
        }
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


def make_execution_config() -> ExecutionConfig:
    return ExecutionConfig(
        max_stage_concurrency=1,
        max_chunk_concurrency=1,
        max_llm_attempts=1,
    )


def make_candidate(
    *,
    candidate_id: str = "candidate-1",
    chunk: Chunk | None = None,
    source_text: str = "Revenue increased",
    start_char: int = 0,
    value: str = "Revenue increased",
) -> LensCandidate:
    actual_chunk = chunk or make_chunks()[0]
    start_byte = start_char
    return LensCandidate(
        candidate_id=candidate_id,
        run_id="run-1",
        doc_id="doc-1",
        chunk_id=actual_chunk.chunk_id,
        lens="claim",
        category="Finding",
        field_name="summary",
        value=value,
        source_span=SourceSpan(
            doc_id="doc-1",
            chunk_id=actual_chunk.chunk_id,
            start_char=start_char,
            end_char=start_char + len(source_text),
            start_byte=start_byte,
            end_byte=start_byte + len(source_text.encode("utf-8")),
            text=source_text,
        ),
        confidence=0.8,
        executor_call_id="call-executor-1",
    )


def make_critic_report(
    candidate: LensCandidate,
    *,
    accepted: bool = True,
    corrected_candidate: LensCandidate | None = None,
) -> CriticReport:
    return CriticReport(
        report_id=f"critic-{candidate.candidate_id}",
        run_id="run-1",
        candidate_id=candidate.candidate_id,
        critic_call_id=f"call-critic-{candidate.candidate_id}",
        plausibility_score=0.9 if accepted else 0.2,
        accepted=accepted,
        issues=(),
        corrected_candidate=corrected_candidate,
    )


async def seed_audit_store(
    audit_store: AuditStore,
    candidates: tuple[LensCandidate, ...],
    critic_reports: tuple[CriticReport, ...],
) -> None:
    await audit_store.record_run_manifest(make_run_manifest())
    document = make_document()
    await audit_store.record_document(document)
    for chunk in make_chunks():
        await audit_store.record_chunk(chunk)
    await audit_store.record_extraction_plan(make_plan())
    for candidate in candidates:
        await audit_store.record_lens_candidate(candidate)
    for report in critic_reports:
        await audit_store.record_critic_report(report)


def accepted_payload(*, candidate_id: str = "candidate-1") -> dict[str, object]:
    return {
        "id": short_candidate_id(candidate_id),
        "decision": "accept",
    }


def rejected_payload(*, candidate_id: str = "candidate-1") -> dict[str, object]:
    return {
        "id": short_candidate_id(candidate_id),
        "decision": "reject",
        "code": "schema_violation",
        "evidence": "Candidate value does not align with the approved field.",
    }


def batch_payload(*items: dict[str, object]) -> dict[str, object]:
    return {"verdicts": tuple(items)}


def test_verifier_batch_verdicts_expand_compact_tuple_shape() -> None:
    batch = VerifierBatchVerdicts.model_validate(
        {
            "verdicts": (
                ("abc123", "a", None, None, None),
                (
                    "def456",
                    "r",
                    "schema_violation",
                    "Value does not align with the approved field.",
                ),
            )
        }
    )

    assert [verdict.decision for verdict in batch.verdicts] == ["accept", "reject"]
    assert batch.verdicts[0].code is None
    assert batch.verdicts[1].code == "schema_violation"
    assert batch.verdicts[1].evidence == (
        "Value does not align with the approved field."
    )


def test_verifier_batch_verdicts_omit_overlong_compact_evidence() -> None:
    batch = VerifierBatchVerdicts.model_validate(
        {
            "verdicts": [
                [
                    "abc123",
                    "r",
                    "schema_violation",
                    "x" * 201,
                    None,
                ],
            ]
        }
    )

    assert batch.verdicts[0].decision == "reject"
    assert batch.verdicts[0].code == "schema_violation"
    assert batch.verdicts[0].evidence is None


def test_verifier_batch_verdicts_trim_extra_trailing_null_slots() -> None:
    batch = VerifierBatchVerdicts.model_validate(
        {
            "verdicts": [
                [
                    "abc123",
                    "r",
                    "schema_violation",
                    "Value does not align.",
                    None,
                    None,
                ],
            ]
        }
    )

    assert batch.verdicts[0].decision == "reject"
    assert batch.verdicts[0].code == "schema_violation"
    assert batch.verdicts[0].evidence == "Value does not align."


def test_verifier_batch_verdicts_normalize_stringified_short_forms() -> None:
    batch = VerifierBatchVerdicts.model_validate(
        {
            "verdicts": json.dumps(
                [
                    ["abc123", "a"],
                    ["def456", "r", None, "Value is not grounded."],
                ]
            )
        }
    )

    assert batch.verdicts[0].decision == "accept"
    assert batch.verdicts[0].code is None
    assert batch.verdicts[1].decision == "reject"
    assert batch.verdicts[1].code == "verifier_rejected"
    assert batch.verdicts[1].evidence == "Value is not grounded."


def test_verify_candidates_persists_reports_rejections_and_logs(tmp_path: Path) -> None:
    async def run_check() -> None:
        chunks = make_chunks()
        second_start = make_document().text.index("Margin")
        candidates = (
            make_candidate(candidate_id="candidate-1"),
            make_candidate(
                candidate_id="candidate-2",
                chunk=chunks[1],
                source_text="Margin declined",
                start_char=second_start,
                value="Margin declined materially",
            ),
        )
        critic_reports = tuple(make_critic_report(candidate) for candidate in candidates)
        anthropic_client = QueuedAnthropicClient(
            [
                batch_payload(accepted_payload(candidate_id="candidate-1")),
                batch_payload(rejected_payload(candidate_id="candidate-2")),
            ]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, candidates, critic_reports)
            result = await verify_candidates(
                plan=make_plan(),
                chunks=chunks,
                candidates=candidates,
                critic_reports=critic_reports,
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )
            first_reports = await audit_store.list_verifier_reports("candidate-1")
            second_reports = await audit_store.list_verifier_reports("candidate-2")
            rejections = await audit_store.list_candidate_rejections("candidate-2")
            logs = await audit_store.list_llm_call_logs("run-1")

        assert result.accepted_candidates == (candidates[0],)
        assert result.rejected_candidates == (candidates[1],)
        assert result.reports == (*first_reports, *second_reports)
        assert result.rejections == rejections
        assert first_reports[0].accepted is True
        assert first_reports[0].alignment_score == 1.0
        assert first_reports[0].rejection_reasons == ()
        assert second_reports[0].accepted is False
        assert second_reports[0].alignment_score == 0.0
        assert second_reports[0].category_verified is False
        assert second_reports[0].rejection_reasons[0].message == (
            "Candidate value does not align with the approved field."
        )
        assert rejections[0].stage == "verifier"
        assert rejections[0].reasons[0].code == "schema_violation"
        assert [log.stage for log in logs] == ["verifier", "verifier"]
        assert [call["tool_choice"] for call in anthropic_client.messages.calls] == [
            {"type": "tool", "name": "verify_candidates_batch"},
            {"type": "tool", "name": "verify_candidates_batch"},
        ]
        user_payload_text = call_user_text(anthropic_client.messages.calls[0])
        user_payload = json.loads(user_payload_text)
        assert user_payload["items"][0]["critic_summary"] == {"accepted": True}
        assert user_payload["items"][0]["candidate"]["id"] == short_candidate_id(
            "candidate-1"
        )
        for forbidden in (
            "critic_report",
            "candidate_id",
            "chunk_id",
            "doc_id",
            "run_id",
            "start_byte",
            "end_byte",
            "chunk_policy",
            "budget",
            "domain_hints",
            "executor_call_id",
        ):
            assert f'"{forbidden}"' not in user_payload_text

    asyncio.run(run_check())


def test_verify_candidates_overrides_accepted_output_for_invented_span(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        bad_start = make_document().text.index("Margin")
        bad_candidate = make_candidate(start_char=bad_start)
        critic_report = make_critic_report(bad_candidate)
        anthropic_client = QueuedAnthropicClient(
            [batch_payload(accepted_payload(candidate_id="candidate-1"))]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, (bad_candidate,), (critic_report,))
            result = await verify_candidates(
                plan=make_plan(),
                chunks=make_chunks(),
                candidates=(bad_candidate,),
                critic_reports=(critic_report,),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )
            reports = await audit_store.list_verifier_reports(bad_candidate.candidate_id)
            rejections = await audit_store.list_candidate_rejections(bad_candidate.candidate_id)

        assert result.accepted_candidates == ()
        assert result.rejected_candidates == (bad_candidate,)
        assert reports[0].accepted is False
        assert reports[0].span_verified is False
        assert reports[0].rejection_reasons[0].code == "invented_span"
        assert rejections[0].stage == "verifier"
        assert rejections[0].reasons[0].code == "invented_span"

    asyncio.run(run_check())


def test_verify_candidates_overrides_hallucinated_span_rejection(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        candidate = make_candidate()
        critic_report = make_critic_report(candidate)
        hallucinated_payload = {
            "id": short_candidate_id("candidate-1"),
            "decision": "reject",
            "code": "invalid_source_offsets",
            "evidence": "Offsets do not match the claimed span_text.",
        }
        anthropic_client = QueuedAnthropicClient(
            [batch_payload(hallucinated_payload)]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, (candidate,), (critic_report,))
            result = await verify_candidates(
                plan=make_plan(),
                chunks=make_chunks(),
                candidates=(candidate,),
                critic_reports=(critic_report,),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
                audit_store=audit_store,
            )
            reports = await audit_store.list_verifier_reports(candidate.candidate_id)
            rejections = await audit_store.list_candidate_rejections(candidate.candidate_id)

        assert result.accepted_candidates == (candidate,)
        assert result.rejected_candidates == ()
        assert reports[0].accepted is True
        assert reports[0].span_verified is True
        assert reports[0].rejection_reasons == ()
        assert rejections == ()

    asyncio.run(run_check())


def test_verify_candidates_overrides_source_traced_label_schema_rejection() -> None:
    async def run_check() -> None:
        chunk_text = "approved acquiring"
        chunk = Chunk(
            chunk_id="chunk-event",
            doc_id="doc-1",
            chunk_index=0,
            text=chunk_text,
            start_char=0,
            end_char=len(chunk_text),
            start_byte=0,
            end_byte=len(chunk_text.encode("utf-8")),
            start_token=0,
            end_token=2,
        )
        plan = ExtractionPlan(
            run_id="run-1",
            doc_id="doc-1",
            domain_hints=("finance",),
            approved_categories=(
                CategoryDefinition(
                    name="CorporateEvent",
                    description="Source-backed corporate events.",
                    fields=(
                        FieldDefinition(
                            name="event_type",
                            description="Source-traced event type label.",
                            value_type="text",
                            required=True,
                        ),
                    ),
                ),
            ),
            enabled_lenses=("event",),
            chunk_policy=ChunkPolicy(window_tokens=100, overlap_tokens=10),
            budget=ExtractionBudget(
                per_chunk_concurrency=1,
                lens_budgets=(LensBudget(lens="event", max_calls=1),),
            ),
        )
        candidate = LensCandidate(
            candidate_id="candidate-acquisition",
            run_id="run-1",
            doc_id="doc-1",
            chunk_id=chunk.chunk_id,
            lens="event",
            category="CorporateEvent",
            field_name="event_type",
            value="Acquisition approval",
            source_span=SourceSpan(
                doc_id="doc-1",
                chunk_id=chunk.chunk_id,
                start_char=0,
                end_char=len(chunk_text),
                start_byte=0,
                end_byte=len(chunk_text.encode("utf-8")),
                text=chunk_text,
            ),
            confidence=0.82,
            executor_call_id="call-executor-1",
        )
        critic_report = make_critic_report(candidate)
        hallucinated_payload = {
            "id": short_candidate_id(candidate.candidate_id),
            "decision": "reject",
            "code": "schema_violation",
            "evidence": "Value is not directly stated in source.",
        }
        anthropic_client = QueuedAnthropicClient([batch_payload(hallucinated_payload)])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        result = await verify_candidates(
            plan=plan,
            chunks=(chunk,),
            candidates=(candidate,),
            critic_reports=(critic_report,),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
            execution_config=make_execution_config(),
        )

        assert result.accepted_candidates == (candidate,)
        assert result.rejected_candidates == ()
        assert result.reports[0].accepted is True
        assert result.reports[0].rejection_reasons == ()

    asyncio.run(run_check())


def test_verify_candidates_overrides_source_supported_non_label_schema_rejection() -> None:
    async def run_check() -> None:
        chunk_text = "The acquired laboratory includes two certified clean rooms."
        chunk = Chunk(
            chunk_id="chunk-asset",
            doc_id="doc-1",
            chunk_index=0,
            text=chunk_text,
            start_char=0,
            end_char=len(chunk_text),
            start_byte=0,
            end_byte=len(chunk_text.encode("utf-8")),
            start_token=0,
            end_token=8,
        )
        candidate = LensCandidate(
            candidate_id="candidate-asset-detail",
            run_id="run-1",
            doc_id="doc-1",
            chunk_id=chunk.chunk_id,
            lens="event",
            category="CorporateEvent",
            field_name="asset_detail",
            value=chunk_text,
            source_span=SourceSpan(
                doc_id="doc-1",
                chunk_id=chunk.chunk_id,
                start_char=0,
                end_char=len(chunk_text),
                start_byte=0,
                end_byte=len(chunk_text.encode("utf-8")),
                text=chunk_text,
            ),
            confidence=0.86,
            executor_call_id="call-executor-1",
        )
        critic_report = make_critic_report(candidate)
        hallucinated_payload = {
            "id": short_candidate_id(candidate.candidate_id),
            "decision": "reject",
            "code": "schema_violation",
            "evidence": (
                "asset_detail is for facility details; this span describes the "
                "event rather than a suitable field value."
            ),
        }
        anthropic_client = QueuedAnthropicClient([batch_payload(hallucinated_payload)])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        result = await verify_candidates(
            plan=make_corporate_asset_detail_plan(),
            chunks=(chunk,),
            candidates=(candidate,),
            critic_reports=(critic_report,),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
            execution_config=make_execution_config(),
        )

        assert result.accepted_candidates == (candidate,)
        assert result.rejected_candidates == ()
        assert result.reports[0].accepted is True
        assert result.reports[0].rejection_reasons == ()

    asyncio.run(run_check())


def test_verify_candidates_keeps_schema_rejection_for_unapproved_non_label_field() -> None:
    async def run_check() -> None:
        chunk_text = "The acquired laboratory includes two certified clean rooms."
        chunk = Chunk(
            chunk_id="chunk-asset",
            doc_id="doc-1",
            chunk_index=0,
            text=chunk_text,
            start_char=0,
            end_char=len(chunk_text),
            start_byte=0,
            end_byte=len(chunk_text.encode("utf-8")),
            start_token=0,
            end_token=8,
        )
        candidate = LensCandidate(
            candidate_id="candidate-asset-detail",
            run_id="run-1",
            doc_id="doc-1",
            chunk_id=chunk.chunk_id,
            lens="event",
            category="CorporateEvent",
            field_name="asset_detail",
            value=chunk_text,
            source_span=SourceSpan(
                doc_id="doc-1",
                chunk_id=chunk.chunk_id,
                start_char=0,
                end_char=len(chunk_text),
                start_byte=0,
                end_byte=len(chunk_text.encode("utf-8")),
                text=chunk_text,
            ),
            confidence=0.86,
            executor_call_id="call-executor-1",
        )
        critic_report = make_critic_report(candidate)
        hallucinated_payload = {
            "id": short_candidate_id(candidate.candidate_id),
            "decision": "reject",
            "code": "schema_violation",
            "evidence": "asset_detail is not approved by the schema.",
        }
        anthropic_client = QueuedAnthropicClient([batch_payload(hallucinated_payload)])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        result = await verify_candidates(
            plan=make_plan(),
            chunks=(chunk,),
            candidates=(candidate,),
            critic_reports=(critic_report,),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
            execution_config=make_execution_config(),
        )

        assert result.accepted_candidates == ()
        assert result.rejected_candidates == (candidate,)
        assert result.reports[0].accepted is False
        assert result.reports[0].rejection_reasons[0].code == "schema_violation"

    asyncio.run(run_check())


def test_verify_candidates_rejects_value_that_adds_ungrounded_tokens() -> None:
    async def run_check() -> None:
        span_text = "6,581 in Q1 2025"
        chunk = Chunk(
            chunk_id="chunk-prior",
            doc_id="doc-1",
            chunk_index=0,
            text=span_text,
            start_char=0,
            end_char=len(span_text),
            start_byte=0,
            end_byte=len(span_text.encode("utf-8")),
            start_token=0,
            end_token=5,
        )
        candidate = make_candidate(
            chunk=chunk,
            source_text=span_text,
            value="6,581 gigawatt-hours in Q1 2025",
        )
        critic_report = make_critic_report(candidate)
        anthropic_client = QueuedAnthropicClient(
            [batch_payload(accepted_payload(candidate_id=candidate.candidate_id))]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        result = await verify_candidates(
            plan=make_plan(),
            chunks=(chunk,),
            candidates=(candidate,),
            critic_reports=(critic_report,),
            prompt_loader=PromptLoader(ROOT / "prompts"),
            llm_client=llm_client,
            execution_config=make_execution_config(),
        )

        assert result.accepted_candidates == ()
        assert result.rejected_candidates == (candidate,)
        assert result.reports[0].accepted is False
        assert result.reports[0].rejection_reasons[0].code == "invented_span"
        assert "adds words or units" in result.reports[0].rejection_reasons[0].message

    asyncio.run(run_check())


def test_verify_candidates_rejects_missing_accepted_critic_report_before_llm_calls() -> None:
    async def run_check() -> None:
        candidate = make_candidate()
        rejected_report = make_critic_report(candidate, accepted=False)
        anthropic_client = QueuedAnthropicClient([])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        with pytest.raises(VerifierError, match="accepted critic report"):
            await verify_candidates(
                plan=make_plan(),
                chunks=make_chunks(),
                candidates=(candidate,),
                critic_reports=(rejected_report,),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
            )

        assert anthropic_client.messages.calls == []

    asyncio.run(run_check())


def test_verify_candidates_batches_per_chunk(tmp_path: Path) -> None:
    async def run_check() -> None:
        chunks = make_chunks()
        chunk_a, chunk_b = chunks
        second_start = make_document().text.index("Margin")
        candidates_a = tuple(
            make_candidate(
                candidate_id=f"candidate-a-{index}",
                chunk=chunk_a,
                source_text="Revenue increased",
                start_char=0,
                value="Revenue increased",
            )
            for index in range(8)
        )
        candidates_b = tuple(
            make_candidate(
                candidate_id=f"candidate-b-{index}",
                chunk=chunk_b,
                source_text="Margin declined",
                start_char=second_start,
                value="Margin declined",
            )
            for index in range(4)
        )
        candidates = (*candidates_a, *candidates_b)
        critic_reports = tuple(make_critic_report(candidate) for candidate in candidates)

        # batch_size=5 → 2 batches for chunk A (5+3), 1 batch for chunk B (4) = 3 calls.
        first_chunk_a_payloads = [
            accepted_payload(candidate_id=candidate.candidate_id)
            for candidate in candidates_a[:5]
        ]
        second_chunk_a_payloads = [
            accepted_payload(candidate_id=candidate.candidate_id)
            for candidate in candidates_a[5:]
        ]
        chunk_b_payloads = [
            accepted_payload(candidate_id=candidate.candidate_id)
            for candidate in candidates_b
        ]
        anthropic_client = QueuedAnthropicClient(
            [
                batch_payload(*first_chunk_a_payloads),
                batch_payload(*second_chunk_a_payloads),
                batch_payload(*chunk_b_payloads),
            ]
        )
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)
        execution_config = ExecutionConfig(
            max_stage_concurrency=1,
            max_chunk_concurrency=1,
            max_llm_attempts=1,
            verifier_batch_size=5,
        )

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await seed_audit_store(audit_store, candidates, critic_reports)
            result = await verify_candidates(
                plan=make_plan(),
                chunks=chunks,
                candidates=candidates,
                critic_reports=critic_reports,
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=execution_config,
                audit_store=audit_store,
            )
            logs = await audit_store.list_llm_call_logs("run-1")

        assert len(anthropic_client.messages.calls) == 3
        assert len(result.accepted_candidates) == 12
        assert len(result.reports) == 12
        assert [log.stage for log in logs] == ["verifier", "verifier", "verifier"]

    asyncio.run(run_check())


def test_verify_candidates_rejects_candidate_that_misses_critic_correction() -> None:
    async def run_check() -> None:
        candidate = make_candidate()
        corrected = candidate.model_copy(update={"value": "Corrected revenue finding"})
        critic_report = make_critic_report(candidate, corrected_candidate=corrected)
        anthropic_client = QueuedAnthropicClient([])
        llm_client = LLMClient(make_llm_config(), anthropic_client=anthropic_client)

        with pytest.raises(VerifierError, match="accepted critic correction"):
            await verify_candidates(
                plan=make_plan(),
                chunks=make_chunks(),
                candidates=(candidate,),
                critic_reports=(critic_report,),
                prompt_loader=PromptLoader(ROOT / "prompts"),
                llm_client=llm_client,
                execution_config=make_execution_config(),
            )

        assert anthropic_client.messages.calls == []

    asyncio.run(run_check())
