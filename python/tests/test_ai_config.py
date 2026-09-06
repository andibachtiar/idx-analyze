"""
Tests for AI Configuration Module.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.config import (
    AgentConfig,
    AIConfig,
    APIConfig,
    CacheConfig,
    DatabaseConfig,
    DataSourceConfig,
    LLMConfig,
    LoggingConfig,
    SecurityConfig,
    VectorStoreConfig,
    get_active_model,
    get_config,
    get_llm_config,
    is_llm_available,
    load_and_validate,
    reload_config,
    reset_config,
)


class TestLLMConfig:
    def test_default_values(self, monkeypatch):
        # Clear any existing env vars that might affect defaults
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("OPENAI_TEMPERATURE", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.delenv("CACHE_TYPE", raising=False)

        config = LLMConfig()
        assert config.provider == "openai"
        assert config.openai.model == "gpt-4o"
        assert config.openai.temperature == 0.3
        assert not config.has_api_key

    def test_from_environment(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("LLM_PROVIDER", "openai")

        config = LLMConfig()
        assert config.openai.api_key == "test-key"
        assert config.openai.model == "gpt-4-turbo"
        assert config.has_api_key

    def test_anthropic_config(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        config = LLMConfig()
        assert config.anthropic.api_key == "sk-ant-test"

    def test_ollama_config(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://test:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "mistral")
        config = LLMConfig()
        assert config.ollama.base_url == "http://test:11434"
        assert config.ollama.model == "mistral"

    def test_active_config(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        config = LLMConfig()
        assert config.active_config == config.ollama

    def test_has_api_key_with_any_provider(self):
        config = LLMConfig(openai=type('obj', (object,), {'api_key': 'test'})())
        assert config.has_api_key

    def test_has_api_key_false_when_empty(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LITELLM_API_KEY", raising=False)

        config = LLMConfig()
        assert not config.has_api_key


class TestAgentConfig:
    def test_default_values(self):
        config = AgentConfig()
        assert config.max_iterations == 10
        assert config.timeout_seconds == 120
        assert config.enable_tool_calling is True
        assert config.enable_structured_output is True

    def test_from_environment(self, monkeypatch):
        monkeypatch.setenv("AGENT_MAX_ITERATIONS", "20")
        monkeypatch.setenv("AGENT_TIMEOUT_SECONDS", "60")
        monkeypatch.setenv("ENABLE_TOOL_CALLING", "false")

        config = AgentConfig()
        assert config.max_iterations == 20
        assert config.timeout_seconds == 60
        assert config.enable_tool_calling is False


class TestDatabaseConfig:
    def test_default_values(self):
        config = DatabaseConfig()
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.neo4j_uri == "bolt://localhost:7687"

    def test_from_environment(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/db")
        monkeypatch.setenv("NEO4J_PASSWORD", "neo4j_pass")

        config = DatabaseConfig()
        assert config.url == "postgresql://test:test@localhost/db"
        assert config.neo4j_password == "neo4j_pass"


class TestVectorStoreConfig:
    def test_default_values(self):
        config = VectorStoreConfig()
        assert config.store_type == "chroma"
        assert config.chroma_path == "./data/chroma_db"

    def test_from_environment(self, monkeypatch):
        monkeypatch.setenv("VECTOR_STORE_TYPE", "qdrant")
        monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")

        config = VectorStoreConfig()
        assert config.store_type == "qdrant"
        assert config.qdrant_url == "http://localhost:6333"


class TestDataSourceConfig:
    def test_default_values(self):
        config = DataSourceConfig()
        assert config.yahoo_finance_enabled is True
        assert config.idx_scraper_enabled is True
        assert len(config.news_sources) > 0

    def test_from_environment(self, monkeypatch):
        monkeypatch.setenv("NEWS_SOURCES", "source1,source2")
        monkeypatch.setenv("NEWS_ENABLED", "false")

        config = DataSourceConfig()
        assert config.news_sources == ["source1", "source2"]
        assert config.news_enabled is False


class TestSecurityConfig:
    def test_default_values(self):
        config = SecurityConfig()
        assert config.jwt_algorithm == "HS256"
        assert config.jwt_expire_minutes == 30

    def test_from_environment(self, monkeypatch):
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")
        monkeypatch.setenv("JWT_EXPIRE_MINUTES", "60")

        config = SecurityConfig()
        assert config.jwt_algorithm == "RS256"
        assert config.jwt_expire_minutes == 60


class TestAPIConfig:
    def test_default_values(self):
        config = APIConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.debug is False

    def test_from_environment(self, monkeypatch):
        monkeypatch.setenv("API_PORT", "9000")
        monkeypatch.setenv("API_DEBUG", "true")

        config = APIConfig()
        assert config.port == 9000
        assert config.debug is True


class TestLoggingConfig:
    def test_default_values(self):
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.max_size_mb == 10

    def test_from_environment(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("LOG_MAX_SIZE_MB", "20")

        config = LoggingConfig()
        assert config.level == "DEBUG"
        assert config.max_size_mb == 20


class TestCacheConfig:
    def test_default_values(self, monkeypatch):
        monkeypatch.delenv("CACHE_TYPE", raising=False)
        config = CacheConfig()
        assert config.enabled is True
        assert config.cache_type == "memory"
        assert config.ttl_seconds == 3600

    def test_from_environment(self, monkeypatch):
        monkeypatch.setenv("CACHE_ENABLED", "false")
        monkeypatch.setenv("CACHE_TYPE", "redis")
        monkeypatch.setenv("CACHE_TTL_SECONDS", "1800")

        config = CacheConfig()
        assert config.enabled is False
        assert config.cache_type == "redis"
        assert config.ttl_seconds == 1800


class TestAIConfig:
    def test_master_config(self):
        config = AIConfig()
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.agent, AgentConfig)
        assert isinstance(config.database, DatabaseConfig)

    def test_validate_shows_warnings(self, monkeypatch):
        # Clear any existing API keys
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LITELLM_API_KEY", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        config = AIConfig()
        issues = config.validate()
        # Should have warnings about missing keys and database
        assert len(issues) > 0

    def test_validate_with_keys(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test@test/db")

        config = AIConfig()
        issues = config.validate()
        # Should not have API key warning
        assert not any("API keys" in issue for issue in issues)

    def test_summary(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        config = AIConfig()
        summary = config.summary()
        assert summary["llm_provider"] == "openai"
        assert "llm_model" in summary


class TestSingleton:
    def setup_method(self):
        reset_config()

    def test_singleton_behavior(self):
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_reload_creates_new_instance(self):
        config1 = get_config()
        reload_config()
        config2 = get_config()
        assert config1 is not config2

    def test_reset_clears_instance(self):
        get_config()
        reset_config()
        assert get_config() is not None  # Creates new instance


class TestConvenienceFunctions:
    def setup_method(self):
        reset_config()

    def test_get_llm_config(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config = get_llm_config()
        assert isinstance(config, LLMConfig)

    def test_is_llm_available_false(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LITELLM_API_KEY", raising=False)
        assert is_llm_available() is False

    def test_is_llm_available_true(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        assert is_llm_available() is True

    def test_get_active_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")
        assert get_active_model() == "gpt-4-turbo"

    def test_load_and_validate(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        issues = load_and_validate()
        assert isinstance(issues, list)


class TestEnvironmentIntegration:
    def test_full_configuration_load(self, monkeypatch):
        """Test loading full configuration from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
        monkeypatch.setenv("OPENAI_TEMPERATURE", "0.5")
        monkeypatch.setenv("OPENAI_MAX_TOKENS", "2048")
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("AGENT_MAX_ITERATIONS", "15")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/db")
        monkeypatch.setenv("VECTOR_STORE_TYPE", "chroma")
        monkeypatch.setenv("NEWS_SOURCES", "source1,source2,source3")

        config = AIConfig()

        # Verify LLM config
        assert config.llm.openai.api_key == "sk-test"
        assert config.llm.openai.model == "gpt-4o"
        assert config.llm.openai.temperature == 0.5
        assert config.llm.openai.max_tokens == 2048
        assert config.llm.provider == "openai"

        # Verify agent config
        assert config.agent.max_iterations == 15

        # Verify database config
        assert config.database.url == "postgresql://test:test@localhost/db"

        # Verify vector store config
        assert config.vector_store.store_type == "chroma"

        # Verify data source config
        assert config.data_source.news_sources == ["source1", "source2", "source3"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
