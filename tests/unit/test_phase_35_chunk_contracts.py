import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from extractor.audit import AuditStore
from extractor.config import ChunkingConfig, load_config
from extractor.contracts import Chunk, Document, PageSpan


HASH = "a" * 64


def make_document() -> Document:
    return Document(
        doc_id="doc-1",
        source_path="/tmp/doc.txt",
        format="plain_text",
        text="hello world",
        source_sha256=HASH,
        text_sha256=HASH,
        source_byte_length=11,
        text_byte_length=11,
        page_map=(PageSpan(page_number=1, start_char=0, end_char=11, start_byte=0, end_byte=11),),
    )


def make_legacy_chunk_payload() -> dict[str, object]:
    return {
        "chunk_id": "chunk-legacy",
        "doc_id": "doc-1",
        "chunk_index": 0,
        "text": "hello world",
        "start_char": 0,
        "end_char": 11,
        "start_byte": 0,
        "end_byte": 11,
        "start_token": 0,
        "end_token": 2,
    }


def test_chunk_metadata_defaults_keep_legacy_payloads_readable() -> None:
    chunk = Chunk.model_validate(make_legacy_chunk_payload())

    assert chunk.chunk_kind == "mixed"
    assert chunk.section_path == ()
    assert chunk.layout_span_ids == ()
    assert chunk.table_ids == ()
    assert chunk.page_numbers == ()
    assert chunk.parent_chunk_id is None
    assert chunk.depends_on_chunk_ids == ()
    assert chunk.split_reason == "token_window"
    assert chunk.tokenizer_policy == "tiktoken"


def test_chunk_metadata_accepts_typed_layout_and_dependency_fields() -> None:
    chunk = Chunk.model_validate(
        {
            **make_legacy_chunk_payload(),
            "chunk_kind": "table",
            "section_path": ("Risk Factors", "Liquidity"),
            "layout_span_ids": ("layout-1",),
            "table_ids": ("table-1",),
            "page_numbers": (2,),
            "parent_chunk_id": "chunk-parent",
            "depends_on_chunk_ids": ("chunk-parent",),
            "split_reason": "atomic_table_overflow",
            "tokenizer_policy": "tiktoken",
        }
    )

    assert chunk.chunk_kind == "table"
    assert chunk.section_path == ("Risk Factors", "Liquidity")
    assert chunk.layout_span_ids == ("layout-1",)
    assert chunk.table_ids == ("table-1",)
    assert chunk.page_numbers == (2,)
    assert chunk.parent_chunk_id == "chunk-parent"
    assert chunk.depends_on_chunk_ids == ("chunk-parent",)
    assert chunk.split_reason == "atomic_table_overflow"


def test_chunk_metadata_rejects_unknown_literals_and_invalid_page_numbers() -> None:
    with pytest.raises(ValidationError):
        Chunk.model_validate({**make_legacy_chunk_payload(), "chunk_kind": "fixture_specific"})

    with pytest.raises(ValidationError):
        Chunk.model_validate({**make_legacy_chunk_payload(), "split_reason": "document_title"})

    with pytest.raises(ValidationError):
        Chunk.model_validate({**make_legacy_chunk_payload(), "page_numbers": (0,)})


def test_audit_store_reads_legacy_chunk_payloads_with_metadata_defaults(tmp_path: Path) -> None:
    async def run_check() -> None:
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            await store.record_document(make_document())
            legacy_payload = make_legacy_chunk_payload()
            await store._insert_payload(
                "chunks",
                {
                    "chunk_id": legacy_payload["chunk_id"],
                    "doc_id": legacy_payload["doc_id"],
                    "chunk_index": legacy_payload["chunk_index"],
                    "start_char": legacy_payload["start_char"],
                    "end_char": legacy_payload["end_char"],
                    "payload_json": json.dumps(legacy_payload),
                },
            )

            chunk = await store.get_chunk("chunk-legacy")

        assert chunk is not None
        assert chunk.chunk_kind == "mixed"
        assert chunk.split_reason == "token_window"
        assert chunk.tokenizer_policy == "tiktoken"

    asyncio.run(run_check())


def test_chunking_config_defaults_preserve_legacy_token_window_mode() -> None:
    config = load_config(env={}, include_local=False)

    assert config.chunking.boundary_mode == "token_window"
    assert config.chunking.tokenizer_policy == "tiktoken"
    assert config.chunking.allow_oversized_atomic_chunks is True


def test_chunking_config_rejects_unknown_tokenizer_policy_and_non_strict_flags() -> None:
    with pytest.raises(ValidationError):
        ChunkingConfig(
            tokenizer="cl100k_base",
            window_tokens=1200,
            overlap_tokens=120,
            tokenizer_policy="provider_api",
        )

    with pytest.raises(ValidationError):
        ChunkingConfig(
            tokenizer="cl100k_base",
            window_tokens=1200,
            overlap_tokens=120,
            allow_oversized_atomic_chunks="true",
        )
