"""
AI Agent Configuration Module.

Provides typed access to all AI-related environment variables with defaults
and validation. All configuration is loaded from environment variables or
.env file using python-dotenv.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# =============================================================================
# LLM CONFIGURATION
# =============================================================================

@dataclass
class OpenAIConfig:
    """OpenAI API configuration."""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 4096


@dataclass
class AnthropicConfig:
    """Anthropic API configuration."""
    api_key: str = ""
    model: str = "claude-3-5-sonnet-20241022"
    base_url: str = "https://api.anthropic.com/v1"


@dataclass
class AzureOpenAIConfig:
    """Azure OpenAI configuration."""
    api_key: str = ""
    endpoint: str = ""
    deployment_name: str = "gpt-4o"
    api_version: str = "2024-02-01"


@dataclass
class OllamaConfig:
    """Ollama local model configuration."""
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2"


@dataclass
class vLLMConfig:
    """vLLM self-hosted configuration."""
    base_url: str = "http://localhost:8000/v1"
    model: str = "mistralai/Mistral-7B-Instruct-v0.2"


@dataclass
class LiteLLMConfig:
    """LiteLLM proxy configuration."""
    base_url: str = "http://localhost:4000"
    api_key: str = ""


@dataclass
class LLMConfig:
    """Master LLM configuration containing all provider settings."""
    openai: OpenAIConfig = None  # type: ignore
    anthropic: AnthropicConfig = None  # type: ignore
    azure: AzureOpenAIConfig = None  # type: ignore
    ollama: OllamaConfig = None  # type: ignore
    vllm: vLLMConfig = None  # type: ignore
    litellm: LiteLLMConfig = None  # type: ignore

    # Active provider selection
    provider: str = "openai"  # openai, anthropic, azure, ollama, vllm, litellm

    def __post_init__(self):
        if self.openai is None:
            self.openai = OpenAIConfig(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4096")),
            )
        if self.anthropic is None:
            self.anthropic = AnthropicConfig(
                api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
            )
        if self.azure is None:
            self.azure = AzureOpenAIConfig(
                api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
                deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            )
        if self.ollama is None:
            self.ollama = OllamaConfig(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            )
        if self.vllm is None:
            self.vllm = vLLMConfig(
                base_url=os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
                model=os.getenv("VLLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2"),
            )
        if self.litellm is None:
            self.litellm = LiteLLMConfig(
                base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4000"),
                api_key=os.getenv("LITELLM_API_KEY", ""),
            )
        self.provider = os.getenv("LLM_PROVIDER", "openai")

    @property
    def active_config(self):
        """Get the configuration for the active provider."""
        configs = {
            "openai": self.openai,
            "anthropic": self.anthropic,
            "azure": self.azure,
            "ollama": self.ollama,
            "vllm": self.vllm,
            "litellm": self.litellm,
        }
        return configs.get(self.provider)

    @property
    def has_api_key(self) -> bool:
        """Check if any provider has an API key configured."""
        return bool(
            self.openai.api_key or
            self.anthropic.api_key or
            self.azure.api_key or
            self.litellm.api_key
        )


# =============================================================================
# AI AGENT CONFIGURATION
# =============================================================================

@dataclass
class AgentConfig:
    """AI Agent behavioral configuration."""
    system_prompt: str = ""
    max_iterations: int = 10
    timeout_seconds: int = 120
    default_horizon: str = "MEDIUM"
    confidence_threshold: float = 0.7
    enable_tool_calling: bool = True
    enable_structured_output: bool = True

    # Rate limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_tokens_per_minute: int = 100000

    def __post_init__(self):
        self.system_prompt = os.getenv(
            "AGENT_SYSTEM_PROMPT",
            "You are a professional investment research analyst for Indonesian stocks (IDX/BEI)."
        )
        self.max_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))
        self.timeout_seconds = int(os.getenv("AGENT_TIMEOUT_SECONDS", "120"))
        self.default_horizon = os.getenv("DEFAULT_ANALYSIS_HORIZON", "MEDIUM")
        self.confidence_threshold = float(os.getenv("DEFAULT_CONFIDENCE_THRESHOLD", "0.7"))
        self.enable_tool_calling = os.getenv("ENABLE_TOOL_CALLING", "true").lower() == "true"
        self.enable_structured_output = os.getenv("ENABLE_STRUCTURED_OUTPUT", "true").lower() == "true"
        self.rate_limit_requests_per_minute = int(os.getenv("LLM_RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
        self.rate_limit_tokens_per_minute = int(os.getenv("LLM_RATE_LIMIT_TOKENS_PER_MINUTE", "100000"))


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    url: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""

    def __post_init__(self):
        self.url = os.getenv("DATABASE_URL", "")
        self.pool_size = int(os.getenv("DATABASE_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "")


# =============================================================================
# VECTOR STORE CONFIGURATION
# =============================================================================

@dataclass
class VectorStoreConfig:
    """Vector database configuration."""
    store_type: str = "chroma"
    chroma_path: str = "./data/chroma_db"
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    pgvector_url: str = ""

    def __post_init__(self):
        self.store_type = os.getenv("VECTOR_STORE_TYPE", "chroma")
        self.chroma_path = os.getenv("CHROMA_PATH", "./data/chroma_db")
        self.qdrant_url = os.getenv("QDRANT_URL", "")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", "")
        self.pgvector_url = os.getenv("PGVECTOR_URL", "")


# =============================================================================
# DATA SOURCE CONFIGURATION
# =============================================================================

@dataclass
class DataSourceConfig:
    """Stock data source configuration."""
    yahoo_finance_enabled: bool = True
    yahoo_finance_proxy: str = ""
    idx_scraper_enabled: bool = True
    idx_api_url: str = "https://www.idx.co.id"
    idx_data_dir: str = "./data/idx"
    news_api_key: str = ""
    news_enabled: bool = True
    news_sources: list = None

    def __post_init__(self):
        self.yahoo_finance_enabled = os.getenv("YAHOO_FINANCE_ENABLED", "true").lower() == "true"
        self.yahoo_finance_proxy = os.getenv("YAHOO_FINANCE_PROXY", "")
        self.idx_scraper_enabled = os.getenv("IDX_SCRAPER_ENABLED", "true").lower() == "true"
        self.idx_api_url = os.getenv("IDX_API_URL", "https://www.idx.co.id")
        self.idx_data_dir = os.getenv("IDX_DATA_DIR", "./data/idx")
        self.news_api_key = os.getenv("NEWS_API_KEY", "")
        self.news_enabled = os.getenv("NEWS_ENABLED", "true").lower() == "true"
        sources = os.getenv("NEWS_SOURCES", "cnbc_indonesia,bisnis_com,antara_news")
        self.news_sources = [s.strip() for s in sources.split(",")] if sources else []


# =============================================================================
# DOCUMENT PROCESSING CONFIGURATION
# =============================================================================

@dataclass
class DocumentConfig:
    """Document processing configuration."""
    upload_dir: str = "./data/uploads"
    max_document_size_mb: int = 50
    allowed_extensions: list = None

    def __post_init__(self):
        self.upload_dir = os.getenv("DOCUMENT_UPLOAD_DIR", "./data/uploads")
        self.max_document_size_mb = int(os.getenv("MAX_DOCUMENT_SIZE_MB", "50"))
        extensions = os.getenv("ALLOWED_EXTENSIONS", ".pdf,.doc,.docx,.txt")
        self.allowed_extensions = [ext.strip() for ext in extensions.split(",")] if extensions else [".pdf"]


# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

@dataclass
class SecurityConfig:
    """Security-related configuration."""
    secret_key: str = ""
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    def __post_init__(self):
        self.secret_key = os.getenv("SECRET_KEY", "")
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", "")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))


# =============================================================================
# API SERVER CONFIGURATION
# =============================================================================

@dataclass
class APIConfig:
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list = None

    def __post_init__(self):
        self.host = os.getenv("API_HOST", "0.0.0.0")
        self.port = int(os.getenv("API_PORT", "8000"))
        self.debug = os.getenv("API_DEBUG", "false").lower() == "true"
        origins = os.getenv("API_CORS_ORIGINS", '["*"]')
        try:
            self.cors_origins = json.loads(origins)
        except json.JSONDecodeError:
            self.cors_origins = ["*"]


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    log_file: str = "./logs/app.log"
    max_size_mb: int = 10
    backup_count: int = 5

    def __post_init__(self):
        self.level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "./logs/app.log")
        self.max_size_mb = int(os.getenv("LOG_MAX_SIZE_MB", "10"))
        self.backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))


# =============================================================================
# CACHING CONFIGURATION
# =============================================================================

@dataclass
class CacheConfig:
    """Caching configuration."""
    enabled: bool = True
    cache_type: str = "memory"
    redis_url: str = ""
    ttl_seconds: int = 3600

    def __post_init__(self):
        self.enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        self.cache_type = os.getenv("CACHE_TYPE", "memory")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "3600"))


# =============================================================================
# MASTER CONFIGURATION
# =============================================================================

@dataclass
class AIConfig:
    """Master configuration class containing all AI-related settings."""
    llm: LLMConfig = None
    agent: AgentConfig = None
    database: DatabaseConfig = None
    vector_store: VectorStoreConfig = None
    data_source: DataSourceConfig = None
    document: DocumentConfig = None
    security: SecurityConfig = None
    api: APIConfig = None
    logging: LoggingConfig = None
    cache: CacheConfig = None

    def __post_init__(self):
        if self.llm is None:
            self.llm = LLMConfig()
        if self.agent is None:
            self.agent = AgentConfig()
        if self.database is None:
            self.database = DatabaseConfig()
        if self.vector_store is None:
            self.vector_store = VectorStoreConfig()
        if self.data_source is None:
            self.data_source = DataSourceConfig()
        if self.document is None:
            self.document = DocumentConfig()
        if self.security is None:
            self.security = SecurityConfig()
        if self.api is None:
            self.api = APIConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.cache is None:
            self.cache = CacheConfig()

    def validate(self) -> list[str]:
        """Validate configuration and return list of warnings/errors."""
        issues = []

        if not self.llm.has_api_key:
            issues.append("WARNING: No LLM API keys configured. Set OPENAI_API_KEY or other provider keys.")

        if not self.database.url:
            issues.append("WARNING: DATABASE_URL not set. Some features may not work.")

        if not self.security.secret_key:
            issues.append("WARNING: SECRET_KEY not set. Using default - change in production!")

        return issues

    def summary(self) -> dict:
        """Get a summary of current configuration (without sensitive data)."""
        return {
            "llm_provider": self.llm.provider,
            "llm_model": getattr(self.llm.active_config, 'model', 'unknown'),
            "agent_max_iterations": self.agent.max_iterations,
            "database_configured": bool(self.database.url),
            "vector_store_type": self.vector_store.store_type,
            "news_sources": self.data_source.news_sources,
        }


# =============================================================================
# GLOBAL CONFIGURATION INSTANCE
# =============================================================================

_config_instance: Optional[AIConfig] = None

def get_config() -> AIConfig:
    """
    Get the global configuration instance (singleton).

    Returns:
        AIConfig: Master configuration object
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = AIConfig()
    return _config_instance


