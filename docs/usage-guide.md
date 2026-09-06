# idx-bei Investment Research Platform — User Guide

## Overview

This platform provides deterministic financial analysis tools for Indonesian stocks (IDX/BEI). It includes:

- **Data Models**: Normalized financial data structures
- **Normalization**: Field mapping and data cleaning
- **Fundamental Analysis**: CAGR, margins, ROE, ROA, etc.
- **Historical Analysis**: Time-series growth calculations
- **Technical Analysis**: Moving averages, RSI, MACD, Bollinger Bands
- **Valuation**: P/E, P/B, EV/EBITDA, dividend yield
- **Stock Screening**: Filter stocks based on multiple criteria

---

## Quick Start

### 1. Install Dependencies

```bash
cd python
uv sync
```

### 2. Run Basic Tests

```bash
cd python
uv run pytest tests/test_models.py -v
uv run pytest tests/test_fundamental.py -v
uv run pytest tests/test_technical.py -v
uv run pytest tests/test_valuation.py -v
uv run pytest tests/test_screening.py -v
```

---

## Module Usage Guide

### 1. Data Models (`python/models/`)

#### Creating a Company

```python
from models import Company, PeriodType, Unit, Source

# Create a company
company = Company(
    ticker="BBCA",
    name="Bank Central Asia Tbk",
    sector="Finance",
    sub_sector="Banks",
    industry="Banking"
)

print(f"Ticker: {company.ticker}")  # BBCA (auto-uppercase)
print(f"Name: {company.name}")      # Bank Central Asia Tbk
```

#### Creating Financial Metrics

```python
from models import FinancialMetrics

# Create financial metrics for a period
metrics = FinancialMetrics(
    revenue=50000.0,           # 50 trillion IDR
    net_income=15000.0,
    total_assets=500000.0,
    total_equity=100000.0,
    total_debt=400000.0,
    eps=500.0,
    roe=0.15,                  # 15%
    pe_ratio=12.5
)

# Check filled metrics
filled = metrics.get_filled_metrics()
print(filled)  # {'revenue': 50000.0, 'net_income': 15000.0, ...}

# Check if empty
print(metrics.is_empty())  # False
```

#### Creating Financial Periods

```python
from models import FinancialPeriod, PeriodType
from datetime import date

# Annual period
annual_period = FinancialPeriod(
    ticker="BBCA",
    period_end=date(2024, 12, 31),
    period_type=PeriodType.ANNUAL
)

# Quarterly period
quarterly_period = FinancialPeriod(
    ticker="BBCA",
    period_end=date(2024, 9, 30),
    period_type=PeriodType.QUARTERLY
)

print(annual_period.period_label)   # "2024"
print(quarterly_period.period_label)  # "2024-Q3"
```

---

### 2. Normalization (`python/normalization/`)

#### Using the Normalizer

```python
from normalization import FinancialNormalizer, Source, Unit

normalizer = FinancialNormalizer()

# Raw IDX API data
raw_data = {
    "code": "BBCA",
    "stockName": "Bank Central Asia Tbk",
    "fsDate": "2024-12-31",
    "fiscalYearEnd": "Dec",
    "assets": 500000.0,
    "liabilities": 450000.0,
    "equity": 50000.0,
    "sales": 20000.0,
    "profitAttrOwner": 5000.0,
    "eps": 500.0,
    "roe": 47.5,      # Percentage
    "per": 12.5,
    "de_ratio": 0.5
}

# Normalize the data
result = normalizer.normalize_raw_data(raw_data)

if result:
    print(f"Ticker: {result['ticker']}")  # BBCA
    print(f"Metrics: {result['metrics']}")
    # ROE will be converted from 47.5 to 0.475
```

#### Field Mapping Examples

```python
from normalization.mappings import normalize_field_name

# Map various field names to normalized names
print(normalize_field_name("sales"))           # revenue
print(normalize_field_name("profitAttrOwner")) # net_income
print(normalize_field_name("aset_total"))      # total_assets
print(normalize_field_name("pendapatan"))      # revenue
```

