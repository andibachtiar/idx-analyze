"""
Enrich news_articles with deterministic sector/ticker impact tags (Fase B3).

Takes general/macro news (ticker may be NULL) and tags each article with the
industry sector(s) likely affected and the direction (positive/negative), using
a curated keyword lexicon. Because broad macro news rarely names a ticker, we
also expand a sector-level hit to the companies in that sector (via the
``companies.sector`` column) so the UI can show "which stocks may be affected".

This is purely deterministic. The LLM may later interpret these tags but must
not invent the likelihood/direction mapping — that lives in ``IMPACT_RULES``.

Usage:
    uv run python enrich_news_impacts.py                 # process all news (idempotent, sector-level)
    uv run python enrich_news_impacts.py --limit 100     # only first 100 (testing)
    uv run python enrich_news_impacts.py --expand        # also materialize one row per company in the sector
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from typing import Any

from database.scraper_store import ScraperDatabase

# =============================================================================
# IMMEDIATE: keyword -> (sector, direction) deterministic lexicon.
# Phrases are matched case-insensitively against title + content.
# Direction is per (sector, driver) because the same driver can help one sector
# and hurt another (e.g. "suku bunga naik" -> Keuangan positive, Properti negative).
# =============================================================================

IMPACT_RULES: list[tuple[str, str, list[str]]] = [
    # --- Energy ---
    ("Energi", "positive", [
        "harga minyak naik", "harga minyak dunia naik", "harga brent naik",
        "harga batubara naik", "harga batu bara naik", "harga gas naik",
        "opec sepakat", "produksi minyak turun", "harga batu bara naik",
    ]),
    ("Energi", "negative", [
        "harga minyak turun", "harga minyak dunia turun", "harga brent turun",
        "harga batubara turun", "harga batu bara turun", "harga gas turun",
        "produksi minyak naik",
    ]),
    # --- Financials ---
    ("Keuangan", "positive", [
        "suku bunga naik", "suku bunga acuan naik", "menaikkan suku bunga",
        "kenaikan suku bunga", "naikkan suku bunga", "bi naikkan suku bunga",
        "bi rate naik", "net interest margin", "kredit naik", "laba bank naik",
        "suku bunga dinaikkan", "acuan dinaikkan",
    ]),
    ("Keuangan", "negative", [
        "suku bunga turun", "suku bunga acuan turun", "menurunkan suku bunga",
        "penurunan suku bunga", "bi turunkan suku bunga", "bi rate turun",
        "suku bunga diturunkan", "kredit macet", "npl naik", "non performing loan naik",
    ]),
    # --- Basic Materials (commodities) ---
    ("Barang Baku", "positive", [
        "harga nikel naik", "harga timah naik", "harga emas naik",
        "harga tembaga naik", "harga aluminium naik", "harga kopi naik",
        "harga crude palm oil naik", "kenaikan harga emas",
    ]),
    ("Barang Baku", "negative", [
        "harga nikel turun", "harga timah turun", "harga emas turun",
        "harga tembaga turun", "harga kopi turun",
    ]),
    # --- Property ---
    ("Properti & Real Estat", "positive", [
        "suku bunga turun", "suku bunga acuan turun", "menurunkan suku bunga",
        "penurunan suku bunga", "bi turunkan suku bunga", "penjualan properti naik",
        "permintaan properti naik", "insentif properti", "bunga kpr turun",
    ]),
    ("Properti & Real Estat", "negative", [
        "suku bunga naik", "suku bunga acuan naik", "menaikkan suku bunga",
        "kenaikan suku bunga", "bi naikkan suku bunga", "bunga kpr naik",
        "over supply properti", "penjualan properti turun",
    ]),
    # --- Consumer (staples) ---
    ("Barang Konsumen Primer", "positive", [
        "harga pangan turun", "harga beras turun", "harga minyak goreng turun",
        "inflasi pangan turun",
    ]),
    ("Barang Konsumen Primer", "negative", [
        "harga pangan naik", "harga beras naik", "harga minyak goreng naik",
        "inflasi pangan naik",
    ]),
    # --- Consumer (discretionary) ---
    ("Barang Konsumen Non-Primer", "positive", [
        "daya beli naik", "konsumsi masyarakat naik", "gaji naik",
        "penjualan ritel naik", "penjualan e-commerce naik",
    ]),
    ("Barang Konsumen Non-Primer", "negative", [
        "daya beli turun", "inflasi tinggi", "konsumsi turun",
        "phk masal", "pengangguran naik", "penjualan ritel turun",
    ]),
    # --- Infrastructure ---
    ("Infrastruktur", "positive", [
        "kontrak infrastruktur", "anggaran infrastruktur naik", "proyek tol",
        "proyek pln", "pembangunan infrastruktur", "belanja negara naik",
    ]),
    ("Infrastruktur", "negative", [
        "anggaran infrastruktur dipotong", "proyek ditunda", "pembangunan ditunda",
    ]),
    # --- Transportation & Logistics ---
    ("Transportasi & Logistik", "positive", [
        "volume kargo naik", "penumpang naik", "biaya logistik turun",
        "harga bbm turun",
    ]),
    ("Transportasi & Logistik", "negative", [
        "volume kargo turun", "penumpang turun", "harga bbm naik",
    ]),
    # --- Technology ---
    ("Teknologi", "positive", [
        "digitalisasi", "adopsi digital naik", "investasi teknologi",
        "data center", "kecerdasan buatan",
    ]),
    ("Teknologi", "negative", ["investasi teknologi turun", "regulasi teknologi ketat"]),
    # --- Healthcare ---
    ("Kesehatan", "positive", [
        "anggaran kesehatan naik", "rumah sakit", "vaksinasi", "obat",
    ]),
    ("Kesehatan", "negative", ["anggaran kesehatan dipotong"]),
    # --- Industrials ---
    ("Perindustrian", "positive", [
        "pmi naik", "ekspor manufaktur naik", "pesanan naik", "pabrik baru",
    ]),
    ("Perindustrian", "negative", [
        "pmi turun", "ekspor manufaktur turun", "pesanan turun",
        "permintaan baja turun", "smelter ditunda", "banjir baja", "tarif impor",
    ]),
    # --- Telecommunication ---
    ("Teknologi", "positive", [
        "adopsi 5g", "pelanggan seluler naik", "penetrasi internet naik",
        "data center", "cloud naik", "kecerdasan buatan", "digitalisasi",
    ]),
    # --- Utilities (power/EBT) ---
    ("Utilitas", "positive", [
        "tarif listrik naik", "penjualan listrik naik", "proyek pembangkit",
        "energi terbarukan", "ebt", "panel surya", "kapasitas listrik naik",
    ]),
    ("Utilitas", "negative", [
        "tarif listrik turun", "permintaan listrik turun", "pembangkit ditunda",
        "subsidi listrik dipotong",
    ]),
    # --- Healthcare additions ---
    ("Kesehatan", "positive", [
        "bpjs naik", "anggaran kesehatan naik", "alat kesehatan", "obat generik",
        "rumah sakit baru", "proyek rumah sakit",
    ]),
    ("Kesehatan", "negative", [
        "harga obat turun", "regulasi obat ketat", "alat kesehatan dipangkas",
        "tarif bpjs dipotong",
    ]),
    # --- Consumer discretionary additions ---
    ("Barang Konsumen Non-Primer", "positive", [
        "pariwisata naik", "travel naik", "okupansi hotel naik",
        "penjualan ritel naik", "penjualan e-commerce naik",
    ]),
    ("Barang Konsumen Non-Primer", "negative", [
        "okupansi hotel turun", "travel turun", "pariwisata turun",
    ]),
    # --- Consumer staples (pangan) additions ---
    ("Barang Konsumen Primer", "positive", [
        "panen raya", "pasokan pangan naik", "impor pangan turun",
        "harga pangan turun", "harga beras turun", "harga minyak goreng turun",
    ]),
    ("Barang Konsumen Primer", "negative", [
        "gagal panen", "el nino", "pasokan pangan turun", "harga pangan naik",
        "harga beras naik", "harga minyak goreng naik", "inflasi pangan naik",
    ]),
    # --- Basic Materials additions (mining/pupuk) ---
    ("Barang Baku", "positive", [
        "harga pupuk naik", "pupuk naik", "harga baja naik", "baja naik",
        "harga lpg naik", "harga nikel naik", "nikel naik", "harga timah naik",
        "timah naik", "harga tembaga naik", "tembaga naik", "harga emas naik",
        "emas naik", "harga cpo naik", "cpo naik", "harga crude palm oil naik",
    ]),
    ("Barang Baku", "negative", [
        "harga pupuk turun", "pupuk turun", "harga baja turun", "baja turun",
        "harga lpg turun", "harga nikel turun", "nikel turun", "harga timah turun",
        "timah turun", "harga emas turun", "emas turun", "harga tembaga turun",
        "tembaga turun", "harga cpo turun", "cpo turun",
    ]),
]


def compile_rules() -> list[tuple[str, str, list[tuple[str, re.Pattern]]]]:
    """Pre-compile keyword phrases into case-insensitive regex patterns.

    Each entry keeps the original phrase alongside its compiled pattern so matches
    can be reported with the raw keyword (not the escaped regex).
    """
    compiled = []
    for sector, direction, keywords in IMPACT_RULES:
        patterns = []
        for kw in keywords:
            patterns.append((kw, re.compile(re.escape(kw), re.IGNORECASE)))
        compiled.append((sector, direction, patterns))
    return compiled


_RULES = compile_rules()


def detect_impacts(text: str) -> list[dict[str, Any]]:
    """Return deterministic sector/direction impacts for a piece of text.

    Each result: ``{sector, direction, confidence, matched_keywords}``. Confidence
    is derived from the number of distinct matching phrases (deterministic), so
    an article that hits more signals gets a higher score.
    """
    if not text:
        return []
    lowered = text.lower()
    hits: dict[tuple[str, str], list[str]] = {}
    for sector, direction, patterns in _RULES:
        matched = []
        for phrase, pattern in patterns:
            if pattern.search(lowered):
                matched.append(phrase)
        if matched:
            hits.setdefault((sector, direction), []).extend(matched)

    impacts: list[dict[str, Any]] = []
    for (sector, direction), keywords in hits.items():
        # Deterministic confidence: base 0.6 + 0.1 per extra signal, capped at 0.95.
        n = len(set(keywords))
        confidence = round(min(0.95, 0.6 + 0.1 * (n - 1)), 4)
        impacts.append({
            "sector": sector,
            "direction": direction,
            "confidence": confidence,
            "matched_keywords": list(dict.fromkeys(keywords)),
        })
    return impacts


def build_sector_ticker_map() -> dict[str, list[str]]:
    """Return ``{sector: [tickers]}`` from the companies table."""
    with ScraperDatabase() as store:
        store._ensure_connection()
        assert store.connection is not None
        with store.connection.cursor() as cursor:
            cursor.execute("SELECT ticker, sector FROM companies WHERE sector IS NOT NULL")
            rows = cursor.fetchall()
    mapping: dict[str, list[str]] = defaultdict(list)
    for ticker, sector in rows:
        mapping[sector].append(ticker)
    return dict(mapping)


def _impact_rows(
    news_id: int,
    impact: dict[str, Any],
    article_ticker: str | None,
    sector_tickers: dict[str, list[str]],
    expand: bool = False,
) -> list[tuple[int, str, str | None, str, float, str]]:
    """Expand one sector impact into ``news_impacts`` rows.

    Always writes a sector-level row (ticker=NULL). When the article names a
    ticker, that ticker is tagged too. When ``expand`` is True and the article is
    general/macro (no named ticker), the impacted sector is also expanded to its
    known companies so the UI can list them without a join. Expansion is OFF by
    default because tagging every company in a large sector (e.g. ~100 banks)
    for one macro article creates noise rather than signal.
    """
    sector = str(impact["sector"])
    direction = str(impact["direction"])
    confidence = float(impact["confidence"])
    keywords = ", ".join(str(k) for k in impact["matched_keywords"])

    rows: list[tuple[int, str, str | None, str, float, str]] = [
        (news_id, sector, None, direction, confidence, keywords),
    ]
    if article_ticker:
        rows.append((news_id, sector, article_ticker, direction, confidence, keywords))
    elif expand:
        for ticker in sector_tickers.get(sector, []):
            rows.append((news_id, sector, ticker, direction, confidence, keywords))
    return rows


def enrich_news_impacts(limit: int | None = None, expand: bool = False) -> int:
    """Tag existing news_articles rows with deterministic sector/ticker impacts.

    The default writes one sector-level row (ticker=NULL) per matched impact,
    plus a row for an explicitly named ticker when present. The ``--expand`` flag
    additionally materializes a row per company in the impacted sector, for a
    ready-made "affected stocks" list (can be noisy for large sectors).

    Idempotent via ``ON CONFLICT (news_id, sector, ticker, direction) DO NOTHING``.
    Returns the number of impact rows written.
    """
    with ScraperDatabase() as store:
        store._ensure_connection()
        assert store.connection is not None
        with store.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, content, ticker FROM news_articles ORDER BY id"
            )
            rows = cursor.fetchall()

        if limit:
            rows = rows[:limit]

        sector_tickers = build_sector_ticker_map() if expand else {}

        from psycopg2.extras import execute_values

        written = 0
        with store.connection.cursor() as cursor:
            for news_id, title, content, ticker in rows:
                impacts = detect_impacts(f"{title or ''} {content or ''}")
                if not impacts:
                    continue
                impact_rows = []
                for impact in impacts:
                    impact_rows.extend(_impact_rows(news_id, impact, ticker, sector_tickers, expand))
                if impact_rows:
                    execute_values(
                        cursor,
                        """
                        INSERT INTO news_impacts
                            (news_id, sector, ticker, direction, confidence, matched_keywords)
                        VALUES %s
                        ON CONFLICT (news_id, sector, COALESCE(ticker, ''), direction) DO NOTHING
                        """,
                        impact_rows,
                    )
                    written += len(impact_rows)
            store.connection.commit()
        print(f"Tagged impacts for {len(rows)} news rows; wrote {written} impact rows.")
        return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Tag news_articles with sector/ticker impacts")
    parser.add_argument("--limit", type=int, help="Process only first N articles (testing)")
    parser.add_argument("--expand", action="store_true", help="Materialize one row per company in the impacted sector (noisy)")
    args = parser.parse_args()
    enrich_news_impacts(limit=args.limit, expand=args.expand)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
