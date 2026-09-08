"""
Dividend Analysis Prompt Integration.

Implements a deterministic-first dividend-quality snapshot for IDX/BEI stocks
(adapted from ``prompts/dividend-analysis.md``): dividend yield, EPS-based payout
ratio, leverage, interest coverage and earnings stability feed a 0-100 safety
score. The LLM only interprets the supplied numbers — it never computes or
invents a ratio.

Adapted scope: the original skill also covers buybacks, M&A and credit ratings,
none of which are reliably published for IDX. This module intentionally omits
those and marks explicitly-unknown fields (e.g. FCF-based payout ratio) as
"Not available" instead of estimating them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from ai.data_loader_pg import get_data_loader


def _num(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# =============================================================================
# DETERMINISTIC DIVIDEND RATIOS (read from DB, not computed by the LLM)
# =============================================================================
#
# get_financial_ratios_merged() returns raw DB values in percent scale for
# percent fields (dividend_yield=5.2 means 5.2%), unlike list_stock_metrics()
# which normalises some percent fields to decimals.

def dividend_ratios(ticker: str) -> dict[str, float | None]:
    """Return the deterministic dividend-relevant ratios for a ticker."""
    ratios = get_data_loader().get_financial_ratios_merged(ticker) or {}
    return {
        "dividend_yield": _num(ratios.get("dividend_yield")),
        "payout_ratio": _num(ratios.get("payout_ratio")),
        "fcf_margin": _num(ratios.get("fcf_margin")),
        "earnings_cagr": _num(ratios.get("earnings_cagr")),
        "debt_to_equity": _num(ratios.get("debt_to_equity")),
        "current_ratio": _num(ratios.get("current_ratio")),
        "interest_coverage": _num(ratios.get("interest_coverage")),
    }


# =============================================================================
# DETERMINISTIC SAFETY SCORE (0-100)
# =============================================================================

def _grade(total: float) -> tuple[str, str]:
    """Map a 0-100 safety score to (grade, assessment)."""
    if total >= 90:
        return "A+", "Very Safe"
    if total >= 75:
        return "A", "Safe"
    if total >= 60:
        return "B", "Borderline Safe"
    if total >= 45:
        return "C", "Elevated Risk"
    if total >= 30:
        return "D", "Unsafe"
    return "F", "Danger Zone"


def safety_score(r: dict[str, float | None]) -> tuple[float, str, str]:
    """Compute a 0-100 dividend-safety score from available (honest) inputs.

    Four components, each worth 25 points. Missing data scores 0 for that
    component (never guessed), and is surfaced via ``notes`` by the caller.
    """
    payout = r.get("payout_ratio")
    de = r.get("debt_to_equity")
    ic = r.get("interest_coverage")
    ecagr = r.get("earnings_cagr")

    # 1. EPS payout ratio (25): lower is safer for sustainability.
    if payout is not None:
        if payout < 40:
            payout_s = 25.0
        elif payout < 60:
            payout_s = 20.0
        elif payout < 80:
            payout_s = 10.0
        else:
            payout_s = 0.0
    else:
        payout_s = 0.0

    # 2. Debt / equity (25): leverage limits dividend headroom.
    if de is not None:
        if de < 0.5:
            de_s = 25.0
        elif de < 1.0:
            de_s = 18.0
        elif de < 1.5:
            de_s = 8.0
        else:
            de_s = 0.0
    else:
        de_s = 0.0

    # 3. Interest coverage (25): ability to keep paying while servicing debt.
    if ic is not None:
        if ic > 5:
            ic_s = 25.0
        elif ic >= 3:
            ic_s = 18.0
        elif ic >= 2:
            ic_s = 8.0
        else:
            ic_s = 0.0
    else:
        ic_s = 0.0

    # 4. Earnings stability (25): positive earnings trend supports dividends.
    if ecagr is not None:
        ecagr_s = 25.0 if ecagr > 0 else 5.0
    else:
        ecagr_s = 0.0

    total = round(payout_s + de_s + ic_s + ecagr_s, 1)
    grade, assessment = _grade(total)
    return total, grade, assessment


def yield_trap_check(r: dict[str, float | None]) -> tuple[str, list[str]]:
    """Detect yield-trap risk from yield + payout + earnings direction."""
    yield_pct = r.get("dividend_yield")
    payout = r.get("payout_ratio")
    ecagr = r.get("earnings_cagr")

    flags: list[str] = []
    risk = "none"

    if yield_pct is not None and yield_pct >= 7:
        risk = "high"
        flags.append("Dividend yield >= 7% — usually signals elevated risk")
    if yield_pct is not None and yield_pct >= 4 and payout is not None and payout >= 70:
        risk = "high" if risk != "high" else risk
        flags.append("High yield combined with payout ratio >= 70% — possibly unsustainable")
    if yield_pct is not None and yield_pct >= 4 and ecagr is not None and ecagr <= 0:
        risk = "high"
        flags.append("High yield while earnings trend is flat/negative — value-trap check required")
    if risk == "none" and yield_pct is not None and yield_pct >= 4:
        risk = "monitoring"
    if not flags:
        flags.append("No yield-trap triggers from available data")

    return risk, flags


def missing_notes(r: dict[str, float | None]) -> list[str]:
    """List fields that are unavailable, so the caller never hides gaps."""
    notes: list[str] = []
    if r.get("payout_ratio") is None:
        notes.append("EPS payout ratio not available")
    if r.get("fcf_margin") is None:
        notes.append("Free-cash-flow margin not available")
    if r.get("interest_coverage") is None:
        notes.append("Interest coverage not available")
    if r.get("earnings_cagr") is None:
        notes.append("Earnings CAGR (3Y) not available")
    if r.get("current_ratio") is None:
        notes.append("Current ratio not available")
    if not notes:
        notes.append("All dividend inputs available")
    # FCF-based payout ratio is fundamentally unavailable (needs dividends/FCF
    # per share), which IDX does not publish in this dataset.
    notes.append(
        "FCF-based payout ratio (dividends/FCF) and dividend growth history "
        "(DGR/streak) are not available; score uses EPS payout + balance-sheet input."
    )
    return notes


# =============================================================================
# PROMPT GENERATION
# =============================================================================

def generate_dividend_prompt(ticker: str, r: dict, score: float, grade: str, risk: str) -> str:
    """Build the LLM interpretation prompt for a dividend snapshot."""
    rows = "\n".join(
        f"- {label}: {v}"
        for label, v in [
            ("Dividend Yield", f"{r.get('dividend_yield'):.2f}%" if r.get("dividend_yield") is not None else "N/A"),
            ("Payout Ratio (EPS)", f"{r.get('payout_ratio'):.1f}%" if r.get("payout_ratio") is not None else "N/A"),
            ("FCF Margin", f"{r.get('fcf_margin'):.1f}%" if r.get("fcf_margin") is not None else "N/A"),
            ("Earnings CAGR (3Y)", f"{r.get('earnings_cagr'):.1f}%" if r.get("earnings_cagr") is not None else "N/A"),
            ("Debt / Equity", f"{r.get('debt_to_equity'):.2f}x" if r.get("debt_to_equity") is not None else "N/A"),
            ("Current Ratio", f"{r.get('current_ratio'):.2f}x" if r.get("current_ratio") is not None else "N/A"),
            ("Interest Coverage", f"{r.get('interest_coverage'):.2f}x" if r.get("interest_coverage") is not None else "N/A"),
        ]
        if v is not None
    )
    return f"""# Dividend Analysis — {ticker}

