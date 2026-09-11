# AI Investment Research Platform — Agent Guidelines

## Current Status

**Project:** IDX-BEI Investment Research Platform  
**Last Updated:** 2026-09-11
**Status:** All core phases complete (0-26), including data pipeline (24), UI/UX (25) and real-time updates (26)

### Completed Phases Summary

| Phase | Name                                | Status      | Files | Tests |
| ----- | ----------------------------------- | ----------- | ----- | ----- |
| 0     | Repository Audit                    | ✅ Complete | -     | -     |
| 1     | Data Model & Normalization          | ✅ Complete | 8     | 25+   |
| 2     | Fundamental Analysis                | ✅ Complete | 4     | 40+   |
| 3     | Historical Analysis                 | ✅ Complete | 3     | 37+   |
| 4     | Technical Analysis                  | ✅ Complete | 4     | 55+   |
| 5     | Valuation Engine                    | ✅ Complete | 4     | 54+   |
| 6     | Stock Screener                      | ✅ Complete | 3     | 48+   |
| 7     | Neo4j Relationships                 | ✅ Complete | 6     | 20+   |
| 8     | News/Event Pipeline                 | ✅ Complete | 3     | 30+   |
| 9     | Backtesting Engine                  | ✅ Complete | 4     | 57+   |
| 10    | AI Tool Layer                       | ✅ Complete | 2     | 40+   |
| 11    | AI Research Analyst                 | ✅ Complete | 3     | 35+   |
| 12    | AI Research Report                  | ✅ Complete | 2     | 40+   |
| 13    | Research Memory                     | ✅ Complete | 2     | 20+   |
| 14    | Vector Search/RAG                   | ✅ Complete | 2     | 25+   |
| 15    | API & UI                            | ✅ Complete | 4     | 20+   |
| 16    | LLM Integration + Valuation Prompts | ✅ Complete | 4     | 20+   |
| 17    | Technical Analysis Prompts          | ✅ Complete | 4     | 15+   |
| 18    | Stock Screener Prompts              | ✅ Complete | 4     | 12+   |
| 19    | Financial Report Analyst            | ✅ Complete | 4     | 5+    |
| 20    | Catalyst Calendar                   | ✅ Complete | 4     | 7+    |
| 21    | Competitor Analysis                 | ✅ Complete | 3     | 6+    |
| 22    | Institutional Ownership             | ✅ Complete | 1     | 5+    |
| 23    | Industry Map                        | ✅ Complete | 1     | 9+    |

**Total:** 62 new files, 673+ test cases

---

## Pending Phases

| Phase | Name                      | Description                  | Status      |
| ----- | ------------------------- | ---------------------------- | ----------- |
| 24    | Data Pipeline Integration | Connect scrapers to AI tools | ✅ Complete |
| 25    | UI/UX Enhancement         | Dashboard & stock page UI    | ✅ Complete |
| 26    | Real-time Data Updates    | Scheduled scraping + caching | ✅ Complete |

### Phase 25 — UI/UX Iterasi 1 & 2 (Selesai)

- Dashboard (`/`): statistik ringkas, saham favorit, tabel semua emiten, filter sektor, pencarian.
- Halaman per saham: grafik harga, profil perusahaan, key statistics, tab analisa.
- Endpoint baru: `GET /stocks`, `GET /stocks/{ticker}/prices`, `GET /stocks/{ticker}`, favorites CRUD.
- Migrasi `favorites` table (`202609040009_create_favorites_table`).
- Iterasi 2: candlestick OHLC, overlay indikator (SMA 20/50/200, Bollinger) + volume sub-chart, routing URL `/stock/{ticker}`.
- Iterasi 3: UI Screener (preset + filter kustom) & UI Perbandingan saham; `POST /screen` kini pakai data DB, endpoint `GET /compare`.
- Iterasi 3: enrichment `dividend_yield`/`current_ratio`/`payout_ratio` dari yfinance (migrasi + `scrape_yahoo_financial_fields.py`) mengaktifkan screen Value/Quality/Dividend.
- Iterasi 3: `revenue_cagr`/`earnings_cagr` dihitung dari yfinance `financials` (migrasi + `compute_cagr`) mengaktifkan screen Growth.
- News & Events pipeline aktif: `scrape_idx_news.py` (2484 berita), `enrich_news_tickers.py` (799 ter-link), `events/classif_news_records()`, endpoint `/news`, `/stocks/{ticker}/news`, `/stocks/{ticker}/events`.
- Iterasi 8: Watchlist + alert harga (`favorites` + kolom `alert_price`/`alert_direction`/`alert_enabled`; endpoint `/favorites/{ticker}/alert`, `/favorites/details`, `/favorites/alerts`; kontrol target per kartu favorit + banner alert tersentuh).
- Fix tab Analisa: `get_fundamental_analysis`/`get_valuation` kini memetakan nama kolom DB (`revenue`, `net_income`, `debt_to_equity`, ...) via `_metrics_from_db` (sebelumnya pakai key JSON IDX lama `sales`/`profitAttrOwner`/`deRatio` → kosong); endpoint GET `/technical` & `/valuation` kini menarik harga/metrik dari DB (sebelumnya stub/kosong). Semua tab Fundamental/Technical/Valuation kini terisi dari data riil.
- Dokumentasi roadmap: `docs/roadmap.md`.

