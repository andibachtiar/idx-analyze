"""News relevance gating.

Brave News Search is queried per ticker (``"<TICKER> saham berita"``) and its
results used to be stored with the query ticker unconditionally. Brave matches
loosely, so an SICO (Sigma Energy Compressindo) query returned articles about
Sigma Lithium, SigmaRoc, Super Micro and Kelso Group — all tagged ``SICO`` and
later fed to the AI as "company news".

This module decides, deterministically and offline, whether an article is
actually about a company before it is linked to that company's ticker. It is
shared by the ingest scraper (``scrape_brave_news``) and the cleanup path so the
rule cannot drift.

Matching is deliberately conservative. A false positive (an unrelated article
labelled as company news) actively misleads the analysis, whereas a false
negative merely means less news — so an article is accepted only on strong
evidence:

1. the ticker as an UPPERCASE whole word (IDX convention: "saham ANTM"), or
2. *every* distinctive token of the company name present as a whole word, or
3. the company-name acronym as an UPPERCASE whole word ("Bank Rakyat Indonesia"
   -> "BRI"), length >= 3.

Rule 2 requires all tokens (not any) precisely so "Sigma Lithium" does not pass
for "Sigma Energy Compressindo". The trade-off is recall: an article that only
abbreviates the name (e.g. "Mandiri" for Bank Mandiri) is dropped.
"""

from __future__ import annotations

import re

# Legal / boilerplate tokens removed before building the name acronym.
LEGAL_NAME_TOKENS = frozenset(
    {
        "PT",
        "TBK",
        "PERSERO",
        "LTD",
        "INC",
        "PLC",
        "CORP",
        "CORPORATION",
        "CO",
        "COMPANY",
    }
)

# Tokens carrying no identifying information (boilerplate + geography/industry),
# removed before the "every distinctive token" match so "Bank Central Asia Tbk."
# is matched on BANK/CENTRAL/ASIA only.
GENERIC_NAME_TOKENS = LEGAL_NAME_TOKENS | frozenset(
    {
        "HOLDING",
        "HOLDINGS",
        "GROUP",
        "INTERNATIONAL",
        "INTERNASIONAL",
        "INDONESIA",
    }
)

MIN_ACRONYM_LENGTH = 3

_TOKEN_RE = re.compile(r"[A-Z0-9]+")


def _name_tokens(name: str | None) -> list[str]:
    if not name:
        return []
    return _TOKEN_RE.findall(str(name).upper())


def company_name_tokens(name: str | None) -> list[str]:
    """Return the distinctive (non-boilerplate) uppercase tokens of a name."""
    return [token for token in _name_tokens(name) if token not in GENERIC_NAME_TOKENS]


def company_name_acronym(name: str | None) -> str | None:
    """Return the initials of the legal name (legal designators removed).

    "Bank Rakyat Indonesia (Persero) Tbk." -> "BRI"; "Bank Mandiri (Persero)
    Tbk." -> "BM" (rejected as too short/ambiguous by MIN_ACRONYM_LENGTH).
    """
    initials = "".join(
        token[0] for token in _name_tokens(name) if token not in LEGAL_NAME_TOKENS
    )
    if len(initials) < MIN_ACRONYM_LENGTH:
        return None
    return initials


def article_text(title: str | None, content: str | None = None) -> str:
    """Build the searchable text for a news item (title first, then body)."""
    return " ".join(part for part in (title, content) if part)


def _has_uppercase_word(text: str, word: str) -> bool:
    """True when ``word`` appears as an uppercase whole word (case-sensitive)."""
    return re.search(rf"\b{re.escape(word.upper())}\b", text) is not None


def _has_word(text_lower: str, word: str) -> bool:
    """True when ``word`` appears as a whole word, case-insensitively."""
    return re.search(rf"\b{re.escape(word.lower())}\b", text_lower) is not None


def is_relevant_news(
    text: str | None,
    ticker: str | None,
    company_name: str | None = None,
) -> bool:
    """Return True when ``text`` plausibly refers to the given company.

    ``ticker`` is the ticker the article was fetched/linked for. A missing
    ticker (macro news) is always considered relevant — this gate only guards
    per-company attribution.
    """
    if not ticker:
        return True
    text = text or ""
    if not text.strip():
        return False

    if _has_uppercase_word(text, ticker):
        return True

    tokens = company_name_tokens(company_name)
    if tokens:
        lowered = text.lower()
        if all(_has_word(lowered, token) for token in tokens):
            return True

    acronym = company_name_acronym(company_name)
    return bool(acronym) and _has_uppercase_word(text, acronym)
