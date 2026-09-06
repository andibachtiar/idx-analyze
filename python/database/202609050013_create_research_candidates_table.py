"""Create research_candidates for deterministic macro -> research candidates (Fase B5).

Candidates are derived deterministically from the news_impacts snapshot
(affected tickers of high-pressure sectors). The daily LLM interpretation is
stored alongside so the Research tab can surface "what to analyze next".
"""

name = "202609050013_create_research_candidates_table"


def up(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS research_candidates (
            id BIGSERIAL PRIMARY KEY,
            candidate_date DATE NOT NULL DEFAULT CURRENT_DATE,
            batch_generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            sector VARCHAR(100) NOT NULL,
            ticker VARCHAR(10),
            direction VARCHAR(12) NOT NULL,
            confidence NUMERIC(5, 4),
            net_strength NUMERIC(12, 3),
            reason TEXT,
            llm_interpretation TEXT,
            source_impacts JSONB NOT NULL DEFAULT '[]',
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # NB: a bare UNIQUE (candidate_date, sector, ticker, direction) would treat
    # NULL ticker (sector-level rows) as distinct, so those rows could duplicate.
    # Use an expression unique index on COALESCE(ticker, '') to dedupe them too.
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS research_candidates_uniq_idx "
        "ON research_candidates (candidate_date, sector, COALESCE(ticker, ''), direction)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS research_candidates_date_idx "
        "ON research_candidates(candidate_date DESC)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS research_candidates_ticker_idx "
        "ON research_candidates(ticker)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS research_candidates_status_idx "
        "ON research_candidates(status)"
    )


def down(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS research_candidates CASCADE")
