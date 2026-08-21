# Current Architecture — idx-bei Project

## Overview

The `idx-bei` project is a Python-based data collection and analysis toolkit for Indonesian stocks (IDX/BEI). It scrapes data from IDX (Indonesia Stock Exchange) and Yahoo Finance, stores it in PostgreSQL and Neo4j databases, and provides basic stock screening functionality.

**Repository:** https://github.com/nichsedge/idx-bei  
**Python Version:** >=3.13  
**Package Manager:** uv

---

## Data Flow

```
IDX API (www.idx.co.id) ──┐
                          ├──► JSON Files (data/) ──► PostgreSQL (financial_ratios)
Yahoo Finance API         │                              └──► Neo4j (companies, relationships)
                          │
                          └──► Analysis Scripts ──► Output
```

### Scrapers (Data Collection Layer)

| Script                       | Source                  | Data Collected                                           | Output                                 |
| ---------------------------- | ----------------------- | -------------------------------------------------------- | -------------------------------------- |
| `scrape_company_profiles.py` | IDX Listed Company API  | Company profiles, directors, commissioners, shareholders | `data/companyDetailsByKodeEmiten.json` |
| `scrape_financial_ratio.py`  | IDX Financial Ratio API | Financial ratios per company per period                  | `data/financial_ratio.json`            |
| `scrape_broker_search.py`    | IDX Broker Search API   | Broker directory                                         | `data/brokerSearch.json`               |
| `scrape_index_summary.py`    | IDX Trading Summary API | Index summary data                                       | `index_summary.json`                   |
| `scrape_idx_news.py`         | IDX News API            | Stock news articles                                      | `data/news/`                           |
| `yfinance_data.py`           | Yahoo Finance           | Financial ratios, holders, insiders                      | CSV files                              |

### Data Processing Layer

| Script                        | Purpose                                                              |
| ----------------------------- | -------------------------------------------------------------------- |
| `financial_ratios_json2pg.py` | Load financial ratio JSON → PostgreSQL (`financial_ratios` table)    |
| `neo4j_ingest.py`             | Ingest company profiles → Neo4j (Company, Insider, Subsidiary nodes) |
| `ixbrl.py`                    | Parse iXBRL HTML files to JSON                                       |
| `stock_analysis_psql.py`      | Query PostgreSQL for Buffett-style stock screening                   |
| `analyze_network_alpha.py`    | Network analysis for alpha generation                                |

---

## Database Structure

### PostgreSQL

**Table:** `financial_ratios`

Columns (snake_case from camelCase JSON):

- `code` — Stock ticker
- `fs_date` — Financial statement date
- `fiscal_year_end`
- `assets`, `liabilities`, `equity`, `sales`, `ebt`, `profit_period`, `profit_attr_owner`
- `eps`, `book_value`, `per`, `price_bv`, `de_ratio`, `roa`, `roe`, `npm`
- (and others from IDX financial ratio API)

### Neo4j

**Nodes:**

- `:Company` — Stock/profil perusahaan
- `:Insider` — Directors, commissioners, secretaries, audit committee members
- `:Subsidiary` — Anak perusahaan

**Relationships:**

- `:DIRECTOR_OF` — Person → Company
- `:COMMISSIONER_OF` — Person → Company
- `:CORPORATE_SECRETARY_OF` — Person → Company
- `:AUDIT_COMMITTEE_MEMBER_OF` — Person → Company
- `:OWNS` — Shareholder → Company
- `:SUBSIDIARY_OF` — Subsidiary → Company
- `:HAS_TRADE_DAY` — Company → TradeDay (daily price data)

---

## Key Modules

### 1. Scrapers (`python/*.py`)

All scrapers use `curl_cffi` with `impersonate="chrome"` to bypass Cloudflare.

**Async scraper:** `scrape_company_profiles.py` uses `AsyncSession` with semaphore-based concurrency (limit: 5 concurrent requests).

**Sync scrapers:** `scrape_financial_ratio.py`, `scrape_broker_search.py`, `scrape_index_summary.py`, `scrape_idx_news.py`.

**Rate limiting:** Manual delays (1-30 seconds) between requests.

