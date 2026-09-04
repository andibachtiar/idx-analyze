"""Test script to verify data loading is working."""
import sys

sys.path.insert(0, '.')

from ai.data_loader import get_data_loader

print("="*60)
print("Testing Data Loader")
print("="*60)

loader = get_data_loader()

# Test company info
print("\n1. Testing Company Info:")
for ticker in ['ADRO', 'BBCA', 'AAII']:
    info = loader.get_company_info(ticker)
    if info:
        print(f"   ✓ {ticker}: {info.get('name', 'N/A')} ({info.get('sector', 'N/A')})")
    else:
        print(f"   ✗ {ticker}: Not found")

# Test financial ratios
print("\n2. Testing Financial Ratios:")
for ticker in ['ADRO', 'BBCA', 'AAII']:
    ratios = loader.get_financial_ratios(ticker)
    if ratios:
        print(f"   ✓ {ticker}: ROE={ratios.get('roe', 'N/A')}%, P/E={ratios.get('per', 'N/A')}")
    else:
        print(f"   ✗ {ticker}: Not found")

# Test stock price
print("\n3. Testing Stock Price:")
for ticker in ['ADRO', 'BBCA']:
    price = loader.get_stock_price(ticker)
    if price:
        print(f"   ✓ {ticker}: Price={price.get('price', 'N/A')}")
    else:
        print(f"   ✗ {ticker}: Not found (index_summary may not have individual prices)")

# Test news
print("\n4. Testing News:")
for ticker in ['ADRO', 'BBCA']:
    news = loader.get_news(ticker, limit=3)
    print(f"   {ticker}: {len(news)} articles found")
    if news:
        for i, article in enumerate(news[:2]):
            title = article.get('title', article.get('judul', 'No title'))[:50]
            print(f"      - {title}...")

# Test data status
print("\n5. Data Status Summary:")
for ticker in ['ADRO', 'BBCA', 'AAII']:
    status = loader.get_data_status(ticker)
    available = sum(status.values())
    print(f"   {ticker}: {available}/4 data sources available")
    for k, v in status.items():
        print(f"      - {k}: {'✓' if v else '✗'}")

print("\n" + "="*60)
print("Test Complete")
print("="*60)
