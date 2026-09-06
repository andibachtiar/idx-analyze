# PostgreSQL Migration Guide

## Overview

This guide explains how to migrate from JSON/CSV file storage to PostgreSQL for better performance, scalability, and query capabilities.

---

## Files Created

| File                   | Purpose                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------- |
| `schema.sql`           | Database schema with tables for companies, financial ratios, stock prices, and news |
| `ai/data_loader_pg.py` | PostgreSQL data loader class                                                        |
| `ai/tools.py`          | Updated to use PostgreSQL loader (with JSON fallback)                               |

---

## Setup Steps

### 1. Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql

# Docker (alternative)
docker run --name idx-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
```

### 2. Create Database

```bash
# Create database
createdb idx_bei

# Or using docker
docker exec -i idx-postgres psql -U postgres -c "CREATE DATABASE idx_bei;"
```

### 3. Run Schema

```bash
cd /var/www/idx-scraper/python
psql idx_bei -f schema.sql
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env and set:
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/idx_bei
```

### 5. Migrate Existing Data

```bash
# Import JSON data to PostgreSQL
python financial_ratios_json2pg.py
```

---

## Database Tables

### companies

- ticker (PK)
- name, sector, industry
- listing_date, board

### financial_ratios

- Idx (PK)
- ticker (FK)
- fiscal_year, fiscal_period
- All financial metrics (revenue, net_income, margins, ratios, etc.)

### stock_prices

- id (PK)
- ticker (FK)
- date, open, high, low, close, volume

### news_articles

- id (PK)
- ticker (FK)
- title, content, source, published_at, url, sentiment_score

---

## Benefits

| Feature             | JSON/CSV         | PostgreSQL                     |
| ------------------- | ---------------- | ------------------------------ |
| Query by ticker     | Load entire file | SELECT * WHERE ticker = 'ADRO' |
| Historical analysis | Manual           | ORDER BY date                  |
| Concurrency         | File locks       | Full transaction support       |
| Scalability         | Limited          | Millions of rows               |
| Data integrity      | None             | Constraints, foreign keys      |

---

## Fallback Behavior

If PostgreSQL is not configured, the system automatically falls back to JSON file loading. This ensures the system works in both environments.

---

## Next Steps

1. Set up PostgreSQL database
2. Run schema.sql
3. Configure DATABASE_URL in .env
4. Run scrapers to populate database
5. Test with: `uv run python test_data_loading.py`