---

### 3. Fundamental Analysis (`python/analysis/fundamental.py`)

#### Growth Metrics

```python
from analysis.fundamental import revenue_cagr, earnings_cagr, eps_cagr

# Revenue CAGR: 100M -> 150M over 3 years
cagr = revenue_cagr(100.0, 150.0, 3)
print(f"Revenue CAGR: {cagr.value:.2%}")  # ~14.47%

# EPS CAGR
eps_cagr_result = eps_cagr(100.0, 150.0, 3)
print(f"EPS CAGR: {eps_cagr_result.value:.2%}")
```

#### Profitability Metrics

```python
from analysis.fundamental import gross_margin, roe, roa, net_margin

# Gross Margin
gm = gross_margin(gross_profit=4500.0, revenue=10000.0)
print(f"Gross Margin: {gm.value:.2%}")  # 45%

# ROE
roe_result = roe(net_income=1500.0, total_equity=10000.0)
print(f"ROE: {roe_result.value:.2%}")    # 15%

# ROA
roa_result = roa(net_income=1500.0, total_assets=20000.0)
print(f"ROA: {roa_result.value:.2%}")    # 7.5%

# Net Margin
nm = net_margin(net_income=1500.0, revenue=10000.0)
print(f"Net Margin: {nm.value:.2%}")     # 15%
```

#### Financial Health Metrics

```python
from analysis.fundamental import debt_to_equity, current_ratio, interest_coverage

# Debt-to-Equity
de = debt_to_equity(total_debt=5000.0, total_equity=10000.0)
print(f"D/E Ratio: {de.value:.2f}")      # 0.50

# Current Ratio
cr = current_ratio(current_assets=8000.0, current_liabilities=4000.0)
print(f"Current Ratio: {cr.value:.2f}")  # 2.0

# Interest Coverage
ic = interest_coverage(ebit=5000.0, interest_expense=1000.0)
print(f"Interest Coverage: {ic.value:.2f}")  # 5.0x
```

#### Batch Calculation

```python
from analysis.fundamental import calculate_all_metrics
from models import FinancialMetrics

metrics = FinancialMetrics(
    revenue=50000.0,
    gross_profit=20000.0,
    operating_income=10000.0,
    net_income=7500.0,
    total_assets=100000.0,
    total_equity=40000.0,
    total_debt=60000.0,
    current_assets=30000.0,
    current_liabilities=15000.0,
    operating_cash_flow=12000.0,
    capital_expenditures=3000.0
)

results = calculate_all_metrics(metrics, "2024")

for name, result in results.items():
    if result.is_available:
        print(f"{name}: {result.value:.4f}")
```

---

### 4. Historical Analysis (`python/analysis/historical.py`)

#### Adding Historical Data

```python
from analysis.historical import HistoricalFinancialData
from models import FinancialPeriod, FinancialMetrics, PeriodType
from datetime import date

hfd = HistoricalFinancialData(ticker="BBCA")

# Add annual records
for year in [2020, 2021, 2022, 2023, 2024]:
    period = FinancialPeriod(
        ticker="BBCA",
        period_end=date(year, 12, 31),
        period_type=PeriodType.ANNUAL
    )
    metrics = FinancialMetrics(
        revenue=10000 * (1.1 ** (year - 2020)),
        net_income=1500 * (1.15 ** (year - 2020))
    )
    hfd.add_record(period, metrics)

print(f"Records: {hfd.get_period_count()}")  # 5
```

#### Year-over-Year Growth

```python
# YoY Revenue Growth
yoy = hfd.calculate_yoy_growth("revenue")
print(f"YoY Revenue Growth: {yoy.value:.2%}")
print(f"From {yoy.start_period} to {yoy.end_period}")
```

#### Quarter-over-Quarter Growth

