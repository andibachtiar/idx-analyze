"""
Stock Screener Prompt Integration (Phase 18).

Implements the 5-factor scoring system (Valuation, Quality, Momentum,
Sentiment, Growth) as specified in prompts/stock-screener.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class FactorScore:
    """Score for a single dimension."""
    name: str
    score: float  # 0-10
    sub_scores: Dict[str, float] = field(default_factory=dict)
    weight: float = 0.20
    notes: str = ""


@dataclass
class StockScreenResult:
    """Complete screening result for a single stock."""
    ticker: str
    name: str = ""

    # Dimension scores
    valuation_score: float = 0.0
    quality_score: float = 0.0
    momentum_score: float = 0.0
    sentiment_score: float = 0.0
    growth_score: float = 0.0

    # Composite scores
    total_score: float = 0.0
    rank: int = 1

    # Signal
    signal: str = "HOLD"  # STRONG BUY, BUY, HOLD, AVOID, STRONG AVOID
    conviction: str = "MODERATE"

    # Detailed metrics
    pe_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    peg_ratio: Optional[float] = None
    roic: Optional[float] = None
    debt_to_equity: Optional[float] = None
    gross_margin_trend: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    eps_growth_yoy: Optional[float] = None

    # Metadata
    analysis_date: str = ""
    data_sources: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    catalysts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "valuation_score": self.valuation_score,
            "quality_score": self.quality_score,
            "momentum_score": self.momentum_score,
            "sentiment_score": self.sentiment_score,
            "growth_score": self.growth_score,
            "total_score": self.total_score,
            "rank": self.rank,
            "signal": self.signal,
            "conviction": self.conviction,
            "pe_ratio": self.pe_ratio,
            "ps_ratio": self.ps_ratio,
            "ev_ebitda": self.ev_ebitda,
            "peg_ratio": self.peg_ratio,
            "roic": self.roic,
            "debt_to_equity": self.debt_to_equity,
            "revenue_growth_yoy": self.revenue_growth_yoy,
            "eps_growth_yoy": self.eps_growth_yoy,
            "analysis_date": self.analysis_date,
            "risks": self.risks,
            "catalysts": self.catalysts,
        }


@dataclass
class ScreenUniverseResult:
    """Result of screening an entire universe of stocks."""
    tickers_screened: List[str]
    results: List[StockScreenResult]
    run_date: str
    filters_applied: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    notes: str = ""

    @property
    def top_picks(self) -> List[StockScreenResult]:
        """Get top 3 picks."""
        return [r for r in self.results if r.rank <= 3]

    @property
    def bottom_picks(self) -> List[StockScreenResult]:
        """Get bottom 3 picks."""
        return [r for r in self.results if r.rank >= len(self.results) - 2]

    @property
    def avg_score(self) -> float:
        """Average score across all screened stocks."""
        if not self.results:
            return 0.0
        return sum(r.total_score for r in self.results) / len(self.results)

    @property
    def market_bias(self) -> str:
        """Determine market bias based on average score."""
        avg = self.avg_score
        if avg >= 6.0:
            return "BULLISH"
        elif avg >= 4.0:
            return "NEUTRAL"
        else:
            return "BEARISH"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tickers_screened": self.ticklers_screened,
            "results": [r.to_dict() for r in self.results],
            "run_date": self.run_date,
            "filters_applied": self.filters_applied,
            "exclusions": self.exclusions,
            "avg_score": self.avg_score,
            "market_bias": self.market_bias,
            "notes": self.notes,
        }


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def calculate_valuation_score(
    pe_ratio: Optional[float],
    ps_ratio: Optional[float],
    ev_ebitda: Optional[float],
    peg_ratio: Optional[float],
) -> FactorScore:
    """
    Calculate Valuation score (0-10).

    Higher score = cheaper relative to fundamentals.
    """
    sub_scores = {}

    # P/E vs reasonable range
    if pe_ratio is not None and pe_ratio > 0:
        # Score 10 if P/E < 15, 0 if P/E > 40, linear in between
        pe_score = max(0, min(10, 10 * (40 - pe_ratio) / 25))
        sub_scores["P/E"] = pe_score
    else:
        sub_scores["P/E"] = 5  # Neutral if unavailable

    # Price-to-Sales
    if ps_ratio is not None and ps_ratio > 0:
        # Score 10 if P/S < 1, 0 if P/S > 20
        ps_score = max(0, min(10, 10 * (20 - ps_ratio) / 19))
        sub_scores["P/S"] = ps_score
    else:
        sub_scores["P/S"] = 5

    # EV/EBITDA
    if ev_ebitda is not None and ev_ebitda > 0:
        # Score 10 if < 8x, 0 if > 40x
        ev_score = max(0, min(10, 10 * (40 - ev_ebitda) / 32))
        sub_scores["EV/EBITDA"] = ev_score
    else:
        sub_scores["EV/EBITDA"] = 5

    # PEG Ratio
    if peg_ratio is not None and peg_ratio > 0:
        # Score 10 if < 0.75, 0 if > 3.0
        peg_score = max(0, min(10, 10 * (3.0 - peg_ratio) / 2.25))
        sub_scores["PEG"] = peg_score
    else:
        sub_scores["PEG"] = 5

    # Average sub-scores
    values = list(sub_scores.values())
    avg_score = sum(values) / len(values) if values else 5

    return FactorScore(
        name="Valuation",
        score=round(avg_score, 1),
        sub_scores=sub_scores,
        weight=0.20,
    )


def calculate_quality_score(
    roe: Optional[float],
    roic: Optional[float],
    debt_to_equity: Optional[float],
    gross_margin: Optional[float],
    gross_margin_trend: Optional[float],
) -> FactorScore:
    """
    Calculate Quality score (0-10).

    Higher score = stronger business fundamentals.
    """
    sub_scores = {}

    # ROE
    if roe is not None and roe > 0:
        # Score 10 if ROE > 20%, 5 if 10-20%, 0 if < 10%
        if roe >= 0.20:
            roe_score = 10
        elif roe >= 0.10:
            roe_score = 5 + 5 * (roe - 0.10) / 0.10
        else:
            roe_score = max(0, 5 * roe / 0.10)
        sub_scores["ROE"] = roe_score
    else:
        sub_scores["ROE"] = 5

    # ROIC vs WACC (assume WACC = 10%)
    if roic is not None and roic > 0:
        wacc = 0.10
        spread = roic - wacc
        if spread >= 0.10:
            roic_score = 10
        elif spread >= 0:
            roic_score = 5 + 5 * spread / 0.10
        else:
            roic_score = max(0, 5 + 5 * spread / 0.10)
        sub_scores["ROIC"] = roic_score
    else:
        sub_scores["ROIC"] = 5

    # Debt-to-Equity
    if debt_to_equity is not None and debt_to_equity >= 0:
        # Score 10 if D/E < 0.2, 0 if D/E > 3.0
        de_score = max(0, min(10, 10 * (3.0 - debt_to_equity) / 2.8))
        sub_scores["Debt/Equity"] = de_score
    else:
        sub_scores["Debt/Equity"] = 5

    # Gross Margin Trend
    if gross_margin_trend is not None:
        if gross_margin_trend >= 0.03:  # Expanding >= 3pp/year
            margin_score = 10
        elif gross_margin_trend >= -0.03:
            margin_score = 5
        else:
            margin_score = max(0, 5 * (gross_margin_trend + 0.03) / 0.06)
        sub_scores["Margin Trend"] = margin_score
    else:
        sub_scores["Margin Trend"] = 5

    values = list(sub_scores.values())
    avg_score = sum(values) / len(values) if values else 5

    return FactorScore(
        name="Quality",
        score=round(avg_score, 1),
        sub_scores=sub_scores,
        weight=0.25,
    )


def calculate_momentum_score(
    price: Optional[float],
    sma_50: Optional[float],
    sma_200: Optional[float],
    rsi_14: Optional[float],
) -> FactorScore:
    """
    Calculate Momentum score (0-10).

    Higher score = stronger price and relative performance momentum.
    """
    sub_scores = {}

    # Price vs MA50
    if price is not None and sma_50 is not None and sma_50 > 0:
        pct_above = (price - sma_50) / sma_50
        if pct_above >= 0.10:
            ma50_score = 10
        elif pct_above >= 0:
            ma50_score = 5 + 5 * pct_above / 0.10
        elif pct_above >= -0.10:
            ma50_score = 5 * (1 + pct_above / 0.10)
        else:
            ma50_score = max(0, 5 * (1 + pct_above / 0.10))
        sub_scores["Price vs MA50"] = ma50_score
    else:
        sub_scores["Price vs MA50"] = 5

    # Price vs MA200
    if price is not None and sma_200 is not None and sma_200 > 0:
        pct_above = (price - sma_200) / sma_200
        if pct_above >= 0.20:
            ma200_score = 10
        elif pct_above >= 0:
            ma200_score = 5 + 5 * pct_above / 0.20
        elif pct_above >= -0.20:
            ma200_score = 5 * (1 + pct_above / 0.20)
        else:
            ma200_score = max(0, 5 * (1 + pct_above / 0.20))
        sub_scores["Price vs MA200"] = ma200_score
    else:
        sub_scores["Price vs MA200"] = 5

    # RSI
    if rsi_14 is not None:
        if 55 <= rsi_14 <= 70:
            rsi_score = 10
        elif rsi_14 == 50:
            rsi_score = 5
        elif rsi_14 < 30 or rsi_14 > 80:
            rsi_score = 0
        elif rsi_14 < 55:
            rsi_score = 5 * rsi_14 / 55
        else:
            rsi_score = max(0, 10 - 5 * (rsi_14 - 70) / 10)
        sub_scores["RSI"] = rsi_score
    else:
        sub_scores["RSI"] = 5

    values = list(sub_scores.values())
    avg_score = sum(values) / len(values) if values else 5

    return FactorScore(
        name="Momentum",
        score=round(avg_score, 1),
        sub_scores=sub_scores,
        weight=0.20,
    )


def calculate_sentiment_score(
    insider_net_buying: Optional[float],
    institutional_flow: Optional[float],
    short_interest_change: Optional[float],
    analyst_revisions: Optional[int],
) -> FactorScore:
    """
    Calculate Sentiment score (0-10).

    Higher score = more positive smart-money and market positioning.
    """
    sub_scores = {}

    # Insider buying
    if insider_net_buying is not None:
        if insider_net_buying > 5:  # > $5M
            insider_score = 10
        elif insider_net_buying > 0:
            insider_score = 5 + 5 * insider_net_buying / 5
        else:
            insider_score = max(0, 5 * (1 + insider_net_buying / 5))
        sub_scores["Insider Activity"] = insider_score
    else:
        sub_scores["Insider Activity"] = 5

    # Institutional flow
    if institutional_flow is not None:
        if institutional_flow >= 0.02:  # >= +2%
            inst_score = 10
        elif institutional_flow >= 0:
            inst_score = 5 + 5 * institutional_flow / 0.02
        else:
            inst_score = max(0, 5 * (1 + institutional_flow / 0.02))
        sub_scores["Institutional Flow"] = inst_score
    else:
        sub_scores["Institutional Flow"] = 5

    # Short interest change (negative = covering = bullish)
    if short_interest_change is not None:
        if short_interest_change <= -0.20:  # -20% or more
            short_score = 10
        elif short_interest_change <= 0:
            short_score = 5 + 5 * abs(short_interest_change) / 0.20
        elif short_interest_change <= 0.20:
            short_score = 5 * (1 - short_interest_change / 0.20)
        else:
            short_score = max(0, 5 * (1 - short_interest_change / 0.20))
        sub_scores["Short Interest"] = short_score
    else:
        sub_scores["Short Interest"] = 5

    # Analyst revisions
    if analyst_revisions is not None:
        if analyst_revisions >= 3:
            revision_score = 10
        elif analyst_revisions > 0:
            revision_score = 5 + 5 * analyst_revisions / 3
        elif analyst_revisions >= -3:
            revision_score = max(0, 5 * (1 + analyst_revisions / 3))
        else:
            revision_score = 0
        sub_scores["Analyst Revisions"] = revision_score
    else:
        sub_scores["Analyst Revisions"] = 5

    values = list(sub_scores.values())
    avg_score = sum(values) / len(values) if values else 5

    return FactorScore(
        name="Sentiment",
        score=round(avg_score, 1),
        sub_scores=sub_scores,
        weight=0.15,
    )


def calculate_growth_score(
    revenue_growth_yoy: Optional[float],
    eps_growth_yoy: Optional[float],
    forward_revenue_growth: Optional[float],
    guidance_trend: Optional[str],
) -> FactorScore:
    """
    Calculate Growth score (0-10).

    Higher score = stronger and more reliable growth trajectory.
    """
    sub_scores = {}

    # Revenue growth
    if revenue_growth_yoy is not None:
        if revenue_growth_yoy >= 0.30:
            rev_score = 10
        elif revenue_growth_yoy >= 0.10:
            rev_score = 5 + 5 * (revenue_growth_yoy - 0.10) / 0.20
        elif revenue_growth_yoy >= 0:
            rev_score = max(0, 5 * revenue_growth_yoy / 0.10)
        else:
            rev_score = max(0, 5 + 5 * revenue_growth_yoy / 0.10)
        sub_scores["Revenue Growth"] = rev_score
    else:
        sub_scores["Revenue Growth"] = 5

    # EPS growth
    if eps_growth_yoy is not None:
        if eps_growth_yoy >= 0.40:
            eps_score = 10
        elif eps_growth_yoy >= 0.15:
            eps_score = 5 + 5 * (eps_growth_yoy - 0.15) / 0.25
        elif eps_growth_yoy >= 0:
            eps_score = max(0, 5 * eps_growth_yoy / 0.15)
        else:
            eps_score = max(0, 5 + 5 * eps_growth_yoy / 0.15)
        sub_scores["EPS Growth"] = eps_score
    else:
        sub_scores["EPS Growth"] = 5

    # Forward revenue growth
    if forward_revenue_growth is not None:
        if forward_revenue_growth >= 0.30:
            fwd_score = 10
        elif forward_revenue_growth >= 0.10:
            fwd_score = 5 + 5 * (forward_revenue_growth - 0.10) / 0.20
        elif forward_revenue_growth >= 0:
            fwd_score = max(0, 5 * forward_revenue_growth / 0.10)
        else:
            fwd_score = max(0, 5 + 5 * forward_revenue_growth / 0.10)
        sub_scores["Forward Growth"] = fwd_score
    else:
        sub_scores["Forward Growth"] = 5

    # Guidance trend
    if guidance_trend:
        if guidance_trend.lower() == "raised":
            guide_score = 10
        elif guidance_trend.lower() == "maintained":
            guide_score = 5
        else:
            guide_score = 0
        sub_scores["Guidance"] = guide_score
    else:
        sub_scores["Guidance"] = 5

    values = list(sub_scores.values())
    avg_score = sum(values) / len(values) if values else 5

    return FactorScore(
        name="Growth",
        score=round(avg_score, 1),
        sub_scores=sub_scores,
        weight=0.20,
    )


# =============================================================================
# MAIN SCREENING FUNCTION
# =============================================================================

def screen_stocks_with_scoring(
    stocks: List[Dict[str, Any]],
    current_prices: Optional[Dict[str, float]] = None,
    technical_data: Optional[Dict[str, Dict]] = None,
) -> List[StockScreenResult]:
    """
    Screen stocks using the 5-factor scoring system.

    Args:
        stocks: List of stock dictionaries with financial metrics
        current_prices: Optional dict of ticker -> current price
        technical_data: Optional dict of ticker -> technical indicators

    Returns:
        List of StockScreenResult sorted by total score descending
    """
    results = []

    for stock in stocks:
        ticker = stock.get("ticker", "UNKNOWN")

        # Extract financial metrics
        pe_ratio = stock.get("pe_ratio")
        ps_ratio = stock.get("ps_ratio")
        ev_ebitda = stock.get("ev_ebitda")
        peg_ratio = stock.get("peg_ratio")
        roe = stock.get("roe")
        roic = stock.get("roic")
        debt_to_equity = stock.get("debt_to_equity")
        gross_margin = stock.get("gross_margin")
        gross_margin_trend = stock.get("gross_margin_trend")
        revenue_growth_yoy = stock.get("revenue_growth_yoy")
        eps_growth_yoy = stock.get("eps_growth_yoy")
        forward_revenue_growth = stock.get("forward_revenue_growth")
        guidance_trend = stock.get("guidance_trend")

        # Extract technical data
        tech = technical_data.get(ticker, {}) if technical_data else {}
        price = current_prices.get(ticker) if current_prices else None
        sma_50 = tech.get("sma_50", {}).get("value") if isinstance(tech.get("sma_50"), dict) else tech.get("sma_50")
        sma_200 = tech.get("sma_200", {}).get("value") if isinstance(tech.get("sma_200"), dict) else tech.get("sma_200")
        rsi_14 = tech.get("rsi_14", {}).get("value") if isinstance(tech.get("rsi_14"), dict) else tech.get("rsi_14")

        # Calculate scores
        valuation = calculate_valuation_score(pe_ratio, ps_ratio, ev_ebitda, peg_ratio)
        quality = calculate_quality_score(roe, roic, debt_to_equity, gross_margin, gross_margin_trend)
        momentum = calculate_momentum_score(price, sma_50, sma_200, rsi_14)
        sentiment = calculate_sentiment_score(None, None, None, None)  # Would need alternative data
        growth = calculate_growth_score(revenue_growth_yoy, eps_growth_yoy, forward_revenue_growth, guidance_trend)

        # Calculate total score with weights
        total = (
            valuation.score * valuation.weight +
            quality.score * quality.weight +
            momentum.score * momentum.weight +
            sentiment.score * sentiment.weight +
            growth.score * growth.weight
        )

        # Determine signal
        if total >= 7.5:
            signal = "STRONG BUY"
            conviction = "STRONG"
        elif total >= 6.0:
            signal = "BUY"
            conviction = "MODERATE"
        elif total >= 4.5:
            signal = "HOLD"
            conviction = "WEAK"
        elif total >= 3.0:
            signal = "AVOID"
            conviction = "MODERATE"
        else:
            signal = "STRONG AVOID"
            conviction = "STRONG"

        result = StockScreenResult(
            ticker=ticker,
            name=stock.get("name", ""),
            valuation_score=valuation.score,
            quality_score=quality.score,
            momentum_score=momentum.score,
            sentiment_score=sentiment.score,
            growth_score=growth.score,
            total_score=round(total, 1),
            signal=signal,
            conviction=conviction,
            pe_ratio=pe_ratio,
            ps_ratio=ps_ratio,
            ev_ebitda=ev_ebitda,
            peg_ratio=peg_ratio,
            roic=roic,
            debt_to_equity=debt_to_equity,
            revenue_growth_yoy=revenue_growth_yoy,
            eps_growth_yoy=eps_growth_yoy,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
        )
        results.append(result)

    # Sort by total score descending
    results.sort(key=lambda x: x.total_score, reverse=True)

    # Assign ranks
    for i, result in enumerate(results):
        result.rank = i + 1

    return results


def generate_screener_prompt(
    tickers: List[str],
    results: List[StockScreenResult],
) -> str:
    """
    Generate a prompt for LLM-based screener interpretation.

    Args:
        tickers: List of ticker symbols screened
        results: Screening results

    Returns:
        Formatted prompt string
    """
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Build leaderboard table
    table_rows = []
    for r in results[:10]:  # Top 10
        table_rows.append(
            f"| {r.rank} | {r.ticker} | {r.valuation_score:.1f} | {r.quality_score:.1f} | "
            f"{r.momentum_score:.1f} | {r.sentiment_score:.1f} | {r.growth_score:.1f} | "
            f"{r.total_score:.1f} | {r.signal} |"
        )

    table = "\n".join(table_rows)

    prompt = f"""# Stock Screener Analysis — {date_str}

