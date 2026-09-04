"""
Events module for idx-bei investment research platform.

This module provides models and processing for corporate events
including earnings, dividends, M&A, management changes, and other
material events affecting Indonesian stocks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EventType(Enum):
    """Types of corporate events."""
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    CAPITAL_RAISE = "capital_raise"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    MANAGEMENT_CHANGE = "management_change"
    REGULATORY = "regulatory"
    NEW_CONTRACT = "new_contract"
    EXPANSION = "expansion"
    OTHER = "other"


class EventImpact(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEUTRAL = "neutral"


class EventSentiment(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class Entity:
    name: str
    type: str
    ticker: Optional[str] = None

    def __hash__(self) -> int:
        return hash((self.name.lower(), self.type))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.name.lower() == other.name.lower() and self.type == other.type


@dataclass
class CorporateEvent:
    event_type: EventType
    tickers: List[str]
    title: str
    published_at: datetime
    source: str
    description: Optional[str] = None
    url: Optional[str] = None
    sentiment: Optional[EventSentiment] = None
    confidence: Optional[float] = None
    impact: Optional[EventImpact] = None
    entities: List[Entity] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed_at: datetime = field(default_factory=datetime.now)

    @property
    def primary_ticker(self) -> Optional[str]:
        return self.tickers[0] if self.tickers else None

    @property
    def is_material(self) -> bool:
        return (
            self.impact == EventImpact.HIGH or
            self.sentiment in (EventSentiment.POSITIVE, EventSentiment.NEGATIVE)
        )

    def __repr__(self) -> str:
        tickers = ",".join(self.tickers) if self.tickers else "unknown"
        return f"CorporateEvent({self.event_type.value}: {self.title[:50]}... [{tickers}])"


class EventClassifier:
    """Classifies news articles into event types using rule-based extraction."""

    KEYWORDS = {
        EventType.EARNINGS: ["laba rugi", "earnings", "report keuangan", "EPS", "pendapatan", "revenue", "profit"],
        EventType.DIVIDEND: ["dividen", "dividend", "pembagian laba"],
        EventType.ACQUISITION: ["akuisisi", "acquisition", "pengambilalihan", "acqui"],
        EventType.MERGER: ["merger", "gabungan", "consolidasi"],
        EventType.MANAGEMENT_CHANGE: ["direktur", "komisaris", "CEO", "CFO", "resign"],
        EventType.NEW_CONTRACT: ["kontrak", "contract", "kerja sama"],
        EventType.REGULATORY: ["regulasi", "OJK", "izin"],
    }

    @classmethod
    def classify(cls, title: str, content: str = "") -> List[EventType]:
        """Classify text into event types based on keywords."""
        text = f"{title} {content}".lower()
        matches = []

        for event_type, keywords in cls.KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    if event_type not in matches:
                        matches.append(event_type)
                    break

        return matches

    @classmethod
    def extract_entities(cls, text: str, known_tickers: Optional[set] = None) -> List[Entity]:
        """Extract entities from text."""
        entities = []
        text_upper = text.upper()

        if known_tickers:
            for ticker in known_tickers:
                if ticker in text_upper:
                    entities.append(Entity(name=ticker, type="ticker", ticker=ticker))

        return entities


class EventProcessor:
    """Processes raw news/data into structured CorporateEvent objects."""

    def __init__(self, known_tickers: Optional[List[str]] = None):
        self.known_tickers = set(ticker.upper() for ticker in known_tickers or [])
        self.classifier = EventClassifier()

    def process_article(
        self,
        title: str,
        content: str,
        source: str,
        published_at: Optional[datetime] = None,
        url: Optional[str] = None
    ) -> List[CorporateEvent]:
        """Process a news article into events."""
        if published_at is None:
            published_at = datetime.now()

        event_types = self.classifier.classify(title, content)
        entities = self.classifier.extract_entities(f"{title} {content}", self.known_tickers)
        tickers = [e.ticker for e in entities if e.ticker]

        if not tickers:
            text_upper = f"{title} {content}".upper()
            tickers = [t for t in self.known_tickers if t in text_upper]

        if not tickers:
            tickers = ["UNKNOWN"]

        events = []
        for event_type in event_types:
            event = CorporateEvent(
                event_type=event_type,
                tickers=tickers,
                title=title,
                published_at=published_at,
                source=source,
                url=url,
                entities=entities
            )
            events.append(event)

        return events


def classify_event(title: str, content: str = "") -> List[EventType]:
    """Quick function to classify an event."""
    return EventClassifier.classify(title, content)


def process_news_article(
    title: str,
    content: str,
    source: str,
    known_tickers: Optional[List[str]] = None,
    **kwargs
) -> List[CorporateEvent]:
    """Quick function to process a news article into events."""
    processor = EventProcessor(known_tickers=known_tickers)
    return processor.process_article(title, content, source, **kwargs)


def event_to_dict(event: CorporateEvent) -> Dict[str, Any]:
    """Serialize a CorporateEvent into a plain dict for the API."""
    return {
        "event_type": event.event_type.value if event.event_type else None,
        "tickers": event.tickers,
        "primary_ticker": event.primary_ticker,
        "title": event.title,
        "published_at": event.published_at.isoformat() if event.published_at else None,
        "source": event.source,
        "description": event.description,
        "url": event.url,
        "sentiment": event.sentiment.value if event.sentiment else None,
        "confidence": event.confidence,
        "impact": event.impact.value if event.impact else None,
        "entities": [{"name": e.name, "type": e.type, "ticker": e.ticker} for e in event.entities],
        "is_material": event.is_material,
    }


def classif_news_records(news: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Classify a list of news dicts (from DB) into serialized CorporateEvents.

    Each news dict should contain title/content/source/published_at/url/ticker.
    Uses EventProcessor to detect event types; returns one event per detected
    type (skipping articles with no matching event type).
    """
    known_tickers = [n.get("ticker") for n in news if n.get("ticker")]
    processor = EventProcessor(known_tickers=known_tickers)
    events: List[Dict[str, Any]] = []
    for item in news:
        title = item.get("title") or ""
        content = item.get("content") or ""
        published = item.get("published_at")
        if isinstance(published, str):
            try:
                from datetime import datetime as _dt
                published = _dt.fromisoformat(published)
            except ValueError:
                published = None
        processed = processor.process_article(
            title,
            content,
            item.get("source") or "IDX",
            published_at=published,
            url=item.get("url"),
        )
        for ev in processed:
            events.append(event_to_dict(ev))
    return events
