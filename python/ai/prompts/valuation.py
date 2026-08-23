"""
Stock Valuation Prompt Integration (Phase 16).

Extends the existing valuation engine with multi-method DCF, comparables,
and football field analysis as specified in prompts/stock-valuation.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from models import FinancialMetrics

# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class WACCCalculation:
    """WACC decomposition."""
    risk_free_rate: float
    beta: float
    equity_risk_premium: float
    size_premium: float
    cost_of_equity: float
    interest_expense: float
    total_debt: float
    pre_tax_cost_of_debt: float
    effective_tax_rate: float
    after_tax_cost_of_debt: float
    equity_weight: float
    debt_weight: float
    wacc: float


@dataclass
class ValuationResult:
    """Result from a single valuation method."""
    method_name: str
    bear_value: Optional[float]
    base_value: Optional[float]
    bull_value: Optional[float]
    confidence: str  # HIGH/MEDIUM/LOW
    notes: str = ""


# =============================================================================
# VALUATION CALCULATIONS
# =============================================================================

def calculate_wacc(
    risk_free_rate: float = 0.06,
    beta: float = 1.0,
    equity_risk_premium: float = 0.05,
    size_premium: float = 0.0,
    interest_expense: float = 0.0,
    total_debt: float = 0.0,
    total_equity: float = 1000.0,
    pre_tax_cost_of_debt: float = 0.08,
    effective_tax_rate: float = 0.25,
) -> WACCCalculation:
    """Calculate WACC with full decomposition."""
    cost_of_equity = risk_free_rate + (beta * equity_risk_premium) + size_premium
    after_tax_cost_of_debt = pre_tax_cost_of_debt * (1 - effective_tax_rate)

    total_capital = total_equity + total_debt
    equity_weight = total_equity / total_capital if total_capital > 0 else 1.0
    debt_weight = total_debt / total_capital if total_capital > 0 else 0.0

    wacc = (cost_of_equity * equity_weight) + (after_tax_cost_of_debt * debt_weight)

    return WACCCalculation(
        risk_free_rate=risk_free_rate,
        beta=beta,
        equity_risk_premium=equity_risk_premium,
        size_premium=size_premium,
        cost_of_equity=cost_of_equity,
        interest_expense=interest_expense,
        total_debt=total_debt,
        pre_tax_cost_of_debt=pre_tax_cost_of_debt,
        effective_tax_rate=effective_tax_rate,
        after_tax_cost_of_debt=after_tax_cost_of_debt,
        equity_weight=equity_weight,
        debt_weight=debt_weight,
        wacc=wacc,
    )


def calculate_pe_multiple(
    eps: float,
    peer_median_pe: float,
    growth_rate: float,
) -> ValuationResult:
    """Calculate P/E based valuation."""
    if eps <= 0:
        return ValuationResult(
            method_name="P/E Multiple",
            bear_value=None,
            base_value=None,
            bull_value=None,
            confidence="LOW",
            notes="Negative or zero EPS - P/E not applicable",
        )

    peg = peer_median_pe / growth_rate if growth_rate > 0 else peer_median_pe
    quality_adjustment = 1.0
    if peg < 1.0:
        quality_adjustment = 1.1
    elif peg > 2.0:
        quality_adjustment = 0.9

    base_multiple = peer_median_pe * quality_adjustment

    return ValuationResult(
        method_name="P/E Multiple",
        bear_value=eps * base_multiple * 0.8,
        base_value=eps * base_multiple,
        bull_value=eps * base_multiple * 1.2,
        confidence="MEDIUM" if growth_rate > 0 else "LOW",
    )


def calculate_pb_multiple(
    book_value_per_share: float,
    roe: float,
    cost_of_equity: float,
) -> ValuationResult:
    """Calculate P/B based valuation using Residual Income model."""
    if book_value_per_share <= 0 or cost_of_equity <= 0:
        return ValuationResult(
            method_name="P/B Multiple",
            bear_value=None,
            base_value=None,
            bull_value=None,
            confidence="LOW",
        )

    terminal_growth = 0.02
    justified_pb = 1 + (roe - cost_of_equity) / (cost_of_equity - terminal_growth)
    justified_pb = max(0.5, min(justified_pb, 5.0))

    return ValuationResult(
        method_name="P/B Multiple",
        bear_value=book_value_per_share * justified_pb * 0.8,
        base_value=book_value_per_share * justified_pb,
        bull_value=book_value_per_share * justified_pb * 1.2,
        confidence="MEDIUM",
    )


# =============================================================================
# PROMPT GENERATION
# =============================================================================

def generate_valuation_prompt(
    ticker: str,
    current_price: float,
    metrics: FinancialMetrics,
    wacc_calc: WACCCalculation,
    peer_pe_median: float = 15.0,
) -> str:
    """Generate a prompt for LLM-based valuation analysis."""
    pe = current_price / metrics.eps if metrics.eps else None
    bvps = metrics.total_equity / (metrics.shares_outstanding or 1) if metrics.total_equity else 0
    pb = current_price / bvps if bvps > 0 else None

    # Handle None values for formatting
    revenue = metrics.revenue or 0
    net_income = metrics.net_income or 0
    fcf = getattr(metrics, 'free_cash_flow', None) or 0
    total_debt = metrics.total_debt or 0
    cash = getattr(metrics, 'cash_and_equivalents', None) or 0
    shares = getattr(metrics, 'shares_outstanding', None) or 0
    roe = metrics.roe or 0
    roic = metrics.roic or 0
    de = metrics.debt_to_equity or 0

    prompt = f"""# Stock Valuation Analysis — {ticker}

