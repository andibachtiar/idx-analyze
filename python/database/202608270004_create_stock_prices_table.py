"""Create daily stock price records."""

name = "202608270004_create_stock_prices_table"


def up(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_prices (
            id BIGSERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL REFERENCES companies(ticker),
            trading_date DATE NOT NULL,
            open_price NUMERIC,
            high_price NUMERIC,
            low_price NUMERIC,
            close_price NUMERIC,
            volume BIGINT,
            source VARCHAR(100) NOT NULL DEFAULT 'yfinance',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (ticker, trading_date)
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS stock_prices_ticker_idx ON stock_prices(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS stock_prices_date_idx ON stock_prices(trading_date)")


def down(cursor) -> None:
    cursor.execute("DROP TABLE IF EXISTS stock_prices CASCADE")