### Phase 24 — Data Pipeline Integration (Selesai)

- **Scraper → PostgreSQL → AI tools terhubung**: semua scraper menulis ke DB via `ScraperDatabase` (idempotent `upsert_*`/`insert_news`), dibaca oleh `PostgreSQLDataLoader` untuk AI tools (`get_stock_price`, `get_financial_ratios`, `get_price_history`, `list_stock_metrics`, `get_news`).
- **Orkestrasi `run_pipeline.py`**: satu entry point berurutan (`companies → prices → financial_ratio → yfinance → financial_history → news_brave → news_impacts → research_candidates → research_analyze`) dengan retry/backoff, structured logging (`logs/pipeline.log`), dan failure ledger (`data/pipeline_ledger.jsonl`). `scrape_stock_prices` incremental via `stored_dates` (hanya fetch missing dates).
- **Fix dedup berita deterministik**: ganti `abs(hash(url/title))` (non-deterministik karena `PYTHONHASHSEED`) dengan SHA-1 (`_stable_hash`) di `insert_news` & `scrape_company_news.py`, agar re-run tidak menduplikat artikel (ON CONFLICT news_code).
- **Validasi numerik terpusat**: `_number` kini menolak NaN/Inf agar tidak mencemari kolom numerik; `backfill_financial_history.py` menormalisasi unit yfinance ke konvensi IDX (moneter ÷ 1e9, margin × 100).
- **Data riil terisi**: 973 perusahaan, 429.718 harga, 2.886 financial_ratios (+multitahun via backfill), 2.484 berita (799 ter-link).

### Phase 26 — Real-time Data Updates (Selesai)

- **Scraping dijalankan oleh pipeline, bukan manual**: `run_pipeline.py` adalah satu-satunya entry point yang menarik semua scraper berurutan (`companies → prices → financial_ratio → yfinance → financial_history → news_brave → news_impacts → research_candidates → research_analyze`) dengan retry/backoff, logging (`logs/pipeline.log`), dan failure ledger. Jalankan dengan `uv run python run_pipeline.py --all` (atau `--steps prices,news_brave` untuk subset).
- **Scheduling `scheduler.py`**: daemon loop yang menfiap Pipeline pada jadwal (env `SCRAPE_SCHEDULE_TIME` HH:MM Harian Asia/Jakarta, atau `SCRAPE_INTERVAL_HOURS` default 24h). Setiap selesai menjalankan `clear_cache()` agar API langsung membaca data baru. Semua stdlib (zoneinfo + subprocess), tanpa Celery/Redis.
- **Read cache TTL**: `PostgreSQLDataLoader` kini mem-cache hasil baca yang sering dipanggil (`list_stocks`, `list_stock_metrics`, `get_price_history`, `get_news`, `get_financial_ratios`, `get_financial_ratio_history`, dll.) selama `DATA_CACHE_TTL` detik (default 60, 0 = mati). `_ttl_cache` decorator menjaga hit per-argumen & thread-safe-ish; `clear_cache()` membatalkannya setelah pipeline.
- **Documentasi**: `docs/data-pipeline.md` menjelaskan bahwa scraping dilakukan oleh pipeline & cara menjalan/menjadwalkannya.
- **Screen `technical` aktif**: `PostgreSQLDataLoader.list_technical_metrics()` menghitung `price_vs_sma_200`/`rsi_14`/`volume_ratio` per ticker dari riwayat harga (di-cache TTL) dan `run_screening` menggabungkannya untuk `screen_type='technical'`; tombol preset Technical di UI Screener + backfill harga (~5 tahun, `--steps prices --backfill`) membuatnya berfungsi.

