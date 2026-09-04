"""Add news_code dedup column and image_url to existing news_articles."""

name = "202608270008_add_news_code_to_news_articles"


def up(cursor) -> None:
    # Add news_code column (nullable initially so existing rows are not broken).
    cursor.execute(
        "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS news_code VARCHAR(100)"
    )
    cursor.execute(
        "ALTER TABLE news_articles ADD COLUMN IF NOT EXISTS image_url TEXT"
    )

    # Populate news_code for any existing rows using the url or id as a fallback key.
    cursor.execute(
        """
        UPDATE news_articles
        SET news_code = COALESCE(news_code, 'n' || id::text)
        WHERE news_code IS NULL
        """
    )

    # Enforce NOT NULL and uniqueness for idempotent inserts.
    cursor.execute("ALTER TABLE news_articles ALTER COLUMN news_code SET NOT NULL")
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS news_articles_news_code_idx ON news_articles(news_code)"
    )


def down(cursor) -> None:
    cursor.execute("DROP INDEX IF EXISTS news_articles_news_code_idx")
    cursor.execute("ALTER TABLE news_articles DROP COLUMN IF EXISTS news_code")
    cursor.execute("ALTER TABLE news_articles DROP COLUMN IF EXISTS image_url")
