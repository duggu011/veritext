from extractor.contracts import Document, PageSpan
from extractor.ingestion import detect_document_format


HASH = "a" * 64


def test_phase_34_detects_docx_html_and_email_formats() -> None:
    assert detect_document_format("contract.docx") == "docx"
    assert detect_document_format("notice.html") == "html"
    assert detect_document_format("notice.htm") == "html"
    assert detect_document_format("message.eml") == "email"
    assert detect_document_format("CONTRACT.DOCX") == "docx"
    assert detect_document_format("NOTICE.HTML") == "html"
    assert detect_document_format("MESSAGE.EML") == "email"


def test_document_contract_accepts_phase_34_formats() -> None:
    for document_format in ("docx", "html", "email"):
        document = Document(
            doc_id=f"doc-{document_format}",
            source_path=f"/tmp/source.{document_format}",
            format=document_format,
            text="alpha",
            source_sha256=HASH,
            text_sha256=HASH,
            source_byte_length=5,
            text_byte_length=5,
            page_map=(
                PageSpan(
                    page_number=1,
                    start_char=0,
                    end_char=5,
                    start_byte=0,
                    end_byte=5,
                ),
            ),
        )

        assert document.format == document_format
