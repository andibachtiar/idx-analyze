"""
AI Research Analyst for idx-bei investment research platform.

Provides AI-powered investment research using deterministic data engines
with structured report generation.
"""

# LLM Integration (Phase 16+)
from .llm import (
    LLMClient,
    analyze_text,
    create_llm_client,
)

# Research Memory (Phase 13)
from .memory import (
    ResearchMemory,
    compare_research_theses,
    get_research_history,
    save_research_report,
)

# Technical Analysis Prompts (Phase 17)
from .prompts.technical import (
    BollingerBandResult,
    IchimokuResult,
    MACDResult,
    MovingAverageSignal,
    TechnicalAnalysisResult,
    analyze_stock_technicals,
    generate_technical_prompt,
    get_technical_analysis_with_llm,
)

# Valuation Prompts (Phase 16+)
from .prompts.valuation import (
    ValuationResult,
    WACCCalculation,
    analyze_stock_valuation,
    calculate_wacc,
    generate_valuation_prompt,
)

# Report classes
from .report import (
    ClaimTracker,
    ResearchReport,
)
from .report_templates import (
    Claim,
    ClaimType,
    InvestmentReport,
    ReportSection,
    create_standard_report,
)
from .researcher import (
    AIResearcher,
    analyze_stock,
    compare_stocks,
    create_researcher,
)
from .tools import (
    batch_compare,
    batch_screen,
    get_company_news,
    get_financials,
    get_fundamental_analysis,
    get_historical_analysis,
    get_ownership,
    get_stock_price,
    get_stock_profile,
    get_technical_analysis,
    get_valuation,
    run_backtest,
    run_screening,
)
from .tools import (
    compare_stocks as tools_compare_stocks,
)

__all__ = [
    # LLM
    "LLMClient",
    "create_llm_client",
    "analyze_text",
    # Valuation Prompts
    "WACCCalculation",
    "ValuationResult",
    "calculate_wacc",
    "analyze_stock_valuation",
    "generate_valuation_prompt",
    # Technical Analysis Prompts
    "TechnicalAnalysisResult",
    "MACDResult",
    "BollingerBandResult",
    "MovingAverageSignal",
    "IchimokuResult",
    "analyze_stock_technicals",
    "generate_technical_prompt",
    "get_technical_analysis_with_llm",
    # Researcher
    "AIResearcher",
    "analyze_stock",
    "compare_stocks",
    "create_researcher",
    # Report
    "ClaimTracker",
    "ResearchReport",
    # Enhanced Report
    "ReportGenerator",
    "generate_report",
    "Claim",
    "ClaimType",
    "InvestmentReport",
    "ReportSection",
    "create_standard_report",
    # Memory
    "ResearchMemory",
    "save_research_report",
    "get_research_history",
    "compare_research_theses",
    # Tools
    "get_stock_price",
    "get_financials",
    "get_fundamental_analysis",
    "get_technical_analysis",
    "get_valuation",
    "get_historical_analysis",
    "get_company_news",
    "get_ownership",
    "run_screening",
    "compare_stocks",
    "run_backtest",
    "get_stock_profile",
    "batch_screen",
    "batch_compare",
]