> **Catatan**: scraping otomatis & caching kini ditangani Phase 26 (Real-time Data Updates) — lihat `docs/data-pipeline.md`.

Cakupan selanjutnya (favorit per-user, chat streaming, news, export) ada di roadmap.

---

## Prompt Integration Roadmap (Post-Phase 15)

The following prompts exist in `prompt/` directory and need to be integrated:

| Priority | Prompt                      | Description                                                                                    | Target Phase |
| -------- | --------------------------- | ---------------------------------------------------------------------------------------------- | ------------ |
| 1        | stock-valuation.md          | Multi-method DCF + comparables valuation                                                       | PHASE 16 ✅  |
| 2        | technical-analysis.md       | Chart patterns, MAs, Ichimoku, options flow                                                    | PHASE 17 ✅  |
| 3        | stock-screener.md           | 5-factor scoring (Valuation, Quality, Momentum, Sentiment, Growth)                             | PHASE 18 ✅  |
| 4        | financial-report-analyst.md | 10-K/10-Q document analysis                                                                    | PHASE 19 ✅  |
| 5        | catalyst-calendar.md        | Event-driven catalyst identification                                                           | PHASE 20 ✅  |
| 6        | competitor-analysis.md      | Moat & Porter's Five Forces analysis                                                           | PHASE 21 ✅  |
| 7        | institutional-ownership.md  | 13F institutional holder tracking                                                              | PHASE 22     |
| 8        | industry-map.md             | Value chain & supply chain analysis                                                            | PHASE 23     |
| 9        | fundamental-analysis.md     | Key ratios + deterministic Signal Output (`ai/prompts/fundamental.py`, `POST /ai/fundamental`) | PHASE 15+ ✅ |

### Integration Strategy

All prompts follow a consistent structure:

1. **Data Verification** - Always fetch live data first
2. **Analysis Framework** - Step-by-step methodology
3. **Output Format** - Structured tables and scores
4. **Signal Output** - Standardized investment signal block

Integration approach:

- Create `ai/prompts/` module to load and manage prompts
- Extend existing analysis engines with prompt-guided output formatting
- Add new API endpoints for specialized analyses
- Maintain separation between deterministic calculations and AI interpretation

## 1. Project Goal

Transform the existing `idx-bei` Python project into an AI-assisted Indonesian stock research and investment analysis platform.

The system should eventually provide:

1. IDX stock data collection
2. Financial statement normalization
3. Fundamental analysis
4. Technical analysis
5. Valuation analysis
6. Stock screening
7. Ownership and company relationship analysis
8. News and event analysis
9. Historical data analysis
10. Backtesting
11. AI-assisted research and reasoning
12. Research reports and an interactive analysis interface

The existing repository is the starting point.

Repository:
https://github.com/nichsedge/idx-bei

Do NOT rewrite the existing project from scratch.

Preserve working functionality unless there is a clear technical reason to change it.

---

# 2. CRITICAL AGENT RULES

## 2.1 NEVER implement everything at once

Work strictly in phases.

Only implement the current phase.

Do NOT automatically continue to the next phase after completing a phase.

After completing a phase:

1. Run tests.
2. Run lint/type checks where applicable.
3. Review the changes.
4. Summarize what changed.
5. List any known problems.
6. STOP.

Wait for explicit user approval before starting the next phase.

---

## 2.2 Inspect before modifying

Before writing code:

1. Inspect the repository structure.
2. Identify the existing architecture.
3. Identify existing data models.
4. Identify existing database integration.
5. Identify existing scraper implementations.
6. Identify existing Neo4j integration.
7. Identify existing tests.
8. Identify configuration/environment files.
9. Identify dependencies.
10. Identify reusable existing code.

