# LLM Configuration Documentation

## Overview

The LLM Configuration module provides a unified interface for AI-powered analysis with integrated access to processed financial data. It enables the LLM to retrieve structured data from deterministic engines while maintaining the principle that **financial calculations are never performed by the LLM**.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Configuration                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   LLMConfig  │───▶│  DataRegistry │───▶│  Tool System │  │
│  │              │    │              │    │              │  │
│  │ - Chat API   │    │ - Register   │    │ - Function   │  │
│  │ - Tools      │    │ - Retrieve   │    │   Calling    │  │
│  │ - Structured │    │ - Context    │    │ - Schemas    │  │
│  │   Output     │    │              │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                     Analysis Engines                         │
├─────────────────────────────────────────────────────────────┤
│  Fundamental │ Technical │ Valuation │ Historical │ Screen  │
│   Engine     │   Engine  │   Engine  │   Engine   │ Engine  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                    ┌──────────────┐
                    │  DataRegistry │
                    │  (Processed)  │
                    └──────────────┘
```

## Core Components

### 1. DataRegistry

The `DataRegistry` is a central store for all processed data that the LLM can access. It ensures the LLM only works with deterministic, engine-calculated values.

```python
from ai.llm_config import get_data_registry

registry = get_data_registry()

# Register analysis results
registry.register("fundamentals", fundamental_result)
registry.register("technical", technical_result)
registry.register("valuation", valuation_result)

# Retrieve data
data = registry.get("fundamentals")

# Get context string for LLM
context = registry.to_context_string()
```

#### Key Methods

| Method                          | Description                                 |
| ------------------------------- | ------------------------------------------- |
| `register(key, data, metadata)` | Store processed data with optional metadata |
| `get(key)`                      | Retrieve data by key                        |
| `get_metadata(key)`             | Get registration metadata                   |
| `list_keys()`                   | List all registered data keys               |
| `clear()`                       | Clear all registered data                   |
| `to_context_string()`           | Convert all data to LLM-readable format     |

### 2. LLMConfig

The `LLMConfig` class provides an enhanced LLM client with tool support and structured output.

```python
from ai.llm_config import LLMConfig

config = LLMConfig(
    api_key="your-api-key",
    base_url="https://api.openai.com/v1",
    model="gpt-4o",
    temperature=0.3,
    max_tokens=4096,
    enable_tools=True,
    enable_structured_output=True,
)
```

#### Configuration Options

| Parameter                  | Default                  | Description                |
| -------------------------- | ------------------------ | -------------------------- |
| `api_key`                  | `OPENAI_API_KEY` env var | API key for LLM provider   |
| `base_url`                 | OpenAI default           | Custom API endpoint        |
| `model`                    | `gpt-4o`                 | Model name to use          |
| `temperature`              | `0.3`                    | Sampling temperature (0-2) |
| `max_tokens`               | `4096`                   | Maximum response tokens    |
| `enable_tools`             | `True`                   | Enable function calling    |
| `enable_structured_output` | `True`                   | Enable JSON schema output  |

#### Key Methods

| Method                                                      | Description                      |
| ----------------------------------------------------------- | -------------------------------- |
| `chat(messages, tools, tool_choice, response_format)`       | Send chat completion request     |
| `chat_async(messages, tools, tool_choice, response_format)` | Async version of chat()          |
| `register_tool(name, func)`                                 | Register a tool function         |
| `call_tool(name, arguments)`                                | Call a registered tool           |
| `analyze_with_data(ticker, question, data_context)`         | Quick analysis with data context |

## Tool System

The tool system allows the LLM to retrieve processed data through function calling.

### Built-in Tools

| Tool Name                  | Description                       | Parameters                                      |
| -------------------------- | --------------------------------- | ----------------------------------------------- |
| `get_stock_price`          | Get current stock price           | `ticker`, `source`                              |
| `get_financial_metrics`    | Get normalized financial metrics  | `ticker`, `period`, `include_ratios`            |
| `get_fundamental_analysis` | Get fundamental analysis          | `ticker`                                        |
| `get_technical_analysis`   | Get technical indicators          | `ticker`, `indicators`                          |
| `get_valuation`            | Get valuation multiples           | `ticker`, `current_price`, `include_historical` |
| `get_historical_trends`    | Get historical trends and CAGR    | `ticker`, `years`                               |
| `run_screening`            | Screen stocks based on criteria   | `filters`, `screen_type`                        |
| `get_industry_map`         | Get industry value chain analysis | `theme`, `ticker`                               |

### Getting Tool Definitions

```python
from ai.llm_config import get_tool_definitions

