"""Create daily IDX index summary records."""

name = "202608270006_create_index_summaries_table"


def up(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS index_summaries (
            id BIGSERIAL PRIMARY KEY,
            index_code VARCHAR(50) NOT NULL,
            summary_date DATE NOT NULL,
            previous NUMERIC,
            highest NUMERIC,
            lowest NUMERIC,
            close_value NUMERIC,
            number_of_stocks NUMERIC,
            change_value NUMERIC,
            volume NUMERIC,
            traded_value NUMERIC,
            frequency NUMERIC,
            market_capital NUMERIC,
            source VARCHAR(100) NOT NULL DEFAULT 'idx',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (index_code, summary_date)
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS index_summaries_code_idx ON index_summaries(index_code)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS index_summaries_date_idx ON index_summaries(summary_date)"
    )


def down(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS index_summaries")
