"""Create screen_analyses to persist AI stock-screener interpretations.

Each ``POST /ai/screen-analysis`` run is appended as one row so the user can
review past AI interpretations of the deterministic screener results. Only the
scores (``results``) and the LLM interpretation (``llm_analysis``) are stored;
nothing here is invented by the AI.
"""

name = "202609080016_create_screen_analyses_table"


def up(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS screen_analyses (
            id BIGSERIAL PRIMARY KEY,
            screen_type VARCHAR(50),
            filters JSONB NOT NULL DEFAULT '[]',
            question TEXT,
            tickers JSONB NOT NULL DEFAULT '[]',
            results JSONB NOT NULL DEFAULT '[]',
            llm_analysis TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS screen_analyses_created_at_idx "
        "ON screen_analyses(created_at DESC)"
    )


def down(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS screen_analyses CASCADE")
