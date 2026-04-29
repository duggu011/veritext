import asyncio
import hashlib

import pytest

from extractor.audit import AuditStore
from extractor.chunker import ChunkingError, chunk_document
from extractor.config import ChunkingConfig
from extractor.contracts import Document, PageSpan


HASH = "a" * 64


def make_document(text: str, *, doc_id: str = "doc-1") -> Document:
    text_bytes = text.encode("utf-8")
    return Document(
        doc_id=doc_id,
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
    )


def make_config(window_tokens: int, overlap_tokens: int = 0) -> ChunkingConfig:
    return ChunkingConfig(
        tokenizer="cl100k_base",
        window_tokens=window_tokens,
        overlap_tokens=overlap_tokens,
    )


def test_chunk_document_uses_token_windows_overlap_and_stable_ids() -> None:
    async def run_check() -> None:
        document = make_document("one two three four five six")
        chunks = await chunk_document(document, make_config(window_tokens=3, overlap_tokens=1))
        repeated = await chunk_document(document, make_config(window_tokens=3, overlap_tokens=1))

        assert chunks == repeated
        assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
        assert [(chunk.start_token, chunk.end_token) for chunk in chunks] == [
            (0, 3),
            (2, 5),
            (4, 6),
        ]
        assert [chunk.text for chunk in chunks] == [
            "one two three",
            " three four five",
            " five six",
        ]
        assert all(chunk.chunk_id.startswith("chunk-") for chunk in chunks)
        assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
        assert chunks[0].doc_id == document.doc_id
        assert chunks[1].start_byte == len("one two".encode("utf-8"))
        assert chunks[1].end_byte == len("one two three four five".encode("utf-8"))

    asyncio.run(run_check())


def test_chunk_document_preserves_utf8_boundaries_when_tokens_split_characters() -> None:
    async def run_check() -> None:
        document = make_document("😀 test alpha")
        chunks = await chunk_document(document, make_config(window_tokens=1, overlap_tokens=0))
        document_bytes = document.text.encode("utf-8")

        assert "".join(chunk.text for chunk in chunks) == document.text
        assert chunks[0].text == "😀"
        assert chunks[0].start_token == 0
        assert chunks[0].end_token == 2

        for chunk in chunks:
            assert chunk.text == document.text[chunk.start_char : chunk.end_char]
            assert chunk.text.encode("utf-8") == document_bytes[chunk.start_byte : chunk.end_byte]

    asyncio.run(run_check())


def test_chunk_document_records_chunks_to_audit_store(tmp_path) -> None:
    async def run_check() -> None:
        document = make_document("one two three four", doc_id="doc-audit")

        async with AuditStore(tmp_path / "audit.sqlite3") as audit_store:
            await audit_store.record_document(document)
            chunks = await chunk_document(
                document,
                make_config(window_tokens=2, overlap_tokens=0),
                audit_store=audit_store,
            )
            stored_chunks = await audit_store.list_chunks(document.doc_id)

        assert stored_chunks == chunks

    asyncio.run(run_check())


def test_chunk_document_rejects_unknown_tokenizer() -> None:
    async def run_check() -> None:
        document = make_document("one two")
        config = ChunkingConfig(tokenizer="missing-tokenizer", window_tokens=10, overlap_tokens=0)

        with pytest.raises(ChunkingError, match="Unknown tokenizer"):
            await chunk_document(document, config)

    asyncio.run(run_check())
