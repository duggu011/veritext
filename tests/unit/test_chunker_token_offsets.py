import pytest

from extractor.chunker.token_offsets import (
    TokenOffsetError,
    build_token_offset_map,
    next_token_end_at_char_boundary,
    next_token_start_at_char_boundary,
    token_span_to_text_range,
)


def test_token_offset_map_advances_to_utf8_character_boundaries() -> None:
    import tiktoken

    encoding = tiktoken.get_encoding("cl100k_base")
    text = "😀 test alpha"
    tokens = tuple(encoding.encode(text, disallowed_special=()))

    offsets = build_token_offset_map(text, encoding, tokens)
    end_token = next_token_end_at_char_boundary(1, offsets)
    text_range = token_span_to_text_range(offsets, 0, end_token)

    assert end_token == 2
    assert offsets.byte_to_char[0] == 0
    assert offsets.byte_to_char[len("😀".encode("utf-8"))] == 1
    assert offsets.byte_to_char[len(text.encode("utf-8"))] == len(text)
    assert next_token_start_at_char_boundary(0, offsets) == 0
    assert text_range.start_byte == 0
    assert text_range.end_byte == len("😀".encode("utf-8"))
    assert text_range.start_char == 0
    assert text_range.end_char == 1


def test_token_offset_map_rejects_tokenizer_byte_mismatch() -> None:
    class BadEncoding:
        def decode_single_token_bytes(self, token: int) -> bytes:
            return b"x"

    with pytest.raises(TokenOffsetError, match="Tokenizer byte reconstruction"):
        build_token_offset_map("abc", BadEncoding(), (1,))
