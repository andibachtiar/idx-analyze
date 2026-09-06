"""Add price-alert columns to the favorites/watchlist table."""

name = "202609050010_add_alert_to_favorites"


def up(cursor) -> None:
    cursor.execute(
        "ALTER TABLE favorites ADD COLUMN IF NOT EXISTS alert_price NUMERIC"
    )
    cursor.execute(
        "ALTER TABLE favorites ADD COLUMN IF NOT EXISTS alert_direction VARCHAR(8) NOT NULL DEFAULT 'above'"
    )
    cursor.execute(
        "ALTER TABLE favorites ADD COLUMN IF NOT EXISTS alert_enabled BOOLEAN NOT NULL DEFAULT false"
    )
    cursor.execute(
        "ALTER TABLE favorites ADD COLUMN IF NOT EXISTS alert_updated_at TIMESTAMPTZ"
    )


def down(cursor) -> None:
    cursor.execute("ALTER TABLE favorites DROP COLUMN IF EXISTS alert_price")
    cursor.execute("ALTER TABLE favorites DROP COLUMN IF EXISTS alert_direction")
    cursor.execute("ALTER TABLE favorites DROP COLUMN IF EXISTS alert_enabled")
    cursor.execute("ALTER TABLE favorites DROP COLUMN IF EXISTS alert_updated_at")
