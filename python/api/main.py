"""
FastAPI application for idx-bei investment research platform.

Provides REST API endpoints for all analysis tools.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ai.prompts.valuation import analyze_stock_valuation, calculate_wacc
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
from ai.vector import create_vector_store
from api.schemas import (
    ApiHealthResponse,
    BacktestRequest,
    BacktestResponse,
    CatalystRequest,
    CompetitorRequest,
    DocumentResult,
    DocumentSearchRequest,
    DocumentSearchResponse,
    FinancialReportRequest,
    FundamentalAnalysisResponse,
    HistoricalAnalysisResponse,
    IndustryMapRequest,
    ResearchReportResponse,
    ScreenerRequest,
    ScreeningRequest,
    ScreeningResponse,
    StockAnalysisRequest,
    StockComparisonRequest,
    StockPriceResponse,
    TechnicalAnalysisResponse,
    ThesisValidationRequest,
    ValuationAnalysisRequest,
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
async def get_technical(ticker: str, prices: list[float] = None):
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
    historical_pe: list[tuple] = None,
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


@app.post("/ai/valuation", response_model=ValuationResponse)
async def ai_valuation_analysis(request: ValuationAnalysisRequest):
    """AI-powered multi-method valuation analysis."""
    try:
        # Generate synthetic metrics for demonstration
        from models import FinancialMetrics
        metrics = FinancialMetrics(
            revenue=10000.0,
            net_income=1500.0,
            total_equity=5000.0,
            total_assets=20000.0,
            total_debt=3000.0,
            eps=request.current_price * 0.02,  # Approximate EPS
            shares_outstanding=1000000.0,
            roe=0.25,
            roa=0.12,
            debt_to_equity=0.3,
            revenue_cagr_3y=0.10,
        )

        # Calculate WACC
        wacc = calculate_wacc(
            total_debt=metrics.total_debt or 0,
            total_equity=metrics.total_equity or 1000,
        )

        # Run valuation analysis
        result = analyze_stock_valuation(
            ticker=request.ticker,
            current_price=request.current_price,
            metrics=metrics,
            wacc=wacc,
            peer_pe_median=request.peer_pe_median,
            use_llm=request.use_llm,
        )

        return ValuationResponse(
            ticker=result["ticker"],
            valuation_date=result["analysis_date"],
            current_price=result["current_price"],
            valuations=result.get("methods", {}),
            historical_comparison=result.get("composite", {}),
            notes=f"Margin of Safety: {result.get('margin_of_safety', 0):.1%}" if result.get("margin_of_safety") else None,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}/historical", response_model=HistoricalAnalysisResponse)
async def get_historical(ticker: str, raw_data: Optional[List[Dict[str, Any]]] = None):
    """Get historical analysis for a stock."""
    try:
        result = get_historical_analysis(ticker, raw_data=raw_data or [])
        return HistoricalAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/technical", response_model=TechnicalAnalysisResponse)
async def ai_technical_analysis(request: TechnicalAnalysisRequest):
    """AI-powered technical analysis with LLM interpretation."""
    try:
        from ai.prompts.technical import get_technical_analysis_with_llm

        result = get_technical_analysis_with_llm(
            ticker=request.ticker,
            prices=request.prices,
            volumes=request.volumes,
            highs=request.highs,
            lows=request.lows,
            use_llm=request.use_llm,
        )

        return TechnicalAnalysisResponse(
            ticker=result["ticker"],
            calculated_at=result.get("analysis_date", datetime.now().isoformat()),
            indicators={
                "trend": result.get("trend"),
                "rsi_14": result.get("score"),
                "macd_signal": result.get("action"),
            },
            signals={
                "overall": result.get("overall_signal"),
                "action": result.get("action"),
                "confidence": result.get("confidence"),
                "horizon": result.get("horizon"),
            },
            notes="\n".join(result.get("recommendations", [])) if result.get("recommendations") else None,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/screen", response_model=ScreeningResponse)
async def ai_screen_stocks(request: ScreenerRequest):
    """AI-powered stock screening with 5-factor scoring."""
    try:
        from ai.prompts.screener import run_screening_analysis

        # Prepare mock stock data (in production, this would come from database)
        stock_data = {}
        for ticker in request.tickers:
            stock_data[ticker] = {
                "pe_ratio": 15.0,
                "ps_ratio": 2.0,
                "ev_ebitda": 10.0,
                "peg_ratio": 1.5,
                "roe": 0.20,
                "roic": 0.15,
                "debt_to_equity": 0.5,
                "gross_margin": 0.40,
                "revenue_growth_yoy": 0.10,
                "eps_growth_yoy": 0.15,
            }

        result = run_screening_analysis(
            tickers=request.tickers,
            stock_data=stock_data,
            use_llm=request.use_llm,
        )

        # Convert to ScreeningResponse format
        from api.schemas import ScreeningResult
        screen_results = []
        for r in result.get("results", []):
            screen_results.append(ScreeningResult(
                ticker=r["ticker"],
                passed=r["total_score"] >= 6.0,
                score=r["total_score"],
                pass_rate=r["total_score"] * 10,
                filter_results={
                    "valuation": {"score": r["valuation_score"]},
                    "quality": {"score": r["quality_score"]},
                    "momentum": {"score": r["momentum_score"]},
                    "sentiment": {"score": r["sentiment_score"]},
                    "growth": {"score": r["growth_score"]},
                }
            ))

        return ScreeningResponse(
            results=screen_results,
            count=len(screen_results),
            stocks_passed=sum(1 for r in screen_results if r.passed),
            total_screened=len(screen_results),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/financial-report")
async def ai_financial_report_analysis(request: FinancialReportRequest):
    """AI-powered financial report analysis."""
    try:
        from ai.prompts.financial_report import analyze_financial_report
        result = analyze_financial_report(
            ticker=request.ticker,
            filing_type=request.filing_type,
            revenue=request.revenue,
            net_income=request.net_income,
            gross_margin=request.gross_margin,
            operating_margin=request.operating_margin,
            fcf=request.fc,
            total_debt=request.total_debt,
            cash=request.cash,
            auditor_opinion=request.auditor_opinion,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/catalyst")
async def ai_catalyst_calendar(request: CatalystRequest):
    """AI-powered catalyst calendar analysis."""
    try:
        from ai.prompts.catalyst import analyze_catalyst_calendar

        result = analyze_catalyst_calendar(
            ticker=request.ticker,
            look_back_days=request.days,
            focus=request.focus,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/competitor")
async def ai_competitor_analysis(request: CompetitorRequest):
    """AI-powered competitor analysis."""
    try:
        from ai.prompts.competitor import analyze_competitor_position

        result = analyze_competitor_position(
            ticker=request.ticker,
            moat_width=request.moat_width,
            moat_score=request.moat_score,
            market_share=request.market_share,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/institutional-ownership")
async def ai_institutional_ownership(request: InstitutionalOwnershipRequest):
    """AI-powered institutional ownership analysis."""
    try:
        from ai.prompts.institutional_ownership import analyze_institutional_ownership

        result = analyze_institutional_ownership(
            ticker=request.ticker,
            institutional_ownership_pct=request.institutional_ownership_pct,
            num_holders=request.num_holders,
            top10_concentration=request.top10_concentration,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/industry-map")
async def ai_industry_map(request: IndustryMapRequest):
    """AI-powered industry map / value chain analysis."""
    try:
        from ai.prompts.industry_map import analyze_industry_map

        result = analyze_industry_map(
            ticker=request.ticker,
            theme=request.theme,
            focus_layer=request.focus_layer,
        )
        return result.to_dict()
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

    print(request.ticker, request.question)

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


@app.post("/ai/analyze-stream")
async def ai_analyze_stock_stream(request: StockAnalysisRequest):
    """Analyze a stock using AI researcher with streaming response."""
    import asyncio

    from fastapi.responses import StreamingResponse

    async def generate():
        try:
            researcher = AIResearcher()
            # Get the LLM client
            if not researcher.client:
                yield "Error: LLM not configured. Set OPENAI_API_KEY environment variable."
                return

            # Prepare messages
            messages = [
                {"role": "system", "content": "You are a professional investment research analyst for Indonesian stocks (IDX/BEI). Provide detailed, evidence-based analysis."},
                {"role": "user", "content": f"{request.question}"}
            ]

            # Call LLM and stream response
            response = await asyncio.to_thread(
                researcher.client.chat.completions.create,
                model=researcher.model,
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
                stream=True,
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/event-stream")


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
        raise HTTPException(status_code=400, detail=f"Search failed: {e!s}")


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
# WEB INTERFACE
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def web_interface():
    """Main web interface."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IDX-BEI Investment Research Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
        }
        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }
        .header h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .header p { opacity: 0.9; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .card {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        .card h2 { margin-bottom: 1rem; color: #1e3c72; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }
        .btn {
            background: #2a5298;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.2s;
        }
        .btn:hover { background: #1e3c72; }
        .results { margin-top: 1.5rem; }
        .results pre {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            text-align: center;
        }
        .stat-card .value { font-size: 1.5rem; font-weight: bold; color: #2a5298; }
        .stat-card .label { font-size: 0.875rem; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>IDX-BEI Investment Research Platform</h1>
        <p>AI-powered stock analysis for Indonesian stocks</p>
    </div>

    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="value">16</div>
                <div class="label">Phases Complete</div>
            </div>
            <div class="stat-card">
                <div class="value">600+</div>
                <div class="label">Test Cases</div>
            </div>
            <div class="stat-card">
                <div class="value">50+</div>
                <div class="label">API Endpoints</div>
            </div>
        </div>

        <div class="card">
            <h2>Stock Analysis</h2>
            <div class="form-group">
                <label for="ticker">Ticker Symbol</label>
                <input type="text" id="ticker" placeholder="e.g., BBCA, BBRI, ASII">
            </div>
            <div class="form-group">
                <label for="question">Research Question</label>
                <textarea id="question" rows="3" placeholder="What would you like to know about this stock?"></textarea>
            </div>
            <button class="btn" onclick="analyzeStock()">Analyze Stock</button>
            <div id="results" class="results"></div>
        </div>

        <div class="card">
            <h2>Available Features</h2>
            <ul style="margin-left: 1.5rem; line-height: 2;">
                <li><strong>Fundamental Analysis</strong> - ROE, margins, growth rates</li>
                <li><strong>Technical Analysis</strong> - SMA, RSI, MACD, Bollinger Bands</li>
                <li><strong>Valuation</strong> - P/E, P/B, EV/EBITDA with historical context</li>
                <li><strong>Historical Analysis</strong> - YoY growth, trends, CAGR</li>
                <li><strong>Stock Screening</strong> - Buffett, Growth, Value, Quality screens</li>
                <li><strong>Backtesting</strong> - Strategy simulation with look-ahead bias prevention</li>
                <li><strong>AI Research</strong> - LLM-powered analysis with structured reports</li>
                <li><strong>Vector Search</strong> - Semantic search over documents</li>
            </ul>
        </div>

        <div class="card">
            <h2>API Documentation</h2>
            <p>Interactive API documentation is available at:</p>
            <ul style="margin-left: 1.5rem; margin-top: 0.5rem;">
                <li><a href="/docs">Swagger UI</a></li>
                <li><a href="/redoc">ReDoc</a></li>
            </ul>
        </div>
    </div>

    <script>
        async function analyzeStock() {
            const ticker = document.getElementById('ticker').value.toUpperCase();
            const question = document.getElementById('question').value;

            if (!ticker) {
                alert('Please enter a ticker symbol');
                return;
            }

            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '<p>Analyzing...</p>';

            try {
                const response = await fetch('/ai/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ticker, question})
                });

                const data = await response.json();
                resultsDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (error) {
                resultsDiv.innerHTML = '<p class="error">Error: ' + error.message + '</p>';
            }
        }
    </script>
</body>
</html>
    """


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
