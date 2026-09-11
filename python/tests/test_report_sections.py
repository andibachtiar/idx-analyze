"""Tests for report section coverage + real claim_summary (backlog #2).

Guards two regressions:
  1. The LLM prompt must define the exact report structure, and the parser must
     fill every section without duplicating one section into another.
  2. ``claim_summary`` must be derived from the report's inline
     [FACT]/[INTERPRETATION]/... markers, not hardcoded to zeros.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.prompts import (
    INITIAL_ANALYSIS_PROMPT,
    REPORT_SECTION_HEADINGS,
    REPORT_TEMPLATE,
)
from ai.report import (
    CLAIM_TYPES,
    REPORT_SECTION_FIELDS,
    ResearchReport,
    count_claim_markers,
    report_to_dict,
)
from ai.researcher import AIResearcher, _match_section_key, _normalize_heading

_SECTION_KEYS = [key for _, key in REPORT_SECTION_HEADINGS]


# =============================================================================
# PROMPT / TEMPLATE STRUCTURE
# =============================================================================

class TestPromptStructure:
    def test_prompt_lists_every_section_heading(self):
        for title, _ in REPORT_SECTION_HEADINGS:
            assert f"## {title}" in INITIAL_ANALYSIS_PROMPT

    def test_prompt_only_formats_ticker_and_question(self):
        """No stray braces: .format(ticker, question) must succeed."""
        rendered = INITIAL_ANALYSIS_PROMPT.format(ticker="SICO", question="Assess?")
        assert "SICO" in rendered and "Assess?" in rendered

    def test_template_placeholders_match_section_keys(self):
        values = {key: "x" for key in _SECTION_KEYS}
        values.update(ticker="SICO", timestamp="T", sources="S", confidence="C")
        rendered = REPORT_TEMPLATE.format(**values)
        for title, _ in REPORT_SECTION_HEADINGS:
            assert f"## {title}" in rendered

    def test_heading_keys_match_report_fields(self):
        """The prompt/template and the serializer must agree on section keys."""
        assert _SECTION_KEYS == list(REPORT_SECTION_FIELDS)


# =============================================================================
# CLAIM SUMMARY (marker-derived)
# =============================================================================

class TestClaimMarkers:
    def test_counts_each_type(self):
        text = "[FACT] a [INTERPRETATION] b [ASSUMPTION] c [SPECULATION] d"
        assert count_claim_markers(text) == {
            "FACT": 1, "INTERPRETATION": 1, "ASSUMPTION": 1, "SPECULATION": 1,
        }

    def test_case_insensitive_and_spaced(self):
        assert count_claim_markers("[fact] a [ FACT ] b")["FACT"] == 2

    def test_ignores_unknown_and_empty(self):
        counts = count_claim_markers("[OPINION] x", "", None)
        assert counts == {t: 0 for t in CLAIM_TYPES}

    def test_report_to_dict_derives_claim_summary(self):
        report = ResearchReport(ticker="SICO", question="q")
        report.executive_summary = "[FACT] ROE 7% and [INTERPRETATION] cheap."
        report.risks = "[SPECULATION] commodity reversal"
        summary = report_to_dict(report)["claim_summary"]
        assert summary["FACT"] == 1
        assert summary["INTERPRETATION"] == 1
        assert summary["SPECULATION"] == 1
        assert summary["ASSUMPTION"] == 0

    def test_report_to_dict_shape(self):
        report = ResearchReport(ticker="SICO", question="q")
        result = report_to_dict(report)
        assert set(result) == {
            "ticker", "question", "generated_at", "confidence_score",
            "overall_verdict", "data_sources", "claim_summary", "sections",
        }
        assert set(result["sections"]) == set(REPORT_SECTION_FIELDS)

    def test_report_to_dict_serializes_data_sources(self):
        report = ResearchReport(
            ticker="SICO", question="q",
            data_sources=["price_data", "fundamental_analysis"],
        )
        assert report_to_dict(report)["data_sources"] == [
            "price_data", "fundamental_analysis",
        ]

    def test_report_to_dict_data_sources_defaults_empty(self):
        report = ResearchReport(ticker="SICO", question="q")
        assert report_to_dict(report)["data_sources"] == []

    def test_data_sources_provenance_improves_validator(self):
        """Provenance must reach the validator's data-quality dimension (+5)."""
        from ai.prompts.validator import validate_analysis

        report = ResearchReport(ticker="SICO", question="q")
        report.executive_summary = "[FACT] ROE 7%."
        without = validate_analysis(report_to_dict(report))["dimensions"]["data_quality"]
        report.data_sources = ["fundamental_analysis"]
        with_sources = validate_analysis(report_to_dict(report))["dimensions"]["data_quality"]
        assert with_sources == without + 5


