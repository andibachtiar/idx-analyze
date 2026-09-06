# Action Plan: Data & UI Fixes

## Issue 1: Missing ADRO Data

### Problem

The `financial_ratio.json` contains **AADI** (Adaro Andalan Indonesia), not **ADRO** (Adaro Energy). These are different companies.

### Solution: Run Scrapers

```bash
cd /var/www/idx-scraper/python

# Run all scrapers to fetch fresh data
uv run python scrape_company_profiles.py
uv run python scrape_financial_ratio.py
uv run python scrape_index_summary.py
uv run python scrape_idx_news.py

# Verify ADRO is in the data
python -c "import json; data=json.load(open('../data/financial_ratio.json')); adro=[d for d in data['data'] if d.get('code')=='ADRO']; print(f'ADRO found: {len(adro)>0}, Records: {len(data[\"data\"])}')"
```

### If ADRO Still Not Found

The scraper might not be fetching ADRO. Check:

1. Is ADRO listed on IDX? (It should be)
2. Check the scraper code in `scrape_financial_ratio.py` - it might need updating to include ADRO
3. Manually add ADRO data or fix the scraper

---

## Issue 2: UI Streaming Response

### What I've Added

Added `/ai/analyze-stream` endpoint to `api/main.py` that streams LLM responses.

### Next Steps for UI

1. The web interface at `index.html` needs to be updated to:
   - Use markdown rendering (already included via marked.js)
   - Call the new `/ai/analyze-stream` endpoint
   - Display streaming responses char-by-char

### Quick Test

```bash
# Start the server
cd /var/www/idx-scraper/python
uv run uvicorn api.main:app --reload

# In another terminal, test streaming
curl -X POST http://localhost:8000/ai/analyze-stream \
  -H "Content-Type: application/json" \
  -d '{"ticker": "ADRO", "question": "Analyze this stock"}'
```

---

## Issue 3: What Data is Available Now

### Current Data Files

- `data/allCompanies.json` - List of all IDX companies
- `data/companyDetailsByKodeEmiten.json` - Company profiles
- `data/financial_ratio.json` - Financial ratios (has AADI, not ADRO)
- `data/index_summary.json` - Index-level data (not individual stock prices)
- `data/idx_news.json` - News articles

### Missing Data

- Individual stock prices (need yfinance or IDX real-time data)
- Historical price data for technical analysis
- ADRO-specific financial data

---

## Recommended Next Steps

### Priority 1: Get ADRO Data

1. Run the scrapers above
2. If ADRO still missing, check if it's a valid ticker on IDX
3. Consider adding manual data entry for testing

### Priority 2: Fix UI

1. Update `index.html` to use streaming endpoint
2. Add markdown rendering
3. Improve response formatting

### Priority 3: Add More Data Sources

1. Integrate yfinance for historical prices
2. Add real-time price fetching
3. Create data caching layer

---

## Code Changes Made

### 1. ai/data_loader.py

- Fixed financial_ratio.json parsing (handles "code" field)
- Added proper error handling

### 2. ai/tools.py

- Updated get_stock_price() to use DataLoader
- Updated get_financials() to use DataLoader
- Updated get_fundamental_analysis() to load from DataLoader
- Updated get_valuation() to load from DataLoader
- Added get_company_info() function
- Updated get_company_news() to use DataLoader

### 3. ai/researcher.py

- Added imports for get_company_info and get_company_news
- Updated analyze_stock() to call new functions
- Updated _prepare_data_context() to include company info and news

### 4. api/main.py

- Added /ai/analyze-stream endpoint for streaming responses

### 5. AGENTS.md

- Updated pending phases section

---

## Testing Checklist

Run these commands to verify:

```bash
cd /var/www/idx-scraper/python

# Test data loading
uv run python -c "from ai.data_loader import get_data_loader; loader=get_data_loader(); print('ADRO financial:', loader.get_financial_ratios('ADRO') is not None)"

# Test tools
uv run python -c "from ai.tools import get_company_info; print(get_company_info('ADRO'))"

# Run tests
uv run pytest tests/test_ai_config.py tests/test_ai_llm_config.py -v
```
