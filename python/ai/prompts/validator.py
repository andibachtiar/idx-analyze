"""
Result Validator — deterministic confidence audit for AI analyses (Phase 18k).

Audits any analysis output (research report, screen-AI, dividend, macro) across
five dimensions and produces a 0-100 Confidence Score + tier. The score is
computed deterministically from the structure of the supplied analysis (which
sections/facts/scenarios actually exist), so it never relies on the LLM to
"grade itself" and never invents financial figures.

The LLM is only optional: when ``use_llm`` is true and a client is passed, it
produces a narrative + warnings/red-flags on top of the deterministic scores.
Default (no LLM) still yields a fully deterministic confidence score.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

# =============================================================================
# DETERMINISTIC CONFIDENCE SCORE (0-100) — 5 dimensions, 20 points each
# =============================================================================

# Report sections the AI writes into; used to measure completeness.
_SECTIONS = [
    "executive_summary",
    "business_quality",
    "growth_analysis",
    "profitability",
    "financial_health",
    "valuation",
    "technical_position",
    "recent_events",
    "risks",
    "bull_case",
    "base_case",
    "bear_case",
    "conclusion",
]


def _sections(analysis: dict[str, Any]) -> dict[str, Any]:
    """Return the report ``sections`` dict (canonical or flat fallback)."""
    sections = analysis.get("sections")
    if isinstance(sections, dict):
        return sections
    # Older pipeline reports stored fields flat at the top level.
    return {k: analysis.get(k) for k in _SECTIONS if k in analysis}


def _count_nonempty(mapping: dict[str, Any]) -> int:
    return sum(1 for v in mapping.values() if v and str(v).strip())


def _data_sources(analysis: dict[str, Any]) -> list[str]:
    src = analysis.get("data_sources")
    if isinstance(src, list):
        return src
    if isinstance(src, str):
        return [src]
    return []


def _claim_summary(analysis: dict[str, Any]) -> dict[str, int]:
    cs = analysis.get("claim_summary")
    if isinstance(cs, dict):
        return {k: int(v or 0) for k, v in cs.items() if k in ("FACT", "INTERPRETATION", "ASSUMPTION", "SPECULATION")}
    return {}


def _text_blob(analysis: dict[str, Any]) -> str:
    sec = _sections(analysis)
    parts = [analysis.get("llm_analysis", ""), analysis.get("conclusion", "")]
    parts += [str(v) for v in sec.values() if isinstance(v, str)]
    return " ".join(parts).lower()


def _dim_data_quality(analysis: dict[str, Any]) -> int:
    score = 0
    if _data_sources(analysis) or analysis.get("source"):
        score += 5
    if _claim_summary(analysis).get("FACT", 0) > 0:
        score += 5
    sec = _sections(analysis)
    if sec and _count_nonempty(sec) / len(sec) >= 0.5:
        score += 5
    if analysis.get("confidence_score") is not None:
        score += 5
    return score


def _dim_methodology(analysis: dict[str, Any]) -> int:
    sec = _sections(analysis)
    score = 0
    if str(sec.get("valuation", "")).strip():
        score += 5
    if all(str(sec.get(k, "")).strip() for k in ("bull_case", "base_case", "bear_case")):
        score += 5
    if analysis.get("overall_verdict"):
        score += 5
    if str(sec.get("conclusion", "")).strip():
        score += 5
    return score


def _dim_signal_consistency(analysis: dict[str, Any]) -> int:
    sec = _sections(analysis)
    score = 0
    # Fundamental + technical both present means the report can cross-check signals.
    if str(sec.get("profitability", "")).strip() and str(sec.get("technical_position", "")).strip():
        score += 7
    verdict = str(analysis.get("overall_verdict", "")).lower()
    if verdict and "uncertainty" not in verdict:
        score += 7
    if str(sec.get("financial_health", "")).strip():
        score += 6
    return score


def _dim_risk_coverage(analysis: dict[str, Any]) -> int:
    sec = _sections(analysis)
    score = 0
    risks = str(sec.get("risks", "")).strip()
    if risks:
        score += 7
    if str(sec.get("bear_case", "")).strip():
        score += 7
    if str(sec.get("recent_events", "")).strip():
        score += 6
    return score


def _dim_transparency(analysis: dict[str, Any]) -> int:
    score = 0
    cs = _claim_summary(analysis)
    if cs.get("FACT", 0) > 0:
        score += 7
    if cs.get("INTERPRETATION", 0) > 0:
        score += 7
    blob = _text_blob(analysis)
    if any(word in blob for word in ("not available", "unavailable", "tidak tersedia", "not found", "insufficient", "terbatas")):
        score += 6
    return score


def validate_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Audit an analysis dict and return a deterministic confidence score."""
    dimensions = {
        "data_quality": _dim_data_quality(analysis),
        "methodology": _dim_methodology(analysis),
        "signal_consistency": _dim_signal_consistency(analysis),
        "risk_coverage": _dim_risk_coverage(analysis),
        "transparency": _dim_transparency(analysis),
    }
    total = sum(dimensions.values())
    tier = confidence_tier(total)
    warnings = _build_warnings(dimensions, analysis)
    return {
        "total": total,
        "tier": tier,
        "dimensions": dimensions,
        "warnings": warnings,
        "strengths": _build_strengths(dimensions, analysis),
    }


