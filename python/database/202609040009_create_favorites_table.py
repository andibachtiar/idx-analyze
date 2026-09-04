"""Create favorite stocks table for the dashboard."""

name = "202609040009_create_favorites_table"


def up(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            id BIGSERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL UNIQUE REFERENCES companies(ticker),
            position INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS favorites_position_idx ON favorites(position)")


def down(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS favorites CASCADE")
