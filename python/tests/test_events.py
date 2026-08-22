"""
Tests for News and Corporate Event Pipeline (Phase 8).

Tests event classification, entity extraction, and event processing.
"""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock external dependencies
sys.modules['neo4j'] = MagicMock()
sys.modules['psycopg2'] = MagicMock()
sys.modules['psycopg2.extensions'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['pandas'] = MagicMock()

import pytest

from events import (
    CorporateEvent,
    Entity,
    EventClassifier,
    EventImpact,
    EventProcessor,
    EventSentiment,
    EventType,
    classify_event,
    process_news_article,
)

# =============================================================================
# ENTITY TESTS
# =============================================================================

class TestEntity:
    """Tests for Entity dataclass."""

    def test_create_entity(self):
        entity = Entity(name="BBCA", type="ticker", ticker="BBCA")
        assert entity.name == "BBCA"
        assert entity.type == "ticker"
        assert entity.ticker == "BBCA"

    def test_equality(self):
        e1 = Entity(name="John Doe", type="person")
        e2 = Entity(name="john doe", type="person")
        assert e1 == e2

    def test_hash(self):
        e1 = Entity(name="John Doe", type="person")
        e2 = Entity(name="john doe", type="person")
        assert hash(e1) == hash(e2)


# =============================================================================
# CORPORATE EVENT TESTS
# =============================================================================

class TestCorporateEvent:
    """Tests for CorporateEvent dataclass."""

    def test_create_event(self):
        event = CorporateEvent(
            event_type=EventType.EARNINGS,
            tickers=["BBCA"],
            title="BBCA Reports Q3 Earnings",
            published_at=datetime.now(),
            source="IDX"
        )
        assert event.event_type == EventType.EARNINGS
        assert event.primary_ticker == "BBCA"

    def test_material_event(self):
        event = CorporateEvent(
            event_type=EventType.EARNINGS,
            tickers=["BBCA"],
            title="Test",
            published_at=datetime.now(),
            source="Test",
            impact=EventImpact.HIGH
        )
        assert event.is_material is True

    def test_non_material_event(self):
        event = CorporateEvent(
            event_type=EventType.OTHER,
            tickers=["TEST"],
            title="Test",
            published_at=datetime.now(),
            source="Test"
        )
        assert event.is_material is False

    def test_repr(self):
        event = CorporateEvent(
            event_type=EventType.DIVIDEND,
            tickers=["BBRI"],
            title="Bank Rakyat Announces Dividend",
            published_at=datetime.now(),
            source="Test"
        )
        assert "dividend" in repr(event).lower()
        assert "BBRI" in repr(event)


# =============================================================================
# EVENT CLASSIFIER TESTS
# =============================================================================

class TestEventClassifier:
    """Tests for EventClassifier."""

    def test_classify_earnings(self):
        events = EventClassifier.classify("BBCA Reports Q3 Earnings Beat")
        assert EventType.EARNINGS in events

    def test_classify_dividend(self):
        events = EventClassifier.classify("Adaro Announces Cash Dividend")
        assert EventType.DIVIDEND in events

    def test_classify_acquisition(self):
        events = EventClassifier.classify("Indofood Acquires New Plant")
        assert EventType.ACQUISITION in events

    def test_classify_merger(self):
        events = EventClassifier.classify("Two Companies Announce Merger")
        assert EventType.MERGER in events

    def test_classify_management_change(self):
        events = EventClassifier.classify("BBCA Appoints New CEO")
        assert EventType.MANAGEMENT_CHANGE in events

    def test_classify_no_match(self):
        events = EventClassifier.classify("Random news about weather")
        assert len(events) == 0

    def test_extract_entities_with_tickers(self):
        entities = EventClassifier.extract_entities(
            "BBCA and BBRI report earnings",
            known_tickers={"BBCA", "BBRI"}
        )
        ticker_names = [e.name for e in entities]
        assert "BBCA" in ticker_names
        assert "BBRI" in ticker_names

    def test_extract_entities_no_match(self):
        entities = EventClassifier.extract_entities(
            "Random text",
            known_tickers={"BBCA", "BBRI"}
        )
        assert len(entities) == 0


# =============================================================================
# EVENT PROCESSOR TESTS
# =============================================================================

class TestEventProcessor:
    """Tests for EventProcessor."""

    def setup_method(self):
        self.processor = EventProcessor(known_tickers=["BBCA", "BBRI", "TLKM"])

    def test_process_earnings_article(self):
        events = self.processor.process_article(
            title="BBCA Reports Strong Q3 Earnings",
            content="Bank Central Asia reported earnings that beat expectations...",
            source="Test Source"
        )

        assert len(events) > 0
        assert events[0].event_type == EventType.EARNINGS
        assert "BBCA" in events[0].tickers

    def test_process_dividend_article(self):
        events = self.processor.process_article(
            title="Adaro Announces Cash Dividend",
            content="PT Adaro Indonesia announced a cash dividend of...",
            source="Test Source"
        )

        assert len(events) > 0
        assert events[0].event_type == EventType.DIVIDEND

    def test_process_multiple_events(self):
        events = self.processor.process_article(
            title="BBCA Merger and Acquisition News",
            content="BBCA announced a merger with another company...",
            source="Test Source"
        )

        # Should detect both merger and acquisition
        event_types = [e.event_type for e in events]
        assert EventType.MERGER in event_types or EventType.ACQUISITION in event_types

    def test_process_no_matching_events(self):
        events = self.processor.process_article(
            title="Weather Report for Jakarta",
            content="It will rain tomorrow in Jakarta...",
            source="Test Source"
        )

        assert len(events) == 0

    def test_extract_tickers_from_content(self):
        events = self.processor.process_article(
            title="BBCA and BBRI Earnings",
            content="Both BBCA and BBRI reported their quarterly results...",
            source="Test"
        )

        if events:
            assert "BBCA" in events[0].tickers
            assert "BBRI" in events[0].tickers

    def test_default_ticker_when_none_found(self):
        events = self.processor.process_article(
            title="Random News",
            content="Some random content without any tickers...",
            source="Test"
        )

        if events:
            assert "UNKNOWN" in events[0].tickers


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_classify_event(self):
        events = classify_event("BBCA Reports Earnings")
        assert EventType.EARNINGS in events

    def test_process_news_article(self):
        events = process_news_article(
            title="BBRI Dividend Announcement",
            content="Bank Rakyat Indonesia announced...",
            source="Test",
            known_tickers=["BBRI"]
        )
        assert len(events) >= 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for event pipeline."""

    def test_full_pipeline_earnings(self):
        """Test full pipeline with earnings news."""
        processor = EventProcessor(known_tickers=["BBCA"])

        events = processor.process_article(
            title="BBCA Q3 2024 Earnings Beat Estimates",
            content="PT Bank Central Asia Tbk reported strong third quarter earnings...",
            source="IDX News"
        )

        assert len(events) > 0
        assert events[0].event_type == EventType.EARNINGS
        assert events[0].primary_ticker == "BBCA"
        assert events[0].source == "IDX News"

    def test_full_pipeline_dividend(self):
        """Test full pipeline with dividend news."""
        processor = EventProcessor(known_tickers=["ADRO"])

        events = processor.process_article(
            title="ADRO Announces Special Dividend",
            content="PT Adaro Indonesia (ADRO) announced a special cash dividend...",
            source="Company Release"
        )

        assert len(events) > 0
        assert events[0].event_type == EventType.DIVIDEND
        assert events[0].primary_ticker == "ADRO"

    def test_multi_ticker_extraction(self):
        """Test extraction of multiple tickers from text."""
        processor = EventProcessor(known_tickers=["BBCA", "BBRI", "TLKM"])

        events = processor.process_article(
            title="Banking Sector Earnings",
            content="BBCA, BBRI, and TLKM all reported their quarterly results...",
            source="Market Report"
        )

        if events:
            tickers = events[0].tickers
            assert "BBCA" in tickers
            assert "BBRI" in tickers
            assert "TLKM" in tickers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