# =============================================================================
# HEADING PARSING
# =============================================================================

class TestHeadingMatching:
    def test_normalize_strips_markup_and_numbering(self):
        assert _normalize_heading("## 4. Valuation") == "Valuation"
        assert _normalize_heading("# **Executive Summary:**") == "Executive Summary"
        assert _normalize_heading("not a heading") is None
        assert _normalize_heading("##   ") is None

    def test_word_boundary_matching(self):
        assert _match_section_key("Bear Case") == "bear_case"
        assert _match_section_key("Base Case") == "base_case"
        # "base" must not be found inside "database"
        assert _match_section_key("Database Notes") is None

    def test_indonesian_headings(self):
        assert _match_section_key("Ringkasan Eksekutif") == "executive_summary"
        assert _match_section_key("Risiko") == "risks"


# =============================================================================
# PARSER: SECTION COVERAGE + NO DUPLICATION
# =============================================================================

_FULL_RESPONSE = """## Executive Summary
[FACT] ROE 7%.

## Business Quality
[FACT] Operating margin 15%.

## Growth Analysis
No CAGR data available.

## Profitability
[FACT] Net margin 15%.

## Financial Health
[INTERPRETATION] Lightly levered.

## Valuation
[FACT] PE 9.7.

## Technical Position
[FACT] RSI 67.

## Recent Events & Catalysts
[FACT] Oil above 100.

## Risks
[SPECULATION] Commodity reversal.

## Bull Case
[INTERPRETATION] Deep value.

## Base Case
[ASSUMPTION] Margins flat.

## Bear Case
[INTERPRETATION] Value trap.

## Conclusion
[INTERPRETATION] HOLD.
"""


class TestParserCoverage:
    def _parse(self, response):
        return AIResearcher()._parse_report_response("SICO", "q", response)

    def test_all_sections_filled(self):
        report = self._parse(_FULL_RESPONSE)
        for key in REPORT_SECTION_FIELDS:
            assert getattr(report, key).strip(), f"{key} should be non-empty"

    def test_sections_are_distinct(self):
        report = self._parse(_FULL_RESPONSE)
        assert report.executive_summary != report.business_quality
        assert report.base_case != report.bear_case

    def test_preamble_becomes_exec_summary_without_duplication(self):
        """The old fallback copied another section into the exec summary."""
        response = (
            "Before the analysis, four issues affect confidence.\n\n"
            "## Business Quality\n[FACT] Operating margin 15%.\n"
        )
        report = self._parse(response)
        assert report.executive_summary.startswith("Before the analysis")
        assert report.executive_summary != report.business_quality
        assert "Operating margin" in report.business_quality

    def test_missing_exec_summary_synthesises_verdict(self):
        response = "## Valuation\n[FACT] PE 9.7.\n\n## Conclusion\nWe recommend a buy.\n"
        report = self._parse(response)
        assert report.executive_summary  # never left empty
        assert report.executive_summary != report.valuation
        assert report.overall_verdict == "BUY"

    def test_numbered_headings(self):
        response = "# 1. Valuation\n[FACT] PE 9.7.\n\n## 2. Risks\n[FACT] thin liquidity.\n"
        report = self._parse(response)
        assert "PE 9.7" in report.valuation
        assert "thin liquidity" in report.risks

    def test_unrecognised_heading_keeps_content(self):
        """An unknown heading is a boundary but must not drop its body."""
        response = "## Conclusion\n[FACT] A.\n\n## Appendix\n[FACT] extra detail.\n"
        report = self._parse(response)
        assert "extra detail" in report.conclusion

    def test_plain_text_falls_back_to_exec_summary(self):
        report = self._parse("no headings here at all")
        assert "no headings here" in report.executive_summary


# =============================================================================
# SHARED SERIALIZER (API + pipeline)
# =============================================================================

class TestSharedSerializer:
    def test_api_and_pipeline_agree(self):
        import auto_analyze as aa
        from api.main import _research_report_to_dict

        report = ResearchReport(ticker="SICO", question="q")
        report.executive_summary = "[FACT] ROE 7%."
        assert aa.report_to_dict(report) == _research_report_to_dict(report)

    def test_pipeline_claim_summary_not_hardcoded(self):
        import auto_analyze as aa

        report = ResearchReport(ticker="SICO", question="q")
        report.profitability = "[FACT] margin [INTERPRETATION] improving"
        result = aa.report_to_dict(report)
        assert result["claim_summary"]["FACT"] == 1
        assert result["claim_summary"]["INTERPRETATION"] == 1
