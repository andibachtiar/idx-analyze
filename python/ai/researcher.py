"""
AI Research Analyst for idx-bei investment research platform.

This module provides an AI-powered research analyst that uses the tools
from Phase 10 to retrieve structured data and generate investment research
reports.

The analyst:
- Understands user questions about stocks
- Determines which tools are needed
- Retrieves structured data
- Analyzes evidence using LLM
- Produces structured research reports
- Distinguishes between facts, interpretations, assumptions, and speculation
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Load environment variables from .env file
# Check multiple possible locations
_env_paths = [
    Path(__file__).parent.parent / ".env",  # python/.env
    Path(__file__).parent.parent.parent / ".env",  # root/.env
    Path.cwd() / ".env",  # current working directory/.env
]

for _env_path in _env_paths:
    if _env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(_env_path)
        print(f"Loaded environment from: {_env_path}")
        break
else:
    print("WARNING: No .env file found. Using default values.")

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from ai.prompts import (
    COMPARISON_PROMPT,
    INITIAL_ANALYSIS_PROMPT,
    SYSTEM_PROMPT,
    THESIS_VALIDATION_PROMPT,
)
from ai.report import ClaimTracker, ResearchReport
from ai.tools import (
    get_company_info,
    get_company_news,
    get_fundamental_analysis,
    get_historical_analysis,
    get_stock_price,
    get_technical_analysis,
    get_valuation,
    run_screening,
)


def _derive_verdict(text: str) -> str:
    """Extract a concise overall verdict from the LLM report text.

    Prioritises actionable ratings (buy/sell/hold) then directional terms
    (bullish/bearish/neutral). Returns "" when none are found.
    """
    low = (text or "").lower()
    order = [
        ("strong buy", "STRONG BUY"),
        ("strong sell", "STRONG SELL"),
        ("buy", "BUY"),
        ("sell", "SELL"),
        ("hold", "HOLD"),
        ("bullish", "BULLISH"),
        ("bearish", "BEARISH"),
        ("neutral", "NEUTRAL"),
    ]
    for key, verdict in order:
        if key in low:
            return verdict
    return ""


class AIResearcher:
    """
    AI-powered investment research analyst.

    Uses LLM to analyze stock data retrieved from deterministic engines
    and generate structured investment research reports.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
    ):
        """
        Initialize the AI researcher.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: LLM model to use (defaults to OPENAI_MODEL env var)
            base_url: Optional custom API base URL (defaults to OPENAI_BASE_URL env var)
        """
        # Get config from environment or parameters
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model if model != "gpt-4o" else os.environ.get("OPENAI_MODEL", "gpt-4o")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

        # Debug: print config status (only in development)
        if not self.api_key:
            print("WARNING: No OpenAI API key found. Set OPENAI_API_KEY env var or pass api_key parameter.")
            print(f"  Current model: {self.model}")
            print(f"  Current base_url: {self.base_url}")

        self._client = None
        if OpenAI is None:
            raise ImportError(
                "OpenAI package not installed. Run: pip install openai"
            )
        if self.api_key:
            try:
                print(f"[DEBUG] Initializing OpenAI client with model: {self.model}")
                print(f"[DEBUG] Base URL: {self.base_url}")
                # Add timeout to prevent hanging
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=30.0  # 30 second timeout
                )
                print(f"OpenAI client initialized successfully")
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
                self._client = None
        else:
            print("No API key configured - using mock responses")

    @property
    def client(self):
        """Get OpenAI client, initializing if needed."""
        return self._client

    def _prepare_data_context(
        self,
        ticker: str,
        fundamental_data: Dict[str, Any],
        valuation_data: Dict[str, Any],
        technical_data: Dict[str, Any],
        historical_data: Dict[str, Any],
        company_info: Optional[Dict[str, Any]] = None,
        news_data: Optional[Dict[str, Any]] = None,
        price_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Prepare data context for LLM analysis.

        Converts tool results to a structured text format for the LLM.
        """
        context_parts = [f"## Stock: {ticker}"]

        # Add company info
        if company_info:
            context_parts.append("\n### Company Information")
            context_parts.append(json.dumps(company_info, indent=2, default=str))

        # Add price data
        if price_data and price_data.get("price"):
            context_parts.append("\n### Price Data")
            context_parts.append(json.dumps(price_data, indent=2, default=str))

        # Add fundamental data
        if fundamental_data:
            context_parts.append("\n### Fundamental Analysis")
            context_parts.append(json.dumps(fundamental_data, indent=2, default=str))

        # Add valuation data
        if valuation_data:
            context_parts.append("\n### Valuation Analysis")
            context_parts.append(json.dumps(valuation_data, indent=2, default=str))

        # Add technical data
        if technical_data:
            context_parts.append("\n### Technical Analysis")
            context_parts.append(json.dumps(technical_data, indent=2, default=str))

        # Add news data
        if news_data and news_data.get("news"):
            context_parts.append("\n### Recent News")
            context_parts.append(json.dumps(news_data, indent=2, default=str))

        # Add historical data
        if historical_data:
            context_parts.append("\n### Historical Analysis")
            context_parts.append(json.dumps(historical_data, indent=2, default=str))

        return "\n".join(context_parts)

    def _fill_news_sections(self, report: ResearchReport, news_data: Optional[Dict[str, Any]]) -> None:
        """Populate ``recent_events``/``risks`` from real news, deterministically.

        The LLM is free to interpret news, but the report must never present an
        empty section when actual news exists. Facts come from the news rows;
        this only formats them (event classifier + sentiment/keyword risk tags)
        and never invents headlines.
        """
        news = (news_data or {}).get("news") or []
        if not news:
            return

        if not getattr(report, "recent_events", ""):
            events = []
            try:
                from events import classif_news_records
                events = classif_news_records(news)
            except Exception:
                events = []
            if events:
                lines = []
                for ev in events[:8]:
                    date = (ev.get("published_at") or "")[:10]
                    etype = ev.get("event_type") or "event"
                    lines.append(
                        f"- **{etype}** ({date}): {ev.get('title','')} — {ev.get('source','')}"
                    )
            else:
                lines = [
                    f"- ({str(n.get('published_at',''))[:10]}) {n.get('title','')} — {n.get('source','')}"
                    for n in news[:8]
                    if n.get("title")
                ]
            if lines:
                report.recent_events = "\n".join(lines)

        if not getattr(report, "risks", ""):
            risk_keywords = (
                "penurunan", "turun", "rugi", "kerugian", "hutang", "gugatan",
                "sanksi", "pemecatan", "delisting", "suspend", "warning",
                "probe", "investigasi", "krisis", "default", "gagal bayar",
            )
            risk_lines = []
            for n in news:
                text = ((n.get("title") or "") + " " + (n.get("content") or "")).lower()
                sent = n.get("sentiment", n.get("sentiment_score"))
                if (sent is not None and sent < 0) or any(
                    k in text for k in risk_keywords
                ):
                    risk_lines.append(
                        f"- ({str(n.get('published_at',''))[:10]}) {n.get('title','')} — {n.get('source','')}"
                    )
            if risk_lines:
                report.risks = "\n".join(risk_lines[:8])

    def _fill_business_quality(self, report: ResearchReport, fundamental_data: Optional[Dict[str, Any]]) -> None:
        """Synthesize ``business_quality`` from deterministic fundamentals.

        The LLM may leave this section empty; this fills it from the computed
        profitability/health metrics (never invented). Margins/ROE/ROA/ROIC are
        decimals (0.20 = 20%), D/E and current-ratio are ratios.
        """
        if getattr(report, "business_quality", ""):
            return
        profitability = (fundamental_data or {}).get("profitability") or {}
        health = (fundamental_data or {}).get("financial_health") or {}

        def val(section, key) -> float | None:
            entry = (section or {}).get(key) or {}
            return entry.get("value") if entry.get("is_available") else None

        roe = val(profitability, "roe")
        roa = val(profitability, "roa")
        roic = val(profitability, "roic")
        net_margin = val(profitability, "net_margin")
        operating_margin = val(profitability, "operating_margin")
        gross_margin = val(profitability, "gross_margin")
        d_e = val(health, "debt_to_equity")
        current = val(health, "current_ratio")

        if roe is None and roa is None and d_e is None and current is None:
            return

        def pct(x):
            return f"{x * 100:.1f}%" if isinstance(x, (int, float)) else "—"

        rows = []
        if roe is not None:
            label = "Kuat" if roe >= 0.15 else ("Moderat" if roe >= 0.08 else "Lemah")
            rows.append(("Profitabilitas (ROE)", pct(roe), label))
        if roa is not None:
            rows.append(("Return on Assets", pct(roa), "Baik" if roa >= 0.05 else ("Cukup" if roa >= 0.02 else "Rendah")))
        if roic is not None:
            rows.append(("ROIC", pct(roic), "Baik" if roic >= 0.12 else ("Cukup" if roic >= 0.06 else "Rendah")))
        if net_margin is not None:
            rows.append(("Net Margin", pct(net_margin), "Sehat" if net_margin >= 0.10 else ("Moderat" if net_margin >= 0.04 else "Tipis")))
        if operating_margin is not None:
            rows.append(("Operating Margin", pct(operating_margin), "Sehat" if operating_margin >= 0.12 else ("Moderat" if operating_margin >= 0.05 else "Tipis")))
        if gross_margin is not None:
            rows.append(("Gross Margin", pct(gross_margin), "Sehat" if gross_margin >= 0.30 else ("Moderat" if gross_margin >= 0.15 else "Tipis")))
        if d_e is not None:
            label = "Konservatif" if d_e <= 1.0 else ("Moderat" if d_e <= 2.0 else "Agresif")
            rows.append(("Leverage (D/E)", f"{d_e:.2f}×", label))
        if current is not None:
            label = "Sangat likuid" if current >= 1.5 else ("Cukup" if current >= 1.0 else "Ketat")
            rows.append(("Likuiditas (Current Ratio)", f"{current:.2f}×", label))

        table = ["| Dimensi | Nilai | Penilaian |", "|---|---|---| "]
        table += [f"| {a} | {b} | {c} |" for a, b, c in rows]

        notes = []
        if roe is not None: notes.append(f"ROE {pct(roe)}")
        if roic is not None: notes.append(f"ROIC {pct(roic)}")
        if d_e is not None: notes.append(f"D/E {d_e:.2f}×")
        if current is not None: notes.append(f"current ratio {current:.2f}×")
        conclusion = (
            "Kualitas bisnis disintesis dari metrik deterministik. "
            + (", ".join(notes) if notes else "terbatas karena metrik yang tersedia")
            + "."
        )
        report.business_quality = "\n".join(table) + "\n\n**Kesimpulan:** " + conclusion

    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        Call LLM with messages and return response.

        Args:
            messages: List of message dictionaries with 'role' and 'content'

        Returns:
            LLM response text
        """
        if not self.client:
            print("[DEBUG] No client available, using mock response")
            return self._mock_llm_response(messages)

        try:
            print(f"[DEBUG] Calling LLM with model: {self.model}")
            print(f"[DEBUG] Sending {len(messages)} messages")

            # Use streaming with timeout to prevent hanging
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
                timeout=30,  # 30 second timeout for the request
                stream=False,
            )
            print("[DEBUG] LLM response received successfully")
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"LLM call failed: {e}")
            return self._mock_llm_response(messages)

    def _mock_llm_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Return mock response when LLM is not available.

        This allows the system to function without an API key for testing.
        """
        last_message = messages[-1] if messages else {}
        content = last_message.get("content", "")

        return f"""[MOCK RESPONSE - No OpenAI API configured]

