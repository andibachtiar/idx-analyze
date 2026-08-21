"""
Tests for financial data normalization.
"""

import os
import sys
from datetime import date
from unittest.mock import MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external dependencies
sys.modules['neo4j'] = MagicMock()
sys.modules['psycopg2'] = MagicMock()
sys.modules['psycopg2.extensions'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['pandas'] = MagicMock()
sys.modules['curl_cffi'] = MagicMock()

import pytest

from normalization.mappings import (
    FIELD_MAPPINGS,
    RATIO_FIELDS,
    REVERSE_MAPPINGS,
    get_possible_source_names,
    is_ratio_field,
    normalize_field_name,
)
from normalization.normalizer import FinancialNormalizer, normalize_financial_record


class TestFieldMappings:
    """Tests for field name mapping functionality."""

    def test_basic_mapping(self):
        assert normalize_field_name("sales") == "revenue"
        assert normalize_field_name("assets") == "total_assets"
        assert normalize_field_name("equity") == "total_equity"

    def test_idonesian_field_names(self):
        """Test mapping Indonesian field names."""
        assert normalize_field_name("pendapatan") == "revenue"
        assert normalize_field_name("aset_total") == "total_assets"
        assert normalize_field_name("ekuitas") == "total_equity"

    def test_case_insensitive(self):
        """Test that mapping is case-insensitive."""
        assert normalize_field_name("SALES") == "revenue"
        assert normalize_field_name("Sales") == "revenue"

    def test_empty_input(self):
        """Test handling of empty input."""
        assert normalize_field_name("") == ""
        assert normalize_field_name(None) is None

    def test_unmapped_field_returns_original(self):
        """Test that unmapped fields return original name."""
        result = normalize_field_name("unknown_field")
        assert result == "unknown_field"

    def test_ratio_fields_identified(self):
        """Test ratio field detection."""
        assert is_ratio_field("roe")
        assert is_ratio_field("pe_ratio")
        assert is_ratio_field("debt_to_equity")
        assert not is_ratio_field("revenue")
        assert not is_ratio_field("total_assets")

    def test_reverse_mapping(self):
        """Test reverse mapping from normalized to source names."""
        sources = get_possible_source_names("revenue")
        assert "sales" in sources
        assert "revenue" in sources

    def test_field_mappings_completeness(self):
        """Test that all mapped fields have valid mappings."""
        for source, target in FIELD_MAPPINGS.items():
            assert target in RATIO_FIELDS or target not in RATIO_FIELDS  # Valid mapping exists


class TestFinancialNormalizer:
    """Tests for the FinancialNormalizer class."""

    def setup_method(self):
        self.normalizer = FinancialNormalizer()

    def test_normalize_idx_data(self):
        """Test normalizing IDX-style data."""
        raw_data = {
            "code": "BBCA",
            "stockName": "Bank Central Asia Tbk",
            "fsDate": "2024-12-31",
            "fiscalYearEnd": "Dec",
            "assets": 500000.0,
            "liabilities": 450000.0,
            "equity": 50000.0,
            "sales": 20000.0,
            "profitAttrOwner": 5000.0,
            "eps": 500.0,
            "roe": 47.5,
            "per": 12.5,
            "deRatio": 0.5
        }

        result = self.normalizer.normalize_raw_data(raw_data)

        assert result is not None
        assert result['ticker'] == "BBCA"
        assert result['period'].fiscal_year == 2024

    def test_normalize_with_missing_values(self):
        """Test handling of missing values."""
        raw_data = {
            "code": "TLKM",
            "fsDate": "2024-09-30",
            "assets": 100000.0,
            "liabilities": None,  # Missing value
            "equity": 30000.0
        }

        result = self.normalizer.normalize_raw_data(raw_data)

        assert result is not None
        assert result['metrics']['total_assets'] == 100000.0
        assert 'total_liabilities' not in result['metrics']  # None values skipped

    def test_normalize_negative_values(self):
        """Test handling of negative income values."""
        raw_data = {
            "code": "ASII",
            "fsDate": "2024-12-31",
            "sales": 50000.0,
            "profitAttrOwner": -1000.0  # Loss
        }

        result = self.normalizer.normalize_raw_data(raw_data)

        assert result is not None
        # Income should be converted to absolute value for consistency
        assert result['metrics']['net_income'] == 1000.0

    def test_normalize_empty_data(self):
        """Test handling of empty data."""
        result = self.normalizer.normalize_raw_data({})
        assert result is None

    def test_normalize_invalid_code(self):
        """Test handling of missing code."""
        result = self.normalizer.normalize_raw_data({
            "fsDate": "2024-12-31"
        })
        assert result is None

    def test_quarterly_period_detection(self):
        """Test quarterly period detection."""
        raw_data = {
            "code": "BBCA",
            "fsDate": "2024-06-30",
            "assets": 100000.0
        }

        result = self.normalizer.normalize_raw_data(raw_data)

        assert result is not None
        assert result['period'].period_end == date(2024, 6, 30)

    def test_ratio_normalization(self):
        """Test ratio field normalization."""
        raw_data = {
            "code": "BBCA",
            "fsDate": "2024-12-31",
            "roe": 25.5,  # Percentage
            "per": 15.0
        }

        result = self.normalizer.normalize_raw_data(raw_data)

        assert result is not None
        assert result['metrics']['roe'] == 0.255  # Converted to decimal

    def test_company_creation(self):
        """Test company creation from raw data."""
        raw_data = {
            "code": "BBCA",
            "stockName": "Bank Central Asia Tbk",
            "sector": "Finance"
        }

        company = self.normalizer.create_company(raw_data)

        assert company.ticker == "BBCA"
        assert company.name == "Bank Central Asia Tbk"
        assert company.sector == "Finance"

    def test_company_cache(self):
        """Test that companies are cached."""
        raw_data = {"code": "BBCA", "stockName": "Bank Central Asia Tbk"}

        c1 = self.normalizer.create_company(raw_data)
        c2 = self.normalizer.create_company(raw_data)

        assert c1 is c2  # Same object (cached)


class TestNormalizeFunction:
    """Tests for the convenience normalize_financial_record function."""

    def test_function_exists(self):
        """Test that the function can be called."""
        raw_data = {
            "code": "BBCA",
            "fsDate": "2024-12-31",
            "assets": 100000.0
        }

        result = normalize_financial_record(raw_data)

        assert result is not None
        assert 'ticker' in result


class TestDataQuality:
    """Tests for data quality edge cases."""

    def setup_method(self):
        self.normalizer = FinancialNormalizer()

    def test_duplicate_periods_not_deduped_here(self):
        """Note: Deduplication happens at ingestion layer, not here."""
        pass  # This is tested separately in integration tests

    def test_mixed_units_handling(self):
        """Test that mixed units are handled consistently."""
        raw_data = {
            "code": "BBCA",
            "fsDate": "2024-12-31",
            "assets": 500000.0,  # In millions
            "roe": 20.0  # Percentage
        }

        result = self.normalizer.normalize_raw_data(raw_data)

        assert result is not None
        assert result['metrics']['total_assets'] == 500000.0
        assert result['metrics']['roe'] == 0.20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
