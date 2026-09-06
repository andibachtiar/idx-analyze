"""
Fundamental Analysis Prompt Integration.

Implements ``prompts/fundamental-analysis.md``: a deterministic key-ratio
snapshot plus the standardized Signal Output (thesis invalidation + investment
signal box). Financial values come from PostgreSQL via the data loader — the
LLM never computes or invents a ratio. It may only interpret the supplied,
deterministic numbers.

The prompt spec notes this skill was folded into ``stock-eval``; this module
keeps the lightweight key-ratio + signal-output contract that the original
file still documents.
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


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# =============================================================================
# DETERMINISTIC KEY RATIOS (read from DB, not computed by the LLM)
# =============================================================================

def key_ratios(ticker: str) -> dict[str, float | None]:
    """Return the deterministic key ratios for a ticker from PostgreSQL.

    Uses the merged (richest) snapshot so ratios that live on the IDX row
    (P/E, ROE, D/E) are present even when the latest row is a yfinance backfill.
    """
    ratios = get_data_loader().get_financial_ratios_merged(ticker) or {}
    return {
        "pe_ratio": _num(ratios.get("pe_ratio")),
        "pb_ratio": _num(ratios.get("pb_ratio")),
        "ev_ebitda": _num(ratios.get("ev_ebitda")),
        "roe": _num(ratios.get("roe")),
        "roic": _num(ratios.get("roic")),
        "current_ratio": _num(ratios.get("current_ratio")),
        "debt_to_equity": _num(ratios.get("debt_to_equity")),
        "dividend_yield": _num(ratios.get("dividend_yield")),
        "gross_margin": _num(ratios.get("gross_margin")),
        "operating_margin": _num(ratios.get("operating_margin")),
        "net_margin": _num(ratios.get("net_margin")),
    }


def compute_score(r: dict[str, float | None]) -> float:
    """Return a deterministic 0–10 score from the key ratios (score guide)."""
    roe = r.get("roe") or 0.0
    de = r.get("debt_to_equity") or 0.0
    pe = r.get("pe_ratio")
    ev = r.get("ev_ebitda")
    nm = r.get("net_margin") or 0.0
    cr = r.get("current_ratio")

    roe_s = _clamp(roe / 20.0)             # 20% ROE -> full
    de_s = 1.0 - _clamp(de / 2.0)          # D/E >= 2 -> zero
    pe_s = _clamp(1.0 - pe / 25.0) if pe and pe > 0 else 0.5
    ev_s = _clamp(1.0 - ev / 20.0) if ev and ev > 0 else 0.5
    nm_s = _clamp(nm / 25.0)               # 25% net margin -> full
    cr_s = _clamp((cr - 1.0) / 1.0) if cr else 0.5  # current >= 2 -> full

    components = [roe_s, de_s, pe_s, ev_s, nm_s, cr_s]
    return round(sum(components) / len(components) * 10.0, 1)


def signal_from_score(score: float) -> str:
    """Map a score to BULLISH / NEUTRAL / BEARISH per the score guide."""
    if score >= 6.0:
        return "BULLISH"
    if score >= 4.0:
        return "NEUTRAL"
    return "BEARISH"


def confidence_from_score(score: float, has_data: bool) -> str:
    if not has_data:
        return "LOW"
    if score >= 7.0 or score <= 2.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    return "LOW"


# =============================================================================
# PROMPT GENERATION (per fundamental-analysis.md)
# =============================================================================

def generate_fundamental_prompt(ticker: str, r: dict, score: float, signal: str) -> str:
    """Build the LLM interpretation prompt following the signal-output spec."""
    rows = "\n".join(
        f"- {label}: {_fmt(v)}" for label, v in [
            ("P/E", r.get("pe_ratio")),
            ("P/B", r.get("pb_ratio")),
            ("EV/EBITDA", r.get("ev_ebitda")),
            ("ROE", f"{r.get('roe'):.1f}%" if r.get("roe") is not None else None),
            ("ROIC", f"{r.get('roic'):.1f}%" if r.get("roic") is not None else None),
            ("Current Ratio", r.get("current_ratio")),
            ("D/E", r.get("debt_to_equity")),
            ("Net Margin", f"{r.get('net_margin'):.1f}%" if r.get("net_margin") is not None else None),
        ]
        if v is not None
    )
    return f"""# Fundamental Analysis — {ticker}

## Data Verification

- Date: {datetime.now().strftime('%Y-%m-%d')}
- Source: PostgreSQL (deterministic engine / scraped financial ratios)

## Key Ratios

{rows}

## Deterministic Signal

- Score: {score:.1f}/10 -> {signal}

## Analysis Request

Interpret the deterministic ratios above. Explain what they say about
profitability, leverage, and valuation, and clearly separate FACT,
INTERPRETATION, ASSUMPTION and SPECULATION. Then end with the Signal Output
block:

```
## Thesis Invalidation
If signal is BULLISH: what would break it (price below support, revenue
deceleration, macro shift)? If BEARISH: what would reverse it?

## Investment Signal
Signal: {signal} | Confidence: HIGH/MEDIUM/LOW | Horizon: SHORT/MEDIUM/LONG
Score: {score:.1f}/10 | Action: BUY/HOLD/SELL | Conviction: STRONG/MODERATE/WEAK
```

Do not invent financial numbers and do not give financial advice.
"""


def _fmt(v) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_fundamentals(
    ticker: str,
    use_llm: bool = False,
    llm_client=None,
) -> dict[str, Any]:
    """
    Produce a deterministic fundamental snapshot + optional LLM interpretation.

    Ratios and the score/signal are always deterministic (computed from DB);
    the LLM only interprets them when ``use_llm`` is true and a client is passed.
    """
    r = key_ratios(ticker)
    has_data = any(v is not None for v in r.values())
    score = compute_score(r) if has_data else 0.0
    signal = signal_from_score(score)
    confidence = confidence_from_score(score, has_data)

    result = {
        "ticker": ticker.upper(),
        "analysis_date": datetime.now().isoformat(),
        "key_ratios": r,
        "score": score,
        "signal": signal,
        "confidence": confidence,
        "horizon": "MEDIUM-TERM",
        "thesis_invalidation": {
            "if_bullish": [
                "Price closes below MA200 / key support on above-average volume",
                "Revenue growth decelerates below 5% for 2 consecutive quarters AND gross margin contracts >200bps",
                "Macro regime shift (hawkish pivot / recession probability >60%)",
            ],
            "if_bearish": [
                "Price closes above key resistance / MA200 with volume confirmation",
                "Revenue reaccelerates >15% AND margin expansion resumes",
                "Fundamental improvement: earnings beat >20% with guidance raise",
            ],
        },
        "signal_output": (
            f"Signal: {signal} | Confidence: {confidence} | "
            f"Horizon: MEDIUM-TERM | Score: {score:.1f}/10"
        ),
        "llm_used": False,
    }

    if use_llm and llm_client:
        prompt = generate_fundamental_prompt(ticker, r, score, signal)
        llm_result = llm_client.analyze_with_prompt(
            prompt=prompt,
            system_message=(
                "You are a professional investment analyst for Indonesian stocks (IDX/BEI). "
                "Interpret the supplied deterministic ratios with evidence; separate FACT, "
                "INTERPRETATION, ASSUMPTION, SPECULATION. Never invent numbers and do not give advice."
            ),
            output_format="Markdown: interpretive analysis + Signal Output block.",
        )
        result["llm_analysis"] = llm_result.get("content") or llm_result.get("error") or ""
        result["llm_used"] = True

    return result
