from datetime import datetime, timezone

from extractor.contracts import LensCandidate, SourceSpan
from extractor.executor.dedup import build_dedup_rejections, deduplicate_candidates


def make_candidate(
    candidate_id: str,
    *,
    value: str = "Revenue increased",
    source_text: str = "Revenue increased",
    chunk_id: str = "chunk-1",
) -> LensCandidate:
    return LensCandidate(
        candidate_id=candidate_id,
        run_id="run-1",
        doc_id="doc-1",
        chunk_id=chunk_id,
        lens="claim",
        category="Finding",
        field_name="summary",
        value=value,
        source_span=SourceSpan(
            doc_id="doc-1",
            chunk_id=chunk_id,
            start_char=0,
            end_char=len(source_text),
            start_byte=0,
            end_byte=len(source_text.encode("utf-8")),
            text=source_text,
        ),
        confidence=0.8,
        executor_call_id=f"executor-{candidate_id}",
    )


def test_deduplicate_candidates_groups_exact_duplicates_with_stable_primary() -> None:
    later = make_candidate("candidate-b")
    primary = make_candidate("candidate-a")

    canonical, merged_into = deduplicate_candidates((later, primary))

    assert canonical == (primary,)
    assert merged_into == {"candidate-b": "candidate-a"}


def test_deduplicate_candidates_preserves_distinct_values() -> None:
    first = make_candidate("candidate-a", value="Revenue increased")
    second = make_candidate("candidate-b", value="Margin declined")

    canonical, merged_into = deduplicate_candidates((first, second))

    assert canonical == (first, second)
    assert merged_into == {}


def test_deduplicate_candidates_preserves_distinct_source_text() -> None:
    first = make_candidate("candidate-a", source_text="Revenue increased")
    second = make_candidate("candidate-b", source_text="Revenue increased.")

    canonical, merged_into = deduplicate_candidates((first, second))

    assert canonical == (first, second)
    assert merged_into == {}


def test_build_dedup_rejections_records_merge_target() -> None:
    first = make_candidate("candidate-a")
    second = make_candidate("candidate-b")
    _, merged_into = deduplicate_candidates((first, second))

    rejections = build_dedup_rejections(
        run_id="run-1",
        candidates=(first, second),
        merged_into=merged_into,
    )

    assert len(rejections) == 1
    assert rejections[0].stage == "dedup"
    assert rejections[0].candidate_id == "candidate-b"
    assert rejections[0].reasons[0].code == "duplicate_candidate"
    assert rejections[0].reasons[0].message == "merged_into:candidate-a"
    assert rejections[0].created_at <= datetime.now(timezone.utc)
