"""
Research Memory Module for idx-bei investment research platform.

Provides storage and retrieval of historical research reports,
enabling thesis tracking and evolution analysis over time.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ResearchMemory:
    """
    Stores and retrieves historical research reports for thesis tracking.

    Enables questions like:
    - "What changed in BBCA since our previous analysis?"
    - "Which assumptions in our previous thesis were wrong?"
    - "How has the investment thesis evolved?"
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize research memory.

        Args:
            storage_path: Directory to store report files (default: ./data/research_memory)
        """
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "research_memory"
            )
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        # Use perf_counter for high-resolution unique identifier
        self._save_offset = time.perf_counter()

    def save_report(
        self,
        ticker: str,
        report: Any,
        question: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save a research report to memory.

        Args:
            ticker: Stock ticker symbol
            report: ResearchReport object or dict
            question: The research question asked
            metadata: Additional metadata (price, confidence, etc.)

        Returns:
            File path where report was saved
        """
        ticker_upper = ticker.upper()
        # Use high-resolution time-based unique identifier to prevent overwrites
        # Combine date timestamp with fractional seconds for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Add fractional seconds for uniqueness within the same second
        fractional = int((time.perf_counter() % 1) * 1000000)
        filename = f"{ticker_upper}_{timestamp}_{fractional:06d}.json"
        filepath = self.storage_path / filename

        # Convert report to dict if needed
        if hasattr(report, 'to_dict'):
            report_data = report.to_dict()
        elif isinstance(report, dict):
            report_data = report
        else:
            report_data = {"raw": str(report)}

        # Add metadata
        report_data["saved_at"] = datetime.now().isoformat()
        report_data["question"] = question
        if metadata:
            report_data["metadata"] = metadata

        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)

        return str(filepath)

    def get_reports_for_ticker(
        self,
        ticker: str,
        limit: Optional[int] = None,
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        Get all saved reports for a ticker.

        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of reports to return
            sort_order: "asc" or "desc" (by date)

        Returns:
            List of report dictionaries
        """
        ticker_upper = ticker.upper()
        reports = []

        if not self.storage_path.exists():
            return reports

        for filepath in self.storage_path.glob(f"{ticker_upper}_*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    report["_file"] = str(filepath)
                    reports.append(report)
            except (json.JSONDecodeError, IOError):
                continue

        # Sort by saved_at
        reports.sort(
            key=lambda x: x.get("saved_at", ""),
            reverse=(sort_order == "desc")
        )

        if limit:
            reports = reports[:limit]

        return reports

    def get_latest_report(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent report for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Latest report dict or None if not found
        """
        reports = self.get_reports_for_ticker(ticker, limit=1)
        return reports[0] if reports else None

    def compare_theses(
        self,
        ticker: str,
        max_comparisons: int = 3
    ) -> Dict[str, Any]:
        """
        Compare multiple past theses for a ticker.

        Args:
            ticker: Stock ticker symbol
            max_comparisons: Maximum number of reports to compare

        Returns:
            Dictionary with comparison results
        """
        reports = self.get_reports_for_ticker(ticker, limit=max_comparisons)

        if len(reports) < 2:
            return {
                "ticker": ticker,
                "comparisons": [],
                "notes": "Insufficient reports for comparison"
            }

        comparisons = []
        for i in range(len(reports) - 1):
            current = reports[i]
            previous = reports[i + 1]

            comparison = self._compare_two_reports(current, previous)
            comparisons.append(comparison)

        return {
            "ticker": ticker,
            "reports_analyzed": len(reports),
            "comparisons": comparisons,
        }

    def _compare_two_reports(
        self,
        current: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two reports and identify changes."""
        return {
            "current_date": current.get("saved_at", "Unknown"),
            "previous_date": previous.get("saved_at", "Unknown"),
            "question_changed": current.get("question") != previous.get("question"),
            "confidence_change": self._calculate_confidence_change(current, previous),
            "verdict_change": self._check_verdict_change(current, previous),
            "key_changes": self._identify_key_changes(current, previous),
        }

    def _calculate_confidence_change(
        self,
        current: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate confidence score change."""
        current_conf = current.get("confidence_score", 0)
        previous_conf = previous.get("confidence_score", 0)

        return {
            "current": current_conf,
            "previous": previous_conf,
            "change": current_conf - previous_conf,
            "direction": "increased" if current_conf > previous_conf else
                        "decreased" if current_conf < previous_conf else "unchanged"
        }

    def _check_verdict_change(
        self,
        current: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if overall verdict changed."""
        current_verdict = current.get("overall_verdict", "")
        previous_verdict = previous.get("overall_verdict", "")

        return {
            "current_verdict": current_verdict,
            "previous_verdict": previous_verdict,
            "changed": current_verdict != previous_verdict
        }

    def _identify_key_changes(
        self,
        current: Dict[str, Any],
        previous: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify key changes between reports."""
        changes = []

        # Compare claim types
        current_claims = current.get("claim_summary", {})
        previous_claims = previous.get("claim_summary", {})

        for claim_type in ["FACT", "INTERPRETATION", "ASSUMPTION", "SPECULATION"]:
            current_count = current_claims.get(claim_type, 0)
            previous_count = previous_claims.get(claim_type, 0)

            if current_count != previous_count:
                changes.append({
                    "type": claim_type,
                    "previous": previous_count,
                    "current": current_count,
                    "change": current_count - previous_count
                })

        return changes

    def delete_report(self, ticker: str, filename: Optional[str] = None) -> bool:
        """
        Delete a specific report.

        Args:
            ticker: Stock ticker symbol
            filename: Specific filename to delete (if None, deletes all for ticker)

        Returns:
            True if deleted, False otherwise
        """
        ticker_upper = ticker.upper()

        if filename:
            filepath = self.storage_path / filename
            if filepath.exists():
                filepath.unlink()
                return True
            return False

        # Delete all reports for ticker
        deleted = False
        for filepath in self.storage_path.glob(f"{ticker_upper}_*.json"):
            filepath.unlink()
            deleted = True

        return deleted

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored reports.

        Returns:
            Dictionary with usage statistics
        """
        if not self.storage_path.exists():
            return {"total_reports": 0, "tickers": []}

        ticker_counts: Dict[str, int] = {}
        total = 0

        for filepath in self.storage_path.glob("*.json"):
            total += 1
            # Extract ticker from filename
            parts = filepath.stem.split("_")
            if parts:
                ticker = parts[0]
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

        return {
            "total_reports": total,
            "unique_tickers": len(ticker_counts),
            "tickers": ticker_counts,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def save_research_report(
    ticker: str,
    report: Any,
    question: str = "",
    storage_path: Optional[str] = None,
) -> str:
    """
    Convenience function to save a research report.

    Args:
        ticker: Stock ticker symbol
        report: ResearchReport object or dict
        question: The research question
        storage_path: Optional custom storage path

    Returns:
        File path where report was saved
    """
    memory = ResearchMemory(storage_path=storage_path)
    return memory.save_report(ticker, report, question)


def get_research_history(
    ticker: str,
    limit: Optional[int] = None,
    storage_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Convenience function to get research history for a ticker.

    Args:
        ticker: Stock ticker symbol
        limit: Maximum number of reports
        storage_path: Optional custom storage path

    Returns:
        List of report dictionaries
    """
    memory = ResearchMemory(storage_path=storage_path)
    return memory.get_reports_for_ticker(ticker, limit)


def compare_research_theses(
    ticker: str,
    max_comparisons: int = 3,
    storage_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to compare past theses.

    Args:
        ticker: Stock ticker symbol
        max_comparisons: Maximum reports to compare
        storage_path: Optional custom storage path

    Returns:
        Comparison results
    """
    memory = ResearchMemory(storage_path=storage_path)
    return memory.compare_theses(ticker, max_comparisons)
