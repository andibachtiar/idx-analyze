"""
Normalization module for idx-bei financial data.

Provides tools for converting raw scraped financial data into a consistent,
normalized format suitable for analysis.
"""

from normalization.normalizer import (
    FinancialNormalizer,
    normalize_financial_metrics,
    normalize_financial_record,
)

from normalization.mappings import (
    ABSOLUTE_FIELDS,
    FIELD_MAPPINGS,
    RATIO_FIELDS,
    REVERSE_MAPPINGS,
    get_possible_source_names,
    is_absolute_field,
    is_ratio_field,
    normalize_field_name,
)

__all__ = [
    # Mappings
    'FIELD_MAPPINGS',
    'REVERSE_MAPPINGS',
    'RATIO_FIELDS',
    'ABSOLUTE_FIELDS',
    'normalize_field_name',
    'get_possible_source_names',
    'is_ratio_field',
    'is_absolute_field',
    # Normalizer
    'FinancialNormalizer',
    'normalize_financial_record',
    'normalize_financial_metrics',
]
