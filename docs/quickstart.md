# IDX-BEI Python Toolkit

This directory contains the Python-based data collection and analysis tools for IDX (Indonesia Stock Exchange) data.

## 🚀 Getting Started

### Install Dependencies

```bash
uv sync
```

### Run Scrapers

Data is saved to `../data/` directory relative to this folder.

```bash
# Single scraper
uv run scrape_company_profiles.py
uv run scrape_financial_ratio.py
uv run scrape_broker_search.py
uv run scrape_idx_news.py
uv run scrape_index_summary.py
uv run scrape_stock_prices.py

# All scrapers in sequence
uv run scrape_company_profiles.py && uv run scrape_financial_ratio.py && uv run scrape_broker_search.py && uv run scrape_idx_news.py && uv run scrape_index_summary.py
```

### Scrape Stock Prices (daily OHLCV → PostgreSQL)

The price scraper persists daily OHLCV data into the `stock_prices` table
(idempotent upsert keyed by `ticker + trading_date`):

```bash
# Daily mode (default): fetch only dates missing from PostgreSQL.
# Scrapes ALL tickers from the companies table (the IDX universe);
# falls back to a sample list only when that table is empty.
uv run scrape_stock_prices.py

# Single stock, incremental (only missing dates)
uv run scrape_stock_prices.py --ticker BBCA

# Explicit date range
uv run scrape_stock_prices.py --ticker BBCA --start 2025-01-01 --end 2025-12-31

# Multiple tickers
uv run scrape_stock_prices.py --ticker BBCA --ticker TLKM --backfill

# ~5 years of history regardless of what is stored
uv run scrape_stock_prices.py --backfill
```

Tickers that are missing from the `companies` table are auto-created as
placeholder rows during price ingestion (existing company details are never
overwritten). Run `scrape_company_profiles.py` first to populate the full
IDX universe with proper names/sectors.

## 📁 Scraper Scripts

| Script                       | Description                  | Output                                                           |
| ---------------------------- | ---------------------------- | ---------------------------------------------------------------- |
| `scrape_company_profiles.py` | Company listings & details   | `data/allCompanies.json`, `data/companyDetailsByKodeEmiten.json` |
| `scrape_financial_ratio.py`  | Financial ratios (quarterly) | `data/financial_ratio.json`                                      |
| `scrape_broker_search.py`    | Broker/dealer directory      | `data/brokerSearch.json`                                         |
| `scrape_idx_news.py`         | Market news headlines        | `data/idx_news.json`                                             |
| `scrape_index_summary.py`    | Daily index summary          | `data/index_summary.json`                                        |
| `scrape_stock_prices.py`     | Daily OHLCV stock prices     | PostgreSQL `stock_prices` table                                  |

## 🛠️ Analysis Scripts

- `neo4j_ingest.py` - Ingest JSON data into Neo4j graph database
- `neo4j.ipynb` - Jupyter notebook for network analysis
- `analyze_network_alpha.py` - Smart Money synergy scoring
- `stock_analysis_psql.py` - PostgreSQL-based financial analysis
- `yfinance_data.py` - Yahoo Finance supplemental data

## 🧪 Testing

```bash
uv run pytest tests/ -v
```

## 📊 Data Flow

```
IDX API → scrape_*.py → JSON files → neo4j_ingest.py → Neo4j
                                              ↓
                              stock_analysis_psql.py → PostgreSQL
                                              ↓
                              analyze_network_alpha.py → Dashboard
```

For full project documentation, see [root README.md](../README.md).