Do not create duplicate implementations when equivalent functionality already exists.

---

## 2.3 Prefer incremental changes

Do not perform large rewrites.

Prefer:

- adding modules
- extending existing services
- adding database tables/migrations
- adding tests
- refactoring only when necessary

Avoid changing unrelated code.

---

## 2.4 Preserve existing functionality

Before changing existing functionality, understand how it currently works.

Do not remove existing:

- scrapers
- database models
- Neo4j functionality
- API integrations
- parsing logic
- configuration
- CLI functionality

unless explicitly requested.

---

## 2.5 Data correctness is more important than AI

The LLM must NOT become the source of truth for financial calculations.

The following must be calculated deterministically:

- revenue
- earnings
- EPS
- margins
- ROE
- ROA
- debt ratios
- CAGR
- P/E
- P/B
- EV/EBITDA
- dividend yield
- technical indicators
- volatility
- drawdown
- valuation metrics
- backtest metrics

The AI may interpret these values but must not invent them.

---

# 3. Target Architecture

Eventually aim for:

                    IDX / Yahoo / News / Reports
                                |
                                v
                       Data Collection
                                |
                                v
                         Data Processing
                                |
              +-----------------+----------------+
              |                 |                |
              v                 v                v
         PostgreSQL          Neo4j          Object Storage
         Financials         Relations       Raw documents
              |                 |                |
              +-----------------+----------------+
                                |
                                v
                         Analysis Engine
                                |
        +-----------+-----------+-----------+-----------+
        |           |           |           |           |
        v           v           v           v           v

Fundamental Technical Valuation Risk Screening
|
v
AI Researcher
|
v
Research Interface

Do not implement this entire architecture in one phase.

---

# 4. Technology Principles

Prefer the existing project technology where practical.

Primary language:

- Python

Data collection:

- curl_cffi
- existing project scrapers
- requests only where browser impersonation is unnecessary

Data processing:

- pandas
- numpy

Database:

- PostgreSQL for structured production data
- Neo4j for relationship/graph data
- DuckDB for analytical/research workloads where appropriate

AI:

- OpenAI API
- tool/function calling
- structured outputs

API:

- FastAPI if an API layer is needed

Frontend:

- defer frontend implementation until backend/data architecture is stable

Testing:

- pytest

Do not introduce a framework/library merely because it is popular.

Every new dependency must have a clear reason.

---

# 5. Development Phases

## PHASE 0 — Repository Audit

Goal:

Understand the existing repository before making changes.

Tasks:

1. Inspect the complete repository structure.
2. Identify application entry points.
3. Identify scraper modules.
4. Identify database models.
5. Identify PostgreSQL integration.
6. Identify Neo4j integration.
7. Identify existing financial data models.
8. Identify existing Yahoo Finance integration.
9. Identify existing iXBRL parsing.
10. Identify existing tests.
11. Identify configuration and environment variables.
12. Identify duplicated or fragile code.
13. Document the current architecture.

Create:

docs/architecture.md

The document should contain:

- current architecture
- data flow
- major modules
- database structure
- external data sources
- known limitations
- recommended extension points

Do NOT implement new features during Phase 0.

STOP after completing the audit.

---

# PHASE 1 — Data Model and Financial Normalization

Goal:

Create a reliable normalized representation of Indonesian company financial data.

Before implementation:

Inspect the existing financial models.

Do not create duplicate models if suitable models already exist.

Define normalized concepts for:

- company
- ticker
- reporting period
- revenue
- operating income
- net income
- assets
- liabilities
- equity
- cash
- debt
- EPS
- shares outstanding
- dividends

Important:

Financial statements often contain inconsistent names, units, signs, and reporting periods.

Create normalization logic rather than relying on raw scraped field names.

Example conceptual model:

Company
|
+-- FinancialPeriod
|
+-- revenue
+-- operating_income
+-- net_income
+-- assets
+-- liabilities
+-- equity
+-- cash
+-- debt
+-- eps

Add tests for:

- missing values
- negative values
- unit conversion
- duplicate periods
- restated financials
- quarterly vs annual periods
- fiscal-year differences