## Data Sources
- Financial data: Internal calculation engine
- Technical data: Moving averages, RSI
- Date: {date_str}

> ⚠️ **Live data unavailable.** The following analysis uses calculated estimates which may be significantly out of date. Verify all prices and metrics before making any decisions.

---

## Screener Leaderboard (Top 10)

| Rank | Ticker | Val | Quality | Momentum | Sentiment | Growth | TOTAL | Signal |
|------|--------|-----|---------|----------|-----------|--------|-------|--------|
{table}

---

## Scoring Methodology

### Factor Weights:
- **Valuation** (20%): P/E, P/S, EV/EBITDA, PEG
- **Quality** (25%): ROE, ROIC, Debt/Equity, Margin Trend
- **Momentum** (20%): Price vs MA50/MA200, RSI
- **Sentiment** (15%): Insider activity, Institutional flow, Short interest, Analyst revisions
- **Growth** (20%): Revenue growth, EPS growth, Forward growth, Guidance

### Signal Legend:
- TOTAL >= 7.5 → STRONG BUY
- TOTAL 6.0–7.4 → BUY
- TOTAL 4.5–5.9 → HOLD
- TOTAL 3.0–4.4 → AVOID
- TOTAL < 3.0 → STRONG AVOID

---

## Analysis Request

