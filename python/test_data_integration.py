"""Test script to verify data integration."""
import sys

sys.path.insert(0, '.')

from ai.data_loader import get_data_loader
from ai.tools import (
    get_company_info,
    get_company_news,
    get_financials,
    get_fundamental_analysis,
    get_stock_price,
)

# Test data loader
print("=" * 60)
print("Testing Data Loader")
print("=" * 60)

loader = get_data_loader()

# Test company info for ADRO
print("\n1. Company Info for ADRO:")
info = loader.get_company_info("ADRO")
if info:
    print(f"   Found: {info.get('name', 'N/A')}")
    print(f"   Sector: {info.get('sector', 'N/A')}")
    print(f"   Industry: {info.get('industry', 'N/A')}")
else:
    print("   Not found")

# Test financial ratios
print("\n2. Financial Ratios for ADRO:")
ratios = loader.get_financial_ratios("ADRO")
if ratios:
    print(f"   ROE: {ratios.get('roe', 'N/A')}%")
    print(f"   ROA: {ratios.get('roa', 'N/A')}%")
    print(f"   Debt-to-Equity: {ratios.get('deRatio', 'N/A')}")
    print(f"   P/E Ratio: {ratios.get('per', 'N/A')}")
else:
    print("   Not found")

# Test stock price
print("\n3. Stock Price for ADRO:")
price = loader.get_stock_price("ADRO")
if price:
    print(f"   Price: {price.get('price', 'N/A')}")
else:
    print("   Not found (index_summary only has index-level data)")

# Test news
print("\n4. News for ADRO:")
news = loader.get_news("ADRO", limit=3)
print(f"   Found {len(news)} news articles")
if news:
    for i, article in enumerate(news[:3]):
        title = article.get('title', article.get('judul', 'No title'))[:50]
        print(f"   {i+1}. {title}...")

# Test tools integration
print("\n" + "=" * 60)
print("Testing Tools Integration")
print("=" * 60)

print("\n5. get_company_info():")
company = get_company_info("ADRO")
print(f"   Name: {company.get('name', 'N/A')}")
print(f"   Sector: {company.get('sector', 'N/A')}")

print("\n6. get_financials():")
financials = get_financials("ADRO")
if financials.get('metrics'):
    print(f"   Has metrics: Yes")
    print(f"   Source: {financials.get('source', 'N/A')}")
else:
    print(f"   Notes: {financials.get('notes', 'N/A')}")

print("\n7. get_fundamental_analysis():")
fund = get_fundamental_analysis("ADRO")
print(f"   Growth: {fund.get('growth', {})}")
print(f"   Profitability keys: {list(fund.get('profitability', {}).keys())}")
print(f"   Notes: {fund.get('notes', 'None')}")

print("\n8. get_stock_price():")
price_tool = get_stock_price("ADRO")
print(f"   Price: {price_tool.get('price', 'N/A')}")
print(f"   Notes: {price_tool.get('notes', 'None')}")

print("\n9. get_company_news():")
news_tool = get_company_news("ADRO", limit=3)
print(f"   Count: {news_tool.get('count', 0)}")
print(f"   News items: {news_tool.get('count', 0)}")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
