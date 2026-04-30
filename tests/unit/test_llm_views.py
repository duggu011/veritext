from extractor.contracts import (
    CategoryDefinition,
    Chunk,
    ChunkPolicy,
    ExtractionBudget,
    ExtractionPlan,
    FieldDefinition,
    LensBudget,
    LensCandidate,
    SourceSpan,
)
from extractor.llm.views import (
    build_candidate_view_map,
    candidate_view_from_candidate,
    chunk_view_from_chunk,
    schema_card_from_plan,
    short_candidate_id,
)

import pytest


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
            lens_budgets=(LensBudget(lens="claim", max_calls=1),),
        ),
    )


def make_chunk() -> Chunk:
    text = "Revenue increased."
    return Chunk(
        chunk_id="chunk-1",
        doc_id="doc-1",
        chunk_index=3,
        text=text,
        start_char=100,
        end_char=100 + len(text),
        start_byte=100,
        end_byte=100 + len(text.encode("utf-8")),
        start_token=20,
        end_token=23,
    )


def make_candidate(candidate_id: str = "candidate-abcdef1234567890") -> LensCandidate:
    chunk = make_chunk()
    source_text = "Revenue increased"
    start_char = chunk.start_char
    return LensCandidate(
        candidate_id=candidate_id,
        run_id="run-1",
        doc_id="doc-1",
        chunk_id=chunk.chunk_id,
        lens="claim",
        category="Finding",
        field_name="summary",
        value=source_text,
        source_span=SourceSpan(
            doc_id="doc-1",
            chunk_id=chunk.chunk_id,
            start_char=start_char,
            end_char=start_char + len(source_text),
            start_byte=chunk.start_byte,
            end_byte=chunk.start_byte + len(source_text.encode("utf-8")),
            text=source_text,
        ),
        confidence=0.8,
        executor_call_id="executor-call-1",
    )


def test_schema_and_chunk_views_drop_audit_only_fields() -> None:
    schema_card = schema_card_from_plan(make_plan())
    chunk_view = chunk_view_from_chunk(make_chunk())

    assert schema_card.model_dump() == {
        "categories": (
            {
                "name": "Finding",
                "description": "A source-backed finding.",
                "fields": (
                    {
                        "name": "summary",
                        "value_type": "text",
                        "description": "Short finding summary.",
                    },
                ),
            },
        ),
        "enabled_lenses": ("claim",),
    }
    assert chunk_view.model_dump() == {
        "start_char": 100,
        "text": "Revenue increased.",
    }


def test_candidate_view_round_trip_map_preserves_full_candidate() -> None:
    candidate = make_candidate()
    view, candidates_by_view_id = build_candidate_view_map((candidate,))

    assert view == (candidate_view_from_candidate(candidate),)
    assert view[0].id == "abcdef123456"
    assert view[0].span_start_char == candidate.source_span.start_char
    assert view[0].span_text == candidate.source_span.text
    assert candidates_by_view_id == {"abcdef123456": candidate}


def test_short_candidate_id_is_stable_for_non_hex_test_ids() -> None:
    assert short_candidate_id("candidate-1") == short_candidate_id("candidate-1")
    assert short_candidate_id("candidate-1") != short_candidate_id("candidate-2")


def test_candidate_view_map_rejects_short_id_collisions() -> None:
    first = make_candidate("candidate-abcdef1234560000")
    second = make_candidate("candidate-abcdef1234569999")

    with pytest.raises(ValueError, match="short ID collision"):
        build_candidate_view_map((first, second))
