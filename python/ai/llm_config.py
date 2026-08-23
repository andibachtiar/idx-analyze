"""
LLM Configuration Module for idx-bei investment research platform.

Provides enhanced LLM integration with:
- Tool/function calling support
- Structured data access
- Rate limiting and caching
- Multiple provider support (OpenAI, Ollama, vLLM, etc.)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional

try:
    from openai import AsyncOpenAI, OpenAI
    from openai.types.chat import ChatCompletionToolParam
except ImportError:
    OpenAI = None
    AsyncOpenAI = None
    ChatCompletionToolParam = None


# =============================================================================
# DATA ACCESS LAYER
# =============================================================================

class DataRegistry:
    """
    Registry for processed data that the LLM can access.

    The LLM should NEVER calculate financial metrics directly.
    All data must come through this registry from deterministic engines.
    """

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def register(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None):
        """Register processed data for LLM access."""
        self._data[key] = data
        self._metadata[key] = metadata or {
            "registered_at": time.time(),
            "source": "deterministic_engine",
        }

    def get(self, key: str) -> Optional[Any]:
        """Get registered data by key."""
        return self._data.get(key)

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for registered data."""
        return self._metadata.get(key)

    def list_keys(self) -> List[str]:
        """List all registered data keys."""
        return list(self._data.keys())

    def clear(self):
        """Clear all registered data."""
        self._data.clear()
        self._metadata.clear()

    def to_context_string(self) -> str:
        """Convert registered data to a context string for LLM."""
        lines = ["## Available Data Context"]

        for key in sorted(self._data.keys()):
            data = self._data[key]
            meta = self._metadata.get(key, {})

            lines.append(f"\n### [{key}]")
            lines.append(f"Source: {meta.get('source', 'unknown')}")

            if isinstance(data, dict):
                # Format dict nicely
                for k, v in data.items():
                    if v is not None:
                        lines.append(f"  {k}: {v}")
            elif hasattr(data, '__dict__'):
                # Format dataclass/object
                for attr in dir(data):
                    if not attr.startswith('_'):
                        try:
                            val = getattr(data, attr)
                            if not callable(val) and val is not None:
                                lines.append(f"  {attr}: {val}")
                        except:
                            pass
            else:
                lines.append(f"  {data}")

        return "\n".join(lines)


# Global data registry instance
_data_registry = DataRegistry()


def get_data_registry() -> DataRegistry:
    """Get the global data registry instance."""
    return _data_registry


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get tool definitions for LLM function calling.

    Returns a list of tool schemas that the LLM can use.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_stock_price",
                "description": "Get current stock price and market data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "Stock ticker symbol"},
                        "source": {"type": "string", "enum": ["yfinance", "idx", "manual"], "description": "Data source"}
                    },
                    "required": ["ticker"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_financial_metrics",
                "description": "Get normalized financial metrics for a ticker",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "Stock ticker symbol"},
                        "period": {"type": "string", "enum": ["latest", "annual", "quarterly", "ttm"], "description": "Period type"},
                        "include_ratios": {"type": "boolean", "description": "Include calculated ratios"}
                    },
                    "required": ["ticker"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_fundamental_analysis",
                "description": "Get fundamental analysis including growth, profitability, and financial health",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "Stock ticker symbol"}
                    },
                    "required": ["ticker"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_technical_analysis",
                "description": "Get technical indicators and signals",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "Stock ticker symbol"},
                        "indicators": {"type": "array", "items": {"type": "string"}, "description": "Specific indicators to calculate"}
                    },
                    "required": ["ticker"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_valuation",
                "description": "Get valuation multiples and historical comparisons",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "Stock ticker symbol"},
                        "current_price": {"type": "number", "description": "Current stock price"},
                        "include_historical": {"type": "boolean", "description": "Include historical valuation ranges"}
                    },
                    "required": ["ticker", "current_price"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_historical_trends",
                "description": "Get historical financial trends and CAGR calculations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "Stock ticker symbol"},
                        "years": {"type": "integer", "description": "Number of years for trend analysis"}
                    },
                    "required": ["ticker"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_screening",
                "description": "Screen stocks based on criteria",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filters": {"type": "object", "description": "Screening filters"},
                        "screen_type": {"type": "string", "enum": ["value", "growth", "quality", "dividend", "buffett"], "description": "Predefined screen type"}
                    },
                    "required": ["filters"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_industry_map",
                "description": "Get industry value chain analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "theme": {"type": "string", "description": "Industry theme to map"},
                        "ticker": {"type": "string", "description": "Optional ticker to position in chain"}
                    },
                    "required": ["theme"]
                }
            }
        },
    ]


# =============================================================================
# LLM CLIENT ENHANCED
# =============================================================================