def confidence_tier(total: int) -> str:
    """Map a 0-100 confidence score to a tier label."""
    if total >= 85:
        return "VERY HIGH"
    if total >= 70:
        return "HIGH"
    if total >= 55:
        return "MEDIUM"
    if total >= 40:
        return "LOW"
    return "VERY LOW"


def _build_warnings(dimensions: dict[str, int], analysis: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    sec = _sections(analysis)
    if dimensions["data_quality"] < 10:
        warnings.append("Data sources / facts are sparse — verify the underlying data.")
    if dimensions["methodology"] < 10:
        warnings.append("Valuation or scenario modelling is missing / incomplete.")
    if dimensions["risk_coverage"] < 10:
        warnings.append("Downside risks / bear case are under-covered.")
    if dimensions["transparency"] < 10:
        warnings.append("Claim types (FACT/INTERPRETATION) are not clearly separated.")
    if not _count_nonempty(sec):
        warnings.append("Report sections are empty — analysis may be incomplete.")
    return warnings


def _build_strengths(dimensions: dict[str, int], analysis: dict[str, Any]) -> list[str]:
    strengths: list[str] = []
    if dimensions["data_quality"] >= 15:
        strengths.append("Strong data evidence base.")
    if dimensions["methodology"] >= 15:
        strengths.append("Methodology includes scenario modelling (bull/base/bear).")
    if dimensions["risk_coverage"] >= 15:
        strengths.append("Comprehensive risk coverage.")
    if dimensions["signal_consistency"] >= 14:
        strengths.append("Fundamental & technical signals can be cross-checked.")
    return strengths


# =============================================================================
# VALIDATE FROM RESEARCH MEMORY
# =============================================================================

def validate_report(ticker: str) -> dict[str, Any]:
    """Validate the latest saved research report for a ticker."""
    from ai.memory import get_research_history

    reports = get_research_history(ticker, limit=1)
    if not reports:
        return {
            "ticker": ticker.upper(),
            "found": False,
            "total": 0,
            "tier": "VERY LOW",
            "dimensions": {},
            "warnings": ["No saved research report found for this ticker."],
        }
    report = reports[0]
    analysis = dict(report)
    analysis.setdefault("data_sources", report.get("data_sources") or [])
    result = validate_analysis(analysis)
    result["ticker"] = ticker.upper()
    result["found"] = True
    result["saved_at"] = report.get("saved_at") or report.get("generated_at")
    return result


# =============================================================================
# PROMPT GENERATION (optional LLM narrative)
# =============================================================================

def generate_validator_prompt(ticker: str, analysis: dict[str, Any], scores: dict[str, Any]) -> str:
    """Build the prompt for an LLM to add narrative + flags on top of scores."""
    dims = scores.get("dimensions", {})
    rows = "\n".join(f"- {k}: {v}/20" for k, v in dims.items())
    return f"""# Result Validator — {ticker or 'analysis'}

## Deterministic Confidence Score

- Total: {scores.get('total', 0)}/100 -> {scores.get('tier', '')}

## Per-dimension scores

{rows}

## Audit Request

Given the deterministic scores above, write a short meta-analysis of this
analysis: list the main warnings / red flags, what is well-supported, and what
would raise the confidence score. Do NOT invent financial numbers — only assess
the quality and completeness of the analysis. Do not give financial advice.
"""


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def enrich_with_validator(analysis: dict[str, Any]) -> dict[str, Any]:
    """Attach a deterministic validator score to an analysis dict.

    Returns a shallow copy of ``analysis`` with ``validator_total``,
    ``validator_tier``, ``validator_dimensions``, ``validator_warnings`` and
    ``validator_strengths`` added, so the score can be carried alongside any
    report saved to research memory (or into research_candidates) without
    needing a separate lookup later. Pure and idempotent — no LLM involved.
    """
    scores = validate_analysis(analysis)
    return {
        **analysis,
        "validator_total": scores["total"],
        "validator_tier": scores["tier"],
        "validator_dimensions": scores["dimensions"],
        "validator_warnings": scores["warnings"],
        "validator_strengths": scores["strengths"],
    }


def analyze_validator(
    ticker: str = "",
    analysis: Optional[dict[str, Any]] = None,
    use_llm: bool = False,
    llm_client=None,
) -> dict[str, Any]:
    """Validate an analysis (or the latest report for a ticker)."""
    if analysis is None:
        analysis = validate_report(ticker)
        scores = analysis
        if not analysis.get("found"):
            scores = {"total": 0, "tier": analysis["tier"], "dimensions": {}, "warnings": analysis["warnings"], "strengths": []}
    else:
        scores = validate_analysis(analysis)

    result = {
        "validation_date": datetime.now().isoformat(),
        "ticker": ticker.upper() or "",
        **scores,
        "llm_used": False,
    }

    if use_llm and llm_client:
        prompt = generate_validator_prompt(ticker, analysis or {}, scores)
        llm_result = llm_client.analyze_with_prompt(
            prompt=prompt,
            system_message=(
                "You are a rigorous investment-result validator. Assess only the quality and "
                "completeness of the supplied analysis. Do not invent financial numbers and do "
                "not give financial advice."
            ),
            output_format="Markdown: short meta-analysis with warnings, red flags and strengths.",
        )
        result["llm_analysis"] = llm_result.get("content") or llm_result.get("error") or ""
        result["llm_used"] = True

    return result
