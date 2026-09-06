"""
Prompt templates for AI Research Analyst (Phase 11-16).

Contains system prompts, analysis templates, and prompt integration
modules for generating structured investment research reports.
"""

from __future__ import annotations

# Import LLM configuration
from ai.llm_config import (
    DataRegistry,
    LLMConfig,
    get_llm_config,
    get_tool_definitions,
    is_llm_available,
)

# =============================================================================
# CORE PROMPTS (from prompts.py)
# =============================================================================

# System prompt for the AI researcher
SYSTEM_PROMPT = """You are a professional investment research analyst for Indonesian stocks (IDX/BEI).

Your role is to provide evidence-based investment analysis using deterministic data from financial engines.

**DATA AVAILABILITY:**
- Company information: Retrieved from IDX scraped data
- Financial ratios: Retrieved from IDX scraped data (financial_ratio.json)
- Stock prices: Currently limited - may show "not available" if not in index summary
- News: Retrieved from IDX news scraper
- Technical indicators: Calculated from price history (if available)

**IMPORTANT RULES:**
1. NEVER invent financial numbers - only use data retrieved from tools
2. NEVER fabricate news or sources
3. Distinguish clearly between:
   - FACT: Data retrieved from tools (company info, financial ratios, news)
   - INTERPRETATION: Your analysis of the facts
   - ASSUMPTION: Explicit assumptions you're making
   - SPECULATION: Uncertain future predictions

4. Present balanced analysis with bull case, base case, and bear case
5. Calculate all metrics deterministically - do not ask AI to calculate
6. Express uncertainty appropriately
7. Never present speculation as fact
8. Never claim certainty about future prices

When data is unavailable, clearly state:
- "Data not available for [metric]"
- "No historical data found"
- "Price data not available"

Always cite your data sources and timestamps."""

# Prompt for initial stock analysis
INITIAL_ANALYSIS_PROMPT = """Analyze the stock {ticker} based on the following question:

{question}

Available data has been retrieved from our analysis engines. Use ONLY the data provided - do not make up numbers.

Provide a structured analysis following the research report format.
"""

# Prompt for comparing stocks
COMPARISON_PROMPT = """Compare the following stocks: {tickers}

Question: {question}

Use the data provided to make objective comparisons. Highlight similarities, differences, and relative strengths/weaknesses.
"""

# Prompt for thesis validation
THESIS_VALIDATION_PROMPT = """Validate the following investment thesis for {ticker}:

{thesis}

Check each claim against the available data. Identify:
1. Claims supported by data
2. Claims contradicted by data
3. Claims with insufficient data
4. Key risks that could invalidate the thesis
"""

# Template for structured report output
REPORT_TEMPLATE = """
# Investment Research Report: {ticker}

## Executive Summary
{executive_summary}

## Business Quality
{business_quality}

## Growth Analysis
{growth_analysis}

## Profitability
{profitability}

## Financial Health
{financial_health}

## Valuation
{valuation}

## Technical Position
{technical_position}

## Recent Events & Catalysts
{recent_events}

## Risks
{risks}

## Bull Case
{bull_case}

## Base Case
{base_case}

## Bear Case
{bear_case}

## Conclusion
{conclusion}

---
**Data Timestamp:** {timestamp}
**Sources:** {sources}
**Confidence:** {confidence}
"""

# =============================================================================
# VALUATION PROMPTS (from prompts/valuation.py)
# =============================================================================

# =============================================================================
# TECHNICAL ANALYSIS PROMPTS (from prompts/technical.py)
# =============================================================================
from .financial_report import (
    DocumentInfo,
    FinancialHealth,
    FinancialReportAnalysis,
    ManagementCredibility,
    RiskAssessment,
    analyze_financial_report,
    generate_financial_report_prompt,
)
from .fundamental import (
    analyze_fundamentals,
    compute_score,
    generate_fundamental_prompt,
    key_ratios,
    signal_from_score,
)
from .industry_map import (
    BottleneckAnalysis,
    ChainEdge,
    ChainLayer,
    IndustryMapResult,
    InvestmentIdea,
    PositionLocator,
    SupplyChainRisk,
    ValueMigration,
    analyze_industry_map,
    generate_industry_map_prompt,
)
from .institutional_ownership import (
    InstitutionalOwnershipResult,
    InstitutionHolder,
    OwnershipTrend,
    PositionChange,
    analyze_institutional_ownership,
    generate_institutional_ownership_prompt,
)
from .screener import (
    FactorScore,
    ScreenUniverseResult,
    StockScreenResult,
    generate_screener_prompt,
    run_screening_analysis,
    screen_stocks_with_scoring,
)
from .technical import (
    BollingerBandResult,
    IchimokuResult,
    MACDResult,
    MovingAverageSignal,
    TechnicalAnalysisResult,
    analyze_stock_technicals,
    generate_technical_prompt,
    get_technical_analysis_with_llm,
)
from .valuation import (
    ValuationResult,
    WACCCalculation,
    analyze_stock_valuation,
    calculate_pb_multiple,
    calculate_pe_multiple,
    calculate_wacc,
    generate_valuation_prompt,
)

__all__ = [
    # Core prompts
    "SYSTEM_PROMPT",
    "INITIAL_ANALYSIS_PROMPT",
    "COMPARISON_PROMPT",
    "THESIS_VALIDATION_PROMPT",
    "REPORT_TEMPLATE",
    # Valuation
    "WACCCalculation",
    "ValuationResult",
    "calculate_wacc",
    "calculate_pe_multiple",
    "calculate_pb_multiple",
    "generate_valuation_prompt",
    "analyze_stock_valuation",
    # Technical Analysis
    "TechnicalAnalysisResult",
    "MACDResult",
    "BollingerBandResult",
    "MovingAverageSignal",
    "IchimokuResult",
    "analyze_stock_technicals",
    "generate_technical_prompt",
    "get_technical_analysis_with_llm",
    # Stock Screener
    "StockScreenResult",
    "ScreenUniverseResult",
    "FactorScore",
    "screen_stocks_with_scoring",
    "generate_screener_prompt",
    "run_screening_analysis",
    # Fundamental Analysis
    "analyze_fundamentals",
    "key_ratios",
    "compute_score",
    "signal_from_score",
    "generate_fundamental_prompt",
    # Financial Report Analyst
    "FinancialReportAnalysis",
    "DocumentInfo",
    "FinancialHealth",
    "RiskAssessment",
    "ManagementCredibility",
    "analyze_financial_report",
    "generate_financial_report_prompt",
    # Catalyst Calendar
    "CatalystEvent",
    "CatalystCalendarResult",
    "analyze_catalyst_calendar",
    "generate_catalyst_prompt",
    # Competitor Analysis
    "MoatSource",
    "FiveForcesScore",
    "CompetitorBenchmark",
    "CompetitorAnalysisResult",
    "analyze_competitor_position",
    "generate_competitor_prompt",
    # Institutional Ownership
    "InstitutionHolder",
    "OwnershipTrend",
    "PositionChange",
    "InstitutionalOwnershipResult",
    "analyze_institutional_ownership",
    "generate_institutional_ownership_prompt",
    # Industry Map
    "ChainLayer",
    "ChainEdge",
    "PositionLocator",
    "BottleneckAnalysis",
    "ValueMigration",
    "SupplyChainRisk",
    "InvestmentIdea",
    "IndustryMapResult",
    "analyze_industry_map",
    "generate_industry_map_prompt",
    # LLM Configuration
    "DataRegistry",
    "LLMConfig",
    "get_tool_definitions",
    "get_llm_config",
    "is_llm_available",
]
