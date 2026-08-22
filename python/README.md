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

# All scrapers in sequence
uv run scrape_company_profiles.py && uv run scrape_financial_ratio.py && uv run scrape_broker_search.py && uv run scrape_idx_news.py && uv run scrape_index_summary.py
```

## 📁 Scraper Scripts

| Script                       | Description                  | Output                                                           |
| ---------------------------- | ---------------------------- | ---------------------------------------------------------------- |
| `scrape_company_profiles.py` | Company listings & details   | `data/allCompanies.json`, `data/companyDetailsByKodeEmiten.json` |
| `scrape_financial_ratio.py`  | Financial ratios (quarterly) | `data/financial_ratio.json`                                      |
| `scrape_broker_search.py`    | Broker/dealer directory      | `data/brokerSearch.json`                                         |
| `scrape_idx_news.py`         | Market news headlines        | `data/idx_news.json`                                             |
| `scrape_index_summary.py`    | Daily index summary          | `data/index_summary.json`                                        |

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
