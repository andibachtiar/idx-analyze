# PostgreSQL Setup Guide

## Quick Start

### 1. Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# macOS
brew install postgresql
brew services start postgresql

# Docker (alternative)
docker run --name idx-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
```

### 2. Create Database

```bash
# Using psql
sudo -u postgres psql
CREATE DATABASE idx_bei;
CREATE USER idx_user WITH PASSWORD 'idx_password';
GRANT ALL PRIVILEGES ON DATABASE idx_bei TO idx_user;
\q

# Or using Docker
docker exec -i idx-postgres psql -U postgres -c "CREATE DATABASE idx_bei;"
docker exec -i idx-postgres psql -U postgres -c "CREATE USER idx_user WITH PASSWORD 'idx_password';"
docker exec -i idx-postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE idx_bei TO idx_user;"
```

### 3. Run Schema

```bash
cd /var/www/idx-scraper/python
psql idx_bei -f schema.sql
# Or with user
psql -U idx_user -d idx_bei -f schema.sql
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env:
DATABASE_URL=postgresql://idx_user:idx_password@localhost:5432/idx_bei
```

### 5. Test Connection

```bash
uv run python -c "from ai.data_loader_pg import get_data_loader; dl = get_data_loader(); print('Connected:', dl.get_company_info('ADRO'))"
```

---

## Migrate Existing Data

### From JSON Files

```bash
# Import financial ratios
uv run python financial_ratios_json2pg.py

# Import company profiles
uv run python company_profiles_json2pg.py
```

### Verify Data

```bash
psql idx_bei -c "SELECT COUNT(*) FROM companies;"
psql idx_bei -c "SELECT COUNT(*) FROM financial_ratios;"
psql idx_bei -c "SELECT ticker, name FROM companies LIMIT 10;"
```

---

## Benefits

| Feature          | Before (JSON)        | After (PostgreSQL)             |
| ---------------- | -------------------- | ------------------------------ |
| Query by ticker  | Load entire file     | `SELECT * WHERE ticker='ADRO'` |
| Historical data  | Manual parsing       | `ORDER BY date DESC`           |
| Multiple periods | Limited              | Full time-series support       |
| Concurrency      | File locks           | Transaction support            |
| Scaling          | Slow with large data | Optimized indexes              |

---

## Fallback Behavior

If PostgreSQL is not available, the system automatically falls back to JSON file loading. No code changes needed.
