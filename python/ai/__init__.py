"""
AI Research Analyst for idx-bei investment research platform.

Provides AI-powered investment research using deterministic data engines
with structured report generation.
"""

# Researcher
# Enhanced report classes (Phase 12)
from .enhanced_report import (
    ReportGenerator,
    generate_report,
)

# Research Memory (Phase 13)
from .memory import (
    ResearchMemory,
    compare_research_theses,
    get_research_history,
    save_research_report,
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

# Vector Search (Phase 14)
from .vector import (
    DocumentProcessor,
    VectorStore,
    create_vector_store,
    search_documents,
)

__all__ = [
    # Researcher
    "AIResearcher",
    "analyze_stock",
    "compare_stocks",
    "create_researcher",
    # Report (Phase 11)
    "ClaimTracker",
    "ResearchReport",
    # Enhanced Report (Phase 12)
    "ReportGenerator",
    "generate_report",
    "Claim",
    "ClaimType",
    "InvestmentReport",
    "ReportSection",
    "create_standard_report",
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
    # Vector Search (Phase 14)
    "VectorStore",
    "DocumentProcessor",
    "create_vector_store",
    "search_documents",
]
