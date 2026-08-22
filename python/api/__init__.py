"""
API module for idx-bei investment research platform.

Provides FastAPI REST API and web interface.
"""

from .main import app
from .schemas import (
    BacktestRequest,
    DocumentSearchRequest,
    ScreeningRequest,
    StockAnalysisRequest,
    StockComparisonRequest,
    ThesisValidationRequest,
)

__all__ = [
    "app",
    "StockAnalysisRequest",
    "StockComparisonRequest",
    "ScreeningRequest",
    "BacktestRequest",
    "DocumentSearchRequest",
    "ThesisValidationRequest",
]