### 2. Database Integration

**PostgreSQL:** Via SQLAlchemy + psycopg2-binary. Connection via environment variables.

**Neo4j:** Via official `neo4j` driver. Connection via environment variables. Uses batched Cypher queries.

### 3. Analysis

**Buffett Screening** (`stock_analysis_psql.py`):

- Filter: ROE ≥ 15%, Debt/Equity < 1, P/E > 0, P/BV > 0
- Score: Rank by P/E + P/BV (lower is better)
- Returns top 10 stocks

**Network Analysis** (`analyze_network_alpha.py`):

- Loads financial ratios and company networks
- Runs analysis pipeline (full implementation in file)

---

## Dependencies

```toml
[project]
dependencies = [
    "arelle-release>=2.37.33",   # iXBRL parsing
    "matplotlib>=3.10.3",        # Visualization
    "neo4j>=5.28.1",             # Neo4j driver
    "psycopg2-binary",           # PostgreSQL driver
    "scikit-learn>=1.6.1",       # ML utilities
    "seaborn>=0.13.2",           # Statistical visualization
    "sqlalchemy>=2.0.41",        # ORM
    "tqdm>=4.67.1",              # Progress bars
    "yfinance>=0.2.59",          # Yahoo Finance API
    "curl_cffi>=0.7.4",          # Browser-like HTTP requests
    "python-dotenv>=1.0.1",      # Environment variables
]

[dependency-groups]
dev = [
    "ipykernel>=6.29.5",
    "nbformat>=5.10.4",
]
```

---

## Docker Services

```yaml
# docker-compose.yml (includes neo4j.yml)
services:
  neo4j: # Port 7474 (HTTP), 7687 (Bolt)
  # postgres: # Commented out — not active
  # metabase: # Commented out — not active
```

---

## External Data Sources

| Source               | API Endpoint                                    | Data Type                         |
| -------------------- | ----------------------------------------------- | --------------------------------- |
| IDX Listed Companies | `/primary/ListedCompany/GetCompanyProfiles`     | Profiles, directors, shareholders |
| IDX Financial Ratios | `/primary/DigitalStatistic/GetApiDataPaginated` | Financial ratios                  |
| IDX Broker Search    | `/primary/ExchangeMember/GetBrokerSearch`       | Broker directory                  |
| IDX Trading Summary  | `/primary/TradingSummary/GetIndexSummary`       | Index data                        |
| IDX News             | `/primary/home/content`                         | News articles                     |
| Yahoo Finance        | yfinance library                                | Price history, financials         |

---

## Known Limitations

1. **No data normalization** — Raw field names stored as-is; no handling of inconsistent units/signs
2. **No time-series storage** — Financial data stored flat without period relationship tracking
3. **Limited testing** — Only 2 test files covering error cases (file not found) and URL building
4. **No idempotent ingestion** — Re-running scrapers creates duplicates in PostgreSQL
5. **No error recovery** — Scrapers fail hard on rate limits without exponential backoff
6. **Hardcoded paths** — Some scripts assume specific working directories
7. **Syntax errors** — `scrape_financial_ratio.py:129` has broken f-string
8. **Incomplete code** — `stock_analysis_psql.py` has early return inside wrong block

---

## Recommended Extension Points

| Phase | Feature                          | Where to Add                          |
| ----- | -------------------------------- | ------------------------------------- |
| 1     | Financial models & normalization | New `models/` package                 |
| 2     | Fundamental analysis engine      | New `analysis/fundamental.py`         |
| 3     | Historical time-series           | Extend `models/` with period tracking |
| 4     | Technical analysis engine        | New `analysis/technical.py`           |
| 5     | Valuation engine                 | New `analysis/valuation.py`           |
| 6     | Stock screener                   | New `screening/engine.py`             |
| 7     | Neo4j expansion                  | Extend `neo4j_ingest.py`              |
| 8     | News pipeline                    | Extend `scrape_idx_news.py`           |
| 9     | Backtesting                      | New `backtest/` package               |
| 10+   | AI tools                         | New `ai/` package                     |

---

_Document generated: 2026-08-21_
