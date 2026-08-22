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


class StockComparisonRequest(BaseModel):
    """Request for stock comparison."""
    tickers: List[str] = Field(..., description="List of ticker symbols")
    question: Optional[str] = Field(None, description="Comparison question")


class ScreeningRequest(BaseModel):
    """Request for stock screening."""
    screen_type: Optional[str] = Field(None, description="Predefined screen type")
    filters: Optional[List[Dict[str, Any]]] = Field(None, description="Custom filters")
    min_pass_rate: float = Field(0.0, description="Minimum pass rate")


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
    passed: bool
    score: float
    pass_rate: float
    filter_results: Dict[str, Dict[str, Any]]


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
