# Current Architecture — IDX-BEI Investment Research Platform

## Overview

The `idx-bei` project has grown into an **AI-assisted Indonesian stock research and
investment analysis platform**. It collects data from IDX (Indonesia Stock
Exchange), Yahoo Finance and Brave Search, stores structured data in PostgreSQL
(and relationships in Neo4j), runs deterministic fundamental/technical/valuation
engines, and provides an optional AI research-analyst layer on top of that data.

> This document was originally written during Phase 0 (repository audit). The
> architecture below has since been substantially extended — the authoritative,
> current overview lives in `AGENTS.md` and `docs/data-pipeline.md`. This page
> keeps the high-level shape plus a corrected "Known Limitations" section.

**Repository:** https://github.com/nichsedge/idx-bei  
**Python Version:** >=3.13  
**Package Manager:** uv  
**Run tests:** `uv run pytest tests/ -q -k "not Integration"`

---

## Data Flow

```
IDX / Yahoo / Brave Search (external)
            │
            ▼
   run_pipeline.py  (companies → prices → financial_ratio → yfinance →
                    financial_history → news_brave → news_impacts → research_candidates)
            │
            ▼
        PostgreSQL (structured) ──► Neo4j (relationships)
            │
            ▼
   Deterministic engines (fundamental / technical / valuation / screening / news-impact)
            │
            ▼
   API (FastAPI) ──► Dashboard
            │
            ▼
   AI researcher (optional; interprets, never invents numbers)
```

> The precise, current pipeline order and scheduling are documented in
> `docs/data-pipeline.md`. The table below lists the scraper scripts.

### Scrapers / Pipeline (Data Collection Layer)

| Script / step                      | Source                  | Data Collected                                           | Sink                               |
| ---------------------------------- | ----------------------- | -------------------------------------------------------- | ---------------------------------- |
| `scrape_company_profiles.py`       | IDX Listed Company API  | Company profiles, directors, commissioners, shareholders | PostgreSQL (`companies`)           |
| `scrape_stock_prices.py`           | IDX                     | Daily OHLCV prices (incremental)                         | PostgreSQL (`stock_prices`)        |
| `scrape_financial_ratio.py`        | IDX Financial Ratio API | Financial ratios per company per period                  | PostgreSQL (`financial_ratios`)    |
| `scrape_yahoo_financial_fields.py` | Yahoo Finance           | Dividend yield, current ratio, payout, CAGR, EPS CAGR    | PostgreSQL (`financial_ratios`)    |
| `backfill_financial_history.py`    | Yahoo Finance           | Multi-year financial history                             | PostgreSQL (`financial_ratios`)    |
| `scrape_brave_news.py`             | Brave Search            | Per-ticker + macro news                                  | PostgreSQL (`news_articles`)       |
| `enrich_news_impacts.py`           | computed                | News → sector/direction impact tags                      | PostgreSQL (`news_impacts`)        |
| `generate_research_candidates.py`  | computed                | Macro-driven research candidates                         | PostgreSQL (`research_candidates`) |
| `scheduler.py`                     | —                       | Runs the pipeline on a cadence, then clears cache        | —                                  |

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

1. **iXBRL fundamentals incomplete** — `gross_profit`, `total_debt`,
   `interest_expense`, `operating_cash_flow`, `capital_expenditures` are not yet
   sourced reliably (IDX ratio API + yfinance don't provide them). The orphan
   `ixbrl.py` needs a rewrite to parse inline XBRL from official filings.
2. **News ticker relevance** — Brave sometimes tags unrelated entities to a short
   ticker query (e.g. "SICO" → Sigma Lithium). A deterministic relevance gate
   (`news_relevance.py`) prunes false positives at ingest, at the cost of
   possibly missing short brands without an acronym (precision > recall).
3. **News ingest source** — `scrape_company_news.py` (yfinance) still tags
   tickers without the relevance gate; not proven to pollute, but
   `prune_irrelevant_news.py` is source-agnostic and can clean it anytime.
4. **Docs drift** — some legacy docs lag the code. This page's historical sections
   (DB column names, dependencies, Docker) predate later refactors.

> The Phase 0-era "Known Limitations" (no idempotent ingestion, only 2 test files,
> syntax errors in `scrape_financial_ratio.py`, hardcoded paths) are **resolved**:
> ingestion is idempotent (upsert + stable SHA-1 dedup), the suite is ~1070 tests
> across dozens of files, and the scraper f-string bugs are fixed.

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
