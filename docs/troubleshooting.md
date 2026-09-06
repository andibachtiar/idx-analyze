# idx-bei — Troubleshooting & Setup Guide

## Issue: pytest not found

If you see this error:

```
error: Failed to spawn: `pytest`
  Caused by: No such file or directory (os error 2)
```

### Solution

Run these commands in order:

```bash
# Navigate to Python directory
cd /var/www/idx-scraper/python

# Sync dependencies (this installs pytest and all others)
uv sync

# Now run tests
uv run pytest tests/test_models.py -v
```

---

## Full Test Command

To run all tests:

```bash
cd /var/www/idx-scraper/python
uv run pytest tests/ -v
```

To run specific test files:

```bash
# Models
uv run pytest tests/test_models.py -v

# Normalization
uv run pytest tests/test_normalization.py -v

# Fundamental Analysis
uv run pytest tests/test_fundamental.py -v

# Historical Analysis
uv run pytest tests/test_historical.py -v

# Technical Analysis
uv run pytest tests/test_technical.py -v

# Valuation
uv run pytest tests/test_valuation.py -v

# Screening
uv run pytest tests/test_screening.py -v
```

---

## Quick Test Script

Create `test_quick.py` to verify everything works:

```python
#!/usr/bin/env python3
"""Quick manual test for all modules."""

import sys
sys.path.insert(0, '.')

from models import Company, FinancialMetrics, FinancialPeriod, PeriodType
from analysis.fundamental import calculate_all_metrics, revenue_cagr
from analysis.technical import sma, rsi
from analysis.valuation import calculate_pe_ratio
from analysis.screening import quick_screen
from datetime import date

print("=== Testing Models ===")
company = Company(ticker="BBCA", name="Bank Central Asia")
print(f"Company: {company.ticker} - {company.name}")

metrics = FinancialMetrics(revenue=10000, net_income=1500, roe=0.15)
print(f"Metrics filled: {len(metrics.get_filled_metrics())}")

print("\n=== Testing Fundamental Analysis ===")
cagr = revenue_cagr(10000, 15000, 3)
print(f"Revenue CAGR (3yr): {cagr.value:.2%}")

print("\n=== Testing Technical Analysis ===")
prices = [100, 102, 101, 103, 105, 104, 106, 108]
sma_result = sma(prices, 5)
print(f"SMA(5): {sma_result.value:.2f}")

rsi_result = rsi(prices, 5)
print(f"RSI(5): {rsi_result.value:.2f} ({rsi_result.signal})")

print("\n=== Testing Valuation ===")
pe = calculate_pe_ratio(price=8500, eps=500)
print(f"P/E Ratio: {pe.value:.2f}")

print("\n=== Testing Screening ===")
stocks = {
    "BBCA": {"roe": 0.20, "pe_ratio": 15.0, "pb_ratio": 2.5, "debt_to_equity": 0.5},
    "ADRO": {"roe": 0.25, "pe_ratio": 8.0, "pb_ratio": 1.2, "debt_to_equity": 0.3}
}
result = quick_screen(stocks, "buffett")
print(f"Screen passed: {result.stocks_passed}/{result.total_stocks_screened}")

for stock in result.get_passed_stocks():
    print(f"  ✓ {stock.ticker}: {stock.name}")

print("\n=== All Tests Passed! ===")
```

Run with:

```bash
cd /var/www/idx-scraper/python
uv run python test_quick.py
```

---

## If uv is not installed

Install uv first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then proceed with the steps above.