```python
# Add quarterly data
for quarter, revenue in [(1, 2500), (2, 2700), (3, 2900), (4, 3100)]:
    period = FinancialPeriod(
        ticker="BBCA",
        period_end=date(2024, quarter * 3, 31 if quarter != 3 else 30),
        period_type=PeriodType.QUARTERLY
    )
    metrics = FinancialMetrics(revenue=revenue)
    hfd.add_record(period, metrics)

# QoQ Growth
qoq = hfd.calculate_qoq_growth("revenue")
print(f"QoQ Revenue Growth: {qoq.value:.2%}")
```

#### CAGR Calculation

```python
# 5-year CAGR
cagr = hfd.calculate_cagr("revenue", years=5)
print(f"5-Year Revenue CAGR: {cagr.value:.2%}")
```

#### TTM (Trailing Twelve Months)

```python
# Calculate TTM revenue
ttm = hfd.calculate_ttm("revenue")
print(f"TTM Revenue: {ttm}")
```

---

### 5. Technical Analysis (`python/analysis/technical.py`)

#### Moving Averages

```python
from analysis.technical import sma, ema

prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 110]

# Simple Moving Average
sma_5 = sma(prices, 5)
print(f"SMA(5): {sma_5.value:.2f}")

# Exponential Moving Average
ema_5 = ema(prices, 5)
print(f"EMA(5): {ema_5.value:.2f}")
```

#### RSI (Relative Strength Index)

```python
from analysis.technical import rsi

# Declining prices -> oversold
prices_down = [100, 95, 90, 85, 80, 75, 70, 65, 60, 55]
rsi_result = rsi(prices_down, 5)
print(f"RSI: {rsi_result.value:.2f}")  # Should be < 30 (oversold)
print(f"Signal: {rsi_result.signal}")   # "oversold"
```

#### MACD

```python
from analysis.technical import macd

prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 110,
          112, 115, 114, 116, 118, 120, 119, 121, 123, 125]

result = macd(prices)
print(f"MACD Line: {result['macd_line']:.4f}")
print(f"Signal Line: {result['signal_line']:.4f}")
print(f"Histogram: {result['histogram']:.4f}")
print(f"Signal: {result['signal']}")
```

#### Bollinger Bands

```python
from analysis.technical import bollinger_bands

prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 110] * 5

result = bollinger_bands(prices, period=20)
print(f"Upper Band: {result['upper']:.2f}")
print(f"Middle Band: {result['middle']:.2f}")
print(f"Lower Band: {result['lower']:.2f}")
print(f"%B: {result['percent_b']:.2f}")
print(f"Signal: {result.get('signal')}")
```

#### Batch Technical Analysis

```python
from analysis.technical import calculate_all_technicals

# Generate sample price data
import numpy as np
np.random.seed(42)
prices = [100]
for _ in range(99):
    prices.append(prices[-1] * (1 + np.random.normal(0.001, 0.02)))

results = calculate_all_technicals(prices)

for key, value in results.items():
    if hasattr(value, 'value') and value.value is not None:
        print(f"{key}: {value.value:.4f}")
    elif isinstance(value, dict):
        print(f"{key}: {value}")
```

---

### 6. Valuation (`python/analysis/valuation.py`)

#### P/E Ratio

```python
from analysis.valuation import calculate_pe_ratio
from datetime import date

result = calculate_pe_ratio(
    price=8500,
    eps=500,
    valuation_date=date(2024, 12, 31)
)
print(f"P/E Ratio: {result.value:.2f}")
print(f"Formula: {result.formula}")
```

#### P/B Ratio

```python
from analysis.valuation import calculate_pb_ratio

result = calculate_pb_ratio(
    price=8500,
    book_value_per_share=3000
)
print(f"P/B Ratio: {result.value:.2f}")
```

#### EV/EBITDA

```python
from analysis.valuation import calculate_ev_ebitda

# Enterprise Value = Market Cap + Debt - Cash
result = calculate_ev_ebitda(
    market_cap=100000.0,
    total_debt=50000.0,
    cash=10000.0,
    ebitda=15000.0
)
print(f"EV/EBITDA: {result.value:.2f}")
```