tools = get_tool_definitions()
# Returns list of tool schemas for OpenAI function calling
```

## Usage Examples

### Basic Usage

```python
from ai.llm_config import get_llm_config

# Get the global config (singleton)
config = get_llm_config(api_key="sk-...", model="gpt-4o")

# Check if LLM is available
if config.is_available:
    result = config.chat([
        {"role": "system", "content": "You are an investment analyst."},
        {"role": "user", "content": "Analyze BBCA"},
    ])
    print(result["content"])
```

### With Data Context

```python
from ai.llm_config import get_llm_config, get_data_registry
from ai.prompts import analyze_industry_map

# Get data registry
registry = get_data_registry()

# Run deterministic analysis and register results
industry_result = analyze_industry_map(theme="AI Compute", ticker="NVDA")
registry.register("industry_map", industry_result.to_dict())

# Get context string
context = registry.to_context_string()

# Analyze with LLM
config = get_llm_config()
result = config.analyze_with_data(
    ticker="NVDA",
    question="What is the investment thesis for NVDA in the AI compute stack?",
    data_context=context,
)
```

### With Tool Calling

```python
from ai.llm_config import get_llm_config, get_tool_definitions

config = get_llm_config()
tools = get_tool_definitions()

messages = [
    {"role": "system", "content": "You are an investment analyst."},
    {"role": "user", "content": "What are BBCA's key fundamentals?"},
]

# First call - get tool calls
result = config.chat(messages, tools=tools)

if result.get("tool_calls"):
    # Process tool calls
    for tool_call in result["tool_calls"]:
        tool_result = config.call_tool(tool_call["name"], tool_call["arguments"])

    # Continue conversation with tool results
    messages.append(result)
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "content": tool_result["content"],
    })

    final_result = config.chat(messages)
    print(final_result["content"])
```

### Using Convenience Functions

```python
from ai.llm_config import analyze_stock

# Quick one-liner analysis
result = analyze_stock(
    ticker="BBCA",
    question="Is BBCA undervalued?",
    api_key="sk-...",
    model="gpt-4o",
)
print(result["content"])
```

## Integration with Existing Modules

### Fundamental Analysis

```python
from ai.tools import get_fundamental_analysis
from ai.llm_config import get_data_registry
from models import FinancialMetrics

# Get fundamental analysis
metrics = FinancialMetrics(revenue=1000, net_income=200, ...)
result = get_fundamental_analysis("BBCA", metrics=metrics)

# Register for LLM access
registry = get_data_registry()
registry.register("fundamentals", result)
```

### Technical Analysis

```python
from ai.prompts.technical import analyze_stock_technicals
from ai.llm_config import get_data_registry

# Run technical analysis
prices = [100, 102, 101, 103, ...]
result = analyze_stock_technicals(ticker="BBCA", prices=prices)

# Register for LLM access
registry = get_data_registry()
registry.register("technical", result.to_dict())
```

### Valuation

```python
from ai.prompts.valuation import analyze_stock_valuation
from ai.llm_config import get_data_registry

# Run valuation
result = analyze_stock_valuation(
    ticker="BBCA",
    current_price=8500,
    metrics=metrics,
    wacc=0.08,
)

# Register for LLM access
registry = get_data_registry()
registry.register("valuation", result.to_dict())
```

## Best Practices

### 1. Never Let LLM Calculate Financial Metrics

```python
# WRONG - LLM calculates P/E ratio
prompt = "Calculate the P/E ratio for BBCA"

# CORRECT - LLM retrieves pre-calculated metric
tools = get_tool_definitions()
# LLM calls get_financial_metrics which returns pre-calculated P/E
```

### 2. Use Data Registry for Context

```python
# Register all analysis results before LLM call
registry.register("fundamentals", fundamental_result)
registry.register("technical", technical_result)
registry.register("valuation", valuation_result)

