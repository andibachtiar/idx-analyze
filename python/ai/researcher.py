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
import time
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

from ai.llm import (
    TIER_STRONG,
    TRANSIENT_ERROR_MARKERS,
    content_error,
    provider_error,
    resolve_model,
)
from ai.prompts import (
    COMPARISON_PROMPT,
    INITIAL_ANALYSIS_PROMPT,
    SYSTEM_PROMPT,
    THESIS_VALIDATION_PROMPT,
)
from ai.report import REPORT_SECTION_FIELDS, ClaimTracker, ResearchReport
from ai.tools import (
    get_company_info,
    get_company_news,
    get_fundamental_analysis,
    get_historical_analysis,
    get_macro_news,
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


def _merge_news(
    ticker_news: Optional[Dict[str, Any]],
    macro_news: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Merge per-ticker news and macro news into a single news dict.

    The result keeps the per-ticker news items first (more relevant to the stock)
    then macro/economic items, so deterministic sections (events/risks) and the
    LLM prompt see all available evidence without duplication.
    """
    ticker_items = (ticker_news or {}).get("news") or []
    macro_items = (macro_news or {}).get("news") or []
    merged = list(ticker_items) + list(macro_items)
    return {
        "news": merged,
        "count": len(merged),
        "has_company_news": bool(ticker_items),
        "has_macro_news": bool(macro_items),
    }


# Heading text -> report section key. Phrases are matched on word boundaries and
# in order, so more specific headings win ("Bear Case" must not match "base").
_SECTION_HEADING_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("executive_summary", ("executive summary", "ringkasan eksekutif")),
    (
        "business_quality",
        ("business quality", "kualitas bisnis", "business model", "competitive position"),
    ),
    (
        "growth_analysis",
        (
            "growth analysis",
            "revenue & earnings growth",
            "revenue and earnings growth",
            "growth",
            "pertumbuhan",
        ),
    ),
    ("profitability", ("profitability", "profitabilitas", "profit margin", "margins")),
    (
        "financial_health",
        (
            "financial health",
            "balance sheet",
            "cash flow",
            "kesehatan keuangan",
            "neraca",
            "arus kas",
        ),
    ),
    ("valuation", ("valuation", "valuasi")),
    ("technical_position", ("technical position", "technical analysis", "technical", "teknikal")),
    (
        "recent_events",
        ("recent events", "catalysts", "catalyst", "events", "news", "berita", "peristiwa"),
    ),
    ("risks", ("risks", "risk", "risiko")),
    ("bull_case", ("bull case", "bullish case", "bull")),
    ("base_case", ("base case", "base")),
    ("bear_case", ("bear case", "bearish case", "bear")),
    ("conclusion", ("conclusion", "kesimpulan")),
)


def _normalize_heading(line: str) -> Optional[str]:
    """Return the text of a markdown heading line, or None if it is not one."""
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    text = stripped.lstrip("#").strip()
    # Drop leading list numbering ("1. ", "2) ", "3 - ").
    text = re.sub(r"^\d+\s*[.)\-:]*\s*", "", text)
    text = text.strip("*_` ").rstrip(":").strip()
    return text or None


def _match_section_key(heading: str) -> Optional[str]:
    """Map a heading such as "## 4. Valuation" to its section key, else None."""
    text = heading.lower()
    for key, phrases in _SECTION_HEADING_MAP:
        for phrase in phrases:
            if re.search(rf"\b{re.escape(phrase)}\b", text):
                return key
    return None


class AIResearcher:
    """
    AI-powered investment research analyst.

    Uses LLM to analyze stock data retrieved from deterministic engines
    and generate structured investment research reports.
    """

    # Error substrings that indicate a transient provider/router failure worth
    # retrying (HTTP 200 error payloads, rate limits, connection/timeout errors).
    # Shared with LLMClient (ai.llm) so both paths agree on what is retryable.
    _TRANSIENT_ERROR_MARKERS = TRANSIENT_ERROR_MARKERS

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        total_timeout: Optional[float] = None,
    ):
        """
        Initialize the AI researcher.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: LLM model to use (defaults to OPENAI_MODEL env var)
            base_url: Optional custom API base URL (defaults to OPENAI_BASE_URL env var)
            timeout: Per-request timeout in seconds (defaults to OPENAI_TIMEOUT env var, else 300)
            total_timeout: Hard ceiling on wall-clock for one logical call including
                retries (defaults to OPENAI_TOTAL_TIMEOUT env var, else 600). Bounds
                the worst case so a wedged provider cannot hang a web request for
                the tens of minutes that retry multiplication would otherwise allow.
        """
        # Get config from environment or parameters
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        # Research reports are high-reasoning output, so the default ("gpt-4o"
        # means "not explicitly chosen") resolves to the STRONG tier.
        self.model = model if model != "gpt-4o" else resolve_model(TIER_STRONG)
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.timeout = timeout if timeout is not None else float(
            os.environ.get("OPENAI_TIMEOUT", "300")
        )
        self.total_timeout = total_timeout if total_timeout is not None else float(
            os.environ.get("OPENAI_TOTAL_TIMEOUT", "600")
        )

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
                # Timeout prevents hanging; generous default for slow models/proxies.
                # max_retries=0: the OpenAI SDK retries 2x by default, which would
                # multiply with this class's own retry loop (3 x 3 x timeout ~ 45min)
                # and hang the request. Retries are owned by _call_llm instead.
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout,
                    max_retries=0,
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
        macro_news_data: Optional[Dict[str, Any]] = None,
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

        # Add per-ticker news
        if news_data and news_data.get("news"):
            context_parts.append("\n### Recent News")
            context_parts.append(json.dumps(news_data, indent=2, default=str))

        # Add macro/economic news
        if macro_news_data and macro_news_data.get("news"):
            context_parts.append("\n### Macro News")
            context_parts.append(json.dumps(macro_news_data, indent=2, default=str))

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

    def _call_llm(self, messages: List[Dict[str, str]], max_retries: int = 2) -> str:
        """
        Call LLM with messages and return response.

        Transient provider failures (service_unavailable, rate limit, timeouts)
        are retried with backoff, but bounded by ``self.total_timeout`` so the
        whole logical call cannot exceed a predictable wall-clock budget. If a
        configured provider still fails, this raises instead of returning the
        mock report: a mock saved as a real report would mislead the user and
        block regeneration for 24h via the recency debounce. The mock is only
        used when no client/key is set.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_retries: Extra attempts after the first for transient errors

        Returns:
            LLM response text
        """
        if not self.client:
            print("[DEBUG] No client available, using mock response")
            return self._mock_llm_response(messages)

        deadline = time.monotonic() + self.total_timeout
        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                print(f"[DEBUG] Calling LLM with model: {self.model}")
                print(f"[DEBUG] Sending {len(messages)} messages")

                # Per-request timeout, configurable via OPENAI_TIMEOUT to accommodate
                # slow models/proxies when generating comprehensive analysis.
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=4096,
                    timeout=self.timeout,
                    stream=False,
                )

                # Some routers answer HTTP 200 with an error payload (choices is
                # None plus a top-level 'error' field) OR with the error text as
                # the message content; surface both instead of storing garbage.
                message = provider_error(response)
                content = None
                if message is None:
                    content = response.choices[0].message.content
                    if not (content or "").strip():
                        message = "LLM provider error (empty_content): response returned no content"
                    else:
                        message = content_error(content)
                if message is not None:
                    raise RuntimeError(message)

                print("[DEBUG] LLM response received successfully")
                return content or ""
            except Exception as e:
                last_error = str(e)
                transient = any(
                    marker in last_error.lower()
                    for marker in self._TRANSIENT_ERROR_MARKERS
                )
                delay = 2 * (attempt + 1)
                # Only retry when the error is transient, attempts remain, and a
                # further full request can still finish inside the time budget.
                if (
                    attempt < max_retries
                    and transient
                    and time.monotonic() + delay + self.timeout <= deadline
                ):
                    print(
                        f"LLM call failed ({last_error}); retrying in {delay}s "
                        f"(attempt {attempt + 2}/{max_retries + 1})"
                    )
                    time.sleep(delay)
                    continue
                if not transient:
                    print(f"LLM call failed (non-transient, no retry): {last_error}")
                else:
                    print(f"LLM call failed (no attempts/time budget left): {last_error}")
                raise RuntimeError(
                    f"LLM call failed: {last_error} "
                    f"(attempts={attempt + 1}, per_request_timeout={self.timeout:g}s, "
                    f"total_budget={self.total_timeout:g}s; "
                    f"tune OPENAI_TIMEOUT / OPENAI_TOTAL_TIMEOUT)"
                ) from e
        raise RuntimeError(f"LLM call failed: {last_error}")

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
        macro_news_data: Optional[Dict[str, Any]] = None,
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
        macro_ok = bool((macro_news_data or {}).get("news"))

        score = (
            0.15 * (1.0 if price_ok else 0.0)
            + 0.10 * (1.0 if info_ok else 0.0)
            + 0.25 * fund_score
            + 0.15 * val_score
            + 0.20 * (1.0 if tech_ok else 0.0)
            + 0.10 * (1.0 if news_ok else 0.0)
            + 0.05 * (1.0 if macro_ok else 0.0)
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

        print("[DEBUG] Loading macro news...")
        macro_news_data = get_macro_news(limit=5)
        print(f"[DEBUG] Macro news data loaded: {macro_news_data is not None}")

        historical_data = {}
        if include_history:
            # Load the real multi-period history (price/financial history) from the
            # data loader instead of a hardcoded "not available" stub.
            print("[DEBUG] Loading historical analysis...")
            historical_data = get_historical_analysis(ticker)
            print(f"[DEBUG] Historical periods: {historical_data.get('periods', 'n/a')}")

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
            macro_news_data=macro_news_data,
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
        # not invented by the LLM). Consider per-ticker and macro news together.
        self._fill_news_sections(report, _merge_news(news_data, macro_news_data))

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
        if macro_news_data and macro_news_data.get("news"):
            report.data_sources.append("macro_news")
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
            macro_news_data=macro_news_data,
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
        # Load the real multi-period history instead of a hardcoded stub.
        historical_data = get_historical_analysis(ticker)

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

        Headings are mapped deterministically (see ``_SECTION_HEADING_MAP``).
        Content before the first heading is kept as the executive-summary
        fallback, and unseen headings never copy another section verbatim.
        """
        sections = {field: "" for field in REPORT_SECTION_FIELDS}

        current_section = None
        preamble_lines: List[str] = []

        for line in response.split("\n"):
            heading = _normalize_heading(line)
            if heading is not None:
                key = _match_section_key(heading)
                if key is not None:
                    current_section = key
                # An unrecognised heading is only a boundary: current_section is
                # kept so its body is not silently dropped.
                continue

            stripped = line.strip()
            if not stripped:
                continue
            if current_section is None:
                preamble_lines.append(stripped)
            elif not sections[current_section]:
                sections[current_section] = stripped
            else:
                sections[current_section] += "\n" + stripped

        # Nothing recognisable at all: keep the raw response so nothing is lost.
        if not any(sections.values()):
            sections["executive_summary"] = response.strip()

        # Fill a missing executive summary from the model's opening paragraph.
        # Never copy another section verbatim: that duplicated e.g.
        # ``business_quality`` into the executive summary on every report.
        if not sections["executive_summary"]:
            preamble = "\n".join(preamble_lines).strip()
            if preamble:
                sections["executive_summary"] = preamble
            else:
                verdict = _derive_verdict(response)
                sections["executive_summary"] = (
                    f"Overall verdict: {verdict}."
                    if verdict
                    else "No executive summary was provided; see the sections below."
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
