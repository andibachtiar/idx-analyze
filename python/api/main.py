"""
FastAPI application for idx-bei investment research platform.

Provides REST API endpoints for all analysis tools.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ai.researcher import AIResearcher, analyze_stock, compare_stocks

# Import AI tools
from ai.tools import (
    get_fundamental_analysis,
    get_historical_analysis,
    get_stock_price,
    get_technical_analysis,
    get_valuation,
    run_backtest,
    run_screening,
)
from ai.vector import VectorStore, create_vector_store
from api.schemas import (
    ApiHealthResponse,
    BacktestRequest,
    BacktestResponse,
    DocumentResult,
    DocumentSearchRequest,
    DocumentSearchResponse,
    FundamentalAnalysisResponse,
    HistoricalAnalysisResponse,
    ResearchReportResponse,
    ScreeningRequest,
    ScreeningResponse,
    StockAnalysisRequest,
    StockComparisonRequest,
    StockPriceResponse,
    TechnicalAnalysisResponse,
    ThesisValidationRequest,
    ValuationResponse,
)

# Create FastAPI app
app = FastAPI(
    title="IDX-BEI Investment Research API",
    description="AI-powered stock research and analysis platform for Indonesian stocks",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize vector store
vector_store = create_vector_store()


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health", response_model=ApiHealthResponse)
async def health_check():
    """Health check endpoint."""
    return ApiHealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
        phases_completed=[
            "fundamental_analysis",
            "technical_analysis",
            "valuation",
            "historical_analysis",
            "screening",
            "backtesting",
            "ai_research",
            "vector_search",
        ],
    )


# =============================================================================
# STOCK DATA ENDPOINTS
# =============================================================================

@app.get("/stocks/{ticker}/price", response_model=StockPriceResponse)
async def get_stock_price_endpoint(ticker: str):
    """Get current stock price."""
    try:
        result = get_stock_price(ticker)
        return StockPriceResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}/fundamentals", response_model=FundamentalAnalysisResponse)
async def get_fundamentals(ticker: str):
    """Get fundamental analysis for a stock."""
    try:
        result = get_fundamental_analysis(ticker)
        return FundamentalAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}/technical", response_model=TechnicalAnalysisResponse)
async def get_technical(ticker: str, prices: List[float] = None):
    """Get technical analysis for a stock."""
    try:
        result = get_technical_analysis(ticker, prices=prices or [])
        return TechnicalAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}/valuation", response_model=ValuationResponse)
async def get_valuation(
    ticker: str,
    price: float = None,
    historical_pe: List[tuple] = None,
):
    """Get valuation analysis for a stock."""
    try:
        # Note: Would need FinancialMetrics object for full analysis
        result = {
            "ticker": ticker.upper(),
            "valuation_date": datetime.now().strftime("%Y-%m-%d"),
            "current_price": price,
            "valuations": {},
            "historical_comparison": {},
            "notes": "Provide metrics for full valuation",
        }
        return ValuationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}/historical", response_model=HistoricalAnalysisResponse)
async def get_historical(ticker: str, raw_data: List[Dict] = None):
    """Get historical analysis for a stock."""
    try:
        result = get_historical_analysis(ticker, raw_data=raw_data or [])
        return HistoricalAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# SCREENING ENDPOINTS
# =============================================================================

@app.post("/screen", response_model=ScreeningResponse)
async def screen_stocks(request: ScreeningRequest):
    """Screen stocks with given criteria."""
    try:
        stocks = {}  # Would need stock data source
        result = run_screening(
            stocks=stocks,
            screen_type=request.screen_type,
            filters=request.filters,
        )
        return ScreeningResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# BACKTEST ENDPOINTS
# =============================================================================

@app.post("/backtest", response_model=BacktestResponse)
async def run_backtest_endpoint(request: BacktestRequest):
    """Run backtest simulation."""
    try:
        result = run_backtest(
            ticker=request.ticker,
            strategy=request.strategy,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
        )
        return BacktestResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# AI RESEARCH ENDPOINTS
# =============================================================================

@app.post("/ai/analyze", response_model=ResearchReportResponse)
async def ai_analyze_stock(request: StockAnalysisRequest):
    """Analyze a stock using AI researcher."""
    try:
        report = analyze_stock(request.ticker, question=request.question)
        # Convert ResearchReport to match ResearchReportResponse schema
        result = {
            "ticker": report.ticker,
            "question": report.question,
            "generated_at": report.timestamp.isoformat(),
            "confidence_score": report.confidence,
            "overall_verdict": getattr(report, 'overall_verdict', ''),
            "claim_summary": {"FACT": 0, "INTERPRETATION": 0, "ASSUMPTION": 0, "SPECULATION": 0},
            "sections": {
                "executive_summary": report.executive_summary,
                "business_quality": report.business_quality,
                "growth_analysis": report.growth_analysis,
                "profitability": report.profitability,
                "financial_health": report.financial_health,
                "valuation": report.valuation,
                "technical_position": report.technical_position,
                "recent_events": report.recent_events,
                "risks": report.risks,
                "bull_case": report.bull_case,
                "base_case": report.base_case,
                "bear_case": report.bear_case,
                "conclusion": report.conclusion,
            }
        }
        return ResearchReportResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/compare", response_model=ResearchReportResponse)
async def ai_compare_stocks(request: StockComparisonRequest):
    """Compare multiple stocks using AI."""
    try:
        report = compare_stocks(request.tickers, question=request.question)
        # Convert ResearchReport to match ResearchReportResponse schema
        result = {
            "ticker": report.ticker,
            "question": report.question,
            "generated_at": report.timestamp.isoformat(),
            "confidence_score": report.confidence,
            "overall_verdict": getattr(report, 'overall_verdict', ''),
            "claim_summary": {"FACT": 0, "INTERPRETATION": 0, "ASSUMPTION": 0, "SPECULATION": 0},
            "sections": {
                "executive_summary": report.executive_summary,
                "business_quality": report.business_quality,
                "growth_analysis": report.growth_analysis,
                "profitability": report.profitability,
                "financial_health": report.financial_health,
                "valuation": report.valuation,
                "technical_position": report.technical_position,
                "recent_events": report.recent_events,
                "risks": report.risks,
                "bull_case": report.bull_case,
                "base_case": report.base_case,
                "bear_case": report.bear_case,
                "conclusion": report.conclusion,
            }
        }
        return ResearchReportResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/validate-thesis", response_model=ResearchReportResponse)
async def ai_validate_thesis(request: ThesisValidationRequest):
    """Validate an investment thesis."""
    try:
        researcher = AIResearcher()
        report = researcher.validate_thesis(request.ticker, request.thesis)
        # Convert ResearchReport to match ResearchReportResponse schema
        result = {
            "ticker": report.ticker,
            "question": report.question,
            "generated_at": report.timestamp.isoformat(),
            "confidence_score": report.confidence,
            "overall_verdict": getattr(report, 'overall_verdict', ''),
            "claim_summary": {"FACT": 0, "INTERPRETATION": 0, "ASSUMPTION": 0, "SPECULATION": 0},
            "sections": {
                "executive_summary": report.executive_summary,
                "business_quality": report.business_quality,
                "growth_analysis": report.growth_analysis,
                "profitability": report.profitability,
                "financial_health": report.financial_health,
                "valuation": report.valuation,
                "technical_position": report.technical_position,
                "recent_events": report.recent_events,
                "risks": report.risks,
                "bull_case": report.bull_case,
                "base_case": report.base_case,
                "bear_case": report.bear_case,
                "conclusion": report.conclusion,
            }
        }
        return ResearchReportResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# DOCUMENT SEARCH ENDPOINTS
# =============================================================================

@app.post("/documents/search", response_model=DocumentSearchResponse)
async def search_documents(request: DocumentSearchRequest):
    """Search documents using vector similarity."""
    try:
        # Debug: log the request
        print(f"Search request: query={request.query}, ticker={request.ticker}, top_k={request.top_k}")
        print(f"Vector store has {len(vector_store.documents)} documents")

        results = vector_store.search(
            query=request.query,
            ticker=request.ticker,
            doc_type=request.doc_type,
            top_k=request.top_k,
        )
        print(f"Search returned {len(results)} results")

        # Ensure all required fields are present
        formatted_results = []
        for r in results:
            formatted_results.append(DocumentResult(
                doc_id=r.get("doc_id", ""),
                score=r.get("score", 0.0),
                content=r.get("content", ""),
                ticker=r.get("ticker"),
                doc_type=r.get("doc_type") or "general",
                added_at=r.get("added_at") or datetime.now().isoformat(),
            ))
        return DocumentSearchResponse(
            query=request.query,
            results=formatted_results,
            count=len(formatted_results),
        )
    except Exception as e:
        print(f"Search error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail=f"Search failed: {str(e)}")


@app.post("/documents/add")
async def add_document(
    doc_id: str,
    content: str,
    ticker: str = None,
    doc_type: str = "general",
):
    """Add a document to the vector store."""
    try:
        success = vector_store.add_document(
            doc_id=doc_id,
            content=content,
            ticker=ticker,
            doc_type=doc_type,
        )
        return {"success": success, "doc_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
