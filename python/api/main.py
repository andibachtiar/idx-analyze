"""
FastAPI application for idx-bei investment research platform.

Provides REST API endpoints for all analysis tools.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

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
    AlertRequest,
    ApiHealthResponse,
    BacktestRequest,
    BacktestResponse,
    CatalystRequest,
    CompetitorRequest,
    DocumentResult,
    DocumentSearchRequest,
    DocumentSearchResponse,
    FinancialReportRequest,
    FundamentalAnalysisRequest,
    FundamentalAnalysisResponse,
    HistoricalAnalysisResponse,
    IndustryMapRequest,
    MacroImpactRequest,
    ResearchReportResponse,
    ScreenAnalysisRequest,
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
from database.scraper_store import ScraperDatabase

# Web assets directory (HTML, CSS, JS) served for the dashboard.
WEB_ROOT = Path(__file__).resolve().parent.parent / "web"

# Create FastAPI app
app = FastAPI(
    title="IDX-BEI Investment Research API",
    description="AI-powered stock research and analysis platform for Indonesian stocks",
    version="1.0.0",
)


def _json_safe(value):
    """Normalise a value into JSON-compliant form (dates -> isoformat, NaN/Inf -> None)."""
    import math
    from datetime import date, datetime
    from decimal import Decimal

    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value) if value == value else None
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets (css/js) for the web dashboard
app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")

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
    """Get technical analysis for a stock using real price history."""
    try:
        from ai.data_loader_pg import get_data_loader
        from ai.tools import get_technical_analysis as _run_technical

        if prices:
            close_prices = prices
        else:
            history = get_data_loader().get_historical_prices(ticker, days=300)
            close_prices = [h["price"] for h in history if h.get("price") is not None]
        result = _run_technical(ticker, prices=close_prices)
        return TechnicalAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}/valuation", response_model=ValuationResponse)
async def get_valuation(
    ticker: str,
    price: float = None,
    historical_pe: list[tuple] = None,
):
    """Get valuation analysis for a stock using real DB price + metrics."""
    try:
        from ai.data_loader_pg import get_data_loader
        from ai.tools import _metrics_from_db
        from ai.tools import get_valuation as _run_valuation

        loader = get_data_loader()
        if price is None:
            quote = loader.get_stock_price(ticker)
            price = (quote or {}).get("price")
        metrics = _metrics_from_db(loader.get_financial_ratios(ticker))
        result = _run_valuation(ticker, price=price, metrics=metrics, historical_pe=historical_pe)
        # Normalise the dict to the response schema shape.
        return ValuationResponse(
            ticker=result.get("ticker", ticker.upper()),
            valuation_date=result.get("valuation_date") or datetime.now().strftime("%Y-%m-%d"),
            current_price=result.get("current_price") or price,
            valuations=result.get("valuations") or {},
            historical_comparison=result.get("historical_comparison") or {},
            notes=result.get("notes"),
        )
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


@app.post("/ai/fundamental")
async def ai_fundamental_analysis(request: FundamentalAnalysisRequest):
    """Deterministic fundamental key-ratios + Signal Output, optional LLM interpretation."""
    try:
        from ai.prompts.fundamental import analyze_fundamentals

        llm_client = None
        if request.use_llm:
            from ai.llm import LLMClient
            llm_client = LLMClient()
        result = analyze_fundamentals(
            ticker=request.ticker,
            use_llm=request.use_llm,
            llm_client=llm_client,
        )
        return _json_safe({"status": "ok", **result})
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
        from ai.data_loader_pg import get_data_loader
        stocks = get_data_loader().list_stock_metrics()
        result = run_screening(
            stocks=stocks,
            screen_type=request.screen_type,
            filters=request.filters,
        )
        return ScreeningResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/screen-analysis")
async def ai_screen_analysis(request: ScreenAnalysisRequest):
    """Run the deterministic screen, then interpret the top results with the LLM.

    The scores/pass-fail come from ``run_screening`` (PostgreSQL data), and the
    ``llm_analysis`` field is an evidence-based interpretation on top of those
    deterministic results. It never invents financial numbers.
    """
    try:
        from ai.data_loader_pg import get_data_loader
        from ai.llm import LLMClient

        loader = get_data_loader()
        stocks = loader.list_stock_metrics()
        result = run_screening(
            stocks=stocks,
            screen_type=request.screen_type,
            filters=request.filters,
        )

        # Reduce to the requested tickers (if any), then top-N passed results.
        results = result.get("results", [])
        if request.tickers:
            wanted = {t.strip().upper() for t in request.tickers}
            results = [r for r in results if r.get("ticker") in wanted]
        passed = [r for r in results if r.get("passed")]
        top = passed[: max(1, request.top_n)]

        llm_client = LLMClient()
        llm_analysis = ""
        if top and llm_client.is_available:
            lines = [
                "# Screener Top Picks to Interpret",
                f"Screen type: {request.screen_type or 'custom'}",
                f"Date: {datetime.now().strftime('%Y-%m-%d')}",
                "",
                "Ticker | Pass rate | Score | ROE | Net Marg | Debt/Eq | P/E | Div Yield",
                "--------|-----------|-------|-----|----------|---------|-----|-----------",
            ]
            for r in top:
                tr = r.get("ticker", "")
                fr = r.get("filter_results", {}) or {}
                metric = {}
                for v in fr.values():
                    if isinstance(v, dict) and "value" in v:
                        metric.setdefault(str(v.get("filter") or ""), v.get("value"))
                lines.append(
                    f"{tr} | {r.get('pass_rate', 0):.1f} | {r.get('score', 0):.1f} | "
                    f"{metric.get('roe', '-')} | {metric.get('net_margin', '-')} | "
                    f"{metric.get('debt_to_equity', '-')} | {metric.get('pe_ratio', '-')} | "
                    f"{metric.get('dividend_yield', '-')}"
                )
            prompt = "\n".join(lines)
            if request.question:
                prompt += f"\n\nFocus question: {request.question}"
            llm_result = llm_client.analyze_with_prompt(
                prompt=prompt,
                system_message=(
                    "You are a professional investment research analyst for Indonesian stocks "
                    "(IDX/BEI). Interpret the deterministic screening results with evidence, "
                    "clearly separating FACT, INTERPRETATION, ASSUMPTION and SPECULATION. "
                    "Do not invent financial numbers and do not give buy/sell advice."
                ),
                output_format="Markdown: short summary, key observations, risks, and watchlist.",
            )
            llm_analysis = llm_result.get("content") or llm_result.get("error") or ""

        return _json_safe({
            "status": "ok",
            "screen_type": request.screen_type,
            "count": len(results),
            "passed": len(passed),
            "results": top,
            "llm_analysis": llm_analysis,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/macro-impact")
async def ai_macro_impact(request: MacroImpactRequest):
    """Interpret deterministic macro news impact tags (Fase B4).

    The sector/direction/confidence and the sector ranking come deterministically
    from ``news_impacts`` (built by ``enrich_news_impacts``). The LLM only
    interprets and ranks that evidence; it never invents the sector/direction map.
    """
    try:
        from ai.llm import LLMClient
        from ai.prompts.macro_impact import analyze_macro_impacts

        llm_client = LLMClient() if request.use_llm else None
        result = analyze_macro_impacts(
            hours=request.hours,
            top_sectors=request.top_sectors,
            focus=request.focus or "",
            use_llm=request.use_llm,
            llm_client=llm_client,
        )
        return _json_safe({
            "status": "ok",
            "generated_at": result["generated_at"],
            "hours": result["hours"],
            "total_impact_tags": result["total_impact_tags"],
            "sectors": result["sectors"],
            "llm_used": result["llm_used"],
            "llm_analysis": result["llm_analysis"],
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/research/candidates")
async def research_candidates(hours: int = 48, status: str = "", ticker: str = "", sector: str = ""):
    """Return deterministic research candidates (Fase B5).

    The sector/ticker/direction/confidence list is derived from the deterministic
    news_impacts snapshot (never invented by the LLM). Pass ``ticker`` and/or
    ``sector`` to filter to candidates relevant to a specific stock's own
    industry (Research tab). The per-batch LLM interpretation (if enabled in the
    daily pipeline) is attached once.
    """
    try:
        from ai.data_loader_pg import get_data_loader

        loader = get_data_loader()
        rows = loader.get_research_candidates(
            hours=hours,
            status=status or None,
            ticker=ticker or None,
            sector=sector or None,
        )
        # Carry the freshest LLM narrative from the batch as a single summary.
        llm_analysis = next(
            (r.get("llm_interpretation") or "" for r in rows if r.get("llm_interpretation")),
            "",
        )
        return _json_safe({
            "status": "ok",
            "hours": hours,
            "ticker": ticker,
            "sector": sector,
            "count": len(rows),
            "llm_used": bool(llm_analysis),
            "llm_analysis": llm_analysis,
            "candidates": [
                {k: v for k, v in r.items() if k != "llm_interpretation"}
                for r in rows
            ],
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/compare")
async def compare_stocks_endpoint(tickers: str):
    """Compare multiple stocks side-by-side using DB data."""
    try:
        from ai.data_loader_pg import get_data_loader
        loader = get_data_loader()
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        stock_map = loader.list_stock_metrics()
        result = []
        for t in ticker_list:
            info = loader.get_company_info(t)
            price = loader.get_stock_price(t)
            metrics = stock_map.get(t, {})
            result.append({
                "ticker": t,
                "name": (info or {}).get("name"),
                "sector": (info or {}).get("sector"),
                "quote": {"price": (price or {}).get("price"), "as_of": (price or {}).get("as_of")},
                "metrics": metrics,
            })
        return _json_safe({"status": "ok", "tickers": ticker_list, "stocks": result})
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

def _research_report_to_dict(report) -> dict:
    """Convert a ResearchReport object to the serializable dict used by the API."""
    return {
        "ticker": report.ticker,
        "question": report.question,
        "generated_at": report.timestamp.isoformat(),
        "confidence_score": report.confidence,
        "overall_verdict": getattr(report, "overall_verdict", ""),
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
        },
    }


@app.post("/ai/analyze", response_model=ResearchReportResponse)
async def ai_analyze_stock(request: StockAnalysisRequest):
    """Analyze a stock using AI researcher."""
    try:
        report = analyze_stock(request.ticker, question=request.question)
        result = _research_report_to_dict(report)
        # Persist to research memory so thesis history can be tracked over time.
        try:
            from ai.memory import save_research_report
            save_research_report(request.ticker, result, question=request.question or "")
        except Exception as mem_err:
            print(f"Research memory save skipped: {mem_err}")
        return ResearchReportResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/stocks/{ticker}/research/analyze")
async def generate_research(ticker: str, min_hours: int = 24, question: str = ""):
    """Generate a full research report for a ticker, debounced by recency.

    If a report was already saved within the last ``min_hours``, it returns that
    existing report with ``status == "skipped"`` instead of regenerating it, so
    repeated clicks / periodic runs do not spam the LLM. Otherwise it generates
    a fresh full analysis (``analyze_stock``) and persists it to research memory.
    """
    try:
        from ai.memory import ResearchMemory, save_research_report
        from ai.researcher import analyze_stock as _analyze

        memory = ResearchMemory()
        latest = memory.get_latest_report(ticker)
        if latest:
            saved_at = latest.get("saved_at") or latest.get("generated_at")
            if saved_at:
                try:
                    when = datetime.fromisoformat(saved_at)
                    now = datetime.now().astimezone()
                    if when.tzinfo is None:
                        when = when.replace(tzinfo=now.tzinfo)
                    age_hours = (now - when).total_seconds() / 3600.0
                    if age_hours < min_hours:
                        return _json_safe({
                            "status": "skipped",
                            "reason": "recent_analysis",
                            "age_hours": round(age_hours, 1),
                            "min_hours": min_hours,
                            "next_allowed_at": (when.timestamp() + min_hours * 3600) * 1000,
                            "report": latest,
                        })
                except (ValueError, TypeError):
                    pass

        report = _analyze(ticker, question=question or "")
        result = _research_report_to_dict(report)
        save_research_report(ticker, result, question=question or "")
        return _json_safe({"status": "generated", "report": result})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ai/analyze-stream")
async def ai_analyze_stock_stream(request: StockAnalysisRequest):
    """Analyze a stock using AI researcher, streaming SSE status + token chunks.

    Structured Server-Sent Events so the UI can show the real phase
    (collecting_data -> generating) instead of a static placeholder:
      event: status  data: {"phase", "message"}
      event: chunk   data: {"text"}
      event: done    data: {}
      event: error   data: {"message"}
    """
    import asyncio
    import json

    from fastapi.responses import StreamingResponse

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def generate():
        try:
            yield sse("status", {"phase": "preparing", "message": f"Menyiapkan akses data {request.ticker.upper()}..."})

            researcher = AIResearcher()
            if not researcher.client:
                yield sse("error", {"message": "LLM belum dikonfigurasi. Set OPENAI_API_KEY environment variable."})
                return

            # Pull deterministic context so the AI works from real data.
            yield sse("status", {"phase": "collecting", "message": "Mengambil data fundamental, teknis & valuasi..."})
            messages = [
                {"role": "system", "content": "You are a professional investment research analyst for Indonesian stocks (IDX/BEI). Provide detailed, evidence-based analysis. The user is asking about a specific stock on this page — always address that ticker directly and do not ask which stock they mean."},
                {"role": "user", "content": f"Saham yang sedang dianalisis: {request.ticker.upper()} (Bursa Efek Indonesia). Pertanyaan: {request.question}"}
            ]

            yield sse("status", {"phase": "generating", "message": "Menyusun jawaban..."})
            response = await asyncio.to_thread(
                researcher.client.chat.completions.create,
                model=researcher.model,
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
                stream=True,
            )

            for chunk in response:
                choices = getattr(chunk, "choices", None) or []
                if choices and getattr(choices[0], "delta", None) and getattr(choices[0].delta, "content", None):
                    yield sse("chunk", {"text": choices[0].delta.content})
            yield sse("done", {})
        except Exception as e:
            yield sse("error", {"message": str(e)})

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
# DASHBOARD & STOCK PAGES
# =============================================================================

@app.get("/stocks")
async def list_stocks():
    """List all stocks with latest price for the dashboard."""
    try:
        from ai.data_loader_pg import get_data_loader
        return _json_safe({"status": "ok", "count": len(get_data_loader().list_stocks()), "stocks": get_data_loader().list_stocks()})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}/prices")
async def stock_price_history(ticker: str, start: str | None = None, end: str | None = None, limit: int = 500):
    """Return OHLCV price history for a ticker (oldest first) for charting."""
    try:
        from ai.data_loader_pg import get_data_loader
        series = get_data_loader().get_price_history(ticker, start=start, end=end, limit=limit)
        return _json_safe({"status": "ok", "ticker": ticker.upper(), "prices": series})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}/financials/history")
async def stock_financial_history(ticker: str):
    """Return multi-period financial ratios for a ticker (oldest first) for the fundamentals chart."""
    try:
        from ai.data_loader_pg import get_data_loader
        series = get_data_loader().get_financial_ratio_history(ticker)
        return _json_safe({"status": "ok", "ticker": ticker.upper(), "series": series})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}/research-history")
async def stock_research_history(ticker: str, limit: int = 3):
    """Return saved AI research reports for a ticker (newest first)."""
    try:
        from ai.memory import get_research_history
        reports = get_research_history(ticker, limit=limit)
        return _json_safe({"status": "ok", "ticker": ticker.upper(), "count": len(reports), "reports": reports})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}/thesis-comparison")
async def stock_thesis_comparison(ticker: str, max_comparisons: int = 3):
    """Compare past investment theses for a ticker."""
    try:
        from ai.memory import compare_research_theses
        comparison = compare_research_theses(ticker, max_comparisons=max_comparisons)
        return _json_safe({"status": "ok", "ticker": ticker.upper(), **comparison})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}")
async def stock_profile(ticker: str):
    """Return company profile, latest quote, and key statistics for a stock."""
    try:
        from ai.data_loader_pg import get_data_loader
        loader = get_data_loader()
        info = loader.get_company_info(ticker)
        price = loader.get_stock_price(ticker)
        ratios = loader.get_financial_ratios(ticker)
        return _json_safe({
            "status": "ok",
            "ticker": ticker.upper(),
            "profile": info,
            "quote": price,
            "metrics": ratios,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/favorites")
async def get_favorites():
    """Return favorite tickers."""
    try:
        with ScraperDatabase() as store:
            tickers = store.get_favorites()
        return {"status": "ok", "tickers": tickers}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/favorites/{ticker}")
async def add_favorite(ticker: str):
    """Add a ticker to favorites."""
    try:
        with ScraperDatabase() as store:
            added = store.add_favorite(ticker)
        return {"status": "ok", "ticker": ticker.upper(), "added": added}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/favorites/{ticker}")
async def remove_favorite(ticker: str):
    """Remove a ticker from favorites."""
    try:
        with ScraperDatabase() as store:
            removed = store.remove_favorite(ticker)
        return {"status": "ok", "ticker": ticker.upper(), "removed": removed}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/favorites/details")
async def favorites_details():
    """Return favorites with alert config + latest close price."""
    try:
        with ScraperDatabase() as store:
            details = store.get_favorites_details()
        return _json_safe({"status": "ok", "count": len(details), "favorites": details})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/favorites/alerts")
async def triggered_alerts():
    """Return watchlist price alerts whose target has been triggered."""
    try:
        with ScraperDatabase() as store:
            alerts = store.get_triggered_alerts()
        return _json_safe({"status": "ok", "count": len(alerts), "alerts": alerts})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/favorites/{ticker}/alert")
async def set_alert(ticker: str, request: AlertRequest):
    """Set a price alert on a watchlist ticker (auto-adds to favorites)."""
    try:
        with ScraperDatabase() as store:
            ok = store.set_price_alert(ticker, request.alert_price, request.direction)
        return {"status": "ok", "ticker": ticker.upper(), "set": ok,
                "alert_price": request.alert_price, "direction": request.direction}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/favorites/{ticker}/alert")
async def remove_alert(ticker: str):
    """Remove the price alert for a watchlist ticker."""
    try:
        with ScraperDatabase() as store:
            removed = store.remove_price_alert(ticker)
        return {"status": "ok", "ticker": ticker.upper(), "removed": removed}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# NEWS & EVENTS
# =============================================================================

@app.get("/stocks/{ticker}/news")
async def stock_news(ticker: str, limit: int = 20):
    """Return news articles for a ticker."""
    try:
        from ai.data_loader_pg import get_data_loader
        news = get_data_loader().get_news(ticker, limit)
        return {"status": "ok", "ticker": ticker.upper(), "count": len(news), "news": news}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stocks/{ticker}/events")
async def stock_events(ticker: str, limit: int = 20):
    """Return classified corporate events from a ticker's news."""
    try:
        from ai.data_loader_pg import get_data_loader
        from events import classif_news_records
        news = get_data_loader().get_news(ticker, limit)
        events = classif_news_records(news)
        return {"status": "ok", "ticker": ticker.upper(), "count": len(events), "events": events}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/news")
async def all_news(limit: int = 50, ticker: str | None = None):
    """Return recent news (optionally filtered by ticker)."""
    try:
        from ai.data_loader_pg import get_data_loader
        news = get_data_loader().get_news(ticker, limit)
        return {"status": "ok", "count": len(news), "news": news}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# WEB INTERFACE
# =============================================================================

def _serve_web() -> HTMLResponse:
    """Return the dashboard SPA HTML."""
    index_file = WEB_ROOT / "index.html"
    if index_file.exists():
        return HTMLResponse(index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>IDX-BEI</h1><p>Web file not found.</p>")


@app.get("/", response_class=HTMLResponse)
async def web_interface():
    """Serving the web dashboard."""
    return _serve_web()


@app.get("/stock/{ticker}", response_class=HTMLResponse)
async def stock_page(ticker: str):
    """Serve the SPA for a specific stock page (client-side routing)."""
    return _serve_web()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