#### Dividend Yield

```python
from analysis.valuation import calculate_dividend_yield

result = calculate_dividend_yield(
    annual_dividend_per_share=300,
    price=8500
)
print(f"Dividend Yield: {result.value:.2f}%")
```

#### Historical Valuation Context

```python
from analysis.valuation import add_historical_context, ValuationResult

# Current valuation
current = ValuationResult(
    value=15.0,
    metric_name="pe_ratio",
    formula="Price / EPS",
    inputs={"price": 8500, "eps": 567},
    valuation_date=date(2024, 12, 31)
)

# Historical data (last 5 years)
history = [
    ("2020", 12.0),
    ("2021", 14.0),
    ("2022", 16.0),
    ("2023", 15.0),
    ("2024", 15.0)
]

hist_result = add_historical_context(current, history)
print(f"Current P/E: {hist_result.current_value}")
print(f"5-Year Median: {hist_result.median_5y}")
print(f"Percentile: {hist_result.percentile:.1f}%")
print(f"Is Expensive: {hist_result.is_expensive}")
print(f"Is Cheap: {hist_result.is_cheap}")
```

#### Complete Valuation Summary

```python
from analysis.valuation import get_valuation_summary
from models import FinancialMetrics

metrics = FinancialMetrics(
    eps=500.0,
    book_value_per_share=2000.0,
    total_equity=80000.0,
    shares_outstanding=16000.0
)

summary = get_valuation_summary(
    price=8500,
    metrics=metrics,
    historical_pe=[("2020", 12), ("2021", 14), ("2022", 16), ("2023", 15)],
    historical_pb=[("2020", 1.8), ("2021", 2.0), ("2022", 2.2), ("2023", 2.1)]
)

print(f"Current Price: {summary['current_price']}")
print(f"P/E: {summary['valuations']['pe_ratio']['value']}")
print(f"P/B: {summary['valuations']['pb_ratio']['value']}")
print(f"P/E Percentile: {summary['historical_comparison']['pe_ratio']['percentile']:.1f}%")
```

---

### 7. Stock Screening (`python/analysis/screening.py`)

#### Using Predefined Screens

```python
from analysis.screening import quick_screen

# Sample stock data
stocks = {
    "BBCA": {
        "name": "Bank Central Asia",
        "roe": 0.20,
        "pe_ratio": 15.0,
        "pb_ratio": 2.5,
        "debt_to_equity": 0.5,
        "dividend_yield": 3.0,
        "revenue_cagr": 0.12,
        "earnings_cagr": 0.15
    },
    "ADRO": {
        "name": "Adaro Indonesia",
        "roe": 0.25,
        "pe_ratio": 8.0,
        "pb_ratio": 1.2,
        "debt_to_equity": 0.3,
        "dividend_yield": 5.0,
        "revenue_cagr": 0.08,
        "earnings_cagr": 0.10
    },
    "TLKM": {
        "name": "Telkom Indonesia",
        "roe": 0.15,
        "pe_ratio": 18.0,
        "pb_ratio": 3.0,
        "debt_to_equity": 0.6,
        "dividend_yield": 2.0,
        "revenue_cagr": 0.05,
        "earnings_cagr": 0.08
    }
}

# Run Buffett screen
result = quick_screen(stocks, "buffett")
print(f"Passed: {result.stocks_passed}/{result.total_stocks_screened}")

# Show results
for stock in result.get_passed_stocks():
    print(f"  {stock.ticker}: {stock.name}")
```

#### Creating Custom Screens

```python
from analysis.screening import StockScreeningEngine, ScreenFilter, ScreenOperator

engine = StockScreeningEngine()
engine.add_stocks(stocks)

# Custom filter: High ROE + Low Debt
filters = [
    ScreenFilter("roe", ScreenOperator.GREATER_EQUAL, 0.15),
    ScreenFilter("debt_to_equity", ScreenOperator.LESS_EQUAL, 0.8),
    ScreenFilter("pe_ratio", ScreenOperator.LESS_THAN, 20.0)
]

result = engine.screen(filters)
print(f"Screen passed: {result.stocks_passed} stocks")

for stock in result.results:
    print(f"  {stock.ticker}: {'PASS' if stock.passed else 'FAIL'} ({stock.passing_filters}/{stock.total_filters})")
```

