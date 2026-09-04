"""Check what data is available for ADRO."""
import json
from pathlib import Path

# Check financial_ratio.json
financial_file = Path("../data/financial_ratio.json")
if financial_file.exists():
    with open(financial_file) as f:
        data = json.load(f)

    # Handle wrapper format
    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    print(f"Financial ratios: {len(data)} records")

    # Find ADRO
    adro = None
    for item in data:
        if item.get("code", "").upper() == "ADRO":
            adro = item
            break

    if adro:
        print(f"\n✓ ADRO found in financial_ratio.json:")
        print(f"  Name: {adro.get('stockName', 'N/A')}")
        print(f"  ROE: {adro.get('roe', 'N/A')}%")
        print(f"  ROA: {adro.get('roa', 'N/A')}%")
        print(f"  P/E: {adro.get('per', 'N/A')}")
        print(f"  Debt/Equity: {adro.get('deRatio', 'N/A')}")
    else:
        print("\n✗ ADRO NOT found in financial_ratio.json")
        print(f"  Sample codes: {[d.get('code') for d in data[:5]]}")

        # Search for Adaro-related companies
        adaro_related = [d for d in data if 'adaro' in d.get('stockName', '').lower()]
        if adaro_related:
            print(f"\n  Found Adaro-related companies:")
            for a in adaro_related:
                print(f"    - {a.get('code')}: {a.get('stockName')}")

# Check companyDetails
company_file = Path("../data/companyDetailsByKodeEmiten.json")
if company_file.exists():
    with open(company_file) as f:
        data = json.load(f)

    print(f"\nCompany details: {len(data)} records")

    adro_company = None
    for item in data:
        if item.get("KodeEmiten", "").upper() == "ADRO":
            adro_company = item
            break

    if adro_company:
        print(f"\n✓ ADRO found in companyDetails:")
        print(f"  Name: {adro_company.get('NamaEmiten', 'N/A')}")
        print(f"  Sector: {adro_company.get('Sektor', 'N/A')}")
        print(f"  Industry: {adro_company.get('Industri', 'N/A')}")
    else:
        print("\n✗ ADRO NOT found in companyDetails")

        # Search for Adaro
        adaro_companies = [d for d in data if 'adaro' in d.get('NamaEmiten', '').lower()]
        if adaro_companies:
            print(f"\n  Found Adaro-related companies:")
            for a in adaro_companies:
                print(f"    - {a.get('KodeEmiten')}: {a.get('NamaEmiten')}")

print("\n" + "="*60)
print("Data Check Complete")
print("="*60)