Do NOT build AI functionality.

STOP after tests pass.

---

# PHASE 2 — Fundamental Analysis Engine

Goal:

Build deterministic fundamental analysis.

Create reusable functions/services for:

Growth:

- revenue CAGR
- earnings CAGR
- EPS CAGR
- FCF CAGR

Profitability:

- gross margin
- operating margin
- net margin
- ROE
- ROA
- ROIC

Financial health:

- debt/equity
- net debt/EBITDA
- current ratio
- interest coverage

Cash flow:

- operating cash flow
- free cash flow
- FCF margin

Each metric must:

1. Have a clear formula.
2. Handle missing data.
3. Handle division by zero.
4. Preserve the period used for calculation.
5. Have unit-aware calculations.
6. Have tests.

Example:

revenue_cagr(start_revenue, end_revenue, years)

should return a deterministic value.

Do NOT let the LLM calculate these metrics.

STOP after tests pass.

---

# PHASE 3 — Historical Financial Analysis

Goal:

Enable time-series analysis rather than only current metrics.

For each company, support:

- quarterly history
- annual history
- trailing twelve months where possible
- year-over-year growth
- quarter-over-quarter growth
- multi-year CAGR

Example:

BBCA:

2022
2023
2024
2025
2026

Calculate historical:

- revenue
- earnings
- EPS
- margins
- ROE
- debt
- FCF

The output should allow questions such as:

"Is profitability improving?"

"Is growth accelerating?"

"Is debt increasing?"

"Are margins expanding?"

Add tests around period ordering and missing periods.

STOP after tests pass.

---

# PHASE 4 — Technical Analysis Engine

Goal:

Create deterministic technical analysis.

Implement reusable calculations for:

- SMA
- EMA
- RSI
- MACD
- ATR
- Bollinger Bands
- volume moving average
- volume ratio
- volatility
- drawdown
- support/resistance where reliable

Generate structured output.

Example:

{
"trend": "bullish",
"rsi_14": 62.3,
"ema_20": 8450,
"ema_50": 8120,
"ema_200": 7600,
"volume_ratio": 1.42,
"volatility": 0.18
}

Do not generate natural-language investment conclusions here.

This layer only calculates facts/signals.

STOP after tests pass.

---

# PHASE 5 — Valuation Engine

Goal:

Build deterministic valuation analysis.

Implement:

- P/E
- P/B
- EV/EBITDA
- EV/EBIT
- P/FCF
- dividend yield

Add historical valuation analysis:

Current P/E
vs
5Y median P/E

Current P/B
vs
5Y median P/B

Where data permits.

Eventually support valuation models such as:

- earnings multiple valuation
- dividend discount model
- DCF

Do not implement complicated valuation models until the underlying financial data is reliable.

Every valuation result must contain:

- input values
- formula/model
- output
- valuation date
- data source

STOP after tests pass.

---

# PHASE 6 — Stock Screener

Goal:

Build a deterministic stock screening engine.

The engine must support filters such as:

- ROE > X
- revenue growth > X
- earnings growth > X
- P/E < X
- P/B < X
- debt/equity < X
- dividend yield > X
- price > SMA200
- RSI range

Example:

screen(
roe_min=0.15,
revenue_growth_min=0.10,
pe_max=20,
debt_equity_max=1
)

Return structured results.

Do NOT use the LLM for initial screening.

The LLM may later interpret the resulting shortlist.

STOP after tests pass.

---

# PHASE 7 — Neo4j Relationship Intelligence

Goal:

Expand the existing Neo4j implementation.

Model relationships such as:

- Company
- Person
- Director
- Commissioner
- Shareholder
- Parent company
- Subsidiary
- Ownership

Support queries such as:

- companies connected through directors
- ownership chains
- subsidiaries
- major shareholders
- related companies
- 1-2 degree company relationships

Example:

"Find companies related to ADRO within two relationship hops."

Neo4j should be the source of truth for relationship traversal.

Do not duplicate graph relationships into PostgreSQL unless necessary.

Add integration tests where practical.

STOP after tests pass.

---

# PHASE 8 — News and Corporate Event Pipeline

Goal:

Collect and normalize company-related news/events.

Create structured events.

Example:

