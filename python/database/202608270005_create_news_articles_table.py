"""Create scraped news article records."""

name = "202608270005_create_news_articles_table"


def up(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS news_articles (
            id BIGSERIAL PRIMARY KEY,
            news_code VARCHAR(100) NOT NULL,
            ticker VARCHAR(10) REFERENCES companies(ticker),
            title VARCHAR(500),
            content TEXT,
            source VARCHAR(150),
            published_at TIMESTAMPTZ,
            url TEXT,
            image_url TEXT,
            sentiment_score NUMERIC(5, 4),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (news_code)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS news_articles_ticker_idx ON news_articles(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS news_articles_published_idx ON news_articles(published_at)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS news_articles_news_code_idx ON news_articles(news_code)")


def down(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS news_articles CASCADE")
