from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from extractor.contracts.ingestion import (
    LayoutSpan,
    TableCellSpan,
    TableSpan,
    TextRange,
)
from extractor.ingestion.errors import IngestionError


class TextAssembler(Protocol):
    current_char: int
    current_byte: int

    def add_segment(
        self,
        text: str,
        *,
        segment_id: str,
        kind: Literal["generated", "unmapped"],
    ) -> TextRange: ...


@dataclass(frozen=True)
class _CellRecord:
    row_index: int
    column_index: int
    text_range: TextRange
    header_labels: tuple[str, ...]


def append_html_table_rows(
    rows: list[list[str]],
    *,
    assembler: TextAssembler,
    table_index: int,
) -> tuple[TableSpan, LayoutSpan, tuple[LayoutSpan, ...]]:
    table_start_char = assembler.current_char
    table_start_byte = assembler.current_byte
    headers = rows[0]
    cell_records: list[_CellRecord] = []

    for row_index, row in enumerate(rows):
        if row_index > 0:
            assembler.add_segment(
                "\n",
                segment_id=(
                    f"generated:html:table:{table_index}:row-separator:{row_index - 1}"
                ),
                kind="generated",
            )
        row_text = " ".join(row)
        row_start_char = assembler.current_char
        row_start_byte = assembler.current_byte
        assembler.add_segment(
            row_text,
            segment_id=f"unmapped:html:table:{table_index}:row:{row_index}",
            kind="unmapped",
        )

        local_char = 0
        for column_index, cell_text in enumerate(row):
            if cell_text == "":
                raise IngestionError("HTML table cell output must include text")
            start_char = row_start_char + local_char
            end_char = start_char + len(cell_text)
            start_byte = row_start_byte + len(row_text[:local_char].encode("utf-8"))
            end_byte = row_start_byte + len(
                row_text[: local_char + len(cell_text)].encode("utf-8")
            )
            cell_records.append(
                _CellRecord(
                    row_index=row_index,
                    column_index=column_index,
                    text_range=TextRange(
                        start_char=start_char,
                        end_char=end_char,
                        start_byte=start_byte,
                        end_byte=end_byte,
                    ),
                    header_labels=_header_labels(headers, row_index, column_index),
                )
            )
            local_char += len(cell_text) + 1

    if not cell_records:
        raise IngestionError("HTML parser table output must include at least one cell")

    table_id = f"table:html:1:{table_index}:{table_start_char}:{assembler.current_char}"
    table_range = TextRange(
        start_char=table_start_char,
        end_char=assembler.current_char,
        start_byte=table_start_byte,
        end_byte=assembler.current_byte,
    )
    table_span = TableSpan(
        table_id=table_id,
        page_number=1,
        text_range=table_range,
        cells=tuple(
            TableCellSpan(
                cell_id=f"cell:{table_id}:r{cell.row_index}:c{cell.column_index}",
                text_range=cell.text_range,
                row_index=cell.row_index,
                column_index=cell.column_index,
                header_labels=cell.header_labels,
            )
            for cell in cell_records
        ),
    )
    table_layout = LayoutSpan(
        span_id=f"layout:html:1:table:{table_index}",
        page_number=1,
        role="table",
        text_range=table_range,
    )
    cell_layouts = tuple(
        LayoutSpan(
            span_id=(
                f"layout:html:1:table:{table_index}:"
                f"cell:{cell.row_index}:{cell.column_index}"
            ),
            page_number=1,
            role="table_cell",
            text_range=cell.text_range,
        )
        for cell in cell_records
    )
    return table_span, table_layout, cell_layouts


def _header_labels(
    headers: list[str],
    row_index: int,
    column_index: int,
) -> tuple[str, ...]:
    if row_index == 0 or column_index >= len(headers) or headers[column_index] == "":
        return ()
    return (headers[column_index],)


__all__ = ["append_html_table_rows"]
