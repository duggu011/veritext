from extractor.llm.adapters import AnthropicProviderAdapter, OpenAIChatProviderAdapter


def test_llm_provider_adapters_expose_structured_call_boundary() -> None:
    anthropic = AnthropicProviderAdapter()
    openai = OpenAIChatProviderAdapter()

    for adapter in (anthropic, openai):
        assert callable(adapter.build_request)
        assert callable(adapter.send)
        assert callable(adapter.extract_tool_input)
        assert callable(adapter.build_call_log)

    assert anthropic.supports_retry is True
    assert openai.supports_retry is False
