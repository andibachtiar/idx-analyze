"""
Tests for LLM Configuration Module.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.llm_config import (
    DataRegistry,
    LLMConfig,
    get_llm_config,
    get_tool_definitions,
    is_llm_available,
)


class TestDataRegistry:
    def test_register_and_get(self):
        registry = DataRegistry()
        registry.register("test_key", {"value": 123})
        assert registry.get("test_key") == {"value": 123}

    def test_get_missing_key(self):
        registry = DataRegistry()
        assert registry.get("missing") is None

    def test_list_keys(self):
        registry = DataRegistry()
        registry.register("a", 1)
        registry.register("b", 2)
        keys = registry.list_keys()
        assert "a" in keys
        assert "b" in keys

    def test_clear(self):
        registry = DataRegistry()
        registry.register("a", 1)
        registry.clear()
        assert registry.list_keys() == []

    def test_to_context_string(self):
        registry = DataRegistry()
        registry.register("metrics", {"revenue": 1000, "net_income": 200})
        context = registry.to_context_string()
        assert "metrics" in context
        assert "revenue" in context
        assert "1000" in context


class TestToolDefinitions:
    def test_get_tool_definitions(self):
        tools = get_tool_definitions()
        assert len(tools) > 0
        assert tools[0]["type"] == "function"
        assert "function" in tools[0]
        assert "name" in tools[0]["function"]

    def test_tool_names(self):
        tools = get_tool_definitions()
        names = [t["function"]["name"] for t in tools]
        assert "get_stock_price" in names
        assert "get_financial_metrics" in names
        assert "get_fundamental_analysis" in names
        assert "get_technical_analysis" in names
        assert "get_valuation" in names


class TestLLMConfig:
    def setup_method(self):
        # Reset global config before each test
        import ai.llm_config as llm_module
        llm_module._global_config = None

    def test_init_without_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config = LLMConfig(api_key="")
        assert not config.is_available
        assert config.client is None

    def test_init_with_api_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        config = LLMConfig()
        assert config.api_key == "test-key"
        # Client should be created since we have a key
        assert config.client is not None

    def test_register_tool(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        config = LLMConfig(api_key="test")
        def my_tool(x: int) -> int:
            return x * 2
        config.register_tool("my_tool", my_tool)
        assert "my_tool" in config._tool_cache

    def test_call_tool(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        config = LLMConfig(api_key="test")
        config.register_tool("multiply", lambda a, b: a * b)
        result = config.call_tool("multiply", {"a": 5, "b": 3})
        assert result["content"] == "15"

    def test_call_missing_tool(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        config = LLMConfig(api_key="test")
        result = config.call_tool("nonexistent", {})
        assert "error" in result

    def test_analyze_with_data_requires_client(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config = LLMConfig(api_key="")
        result = config.analyze_with_data("AAPL", "Is this a good stock?")
        assert result["content"] is None
        assert "error" in result


class TestConvenienceFunctions:
    def setup_method(self):
        # Reset global config before each test
        import ai.llm_config as llm_module
        llm_module._global_config = None

    def test_get_llm_config_singleton(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config1 = get_llm_config()
        config2 = get_llm_config()
        assert config1 is config2

    def test_is_llm_available_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Should not raise even without API key
        result = is_llm_available()
        assert result is False

    def test_is_llm_available_true(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        assert is_llm_available() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
