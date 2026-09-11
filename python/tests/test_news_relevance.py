"""Tests for news relevance gating (backlog #3).

Brave News Search tags every result with the query ticker, so an SICO query
returned Sigma Lithium / SigmaRoc / Super Micro / Kelso Group articles tagged
``SICO``. These tests pin the deterministic gate that rejects such false
positives while keeping genuinely relevant articles.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from news_relevance import (  # noqa: E402
    article_text,
    company_name_acronym,
    company_name_tokens,
    is_relevant_news,
)

SICO_NAME = "Sigma Energy Compressindo"


class TestCompanyNameTokens:
    def test_drops_legal_and_geography_tokens(self):
        assert company_name_tokens("Bank Rakyat Indonesia (Persero) Tbk.") == [
            "BANK", "RAKYAT",
        ]

    def test_keeps_distinctive_tokens(self):
        assert company_name_tokens(SICO_NAME) == ["SIGMA", "ENERGY", "COMPRESSINDO"]

    def test_empty_name(self):
        assert company_name_tokens(None) == []


class TestCompanyNameAcronym:
    def test_builds_acronym_from_legal_name(self):
        assert company_name_acronym("Bank Rakyat Indonesia (Persero) Tbk.") == "BRI"
        assert company_name_acronym("Bank Central Asia Tbk.") == "BCA"

    def test_rejects_too_short_acronym(self):
        assert company_name_acronym("Bank Mandiri (Persero) Tbk.") is None
        assert company_name_acronym("ANTM") is None


class TestArticleText:
    def test_joins_title_and_content(self):
        assert article_text("Judul", "Isi") == "Judul Isi"
        assert article_text("Judul", None) == "Judul"
        assert article_text(None, None) == ""


class TestRelevance:
    def test_ticker_as_uppercase_whole_word(self):
        assert is_relevant_news("Saham ADMR Naik Kelas", "ADMR", "Alamtri Minerals") is True

    def test_ticker_requires_uppercase_whole_word(self):
        # Lowercase prose mention is not the IDX ticker convention.
        assert is_relevant_news("sico naik hari ini", "SICO", None) is False
        # A longer uppercase token must not match ("SICO" inside "SICOM").
        assert is_relevant_news("SICOM mencatat laba", "SICO", None) is False

    def test_full_company_name_matches(self):
        text = "Sigma Energy Compressindo raih kontrak baru"
        assert is_relevant_news(text, "SICO", SICO_NAME) is True

    def test_requires_every_distinctive_name_token(self):
        # Only "Sigma" present -> ambiguous with Sigma Lithium, must not match.
        assert is_relevant_news("Mengapa saham Sigma Lithium turun?", "SICO", SICO_NAME) is False
        assert is_relevant_news("Saham SigmaRoc melonjak 12%", "SICO", SICO_NAME) is False

    def test_name_acronym_matches(self):
        text = "Fundamental Kokoh, BRI Perkuat Kontribusi bagi Ekonomi Nasional"
        assert is_relevant_news(text, "BBRI", "Bank Rakyat Indonesia (Persero) Tbk.") is True

    def test_macro_news_is_always_relevant(self):
        # ticker None == macro/general news: this gate only guards attribution.
        assert is_relevant_news("BI naikkan suku bunga", None, None) is True

    def test_empty_text_is_not_relevant(self):
        assert is_relevant_news("", "SICO", SICO_NAME) is False
        assert is_relevant_news(None, "SICO", SICO_NAME) is False


class TestSicoFalsePositives:
    """The exact rows that polluted the SICO research report."""

    FALSE_POSITIVES = [
        "Kelso Group luncurkan penawaran saham ritel dengan diskon 5,7%",
        "Pasangan CEO Super Micro Computer jual saham senilai $7,7 juta",
        "Mengapa saham Sigma Lithium turun hari ini?",
        "Saham SigmaRoc melonjak 12% didorong kenaikan laba dan akuisisi baru",
    ]

    def test_all_rejected(self):
        for title in self.FALSE_POSITIVES:
            assert is_relevant_news(title, "SICO", SICO_NAME) is False, title

    def test_genuine_sico_article_kept(self):
        text = "SICO (Sigma Energy Compressindo) umumkan ekspansi pabrik"
        assert is_relevant_news(text, "SICO", SICO_NAME) is True
