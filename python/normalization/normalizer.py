"""
Financial data normalizer.

Handles the conversion of raw scraped financial data into normalized
format consistent across all sources.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from models import Company, FinancialMetrics, FinancialPeriod, PeriodType, Source, Unit
from normalization.mappings import FIELD_MAPPINGS, RATIO_FIELDS, normalize_field_name

logger = logging.getLogger(__name__)


class FinancialNormalizer:
    """
    Normalizes raw financial data from various sources into a consistent format.
    """

    # Common unit multipliers (relative to base unit)
    UNIT_MULTIPLIERS = {
        Unit.THOUSANDS: 1_000,
        Unit.MILLIONS: 1_000_000,
        Unit.BILLIONS: 1_000_000_000,
    }

    def __init__(self):
        self._company_cache: Dict[str, Company] = {}
        self._period_cache: Dict[tuple, FinancialPeriod] = {}

    def normalize_raw_data(
        self,
        raw_data: Dict[str, Any],
        source: Source = Source.IDX,
        default_unit: Unit = Unit.MILLIONS
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize a single raw financial record.

        Args:
            raw_data: Raw dictionary from scraper
            source: Data source
            default_unit: Default unit for absolute values

        Returns:
            Normalized dictionary or None if critical data is missing
        """
        if not raw_data or not raw_data.get('code'):
            logger.warning("Empty or invalid raw data")
            return None

        ticker = raw_data['code'].upper()

        # Extract period information
        period = self._extract_period(raw_data)

        # Normalize field names and values
        normalized = self._normalize_fields(raw_data, source, default_unit)

        if not normalized:
            logger.warning(f"Could not normalize any fields for {ticker}")
            return None

        return {
            'ticker': ticker,
            'period': period,
            'metrics': normalized,
            'source': source.value,
            'ingested_at': str(date.today())
        }

    def _extract_period(self, raw_data: Dict[str, Any]) -> FinancialPeriod:
        """Extract and normalize period information from raw data."""
        fs_date = raw_data.get('fsDate') or raw_data.get('fs_date')

        period_end = None
        if fs_date:
            if isinstance(fs_date, str):
                try:
                    period_end = date.fromisoformat(fs_date[:10])
                except (ValueError, TypeError):
                    pass

        fiscal_year_end = raw_data.get('fiscalYearEnd', 'Dec')
        fiscal_year = period_end.year if period_end else None

        # Determine if quarterly or annual
        period_type = PeriodType.ANNUAL
        fiscal_period = None

        if period_end:
            month = period_end.month
            # Quarterly periods in Indonesia are typically Mar, Jun, Sep, Dec
            if month in (3, 6, 9, 12):
                period_type = PeriodType.QUARTERLY
                if month <= 3:
                    fiscal_period = 1
                elif month <= 6:
                    fiscal_period = 2
                elif month <= 9:
                    fiscal_period = 3
                else:
                    fiscal_period = 4

        return FinancialPeriod(
            ticker=raw_data.get('code', '').upper(),
            period_end=period_end,
            period_type=period_type,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            source=Source.IDX
        )

    def _normalize_fields(
        self,
        raw_data: Dict[str, Any],
        source: Source,
        default_unit: Unit
    ) -> Optional[Dict[str, Any]]:
        """Normalize field names and values from raw data."""
        normalized = {}

        for raw_key, value in raw_data.items():
            # Skip non-financial fields
            if raw_key in ('code', 'stockName', 'sector', 'subSector', 'industry',
                          'fsDate', 'fiscalYearEnd', 'sharia', 'audit', 'opini'):
                continue

            if value is None:
                continue

            # Normalize field name
            norm_key = normalize_field_name(raw_key)

            # Skip if we can't map it
            if not norm_key or norm_key == raw_key and raw_key not in RATIO_FIELDS:
                logger.debug(f"Unmapped field: {raw_key} -> {norm_key}")
                continue

            # Normalize value
            normalized_value = self._normalize_value(value, norm_key, default_unit)

            if normalized_value is not None:
                normalized[norm_key] = normalized_value

        return normalized if normalized else None

    def _normalize_value(
        self,
        value: Any,
        field_name: str,
        default_unit: Unit
    ) -> Optional[float]:
        """
        Normalize a single value based on its field type.

        - Ratio fields: return as-is (already unitless)
        - Absolute fields: validate and return
        - Handle sign issues for income/statement items
        """
        try:
            # Convert to float
            num_value = float(value)
        except (ValueError, TypeError):
            logger.debug(f"Cannot convert {value} to float for {field_name}")
            return None

        # Skip zero or NaN
        if num_value is None or (isinstance(num_value, float) and num_value != num_value):
            return None

        # For ratio fields, convert percentage to decimal
        if field_name in RATIO_FIELDS:
            # Indonesian financial data typically uses percentages (e.g., 25.5 for 25.5%)
            # Convert to decimal (e.g., 0.255)
            if abs(num_value) >= 1:
                # Assume it's a percentage, convert to decimal
                return num_value / 100
            return num_value

        # For absolute fields, apply unit conversion
        # Indonesian financial statements typically in millions
        multiplier = self.UNIT_MULTIPLIERS.get(default_unit, 1)

        # Normalize sign for income statement items
        if field_name in ('net_income', 'operating_income', 'revenue'):
            # Ensure positive values (some sources use negative for losses)
            num_value = abs(num_value)

        return num_value

    def create_company(self, raw_data: Dict[str, Any]) -> Company:
        """Create or update a Company from raw data."""
        ticker = raw_data.get('code', '').upper()
        if not ticker:
            raise ValueError("Company code is required")

        if ticker in self._company_cache:
            return self._company_cache[ticker]

        # Extract company details from raw data
        company = Company(
            ticker=ticker,
            name=raw_data.get('stockName', '') or raw_data.get('NamaEmiten', ''),
            sector=raw_data.get('sector', '') or raw_data.get('Sektor', ''),
            sub_sector=raw_data.get('subSector', '') or raw_data.get('SubSektor', ''),
            industry=raw_data.get('industry', '') or raw_data.get('Industri', ''),
            board=raw_data.get('papan', '') or raw_data.get('PapanPencatatan', '')
        )

        self._company_cache[ticker] = company
        return company


def normalize_financial_record(
    raw_data: Dict[str, Any],
    source: Source = Source.IDX,
    default_unit: Unit = Unit.MILLIONS
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to normalize a single financial record.

    Args:
        raw_data: Raw financial data dictionary
        source: Data source
        default_unit: Default unit for absolute values

    Returns:
        Normalized data dictionary or None
    """
    normalizer = FinancialNormalizer()
    return normalizer.normalize_raw_data(raw_data, source, default_unit)


def normalize_financial_metrics(
    raw_metrics: Dict[str, Any],
    target_fields: List[str]
) -> FinancialMetrics:
    """
    Normalize a dictionary of financial metrics into a FinancialMetrics object.

    Args:
        raw_metrics: Dictionary of raw metric values
        target_fields: List of normalized field names to extract

    Returns:
        FinancialMetrics object with normalized values
    """
    metrics = FinancialMetrics()

    for field_name in target_fields:
        # Find matching raw field
        possible_names = FIELD_MAPPINGS.get(field_name, [field_name])
        for name in possible_names:
            if name in raw_metrics:
                value = raw_metrics[name]
                if value is not None:
                    try:
                        setattr(metrics, field_name, float(value))
                        break
                    except (ValueError, TypeError):
                        continue

    return metrics