{
"ticker": "XYZ",
"event_type": "new_contract",
"sentiment": 0.82,
"confidence": 0.91,
"impact": "medium",
"published_at": "...",
"source": "...",
"title": "..."
}

Possible event types:

- earnings
- dividend
- acquisition
- merger
- new_contract
- expansion
- management_change
- regulatory
- lawsuit
- debt
- capital_raise
- insider_transaction
- commodity_event

Do not rely solely on generic sentiment.

Extract the actual event and entities.

STOP after tests pass.

---

# PHASE 9 — Backtesting Engine

Goal:

Determine whether investment strategies historically worked.

Create a strategy interface.

Example:

Strategy:

ROE > 15%
Revenue CAGR > 10%
P/E < 20
Price > SMA200

Backtest against historical data.

Calculate:

- CAGR
- annual return
- volatility
- Sharpe ratio
- maximum drawdown
- win rate
- turnover
- number of trades
- benchmark performance

Prevent look-ahead bias.

This is critical.

A strategy must only use information that would actually have been available at the historical decision date.

Do not use future financial statements or revised data improperly.

STOP after tests and validation.

---

# PHASE 10 — AI Tool Layer

Only after the deterministic analysis engine is stable should AI integration begin.

Create tools/functions such as:

get_stock_price(ticker)

get_financials(ticker)

get_fundamental_analysis(ticker)

get_technical_analysis(ticker)

get_valuation(ticker)

get_company_news(ticker)

get_ownership(ticker)

get_related_companies(ticker)

screen_stocks(filters)

compare_stocks(tickers)

backtest_strategy(strategy)

Each tool must return structured data.

Do not return huge raw database dumps.

Return only the information required by the AI.

Example:

{
"ticker": "BBCA",
"price": 8650,
"fundamentals": {...},
"valuation": {...},
"technical": {...}
}

STOP after tools are independently tested.

---

# PHASE 11 — AI Research Analyst

Build an AI analyst that uses the tools from Phase 10.

The AI should:

1. Understand the user's question.
2. Determine which tools are needed.
3. Retrieve structured data.
4. Compare evidence.
5. Identify contradictions.
6. Explain important metrics.
7. Produce a structured research report.

The AI must NOT:

- invent financial numbers
- invent news
- fabricate sources
- calculate critical metrics from memory
- claim certainty about future prices
- present speculation as fact

Every factual financial claim should originate from a tool result.

---

# PHASE 12 — AI Research Report

Create a standard report format:

1. Executive Summary
2. Business Quality
3. Revenue/Earnings Growth
4. Profitability
5. Balance Sheet
6. Cash Flow
7. Valuation
8. Technical Position
9. Ownership/Relationships
10. Recent Events
11. Catalysts
12. Risks
13. Bull Case
14. Base Case
15. Bear Case
16. Conclusion
17. Confidence
18. Data Timestamp

The report should distinguish:

FACT
INTERPRETATION
ASSUMPTION
SPECULATION

Never mix them.

---

# PHASE 13 — Research Memory / Historical Thesis

Store previous AI research reports.

For each ticker, maintain:

- analysis date
- price at analysis
- thesis
- bull case
- bear case
- key risks
- valuation
- confidence
- subsequent outcome

This enables questions such as:

"What changed in BBCA since our previous analysis?"

"Which assumptions in our previous thesis were wrong?"

"How has the investment thesis evolved?"

---

# PHASE 14 — Vector Search / RAG

Only implement this after structured data and AI tools are working.

Use vector search for unstructured information:

- annual reports
- PDFs
- earnings presentations
- corporate announcements
- news articles
- management commentary

Do NOT put structured financial metrics into the vector database as the primary source.

Use:

PostgreSQL → structured data

Neo4j → relationships

Vector DB → unstructured documents

---

# PHASE 15 — API and UI

Only after the backend is stable.

Expose endpoints for:

GET /stocks/{ticker}

GET /stocks/{ticker}/financials

GET /stocks/{ticker}/fundamentals

GET /stocks/{ticker}/technical

GET /stocks/{ticker}/valuation

GET /stocks/{ticker}/news

GET /stocks/{ticker}/relationships

POST /screen

POST /backtest

POST /ai/analyze

