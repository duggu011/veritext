class IngestionError(RuntimeError):
    """Base class for document ingestion failures."""


class UnsupportedDocumentFormatError(IngestionError):
    """Raised when a source file has no supported ingestion format."""


class EmptyDocumentError(IngestionError):
    """Raised when source extraction yields no document text."""


__all__ = [
    "EmptyDocumentError",
    "IngestionError",
    "UnsupportedDocumentFormatError",
]