Based on the screening results above, provide:

1. **Top 3 Deep Dives**
   - Why each scores high
   - Key risks
   - Entry considerations

2. **Bottom 3 Analysis**
   - Why they score low
   - Potential catalysts to watch

3. **Market Context**
   - Overall market bias (BULLISH/NEUTRAL/BEARISH)
   - Sector rotation implications
   - Correlation warnings

Format as a structured screening report.
"""

    return prompt


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_screening_analysis(
    tickers: List[str],
    stock_data: Optional[Dict[str, Dict]] = None,
    prices: Optional[Dict[str, float]] = None,
    technicals: Optional[Dict[str, Dict]] = None,
    use_llm: bool = False,
    llm_client=None,
) -> Dict[str, Any]:
    """
    Run comprehensive stock screening analysis.

    Args:
        tickers: List of ticker symbols to screen
        stock_data: Optional dict of ticker -> financial metrics
        prices: Optional dict of ticker -> current price
        technicals: Optional dict of ticker -> technical indicators
        use_llm: Whether to use LLM for enhanced interpretation
        llm_client: Optional LLMClient instance

    Returns:
        Dictionary with screening results and analysis
    """
    from ai.llm import LLMClient

    # Prepare stock data
    if stock_data is None:
        stock_data = {}

    stocks = []
    for ticker in tickers:
        stock = stock_data.get(ticker, {})
        stock["ticker"] = ticker
        stocks.append(stock)

    # Run screening
    results = screen_stocks_with_scoring(stocks, prices, technicals)

    # Build response
    response = {
        "tickers_screened": [r.ticker for r in results],
        "results": [r.to_dict() for r in results],
        "run_date": datetime.now().strftime("%Y-%m-%d"),
        "avg_score": round(sum(r.total_score for r in results) / len(results), 1) if results else 0,
        "market_bias": "BULLISH" if (sum(r.total_score for r in results) / len(results) if results else 0) >= 6.0 else "NEUTRAL" if (sum(r.total_score for r in results) / len(results) if results else 0) >= 4.0 else "BEARISH",
    }

    # Generate LLM-enhanced analysis if requested
    if use_llm and llm_client:
        prompt = generate_screener_prompt(tickers, results)
        llm_result = llm_client.analyze_with_prompt(
            prompt=prompt,
            output_format="Structured screening report with top picks and market context",
        )
        response["llm_analysis"] = llm_result.get("content")

    return response