class LLMConfig:
    """
    LLM Configuration with tool support and data access.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        enable_tools: bool = True,
        enable_structured_output: bool = True,
    ):
        """
        Initialize LLM configuration.

        Args:
            api_key: API key (defaults to OPENAI_API_KEY env var)
            base_url: API base URL (defaults to OpenAI)
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            enable_tools: Whether to enable function calling tools
            enable_structured_output: Whether to enable JSON schema output
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.enable_tools = enable_tools
        self.enable_structured_output = enable_structured_output

        self._client = None
        self._async_client = None
        self._tool_cache: Dict[str, Callable] = {}

        # Only create client if API key is provided
        if OpenAI is not None and self.api_key:
            try:
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception:
                self._client = None

        if AsyncOpenAI is not None and self.api_key:
            try:
                self._async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception:
                self._async_client = None

    @property
    def client(self):
        """Get synchronous OpenAI client."""
        return self._client

    @property
    def async_client(self):
        """Get async OpenAI client."""
        return self._async_client

    @property
    def is_available(self) -> bool:
        """Check if LLM client is available."""
        return self._client is not None and bool(self.api_key)

    def register_tool(self, name: str, func: Callable):
        """Register a tool function for LLM calling."""
        self._tool_cache[name] = func

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a registered tool function."""
        func = self._tool_cache.get(name)
        if func is None:
            return {"error": f"Tool '{name}' not found"}

        try:
            result = func(**arguments)
            return {"content": json.dumps(result, default=str)}
        except Exception as e:
            return {"error": str(e)}

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = "auto",
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional tool definitions
            tool_choice: Tool choice mode ("auto", "none", or specific tool)
            response_format: Optional JSON schema for structured output

        Returns:
            Response dict with content, finish_reason, usage, etc.
        """
        if not self.is_available:
            return {
                "content": None,
                "finish_reason": "error",
                "error": "LLM client not configured. Set OPENAI_API_KEY environment variable.",
            }

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            if self.enable_tools and tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice

            if self.enable_structured_output and response_format:
                kwargs["response_format"] = response_format

            response = self._client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            result = {
                "content": choice.message.content,
                "finish_reason": choice.finish_reason,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            }

            # Handle tool calls
            if choice.message.tool_calls:
                result["tool_calls"] = []
                for tool_call in choice.message.tool_calls:
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments),
                    })

            return result

        except Exception as e:
            return {
                "content": None,
                "finish_reason": "error",
                "error": str(e),
            }

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = "auto",
        response_format: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Async version of chat()."""
        if not self.is_available:
            return {
                "content": None,
                "finish_reason": "error",
                "error": "LLM client not configured.",
            }

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            if self.enable_tools and tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice

            if self.enable_structured_output and response_format:
                kwargs["response_format"] = response_format

            response = await self._async_client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            result = {
                "content": choice.message.content,
                "finish_reason": choice.finish_reason,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            }

            if choice.message.tool_calls:
                result["tool_calls"] = []
                for tool_call in choice.message.tool_calls:
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments),
                    })

            return result

        except Exception as e:
            return {
                "content": None,
                "finish_reason": "error",
                "error": str(e),
            }

    def analyze_with_data(
        self,
        ticker: str,
        question: str,
        data_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a stock with integrated data context.

        Args:
            ticker: Stock ticker symbol
            question: Analysis question
            data_context: Optional pre-formatted data context

        Returns:
            Analysis result dict
        """
        messages = [
            {
                "role": "system",
                "content": """You are a professional investment research analyst for Indonesian stocks (IDX/BEI).

Your role is to provide evidence-based investment analysis using deterministic data from financial engines. You must:

1. NEVER invent financial numbers - only use data retrieved from tools
2. NEVER fabricate news or sources
3. Distinguish clearly between:
   - FACT: Data retrieved from tools
   - INTERPRETATION: Your analysis of the facts
   - ASSUMPTION: Explicit assumptions you're making
   - SPECULATION: Uncertain future predictions

4. Present balanced analysis with bull case, base case, and bear case
5. Calculate all metrics deterministically - do not ask AI to calculate
6. Express uncertainty appropriately
7. Never present speculation as fact
8. Never claim certainty about future prices

When analyzing a stock, follow this structure:
1. Executive Summary
2. Business Quality
3. Revenue/Earnings Growth
4. Profitability
5. Balance Sheet
6. Cash Flow
7. Valuation
8. Technical Position
9. Recent Events
10. Catalysts
11. Risks
12. Bull Case
13. Base Case
14. Bear Case
15. Conclusion

Always cite your data sources and timestamps."""
            },
            {
                "role": "user",
                "content": f"Analyze {ticker} based on the following question:\n\n{question}\n\n{'Data Context:\n' + data_context if data_context else ''}"
            }
        ]

        tools = get_tool_definitions() if self.enable_tools else None

        return self.chat(messages, tools=tools)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_global_config: Optional[LLMConfig] = None

def get_llm_config(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gpt-4o",
) -> LLMConfig:
    """
    Get or create the global LLM configuration.

    Args:
        api_key: Optional API key override
        base_url: Optional base URL override
        model: Model name override

    Returns:
        LLMConfig instance
    """
    global _global_config

    if _global_config is None:
        _global_config = LLMConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
    elif api_key or base_url or model != "gpt-4o":
        # Recreate if parameters changed
        _global_config = LLMConfig(
            api_key=api_key or _global_config.api_key,
            base_url=base_url or _global_config.base_url,
            model=model or _global_config.model,
        )

    return _global_config


def is_llm_available() -> bool:
    """Check if LLM is available."""
    config = get_llm_config()
    return config.is_available


def analyze_stock(
    ticker: str,
    question: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
) -> Dict[str, Any]:
    """
    Quick analysis of a stock using LLM.

    Args:
        ticker: Stock ticker symbol
        question: Analysis question
        api_key: Optional API key
        model: Model name

    Returns:
        Analysis result dict
    """
    config = get_llm_config(api_key=api_key, model=model)
    return config.analyze_with_data(ticker, question)
