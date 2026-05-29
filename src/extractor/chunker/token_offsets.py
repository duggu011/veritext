from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class TokenOffsetError(RuntimeError):
    """Raised when tokenizer bytes cannot be mapped back to document text."""


class TokenEncoding(Protocol):
    def decode_single_token_bytes(self, token: int) -> bytes: ...


@dataclass(frozen=True)
class TokenOffsetMap:
    tokens: tuple[int, ...]
    token_starts: tuple[int, ...]
    token_ends: tuple[int, ...]
    byte_to_char: dict[int, int]


@dataclass(frozen=True)
class TokenTextRange:
    start_byte: int
    end_byte: int
    start_char: int
    end_char: int


def build_token_offset_map(
    text: str,
    encoding: TokenEncoding,
    tokens: Sequence[int],
) -> TokenOffsetMap:
    token_starts: list[int] = []
    token_ends: list[int] = []
    cursor = 0
    pieces: list[bytes] = []
    for token in tokens:
        piece = encoding.decode_single_token_bytes(token)
        token_starts.append(cursor)
        cursor += len(piece)
        token_ends.append(cursor)
        pieces.append(piece)

    text_bytes = text.encode("utf-8")
    if b"".join(pieces) != text_bytes:
        raise TokenOffsetError("Tokenizer byte reconstruction did not match document text")

    return TokenOffsetMap(
        tokens=tuple(tokens),
        token_starts=tuple(token_starts),
        token_ends=tuple(token_ends),
        byte_to_char=byte_to_char_boundaries(text),
    )


def byte_to_char_boundaries(text: str) -> dict[int, int]:
    boundaries = {0: 0}
    cursor = 0
    for char_index, character in enumerate(text, start=1):
        cursor += len(character.encode("utf-8"))
        boundaries[cursor] = char_index
    return boundaries


def next_token_start_at_char_boundary(token_index: int, offsets: TokenOffsetMap) -> int:
    while (
        token_index < len(offsets.token_starts)
        and offsets.token_starts[token_index] not in offsets.byte_to_char
    ):
        token_index += 1
    return token_index


def next_token_end_at_char_boundary(token_index: int, offsets: TokenOffsetMap) -> int:
    if token_index <= 0:
        raise TokenOffsetError("Token end index must be positive")

    while (
        token_index < len(offsets.token_ends)
        and offsets.token_ends[token_index - 1] not in offsets.byte_to_char
    ):
        token_index += 1
    if (
        token_index == len(offsets.token_ends)
        and offsets.token_ends[token_index - 1] not in offsets.byte_to_char
    ):
        raise TokenOffsetError("Final token boundary does not align with UTF-8 text")
    return token_index


def token_span_to_text_range(
    offsets: TokenOffsetMap,
    start_token: int,
    end_token: int,
) -> TokenTextRange:
    if start_token < 0 or end_token <= start_token or end_token > len(offsets.token_ends):
        raise TokenOffsetError("Invalid token span")

    start_byte = offsets.token_starts[start_token]
    end_byte = offsets.token_ends[end_token - 1]
    try:
        start_char = offsets.byte_to_char[start_byte]
        end_char = offsets.byte_to_char[end_byte]
    except KeyError as exc:
        raise TokenOffsetError("Token span does not align with UTF-8 text") from exc

    return TokenTextRange(
        start_byte=start_byte,
        end_byte=end_byte,
        start_char=start_char,
        end_char=end_char,
    )


__all__ = [
    "TokenOffsetError",
    "TokenOffsetMap",
    "TokenTextRange",
    "build_token_offset_map",
    "byte_to_char_boundaries",
    "next_token_end_at_char_boundary",
    "next_token_start_at_char_boundary",
    "token_span_to_text_range",
]
