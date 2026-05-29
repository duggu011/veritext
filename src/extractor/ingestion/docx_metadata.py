from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from extractor.contracts.ingestion import DocumentMetadata, MetadataEntry
from extractor.ingestion.errors import IngestionError


DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOCX_PARSER_NAME = "openxml-docx"
CORE_PROPERTIES_PATH = "docProps/core.xml"

DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"

NS = {
    "dc": DC_NS,
    "dcterms": DCTERMS_NS,
}


@dataclass(frozen=True)
class _DocxMetadata:
    title: str | None = None
    creator: str | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None


def extract_docx_metadata(package: ZipFile, source_path: Path) -> DocumentMetadata:
    raw_metadata = _extract_core_metadata(package, source_path)
    entries: list[MetadataEntry] = []
    if raw_metadata.creator is not None:
        entries.append(MetadataEntry(key="creator", value=raw_metadata.creator))
    if raw_metadata.title is not None:
        entries.append(MetadataEntry(key="title", value=raw_metadata.title))

    return DocumentMetadata(
        source_name=source_path.name,
        mime_type=DOCX_MIME_TYPE,
        parser_name=DOCX_PARSER_NAME,
        created_at=raw_metadata.created_at,
        modified_at=raw_metadata.modified_at,
        raw_metadata=tuple(entries),
    )


def _extract_core_metadata(package: ZipFile, source_path: Path) -> _DocxMetadata:
    try:
        core_xml = package.read(CORE_PROPERTIES_PATH)
    except KeyError:
        return _DocxMetadata()

    try:
        root = ElementTree.fromstring(core_xml)
    except ElementTree.ParseError as exc:
        raise IngestionError(f"DOCX parser failed for source document: {source_path}") from exc

    return _DocxMetadata(
        title=_element_text(root, "dc:title"),
        creator=_element_text(root, "dc:creator"),
        created_at=_parse_docx_datetime(_element_text(root, "dcterms:created"), source_path),
        modified_at=_parse_docx_datetime(
            _element_text(root, "dcterms:modified"),
            source_path,
        ),
    )


def _element_text(root: ElementTree.Element, path: str) -> str | None:
    element = root.find(path, NS)
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _parse_docx_datetime(value: str | None, source_path: Path) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IngestionError(f"DOCX core property timestamp is invalid: {source_path}") from exc


__all__ = [
    "DOCX_MIME_TYPE",
    "DOCX_PARSER_NAME",
    "extract_docx_metadata",
]