def reload_config() -> AIConfig:
    """
    Reload configuration from environment variables.

    Returns:
        AIConfig: New configuration instance
    """
    global _config_instance
    _config_instance = AIConfig()
    return _config_instance


def reset_config():
    """Reset the global configuration instance."""
    global _config_instance
    _config_instance = None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_llm_config() -> LLMConfig:
    """Get the LLM configuration."""
    return get_config().llm


def get_agent_config() -> AgentConfig:
    """Get the agent configuration."""
    return get_config().agent


def get_database_config() -> DatabaseConfig:
    """Get the database configuration."""
    return get_config().database


def is_llm_available() -> bool:
    """Check if LLM is available (has API key)."""
    return get_config().llm.has_api_key


def get_active_model() -> str:
    """Get the currently active model name."""
    return get_config().llm.active_config.model if get_config().llm.active_config else "unknown"


# =============================================================================
# CONFIGURATION VALIDATION AND LOADING
# =============================================================================

def load_and_validate() -> list[str]:
    """
    Load configuration from environment and validate.

    Returns:
        List of warning/error messages
    """
    config = get_config()
    return config.validate()


def print_config_summary():
    """Print a summary of current configuration."""
    config = get_config()
    summary = config.summary()

    print("\n" + "=" * 60)
    print("IDX-BEI AI Configuration Summary")
    print("=" * 60)
    print(f"LLM Provider:     {summary['llm_provider']}")
    print(f"LLM Model:        {summary['llm_model']}")
    print(f"Agent Iterations: {summary['agent_max_iterations']}")
    print(f"Database:         {'Configured' if summary['database_configured'] else 'Not configured'}")
    print(f"Vector Store:     {summary['vector_store_type']}")
    print(f"News Sources:     {', '.join(summary['news_sources'])}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Test the configuration loading
    print("Loading configuration...")
    issues = load_and_validate()

    if issues:
        print("\nConfiguration Issues:")
        for issue in issues:
            print(f"  - {issue}")

    print_config_summary()
