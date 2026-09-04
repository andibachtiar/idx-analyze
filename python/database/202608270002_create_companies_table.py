"""Create normalized company records."""

name = "202608270002_create_companies_table"


def up(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            ticker VARCHAR(10) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            sector VARCHAR(100),
            industry VARCHAR(150),
            sub_industry VARCHAR(150),
            listing_date DATE,
            board VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def down(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS companies CASCADE")