## Data Verification

- Date: {datetime.now().strftime('%Y-%m-%d')}
- Source: PostgreSQL (deterministic engine / scraped financial ratios)

## Deterministic Snapshot

{rows}

## Deterministic Safety Score

- Safety Score: {score:.0f}/100 -> Grade {grade}
- Yield Trap Risk: {risk}

## Analysis Request

Interpret the deterministic dividend metrics above. Comment on: sustainability of
the payout, whether the yield is justified by balance-sheet strength, and any
yield-trap warning signs. Clearly separate FACT, INTERPRETATION, ASSUMPTION and
SPECULATION. Then end with the Signal Output block:

```
## Investment Signal
Signal: BULLISH/NEUTRAL/BEARISH | Confidence: HIGH/MEDIUM/LOW
Horizon: SHORT/MEDIUM/LONG | Action: BUY/HOLD/SELL
```

Do not invent financial numbers and do not give financial advice.
"""


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_dividend(
    ticker: str,
    use_llm: bool = False,
    llm_client=None,
) -> dict[str, Any]:
    """
    Produce a deterministic dividend snapshot + optional LLM interpretation.

    The yield/payout/score and yield-trap risk are always deterministic from the
    DB; the LLM only interprets them when ``use_llm`` is true and a client is
    passed. No numbers are ever invented.
    """
    r = dividend_ratios(ticker)
    has_data = any(v is not None for v in r.values())
    score, grade, assessment = safety_score(r) if has_data else (0.0, "F", "Danger Zone")
    risk, flags = yield_trap_check(r)

    result = {
        "ticker": ticker.upper(),
        "analysis_date": datetime.now().isoformat(),
        "metrics": r,
        "safety_score": score,
        "grade": grade,
        "assessment": assessment,
        "yield_trap_risk": risk,
        "red_flags": flags,
        "notes": missing_notes(r),
        "has_data": has_data,
        "llm_used": False,
    }

    if use_llm and llm_client:
        prompt = generate_dividend_prompt(ticker, r, score, grade, risk)
        llm_result = llm_client.analyze_with_prompt(
            prompt=prompt,
            system_message=(
                "You are a professional investment analyst for Indonesian stocks (IDX/BEI). "
                "Interpret the supplied deterministic dividend metrics with evidence; separate "
                "FACT, INTERPRETATION, ASSUMPTION, SPECULATION. Never invent numbers and do not "
                "give advice."
            ),
            output_format="Markdown: interpretive dividend analysis + Signal Output block.",
        )
        result["llm_analysis"] = llm_result.get("content") or llm_result.get("error") or ""
        result["llm_used"] = True

    return result
