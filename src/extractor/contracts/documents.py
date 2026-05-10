from __future__ import annotations

from typing import Annotated

from pydantic import Field, field_validator, model_validator

from extractor.contracts.base import (
    ContractModel,
    DocumentFormat,
    NonEmptyStr,
    NonNegativeInt,
    PositiveInt,
    Sha256Hex,
)
from extractor.contracts.ingestion import (
    BoundaryValidationContext,
    DocumentMetadata,
    IngestionBoundarySet,
    LayoutSpan,
    OcrConfidenceSpan,
    SourceMapSegment,
    TableSpan,
    validate_ingestion_boundaries,
)


class PageSpan(ContractModel):
    page_number: PositiveInt
    start_char: NonNegativeInt
    end_char: NonNegativeInt
    start_byte: NonNegativeInt
    end_byte: NonNegativeInt

    @model_validator(mode="after")
    def validate_offsets(self) -> PageSpan:
        if self.end_char < self.start_char:
            raise ValueError("end_char must be greater than or equal to start_char")
        if self.end_byte < self.start_byte:
            raise ValueError("end_byte must be greater than or equal to start_byte")
        return self


class Document(ContractModel):
    doc_id: NonEmptyStr
    source_path: NonEmptyStr
    format: DocumentFormat
    text: Annotated[str, Field(strict=True)]
    source_sha256: Sha256Hex
    text_sha256: Sha256Hex
    source_byte_length: NonNegativeInt
    text_byte_length: NonNegativeInt
    page_map: tuple[PageSpan, ...] = Field(min_length=1)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    source_map: tuple[SourceMapSegment, ...] = ()
    layout_spans: tuple[LayoutSpan, ...] = ()
    table_spans: tuple[TableSpan, ...] = ()
    ocr_confidence_spans: tuple[OcrConfidenceSpan, ...] = ()

    @field_validator("text")
    @classmethod
    def reject_empty_text(cls, value: str) -> str:
        if value == "":
            raise ValueError("text must not be empty")
        return value

    @model_validator(mode="after")
    def validate_page_map_and_boundaries(self) -> Document:
        if self.text_byte_length != len(self.text.encode("utf-8")):
            raise ValueError("text_byte_length must match UTF-8 encoded text length")

        previous_char_end = 0
        previous_byte_end = 0
        text_length = len(self.text)
        page_numbers: list[int] = []
        for page in self.page_map:
            page_numbers.append(page.page_number)
            if page.end_char > text_length:
                raise ValueError("page_map entry exceeds document text length")
            if page.end_byte > self.text_byte_length:
                raise ValueError("page_map entry exceeds document text byte length")
            if page.start_char < previous_char_end:
                raise ValueError("page_map character entries must be ordered and non-overlapping")
            if page.start_byte < previous_byte_end:
                raise ValueError("page_map byte entries must be ordered and non-overlapping")
            previous_char_end = page.end_char
            previous_byte_end = page.end_byte

        validate_ingestion_boundaries(
            boundaries=self.boundary_set,
            context=BoundaryValidationContext(
                text_length=text_length,
                text_byte_length=self.text_byte_length,
                source_byte_length=self.source_byte_length,
                page_numbers=tuple(page_numbers),
            ),
        )
        return self

    @property
    def boundary_set(self) -> IngestionBoundarySet:
        return IngestionBoundarySet(
            metadata=self.metadata,
            source_map=self.source_map,
            layout_spans=self.layout_spans,
            table_spans=self.table_spans,
            ocr_confidence_spans=self.ocr_confidence_spans,
        )


__all__ = [
    "Document",
    "PageSpan",
]
