"""Financial Report Analyst (Phase 19)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class DocumentInfo:
    filing_type: str
    period_covered: str
    auditor_name: str
    auditor_opinion: str
    filing_date: str
    red_flags: List[str] = field(default_factory=list)


@dataclass
class FinancialHealth:
    revenue_growth_yoy: float = 0.0
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    fcf_margin: float = 0.0
    net_debt: float = 0.0
    debt_to_ebitda: float = 0.0


@dataclass
class RiskAssessment:
    new_risks: List[str] = field(default_factory=list)
    accounting_quality_score: float = 7.0


@dataclass
class ManagementCredibility:
    guidance_record: str = "meeting"


@dataclass
class FinancialReportAnalysis:
    ticker: str
    document_info: DocumentInfo
    financial_health: FinancialHealth
    risk_assessment: RiskAssessment
    management_credibility: ManagementCredibility
    overall_signal: str = "NEUTRAL"
    confidence: str = "MEDIUM"
    score: float = 5.0
    action: str = "HOLD"
    key_positives: List[str] = field(default_factory=list)
    key_negatives: List[str] = field(default_factory=list)
    analysis_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "signal": self.overall_signal,
            "score": self.score,
            "action": self.action,
            "key_positives": self.key_positives,
            "key_negatives": self.key_negatives,
        }


def analyze_financial_report(
    ticker: str, filing_type: str, revenue: float, net_income: float,
    gross_margin: float, operating_margin: float, fcf: float,
    total_debt: float, cash: float = 0.0, auditor_opinion: str = "unqualified",
) -> FinancialReportAnalysis:
    """Analyze a financial report."""
    debt_to_ebitda = total_debt / (net_income * 3) if net_income else 0
    quality_score = 7.0
    if auditor_opinion != "unqualified":
        quality_score -= 2.0
    if debt_to_ebitda > 3.0:
        quality_score -= 1.0

    if quality_score >= 8.0 and operating_margin > 0.15:
        signal, action, score = "BULLISH", "BUY", min(10, quality_score + 1)
    elif quality_score >= 6.0:
        signal, action, score = "NEUTRAL", "HOLD", quality_score
    else:
        signal, action, score = "BEARISH", "SELL", max(0, quality_score - 1)

    return FinancialReportAnalysis(
        ticker=ticker,
        document_info=DocumentInfo(filing_type=filing_type, period_covered=datetime.now().strftime("%Y-%m-%d"),
                                    auditor_name="Default Auditor", auditor_opinion=auditor_opinion,
                                    filing_date=datetime.now().strftime("%Y-%m-%d")),
        financial_health=FinancialHealth(revenue_growth_yoy=0.10, gross_margin=gross_margin,
                                          operating_margin=operating_margin, fcf_margin=fcf/revenue if revenue else 0,
                                          net_debt=total_debt-cash, debt_to_ebitda=debt_to_ebitda),
        risk_assessment=RiskAssessment(accounting_quality_score=quality_score),
        management_credibility=ManagementCredibility(),
        overall_signal=signal, confidence="HIGH" if quality_score >= 7 else "MEDIUM",
        score=score, action=action, analysis_date=datetime.now().strftime("%Y-%m-%d"),
    )


def generate_financial_report_prompt(ticker: str, analysis: FinancialReportAnalysis) -> str:
    """Generate prompt for LLM analysis."""
    return f"# Financial Report Analysis - {ticker}\nFiling: {analysis.document_info.filing_type}\nScore: {analysis.score}"
