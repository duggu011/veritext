import asyncio
from pathlib import Path

import pytest

from extractor.ingestion import IngestionError, ingest_document


def test_ingest_email_prefers_plain_text_and_preserves_header_boundaries(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        source = tmp_path / "notice.eml"
        source.write_text(
            """Message-ID: <notice-1@example.com>
Subject: Insurance Update
From: risk@example.com
To: ops@example.com
Cc: broker@example.com
Date: Fri, 01 May 2026 10:30:00 +0000
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="alt"

--alt
Content-Type: text/plain; charset=utf-8

Insurance Requirements
Vendor shall maintain coverage.

--alt
Content-Type: text/html; charset=utf-8

<html><body><p>HTML alternative ignored.</p></body></html>
--alt--
""",
            encoding="utf-8",
        )

        document = await ingest_document(source)

        assert document.format == "email"
        assert document.metadata.source_name == "notice.eml"
        assert document.metadata.mime_type == "message/rfc822"
        assert document.metadata.parser_name == "stdlib-email"
        assert document.metadata.declared_encoding == "utf-8"
        assert {entry.key: entry.value for entry in document.metadata.raw_metadata} == {
            "cc": "broker@example.com",
            "content_type": "multipart/alternative",
            "date": "Fri, 01 May 2026 10:30:00 +0000",
            "from": "risk@example.com",
            "message_id": "<notice-1@example.com>",
            "subject": "Insurance Update",
            "to": "ops@example.com",
        }
        assert document.text == (
            "Subject: Insurance Update\n"
            "From: risk@example.com\n"
            "To: ops@example.com\n"
            "Cc: broker@example.com\n"
            "Date: Fri, 01 May 2026 10:30:00 +0000\n\n"
            "Insurance Requirements\n"
            "Vendor shall maintain coverage."
        )
        assert len(document.page_map) == 1
        assert document.page_map[0].start_char == 0
        assert document.page_map[0].end_char == len(document.text)
        assert tuple(segment.kind for segment in document.source_map) == (
            "generated",
            "unmapped",
            "generated",
            "generated",
            "unmapped",
            "generated",
            "generated",
            "unmapped",
            "generated",
            "generated",
            "unmapped",
            "generated",
            "generated",
            "unmapped",
            "generated",
            "unmapped",
        )
        assert all(segment.source_start_byte is None for segment in document.source_map)
        assert document.layout_spans == ()
        assert document.table_spans == ()

    asyncio.run(run_check())


def test_ingest_email_falls_back_to_html_body_when_plain_text_is_absent(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        source = tmp_path / "html-only.eml"
        source.write_text(
            """Subject: HTML Notice
From: risk@example.com
To: ops@example.com
MIME-Version: 1.0
Content-Type: text/html; charset=utf-8

<html><body><h1>Insurance Requirements</h1><p>Vendor shall maintain coverage.</p></body></html>
""",
            encoding="utf-8",
        )

        document = await ingest_document(source)

        assert document.metadata.declared_encoding == "utf-8"
        assert document.text == (
            "Subject: HTML Notice\n"
            "From: risk@example.com\n"
            "To: ops@example.com\n\n"
            "Insurance Requirements\n"
            "Vendor shall maintain coverage."
        )
        assert tuple(span.role for span in document.layout_spans) == (
            "heading",
            "paragraph",
        )

    asyncio.run(run_check())


def test_ingest_email_rejects_attachments_unsupported_charset_and_empty_body(
    tmp_path: Path,
) -> None:
    async def run_check() -> None:
        attachment = tmp_path / "attachment.eml"
        attachment.write_text(
            """Subject: Attachment Notice
From: risk@example.com
To: ops@example.com
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="mixed"

--mixed
Content-Type: text/plain; charset=utf-8

Body text.

--mixed
Content-Type: application/pdf
Content-Disposition: attachment; filename="evidence.pdf"

JVBERi0xLjQK
--mixed--
""",
            encoding="utf-8",
        )

        unsupported_charset = tmp_path / "unsupported.eml"
        unsupported_charset.write_bytes(
            b"Subject: Bad Charset\n"
            b"From: risk@example.com\n"
            b"To: ops@example.com\n"
            b"Content-Type: text/plain; charset=x-unknown\n\n"
            b"alpha"
        )

        empty_body = tmp_path / "empty.eml"
        empty_body.write_text(
            """Subject: Empty
From: risk@example.com
To: ops@example.com
Content-Type: text/plain; charset=utf-8

   \t
""",
            encoding="utf-8",
        )

        with pytest.raises(IngestionError, match="attachments are not supported"):
            await ingest_document(attachment)

        with pytest.raises(IngestionError, match="unsupported charset"):
            await ingest_document(unsupported_charset)

        with pytest.raises(IngestionError, match="yielded no body text"):
            await ingest_document(empty_body)

    asyncio.run(run_check())
