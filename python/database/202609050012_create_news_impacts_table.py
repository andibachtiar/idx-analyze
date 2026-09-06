"""Create news_impacts for deterministic news -> sector/ticker impact mapping."""

name = "202609050012_create_news_impacts_table"


def up(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS news_impacts (
            id BIGSERIAL PRIMARY KEY,
            news_id BIGINT NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
            sector VARCHAR(100),
            ticker VARCHAR(10) REFERENCES companies(ticker),
            direction VARCHAR(12) NOT NULL,
            confidence NUMERIC(5, 4),
            matched_keywords TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # NB: a bare UNIQUE (news_id, sector, ticker, direction) would treat a NULL
    # ticker (sector-level rows) as distinct, so the same impact could duplicate
    # across pipeline runs and inflate counts. Use COALESCE(ticker, '') instead.
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS news_impacts_uniq_idx "
        "ON news_impacts (news_id, sector, COALESCE(ticker, ''), direction)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS news_impacts_news_idx ON news_impacts(news_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS news_impacts_sector_idx ON news_impacts(sector)")
    cursor.execute("CREATE INDEX IF NOT EXISTS news_impacts_ticker_idx ON news_impacts(ticker)")


def down(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS news_impacts CASCADE")
