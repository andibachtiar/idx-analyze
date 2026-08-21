"""
Field mappings for normalizing raw financial data from various sources.

Indonesian financial statements use inconsistent field names across sources:
- IDX API uses camelCase (e.g., "profitAttrOwner")
- Yahoo Finance uses snake_case (e.g., "netIncome")
- iXBRL uses custom taxonomy names

This module provides mappings from various source field names to our normalized names.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# Primary mapping: source_field_name -> normalized_field_name
FIELD_MAPPINGS: Dict[str, str] = {
    # Income Statement - Revenue
    "sales": "revenue",
    "revenue": "revenue",
    "total_revenue": "revenue",
    "penjualan": "revenue",
    "pendapatan": "revenue",
    "net_sales": "revenue",
    "total_sales": "revenue",

    # Income Statement - Costs
    "cost_of_goods_sold": "cost_of_goods_sold",
    "pokok_penjualan": "cost_of_goods_sold",
    "cogs": "cost_of_goods_sold",
    "hcogssold": "cost_of_goods_sold",

    # Income Statement - Gross Profit
    "gross_profit": "gross_profit",
    "laba_kotor": "gross_profit",
    "profit_gross": "gross_profit",

    # Income Statement - Operating Income
    "operating_income": "operating_income",
    "laba_oprasional": "operating_income",
    "operating_profit": "operating_income",
    "ebit": "operating_income",

    # Income Statement - EBT (Earnings Before Tax)
    "ebt": "operating_income",  # Often used as proxy in IDX data
    "laba_sebelum_pajak": "operating_income",
    "profit_before_tax": "operating_income",
    "pbt": "operating_income",

    # Income Statement - Net Income
    "profit_period": "net_income",
    "profitPeriod": "net_income",  # camelCase from IDX API
    "profit_attr_owner": "net_income",
    "profitAttrOwner": "net_income",  # camelCase from IDX API
    "profit_attributable_to_owners": "net_income",
    "net_income": "net_income",
    "laba_rugi": "net_income",
    "laba_untukpemegang Saham": "net_income",
    "net_profit": "net_income",
    "bottom_line": "net_income",

    # Income Statement - EPS
    "eps": "eps",
    "earnings_per_share": "eps",
    "laporan_per_share": "eps",

    # Balance Sheet - Assets
    "assets": "total_assets",
    "total_assets": "total_assets",
    "total_aset": "total_assets",
    "aset_total": "total_assets",
    "current_assets": "current_assets",
    "aset_beredar": "current_assets",

    # Balance Sheet - Cash
    "cash": "cash_and_equivalents",
    "cash_and_equivalents": "cash_and_equivalents",
    "kas_dan_setara_kas": "cash_and_equivalents",
    "cash_equivalents": "cash_and_equivalents",

    # Balance Sheet - Liabilities
    "liabilities": "total_liabilities",
    "total_liabilities": "total_liabilities",
    "total_kewajiban": "total_liabilities",
    "liabilities_total": "total_liabilities",
    "current_liabilities": "current_liabilities",
    "kewajiban_beredar": "current_liabilities",

    # Balance Sheet - Debt
    "debt": "total_debt",
    "total_debt": "total_debt",
    "utang": "total_debt",
    "long_term_debt": "long_term_debt",
    "utang_jangka_panjang": "long_term_debt",
    "short_term_debt": "total_debt",  # Often grouped together in IDX data
    "current_portion_long_term_debt": "total_debt",

    # Balance Sheet - Equity
    "equity": "total_equity",
    "total_equity": "total_equity",
    "total_ekuitas": "total_equity",
    "ekuitas": "total_equity",
    "book_value": "total_equity",  # Sometimes used interchangeably
    "shareholders_equity": "total_equity",
    "stockholders_equity": "total_equity",

    # Per Share Data
    "book_value_per_share": "book_value_per_share",
    "nilai_buku_per_lempeng": "book_value_per_share",
    "shares_outstanding": "shares_outstanding",
    "jumlah_lempeng": "shares_outstanding",
    "shares_out": "shares_outstanding",

    # Dividends
    "dividend_per_share": "dividend_per_share",
    "dividen_per_lempeng": "dividend_per_share",
    "dps": "dividend_per_share",

    # Margin/Ratio fields (these are unitless)
    "npm": "net_margin",
    "net_profit_margin": "net_margin",
    "margin_keuntungan_bersih": "net_margin",

    "roa": "roa",
    "return_on_assets": "roa",
    "rentabilitas_aset": "roa",

    "roe": "roe",
    "return_on_equity": "roe",
    "rentabilitas_ekuitas": "roe",

    "de_ratio": "debt_to_equity",
    "debt_to_equity": "debt_to_equity",
    "der": "debt_to_equity",
    "nisbah_utang_ekuitas": "debt_to_equity",
    "deRatio": "debt_to_equity",  # camelCase from IDX API

    "per": "pe_ratio",
    "price_earning_ratio": "pe_ratio",
    "pe_ratio": "pe_ratio",
    "rasio_pada_laba": "pe_ratio",
    "PER": "pe_ratio",  # uppercase variant

    "price_bv": "pb_ratio",
    "price_to_book": "pb_ratio",
    "pb_ratio": "pb_ratio",
    "rasio_harga_nilai_buku": "pb_ratio",
    "priceBV": "pb_ratio",  # camelCase from IDX API
    "PriceBV": "pb_ratio",  # uppercase variant

    "gross_margin": "gross_margin",
    "margin_kotor": "gross_margin",

    "operating_margin": "operating_margin",
    "margin_oprasional": "operating_margin",

    # Additional common variants
    "total": "total_assets",
    "total_asset": "total_assets",
    "bookValue": "book_value_per_share",  # camelCase from IDX API
    "book_value": "book_value_per_share",
}

# Reverse mapping: normalized_name -> list of possible source names
REVERSE_MAPPINGS: Dict[str, List[str]] = {
    v: [k for k, val in FIELD_MAPPINGS.items() if val == v]
    for v in set(FIELD_MAPPINGS.values())
}

# Fields that should be treated as ratios (unitless)
RATIO_FIELDS: set = {
    "net_margin", "roa", "roe", "debt_to_equity",
    "pe_ratio", "pb_ratio", "gross_margin", "operating_margin",
    "current_ratio", "ev_ebitda"
}

# Fields that represent absolute values (need unit handling)
ABSOLUTE_FIELDS: set = {
    "revenue", "cost_of_goods_sold", "gross_profit", "operating_income",
    "net_income", "eps", "total_assets", "current_assets",
    "cash_and_equivalents", "total_liabilities", "current_liabilities",
    "long_term_debt", "total_debt", "total_equity",
    "book_value_per_share", "shares_outstanding", "dividend_per_share",
    "operating_cash_flow", "capital_expenditures", "free_cash_flow"
}

# Fields containing negative values that need sign normalization
SIGNED_FIELDS: set = {
    "net_income", "operating_income", "revenue", "free_cash_flow",
    "operating_cash_flow"
}


def normalize_field_name(raw_name: str) -> str:
    """
    Map a raw field name to its normalized equivalent.

    Args:
        raw_name: The original field name from the data source

    Returns:
        The normalized field name, or the original if no mapping exists
    """
    if not raw_name:
        return raw_name

    # Try exact match first
    if raw_name in FIELD_MAPPINGS:
        return FIELD_MAPPINGS[raw_name]

    # Try lowercase match
    lower_name = raw_name.lower()
    if lower_name in FIELD_MAPPINGS:
        return FIELD_MAPPINGS[lower_name]

    # Try partial match (for longer field names)
    for key, value in FIELD_MAPPINGS.items():
        if key.lower() in lower_name or lower_name in key.lower():
            return value

    return raw_name


def get_possible_source_names(normalized_name: str) -> List[str]:
    """Get all possible source field names for a normalized field."""
    return REVERSE_MAPPINGS.get(normalized_name, [normalized_name])


def is_ratio_field(field_name: str) -> bool:
    """Check if a field represents a ratio (unitless)."""
    return field_name in RATIO_FIELDS


def is_absolute_field(field_name: str) -> bool:
    """Check if a field represents an absolute value (needs unit handling)."""
    return field_name in ABSOLUTE_FIELDS