The UI should eventually provide:

- stock search
- stock profile
- financial charts
- technical charts
- valuation history
- ownership graph
- news
- AI analysis
- stock screener
- backtesting
- portfolio research

Do not prioritize UI before the data and analysis layers are reliable.

---

# 6. AI Agent Behavior

When working on this project, follow this loop:

STEP 1
Inspect.

STEP 2
Plan the smallest implementation for the current phase.

STEP 3
Implement only that phase.

STEP 4
Run tests.

STEP 5
Fix issues caused by the implementation.

STEP 6
Review changed files.

STEP 7
Check for regressions.

STEP 8
Summarize.

STEP 9
STOP.

Never automatically continue.

---

# 7. Before Every Implementation

Answer internally:

- What existing code handles this?
- Can it be extended?
- What data does this require?
- Where should the data live?
- Is this deterministic or AI-generated?
- What tests are required?
- Could this introduce look-ahead bias?
- Could this introduce duplicate data?
- Could this break existing scrapers?
- Is a new dependency actually necessary?

---

# 8. Financial Data Rules

Financial data is time-sensitive.

Every financial value should have:

- ticker
- company
- period
- fiscal period
- reporting date
- source
- ingestion timestamp
- currency
- unit
- value

Never silently mix:

- quarterly data
- annual data
- TTM data
- restated data
- different currencies
- different units

When data is unavailable, return NULL/None or an explicit unavailable state.

Never fabricate values.

---

# 9. AI Output Rules

AI analysis must be evidence-driven.

Bad:

"BBCA is a great company and should increase."

Good:

"BBCA's ROE has remained above X% over the observed periods while earnings grew at X% CAGR. At the current P/E of X versus its historical median of X, valuation appears relatively expensive/cheap."

The AI should explain:

- what is known
- what is inferred
- what is uncertain

Do not present AI output as financial advice.

---

# 10. Code Quality

Prefer:

- small functions
- explicit types
- reusable services
- clear module boundaries
- deterministic calculations
- unit tests
- integration tests
- structured logging
- configuration through environment variables

Avoid:

- giant functions
- global mutable state
- hardcoded credentials
- hardcoded ticker-specific logic
- unnecessary abstractions
- unnecessary dependencies
- premature microservices

---

# 11. Dependency Rules

Before adding a dependency:

1. Check whether the project already has equivalent functionality.
2. Check whether the Python standard library is sufficient.
3. Check whether an existing dependency can solve the problem.
4. Explain why the dependency is necessary.
5. Keep dependencies minimal.

Do not add LangChain, LangGraph, vector databases, Kafka, Redis, Celery, Kubernetes, or other infrastructure simply because they are common in AI projects.

Introduce them only when a concrete requirement exists.

---

# 12. Production Principles

The system must eventually support:

- scheduled scraping
- retries
- rate limiting
- caching
- incremental updates
- idempotent ingestion
- data validation
- structured logging
- failure recovery

Scrapers must not repeatedly download unchanged data unnecessarily.

Data ingestion should be idempotent whenever possible.

---

# 13. Important Investment-System Principle

This is a research system, not an automatic trading system.

The system should help answer:

"What evidence supports this investment thesis?"

not:

"Tell me what stock to buy."

The AI should provide:

- evidence
- analysis
- alternatives
- risks
- assumptions
- uncertainty

The final investment decision remains with the user.

---

# 14. Current Execution Rule

When the user asks you to work on this project:

1. Determine which phase the requested work belongs to.
2. If the phase has not been completed, work only on that phase.
3. Inspect the repository before modifying it.
4. Do not implement future phases.
5. Do not add unnecessary infrastructure.
6. Run tests.
7. Report the result.
8. STOP.

If the user's request spans multiple phases, do NOT implement all phases.

Instead:

- identify the phases involved
- explain the dependency order
- implement only the earliest required phase
- STOP

Wait for explicit approval before proceeding.

---

# 15. Definition of Done

A phase is complete only when:

- implementation is finished
- tests exist for important behavior
- tests pass
- existing functionality still works
- no unnecessary dependencies were introduced
- documentation is updated where necessary
- changed files have been reviewed
- known limitations are documented

After this, STOP and wait for the user.