Based on the data provided for this analysis:

**Executive Summary:**
This is a mock response. To enable AI analysis, please set the OPENAI_API_KEY environment variable.

**Key Observations:**
- The deterministic analysis engines have calculated all metrics
- Raw data is available for human review
- AI interpretation requires OpenAI API access

**Next Steps:**
1. Set OPENAI_API_KEY environment variable
2. Or implement a custom LLM provider
3. Review the structured data from tool outputs directly
"""

    @staticmethod
    def _count_available(section: Dict[str, Any]) -> tuple[int, int]:
        """Count (available, total) metric entries in a result section.

        Entries are typically ``{"value": ..., "is_available": ...}``;
        ``is_available`` is authoritative but a non-None value is accepted for
        robustness (older results may omit the flag).
        """
        if not isinstance(section, dict) or not section:
            return 0, 0
        available = 0
        for entry in section.values():
            if isinstance(entry, dict):
                if entry.get("is_available") or entry.get("value") is not None:
                    available += 1
            elif entry not in (None, ""):
                available += 1
        return available, len(section)

    def _calculate_confidence(
        self,
        *,
        price_data: Optional[Dict[str, Any]],
        fundamental_data: Optional[Dict[str, Any]],
        valuation_data: Optional[Dict[str, Any]],
        technical_data: Optional[Dict[str, Any]],
        company_info: Optional[Dict[str, Any]],
        news_data: Optional[Dict[str, Any]],
    ) -> float:
        """Deterministic confidence from data completeness (never invented).

        Weights cover the six evidentiary pillars so the score reflects how much
        real data supported the report, rather than a hardcoded value. The AI
        only interprets data; it does not fabricate the confidence level.
        """
        price_ok = bool(price_data and price_data.get("price"))
        info_ok = bool(
            company_info
            and (company_info.get("name") or company_info.get("sector")
                 or company_info.get("industry") or company_info.get("board"))
        )

        # Fundamental completeness across growth / profitability / health / cashflow.
        fund = fundamental_data or {}
        fund_avail, fund_total = 0, 0
        for key in ("growth", "profitability", "financial_health", "cash_flow"):
            a, t = self._count_available(fund.get(key) or {})
            fund_avail += a
            fund_total += t
        fund_score = fund_avail / fund_total if fund_total else 0.0

        # Valuation: current multiples + optional historical comparison.
        val = valuation_data or {}
        val_total = len(val.get("valuations") or {})
        val_avail, _ = self._count_available(val.get("valuations") or {})
        hist_avail = len(val.get("historical_comparison") or {})
        val_score = (
            (val_avail / val_total) * 0.6 if val_total else 0.0
        ) + (0.4 if hist_avail else 0.0)
        val_score = min(val_score, 1.0)

        tech = technical_data or {}
        tech_ok = bool(tech.get("indicators") or tech.get("signals"))
        news_ok = bool((news_data or {}).get("news"))

        score = (
            0.15 * (1.0 if price_ok else 0.0)
            + 0.10 * (1.0 if info_ok else 0.0)
            + 0.25 * fund_score
            + 0.15 * val_score
            + 0.20 * (1.0 if tech_ok else 0.0)
            + 0.15 * (1.0 if news_ok else 0.0)
        )
        return round(min(score, 1.0), 2)

    def analyze_stock(
        self,
        ticker: str,
        question: Optional[str] = None,
        include_history: bool = True,
        max_history_periods: int = 5,
    ) -> ResearchReport:
        """
        Analyze a stock and generate a research report.

        Args:
            ticker: Stock ticker symbol
            question: Optional specific question to answer
            include_history: Whether to include historical analysis
            max_history_periods: Maximum number of historical periods to include

        Returns:
            ResearchReport with complete analysis
        """
        print(f"[DEBUG] Starting analysis for {ticker}")

        if question is None:
            question = f"What is your assessment of {ticker}?"

        # Retrieve data from tools
        print("[DEBUG] Loading stock price...")
        price_data = get_stock_price(ticker)
        print(f"[DEBUG] Price data loaded: {price_data is not None}")

        print("[DEBUG] Loading fundamental analysis...")
        fundamental_data = get_fundamental_analysis(ticker)
        print(f"[DEBUG] Fundamental data loaded: {fundamental_data is not None}")

        print("[DEBUG] Loading valuation...")
        valuation_data = get_valuation(ticker)
        print(f"[DEBUG] Valuation data loaded: {valuation_data is not None}")

        print("[DEBUG] Loading technical analysis...")
        technical_data = get_technical_analysis(ticker)
        print(f"[DEBUG] Technical data loaded: {technical_data is not None}")

        print("[DEBUG] Loading company info...")
        company_info = get_company_info(ticker)
        print(f"[DEBUG] Company info loaded: {company_info is not None}")

        print("[DEBUG] Loading news...")
        news_data = get_company_news(ticker, limit=5)
        print(f"[DEBUG] News data loaded: {news_data is not None}")

        historical_data = {}
        if include_history:
            historical_data = {"note": "Historical data not available in mock mode"}

        # Prepare data context
        print("[DEBUG] Preparing data context...")
        data_context = self._prepare_data_context(
            ticker=ticker,
            fundamental_data=fundamental_data,
            valuation_data=valuation_data,
            technical_data=technical_data,
            historical_data=historical_data,
            company_info=company_info,
            news_data=news_data,
            price_data=price_data,
        )
        print(f"[DEBUG] Data context length: {len(data_context)} chars")

        # Build prompt
        prompt = INITIAL_ANALYSIS_PROMPT.format(
            ticker=ticker,
            question=question,
        )

        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{prompt}\n\n{data_context}"},
        ]

        # Get LLM response
        llm_response = self._call_llm(messages)

        # Parse response into report sections
        report = self._parse_report_response(ticker, question, llm_response)

        # Deterministically fill recent_events/risks from real news so the
        # report never shows empty sections when news exists (facts from data,
        # not invented by the LLM).
        self._fill_news_sections(report, news_data)

        # Fill business_quality from deterministic fundamentals when the LLM
        # left it empty.
        self._fill_business_quality(report, fundamental_data)

        # Add metadata
        report.data_sources = [
            "fundamental_analysis",
            "valuation_analysis",
            "technical_analysis",
            "price_data",
        ]
        if news_data and news_data.get("news"):
            report.data_sources.append("company_news")
        if include_history:
            report.data_sources.append("historical_analysis")

        # Deterministic confidence from real data completeness (not a mock value).
        report.confidence = self._calculate_confidence(
            price_data=price_data,
            fundamental_data=fundamental_data,
            valuation_data=valuation_data,
            technical_data=technical_data,
            company_info=company_info,
            news_data=news_data,
        )

        return report

    def compare_stocks(
        self,
        tickers: List[str],
        question: Optional[str] = None,
    ) -> ResearchReport:
        """
        Compare multiple stocks and generate a comparative analysis.

        Args:
            tickers: List of ticker symbols to compare
            question: Optional specific question to answer

        Returns:
            ResearchReport with comparative analysis
        """
        if question is None:
            question = f"Compare these stocks: {', '.join(tickers)}"

        # Retrieve data for all stocks
        all_data = {}
        for ticker in tickers:
            all_data[ticker] = {
                "price": get_stock_price(ticker),
                "fundamentals": get_fundamental_analysis(ticker),
                "valuation": get_valuation(ticker),
                "technical": get_technical_analysis(ticker),
            }

        # Prepare comparison context
        context_parts = ["## Stock Comparison Data"]
        for ticker in tickers:
            context_parts.append(f"\n### {ticker}")
            ticker_data = all_data[ticker]
            context_parts.append(json.dumps(ticker_data, indent=2, default=str))

        data_context = "\n".join(context_parts)

        # Build prompt
        prompt = COMPARISON_PROMPT.format(
            tickers=", ".join(tickers),
            question=question,
        )

        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{prompt}\n\n{data_context}"},
        ]

        # Get LLM response
        llm_response = self._call_llm(messages)

        # Parse response
        report = self._parse_report_response(tickers[0], question, llm_response)
        report.data_sources = [f"comparison_{t}" for t in tickers]

        return report

    def validate_thesis(
        self,
        ticker: str,
        thesis: str,
    ) -> ResearchReport:
        """
        Validate an investment thesis against available data.

        Args:
            ticker: Stock ticker symbol
            thesis: Investment thesis to validate

        Returns:
            ResearchReport with thesis validation
        """
        # Retrieve data
        fundamental_data = get_fundamental_analysis(ticker)
        valuation_data = get_valuation(ticker)
        historical_data = {"note": "Historical data not available in mock mode"}

        data_context = self._prepare_data_context(
            ticker=ticker,
            fundamental_data=fundamental_data,
            valuation_data=valuation_data,
            technical_data={},
            historical_data=historical_data,
        )

        # Build prompt
        prompt = THESIS_VALIDATION_PROMPT.format(
            ticker=ticker,
            thesis=thesis,
        )

        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{prompt}\n\n{data_context}"},
        ]

        # Get LLM response
        llm_response = self._call_llm(messages)

        # Parse response
        report = self._parse_report_response(ticker, f"Thesis Validation: {thesis}", llm_response)
        report.data_sources = ["thesis_validation"]

        return report

    def _parse_report_response(
        self,
        ticker: str,
        question: str,
        response: str,
    ) -> ResearchReport:
        """
        Parse LLM response into structured report sections.

        Attempts to extract sections from the response text.
        Falls back to placing full response in executive summary if parsing fails.
        """
        # Try to parse structured sections
        sections = {
            "executive_summary": "",
            "business_quality": "",
            "growth_analysis": "",
            "profitability": "",
            "financial_health": "",
            "valuation": "",
            "technical_position": "",
            "recent_events": "",
            "risks": "",
            "bull_case": "",
            "base_case": "",
            "bear_case": "",
            "conclusion": "",
        }

        # Simple section extraction by headers (robust to '## 4. Valuation' style).
        current_section = None
        lines = response.split("\n")

        for line in lines:
            line_lower = line.lower().strip()
            # Normalise header: strip leading #, numbering, and dashes.
            header = line_lower
            if header.startswith("#"):
                header = header.lstrip("#")
                header = re.sub(r"^[\s\d.\-]+", "", header).strip()

            is_header = header != line_lower  # it was a markdown heading

            # Check for section headers ONLY on actual markdown headings.
            if is_header:
                if "executive summary" in header or "summary" in header:
                    current_section = "executive_summary"
                elif "business quality" in header or "quality" in header:
                    current_section = "business_quality"
                elif "growth" in header or "revenue" in header or "earnings" in header:
                    current_section = "growth_analysis"
                elif "profitability" in header:
                    current_section = "profitability"
                elif "financial health" in header or "balance sheet" in header or "financial" in header:
                    current_section = "financial_health"
                elif "valuation" in header:
                    current_section = "valuation"
                elif "technical" in header:
                    current_section = "technical_position"
                elif "recent events" in header or "catalyst" in header or "news" in header:
                    current_section = "recent_events"
                elif "risk" in header:
                    current_section = "risks"
                elif "bull case" in header or "bullish case" in header:
                    current_section = "bull_case"
                elif "base case" in header:
                    current_section = "base_case"
                elif "bear case" in header or "bearish case" in header:
                    current_section = "bear_case"
                elif "conclusion" in header:
                    current_section = "conclusion"
            elif current_section and line.strip():
                # Add content to current section (non-header line)
                if not sections[current_section]:
                    sections[current_section] = line.strip()
                else:
                    sections[current_section] += "\n" + line.strip()

        # If no sections were parsed, put everything in executive summary
        if not any(sections.values()):
            sections["executive_summary"] = response

        # Ensure a usable executive summary exists even when the LLM didn't emit
        # a dedicated header: fall back to the conclusion, then any section.
        if not sections["executive_summary"]:
            sections["executive_summary"] = (
                sections["conclusion"]
                or next((v for v in sections.values() if v), "")
            )

        return ResearchReport(
            ticker=ticker,
            question=question,
            **sections,
            overall_verdict=_derive_verdict(response),
        )

    def screen_and_analyze(
        self,
        screen_type: str = "buffett",
        question: Optional[str] = None,
    ) -> List[ResearchReport]:
        """
        Screen stocks and analyze top results.

        Args:
            screen_type: Type of screen to apply
            question: Optional question for analysis

        Returns:
            List of ResearchReports for screened stocks
        """
        from ai.tools import batch_screen

        # Run screening
        screen_result = batch_screen([], screen_type=screen_type)

        # Extract top stocks from results
        top_stocks = []
        if "results" in screen_result:
            passed = [r for r in screen_result["results"] if r.get("passed")]
            top_stocks = [r["ticker"] for r in passed[:5]]  # Top 5

        if not top_stocks:
            return []

        # Analyze each stock
        reports = []
        for ticker in top_stocks:
            report = self.analyze_stock(ticker, question)
            reports.append(report)

        return reports


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_researcher(
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
) -> AIResearcher:
    """
    Create a new AI researcher instance.

    Args:
        api_key: OpenAI API key
        model: LLM model to use

    Returns:
        AIResearcher instance
    """
    return AIResearcher(api_key=api_key, model=model)


def analyze_stock(
    ticker: str,
    question: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
) -> ResearchReport:
    """
    Convenience function to analyze a stock.

    Args:
        ticker: Stock ticker symbol
        question: Optional question
        api_key: OpenAI API key
        model: LLM model

    Returns:
        ResearchReport
    """
    researcher = create_researcher(api_key=api_key, model=model)
    return researcher.analyze_stock(ticker, question)


def compare_stocks(
    tickers: List[str],
    question: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
) -> ResearchReport:
    """
    Convenience function to compare stocks.

    Args:
        tickers: List of ticker symbols
        question: Optional question
        api_key: OpenAI API key
        model: LLM model

    Returns:
        ResearchReport
    """
    researcher = create_researcher(api_key=api_key, model=model)
    return researcher.compare_stocks(tickers, question)