#### Screening Results Formatting

```python
from analysis.screening import format_screen_results

formatted = format_screen_results(result, top_n=5)
import json
print(json.dumps(formatted, indent=2, default=str))
```

---

## Integration Example

### Complete Analysis Pipeline

```python
from models import Company, FinancialPeriod, FinancialMetrics, PeriodType
from analysis.fundamental import calculate_all_metrics
from analysis.historical import HistoricalFinancialData
from analysis.technical import calculate_all_technicals
from analysis.valuation import get_valuation_summary
from datetime import date

# 1. Create company and historical data
company = Company(ticker="BBCA", name="Bank Central Asia Tbk")

hfd = HistoricalFinancialData(ticker="BBCA")

# Add 5 years of data
for year in range(2020, 2025):
    period = FinancialPeriod(
        ticker="BBCA",
        period_end=date(year, 12, 31),
        period_type=PeriodType.ANNUAL
    )
    metrics = FinancialMetrics(
        revenue=50000 * (1.1 ** (year - 2020)),
        net_income=15000 * (1.12 ** (year - 2020)),
        total_assets=500000 * (1.08 ** (year - 2020)),
        total_equity=100000 * (1.05 ** (year - 2020)),
        eps=500 * (1.1 ** (year - 2020))
    )
    hfd.add_record(period, metrics)

# 2. Calculate fundamental metrics (latest period)
latest = hfd.get_latest()
fundamental = calculate_all_metrics(latest.metrics, latest.period_label)

print("=== Fundamental Analysis ===")
for name, result in fundamental.items():
    if result.is_available:
        print(f"{name}: {result.value:.4f}")

# 3. Calculate growth
growth = hfd.get_growth_summary(['revenue', 'net_income'])
print("\n=== Growth Analysis ===")
for name, result in growth.items():
    if result.is_available:
        print(f"{name}: {result.value:.2%}")

# 4. Technical analysis (simulated price data)
import numpy as np
np.random.seed(42)
prices = [8500]
for _ in range(99):
    prices.append(prices[-1] * (1 + np.random.normal(0.0005, 0.015)))

technicals = calculate_all_technicals(prices)
print("\n=== Technical Analysis ===")
print(f"RSI(14): {technicals['rsi_14'].value:.2f}")
print(f"SMA(20): {technicals['sma_20'].value:.2f}")
print(f"SMA(200): {technicals['sma_200'].value:.2f}")

# 5. Valuation
valuation = get_valuation_summary(
    price=8500,
    metrics=latest.metrics,
    historical_pe=[(f"{y}", 12 + (y-2020)*0.5) for y in range(2020, 2025)]
)
print("\n=== Valuation ===")
print(f"P/E: {valuation['valuations']['pe_ratio']['value']:.2f}")
print(f"P/B: {valuation['valuations']['pb_ratio']['value']:.2f}")
```

---

## Test Data Files

The project includes sample data files in `data/`:

- `financial_ratio.json` - 947 financial ratio records
- `allCompanies.json` - Company profiles
- `companyDetailsByKodeEmiten.json` - Detailed company data with directors/shareholders

Use these files to test normalization and analysis functions.

---

## Running All Tests

```bash
cd python
uv run pytest tests/ -v --tb=short
```

Or run specific test suites:

```bash
uv run pytest tests/test_models.py -v
uv run pytest tests/test_normalization.py -v
uv run pytest tests/test_fundamental.py -v
uv run pytest tests/test_historical.py -v
uv run pytest tests/test_technical.py -v
uv run pytest tests/test_valuation.py -v
uv run pytest tests/test_screening.py -v
```
