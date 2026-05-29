import asyncio
import hashlib

import pytest

from extractor.audit import AuditStore
from extractor.chunker import chunk_document
from extractor.config import ChunkingConfig
from extractor.contracts import Document, LayoutSpan, PageSpan, TextRange
from extractor.orchestrator.errors import OrchestratorError
from extractor.orchestrator.state import validate_resume_chunks


HASH = "a" * 64


def text_range(start: int, end: int) -> TextRange:
    return TextRange(start_char=start, end_char=end, start_byte=start, end_byte=end)


def make_config() -> ChunkingConfig:
    return ChunkingConfig(
        tokenizer="cl100k_base",
        window_tokens=6,
        overlap_tokens=0,
        boundary_mode="layout_aware",
    )


def make_section_document() -> Document:
    text = "Terms\nPayment must occur promptly."
    text_bytes = text.encode("utf-8")
    heading_end = len("Terms")
    paragraph_start = text.index("Payment")
    return Document(
        doc_id="doc-1",
        source_path="/tmp/doc.txt",
        format="plain_text",
        text=text,
        source_sha256=HASH,
        text_sha256=hashlib.sha256(text_bytes).hexdigest(),
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
        layout_spans=(
            LayoutSpan(
                span_id="layout-heading",
                page_number=1,
                role="heading",
                text_range=text_range(0, heading_end),
            ),
            LayoutSpan(
                span_id="layout-payment",
                page_number=1,
                role="paragraph",
                text_range=text_range(paragraph_start, len(text)),
            ),
        ),
    )


def test_layout_aware_chunks_record_section_path_and_dependencies() -> None:
    async def run_check() -> None:
        chunks = await chunk_document(make_section_document(), make_config())

        heading = chunks[0]
        payment = chunks[1]

        assert heading.chunk_kind == "section"
        assert heading.section_path == ("Terms",)
        assert payment.section_path == ("Terms",)
        assert payment.parent_chunk_id == heading.chunk_id
        assert payment.depends_on_chunk_ids == (heading.chunk_id,)

    asyncio.run(run_check())


def test_audit_store_round_trips_layout_aware_chunk_metadata(tmp_path) -> None:
    async def run_check() -> None:
        document = make_section_document()
        async with AuditStore(tmp_path / "audit.sqlite3") as store:
            await store.record_document(document)
            chunks = await chunk_document(document, make_config(), audit_store=store)
            stored_chunks = await store.list_chunks(document.doc_id)

        assert stored_chunks == chunks
        assert stored_chunks[1].section_path == ("Terms",)
        assert stored_chunks[1].depends_on_chunk_ids == (stored_chunks[0].chunk_id,)

    asyncio.run(run_check())


def test_resume_validation_rejects_invalid_chunk_dependency_metadata() -> None:
    async def run_check() -> None:
        document = make_section_document()
        chunks = await chunk_document(document, make_config())
        invalid_dependency = chunks[1].model_copy(
            update={"depends_on_chunk_ids": ("missing-chunk",)}
        )
        invalid_parent = chunks[1].model_copy(update={"parent_chunk_id": "missing-parent"})

        with pytest.raises(OrchestratorError, match="chunk dependency references missing chunk"):
            validate_resume_chunks(document=document, chunks=(chunks[0], invalid_dependency))

        with pytest.raises(OrchestratorError, match="chunk parent references missing chunk"):
            validate_resume_chunks(document=document, chunks=(chunks[0], invalid_parent))

    asyncio.run(run_check())
