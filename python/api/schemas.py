"""
API Schemas for idx-bei investment research platform.

Pydantic models for request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class StockAnalysisRequest(BaseModel):
    """Request for stock analysis."""
    ticker: str = Field(..., description="Stock ticker symbol")
    question: Optional[str] = Field(None, description="Research question")
    include_history: bool = Field(True, description="Include historical analysis")


class FundamentalAnalysisRequest(BaseModel):
    """Request for fundamental analysis interpretation."""
    ticker: str = Field(..., description="Stock ticker symbol")
    use_llm: bool = Field(False, description="Include LLM interpretation of the ratios")


class StockComparisonRequest(BaseModel):
    """Request for stock comparison."""
    tickers: List[str] = Field(..., description="List of ticker symbols")
    question: Optional[str] = Field(None, description="Comparison question")


class ScreeningRequest(BaseModel):
    """Request for stock screening."""
    screen_type: Optional[str] = Field(None, description="Predefined screen type")
    filters: Optional[List[Dict[str, Any]]] = Field(None, description="Custom filters")
    min_pass_rate: float = Field(0.0, description="Minimum pass rate")


class ScreenAnalysisRequest(BaseModel):
    """Request for AI interpretation of screened stocks."""
    screen_type: Optional[str] = Field(None, description="Predefined screen type")
    filters: Optional[List[Dict[str, Any]]] = Field(None, description="Custom filters")
    tickers: Optional[List[str]] = Field(None, description="Limit interpretation to these tickers")
    question: Optional[str] = Field(None, description="Optional focus question for the AI")
    top_n: int = Field(10, description="Number of top results to interpret")


class MacroImpactRequest(BaseModel):
    """Request for AI macro/impact interpretation from deterministic news tags."""
    hours: int = Field(48, description="Lookback window in hours")
    top_sectors: int = Field(10, description="Max sectors to include in the LLM prompt")
    focus: Optional[str] = Field(None, description="Optional focus question")
    use_llm: bool = Field(True, description="Request an LLM interpretation")


class AlertRequest(BaseModel):
    """Request to set a price alert on a watchlist ticker."""
    alert_price: float = Field(..., gt=0, description="Target price")
    direction: str = Field("above", description="'above' or 'below'")


class BacktestRequest(BaseModel):
    """Request for backtesting."""
    ticker: str = Field(..., description="Stock ticker")
    strategy: str = Field("value", description="Strategy type")
    start_date: str = Field("2023-01-01", description="Start date")
    end_date: str = Field("2023-12-31", description="End date")
    initial_capital: float = Field(100000000, description="Initial capital in IDR")


class DocumentSearchRequest(BaseModel):
    """Request for document search."""
    query: str = Field(..., description="Search query")
    ticker: Optional[str] = Field(None, description="Filter by ticker")
    doc_type: Optional[str] = Field(None, description="Filter by document type")
    top_k: int = Field(5, description="Number of results")


class ThesisValidationRequest(BaseModel):
    """Request for thesis validation."""
    ticker: str = Field(..., description="Stock ticker")
    thesis: str = Field(..., description="Investment thesis to validate")


class ValuationAnalysisRequest(BaseModel):
    """Request for AI-powered valuation analysis."""
    ticker: str = Field(..., description="Stock ticker symbol")
    current_price: float = Field(..., description="Current stock price")
    use_llm: bool = Field(True, description="Use LLM for interpretation")
    peer_pe_median: float = Field(15.0, description="Peer median P/E ratio")


class TechnicalAnalysisRequest(BaseModel):
    """Request for AI-powered technical analysis."""
    ticker: str = Field(..., description="Stock ticker symbol")
    prices: List[float] = Field(..., description="List of closing prices (most recent last)")
    volumes: Optional[List[int]] = Field(None, description="List of trading volumes")
    highs: Optional[List[float]] = Field(None, description="List of high prices")
    lows: Optional[List[float]] = Field(None, description="List of low prices")
    use_llm: bool = Field(True, description="Use LLM for enhanced interpretation")


class ScreenerRequest(BaseModel):
    """Request for AI-powered stock screening."""
    tickers: List[str] = Field(..., description="List of ticker symbols to screen")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional screening filters")
    use_llm: bool = Field(True, description="Use LLM for enhanced interpretation")


class FinancialReportRequest(BaseModel):
    """Request for AI-powered financial report analysis."""
    ticker: str = Field(..., description="Stock ticker symbol")
    filing_type: str = Field("10-K", description="Filing type (10-K, 10-Q, etc.)")
    revenue: float = Field(..., description="Total revenue")
    net_income: float = Field(..., description="Net income")
    gross_margin: float = Field(..., description="Gross margin percentage")
    operating_margin: float = Field(..., description="Operating margin percentage")
    fcf: float = Field(..., description="Free cash flow")
    total_debt: float = Field(..., description="Total debt")
    cash: float = Field(0.0, description="Cash and equivalents")
    auditor_opinion: str = Field("unqualified", description="Auditor opinion")


class CatalystRequest(BaseModel):
    """Request for AI-powered catalyst calendar analysis."""
    ticker: str = Field(..., description="Stock ticker symbol")
    days: int = Field(90, description="Look-ahead window in days")
    focus: str = Field("all", description="Filter by category: earnings, macro, corporate, all")


class CompetitorRequest(BaseModel):
    """Request for AI-powered competitor analysis."""
    ticker: str = Field(..., description="Stock ticker symbol")
    moat_width: str = Field("Narrow", description="Moat width: Wide, Narrow, None, At Risk")
    moat_score: float = Field(5.0, description="Moat score (0-10)")
    market_share: float = Field(0.0, description="Current market share percentage")


class InstitutionalOwnershipRequest(BaseModel):
    """Request for AI-powered institutional ownership analysis."""
    ticker: str = Field(..., description="Stock ticker symbol")
    institutional_ownership_pct: float = Field(70.0, description="Percentage of shares held by institutions")
    num_holders: int = Field(500, description="Number of institutional holders")
    top10_concentration: float = Field(40.0, description="Percentage held by top 10 holders")


class IndustryMapRequest(BaseModel):
    """Request for AI-powered industry map analysis."""
    ticker: Optional[str] = Field(None, description="Stock ticker symbol (optional)")
    theme: str = Field(..., description="Theme or product to map (e.g., 'AI compute', 'electric vehicles')")
    focus_layer: Optional[str] = Field(None, description="Optional layer to focus on")


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class StockPriceResponse(BaseModel):
    """Response for stock price."""
    ticker: str
    price: Optional[float]
    currency: str
    as_of: str
    notes: Optional[str] = None


class FundamentalAnalysisResponse(BaseModel):
    """Response for fundamental analysis."""
    ticker: str
    calculated_at: str
    growth: Dict[str, Any]
    profitability: Dict[str, Any]
    financial_health: Dict[str, Any]
    cash_flow: Dict[str, Any]
    notes: Optional[str] = None


class TechnicalAnalysisResponse(BaseModel):
    """Response for technical analysis."""
    ticker: str
    calculated_at: str
    indicators: Dict[str, Any]
    signals: Dict[str, str]
    notes: Optional[str] = None


class ValuationResponse(BaseModel):
    """Response for valuation analysis."""
    ticker: str
    valuation_date: str
    current_price: Optional[float]
    valuations: Dict[str, Any]
    historical_comparison: Dict[str, Any]
    notes: Optional[str] = None


class HistoricalAnalysisResponse(BaseModel):
    """Response for historical analysis."""
    ticker: str
    calculated_at: str
    growth: Dict[str, Any]
    trends: Dict[str, str]
    notes: Optional[str] = None


class ScreeningResult(BaseModel):
    """Individual screening result."""
    ticker: str
    name: Optional[str] = None
    passed: bool
    score: float
    pass_rate: float
    filter_results: Dict[str, Dict[str, Any]]
    metric_values: Dict[str, Any] = Field(default_factory=dict)


class ScreeningResponse(BaseModel):
    """Response for stock screening."""
    results: List[ScreeningResult]
    count: int
    stocks_passed: int
    total_screened: int


class BacktestResponse(BaseModel):
    """Response for backtest results."""
    ticker: str
    strategy: str
    period: str
    initial_capital: float
    final_value: float
    total_return: Optional[float]
    annual_return: Optional[float]
    volatility: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    win_rate: Optional[float]
    total_trades: int
    notes: Optional[str] = None


class DocumentResult(BaseModel):
    """Individual document search result."""
    doc_id: str
    score: float
    content: str
    ticker: Optional[str]
    doc_type: str
    added_at: str


class DocumentSearchResponse(BaseModel):
    """Response for document search."""
    query: str
    results: List[DocumentResult]
    count: int


class ResearchReportResponse(BaseModel):
    """Response for research report."""
    ticker: str
    question: str
    generated_at: str
    confidence_score: float
    overall_verdict: str
    claim_summary: Dict[str, int]
    sections: Dict[str, Any]


class ApiHealthResponse(BaseModel):
    """Response for health check."""
    status: str
    version: str
    timestamp: str
    phases_completed: List[str]


class ErrorResponse(BaseModel):
    """Response for errors."""
    error: str
    details: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