## Data Verification

Current Price: ${current_price:,.2f}
Date: {datetime.now().strftime('%Y-%m-%d')}
Data Source: Internal calculation engine

## Financial Metrics

- Revenue (TTM): ${revenue:,.0f}
- Net Income (TTM): ${net_income:,.0f}
- FCF (TTM): ${fcf:,.0f}
- Total Debt: ${total_debt:,.0f}
- Cash: ${cash:,.0f}
- Shares Outstanding: {shares:,.0f}

## Key Ratios

- P/E: {f"{pe:.1f}x" if pe else "N/A"}
- P/B: {f"{pb:.1f}x" if pb else "N/A"}
- ROE: {f"{roe * 100:.1f}%" if roe else "N/A"}
- ROIC: {f"{roic * 100:.1f}%" if roic else "N/A"}
- Debt/Equity: {f"{de:.2f}" if de else "N/A"}

## WACC Calculation

- Risk-Free Rate: {wacc_calc.risk_free_rate:.2%}
- Beta: {wacc_calc.beta:.2f}
- Cost of Equity: {wacc_calc.cost_of_equity:.2%}
- WACC: {wacc_calc.wacc:.2%}

## Peer Comparison

- Median P/E (Peers): {peer_pe_median:.1f}x

## Analysis Request

Based on the data above, provide a comprehensive multi-method valuation:

1. **Method Selection Rationale** - Which methods are most appropriate?
2. **DCF Analysis** - Three scenarios with assumptions table
3. **Comparables Analysis** - Fair value from peer multiples
4. **Football Field Summary** - Consolidated valuation ranges
5. **Margin of Safety** - Is the stock undervalued?
6. **Risk-Adjusted Return** - Expected return by scenario
7. **Key Risks** - What could go wrong?

Format as a structured investment memo.
"""
    return prompt


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_stock_valuation(
    ticker: str,
    current_price: float,
    metrics: FinancialMetrics,
    wacc: Optional[WACCCalculation] = None,
    peer_pe_median: float = 15.0,
    use_llm: bool = False,
    llm_client=None,
) -> Dict[str, Any]:
    """
    Comprehensive stock valuation analysis.

    Args:
        ticker: Stock ticker symbol
        current_price: Current stock price
        metrics: FinancialMetrics object
        wacc: Optional WACC calculation
        peer_pe_median: Peer median P/E ratio
        use_llm: Whether to use LLM for interpretation
        llm_client: Optional LLMClient instance

    Returns:
        Dictionary with complete valuation analysis
    """
    # Calculate WACC if not provided
    if wacc is None:
        wacc = calculate_wacc(
            total_debt=metrics.total_debt or 0,
            total_equity=metrics.total_equity or 1000,
        )

    # Calculate basic valuations
    pe_result = calculate_pe_multiple(
        eps=metrics.eps or 0,
        peer_median_pe=peer_pe_median,
        growth_rate=metrics.revenue_cagr_3y or 0.10,
    )

    bvps = metrics.total_equity / (metrics.shares_outstanding or 1) if metrics.total_equity else 0
    pb_result = calculate_pb_multiple(
        book_value_per_share=bvps,
        roe=metrics.roe or 0.10,
        cost_of_equity=wacc.cost_of_equity,
    )

    # Build result
    result = {
        "ticker": ticker,
        "analysis_date": datetime.now().isoformat(),
        "current_price": current_price,
        "wacc": {
            "cost_of_equity": wacc.cost_of_equity,
            "wacc": wacc.wacc,
            "beta": wacc.beta,
        },
        "methods": {
            "pe_multiple": {
                "bear": pe_result.bear_value,
                "base": pe_result.base_value,
                "bull": pe_result.bull_value,
                "confidence": pe_result.confidence,
            },
            "pb_multiple": {
                "bear": pb_result.bear_value,
                "base": pb_result.base_value,
                "bull": pb_result.bull_value,
                "confidence": pb_result.confidence,
            },
        },
    }

    # Calculate composite
    values = [v for v in [pe_result.base_value, pb_result.base_value] if v is not None]
    if values:
        composite_base = sum(values) / len(values)
        result["composite"] = {
            "bear": composite_base * 0.9,
            "base": composite_base,
            "bull": composite_base * 1.1,
        }

        # Margin of safety
        if current_price > 0:
            result["margin_of_safety"] = (composite_base - current_price) / current_price

    # Generate LLM prompt if requested
    if use_llm and llm_client:
        prompt = generate_valuation_prompt(
            ticker=ticker,
            current_price=current_price,
            metrics=metrics,
            wacc_calc=wacc,
            peer_pe_median=peer_pe_median,
        )

        llm_result = llm_client.analyze_with_prompt(
            prompt=prompt,
            output_format="Structured investment memo with valuation ranges",
        )

        result["llm_analysis"] = llm_result.get("content")
        result["llm_used"] = True

    return result