# LLM gets comprehensive context
context = registry.to_context_string()
```

### 3. Distinguish Facts from Interpretation

```python
system_prompt = """You are an investment analyst.

IMPORTANT:
- FACTS are data retrieved from tools (pre-calculated by engines)
- INTERPRETATIONS are your analysis of the facts
- SPECULATION is uncertain future prediction

Always cite your data sources."""
```

### 4. Handle Missing Data Gracefully

```python
def get_financial_metrics(ticker: str, period: str = "latest") -> Dict[str, Any]:
    metrics = database.query(ticker, period)
    if not metrics:
        return {
            "ticker": ticker,
            "error": "No financial data available",
            "data": None,
        }
    return metrics
```

## Configuration via Environment Variables

```bash
# Required
export OPENAI_API_KEY="sk-..."

# Optional
export OPENAI_BASE_URL="https://api.openai.com/v1"  # or custom endpoint
export LLM_MODEL="gpt-4o"  # default model
export LLM_TEMPERATURE="0.3"  # default temperature
export LLM_MAX_TOKENS="4096"  # default max tokens
```

## Two-tier model routing

High-reasoning tasks (comprehensive research reports, stock comparison, thesis
validation) use the **STRONG** tier; quick, lower-reasoning summaries
(fundamental/dividend/valuation/technical/screen/macro) use the **FAST** tier.

```bash
# Optional. When unset, each tier falls back to OPENAI_MODEL (then gpt-4o), so
# a single-model deployment behaves exactly as before.
export OPENAI_MODEL_STRONG="gpt-5"        # e.g. comprehensive reports
export OPENAI_MODEL_FAST="gpt-4o-mini"   # e.g. quick metric summaries
export OPENAI_TIMEOUT="120"               # per-request seconds (LLMClient)
export OPENAI_TOTAL_TIMEOUT="600"         # wall-clock budget incl. retries (researcher)
```

Resolution order per tier: `OPENAI_MODEL_STRONG`/`OPENAI_MODEL_FAST`, then
`OPENAI_MODEL`, then `gpt-4o`. Helpers in `ai.llm`:

- `resolve_model(tier)` — pick the model for a tier from the environment.
- `llm_client_for(tier, **kwargs)` — build an `LLMClient` for a tier.

## Supported LLM Providers

| Provider     | Base URL                       | Notes               |
| ------------ | ------------------------------ | ------------------- |
| OpenAI       | `https://api.openai.com/v1`    | Default             |
| Azure OpenAI | `https://{}.openai.azure.com/` | Requires API key    |
| Ollama       | `http://localhost:11434/v1`    | Local models        |
| vLLM         | `http://localhost:8000/v1`     | Self-hosted         |
| LiteLLM      | Custom                         | Proxy server        |
| Anthropic    | Via adapter                    | Requires conversion |

## Error Handling

```python
from ai.llm_config import get_llm_config

config = get_llm_config()

if not config.is_available:
    print("LLM not configured. Set OPENAI_API_KEY environment variable.")
    exit(1)

result = config.chat(messages)

if result.get("error"):
    print(f"LLM Error: {result['error']}")
elif result.get("content"):
    print(result["content"])
else:
    print("No content returned")
```

## Testing

```python
import pytest
from ai.llm_config import DataRegistry, LLMConfig, get_tool_definitions

def test_data_registry():
    registry = DataRegistry()
    registry.register("test", {"value": 123})
    assert registry.get("test") == {"value": 123}

def test_tool_definitions():
    tools = get_tool_definitions()
    assert len(tools) > 0
    assert tools[0]["type"] == "function"

def test_llm_config_without_api_key():
    config = LLMConfig(api_key="")
    assert not config.is_available
```

## Related Modules

- `ai/tools.py` - Tool functions that return processed data
- `ai/prompts/__init__.py` - Prompt templates and exports
- `ai/researcher.py` - AI Research Analyst using LLM
- `analysis/fundamental.py` - Fundamental analysis engine
- `analysis/technical.py` - Technical analysis engine
- `analysis/valuation.py` - Valuation engine
