"""Document ingestion stages."""

from extractor.ingestion.documents import (
    detect_document_format,
    ingest_document,
)
from extractor.ingestion.errors import (
    EmptyDocumentError,
    IngestionError,
    UnsupportedDocumentFormatError,
)

__all__ = [
    "EmptyDocumentError",
    "IngestionError",
    "UnsupportedDocumentFormatError",
    "detect_document_format",
    "ingest_document",
]
