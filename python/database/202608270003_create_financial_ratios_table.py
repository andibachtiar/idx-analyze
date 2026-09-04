"""Create normalized financial ratio records."""

name = "202608270003_create_financial_ratios_table"


def up(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS financial_ratios (
            id BIGSERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL REFERENCES companies(ticker),
            fiscal_year INTEGER,
            fiscal_period INTEGER,
            period_end DATE,
            revenue NUMERIC,
            cost_of_goods_sold NUMERIC,
            gross_profit NUMERIC,
            operating_income NUMERIC,
            net_income NUMERIC,
            eps NUMERIC,
            total_assets NUMERIC,
            total_liabilities NUMERIC,
            total_equity NUMERIC,
            cash_and_equivalents NUMERIC,
            total_debt NUMERIC,
            gross_margin NUMERIC,
            operating_margin NUMERIC,
            net_margin NUMERIC,
            roe NUMERIC,
            roa NUMERIC,
            roic NUMERIC,
            debt_to_equity NUMERIC,
            current_ratio NUMERIC,
            interest_coverage NUMERIC,
            pe_ratio NUMERIC,
            pb_ratio NUMERIC,
            ev_ebitda NUMERIC,
            dividend_yield NUMERIC,
            source VARCHAR(100) NOT NULL DEFAULT 'idx',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (ticker, fiscal_year, fiscal_period)
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS financial_ratios_ticker_idx ON financial_ratios(ticker)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS financial_ratios_period_idx ON financial_ratios(fiscal_year, fiscal_period)"
    )


def down(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS financial_ratios CASCADE")
