#!/usr/bin/env python3
"""Verify FinancialMetrics has the new fields."""
import sys

sys.path.insert(0, '/var/www/idx-scraper/python')

print("Testing FinancialMetrics...")
try:
    from models import FinancialMetrics

    # Test creating with new fields
    metrics = FinancialMetrics(
        revenue=10000.0,
        net_income=1500.0,
        total_equity=5000.0,
        total_assets=20000.0,
        total_debt=3000.0,
        eps=150.0,
        shares_outstanding=1000000.0,
        roe=0.25,
        roa=0.12,
        debt_to_equity=0.3,
        revenue_cagr_3y=0.10,
    )

    print(f"  revenue_cagr_3y: {metrics.revenue_cagr_3y}")
    print(f"  is_empty: {metrics.is_empty()}")
    print("  SUCCESS!")

except Exception as e:
    print(f"  FAILED: {e}")
    import traceback
    traceback.print_exc()
