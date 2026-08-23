#!/usr/bin/env python3
"""Debug script to test InvestmentReport creation."""
import sys

sys.path.insert(0, '/var/www/idx-scraper/python')

print("Testing InvestmentReport creation...")

try:
    from ai.report_templates import InvestmentReport, ReportSection

    # Test 1: Create report with minimal args
    print("\n1. Creating report with minimal args...")
    report = InvestmentReport(
        ticker="BBCA",
        question="Is BBCA a good investment?",
    )
    print(f"   profitability type: {type(report.profitability)}")
    print(f"   conclusion type: {type(report.conclusion)}")
    print(f"   profitability is ReportSection: {isinstance(report.profitability, ReportSection)}")

    # Test 2: Add claims
    print("\n2. Adding claims...")
    report.add_fact(report.profitability, "ROE is 25%")
    report.add_speculation(report.conclusion, "Stock may rise")

    # Test 3: Get summary
    print("\n3. Getting claim summary...")
    d = report.to_dict()
    summary = d["claim_summary"]
    print(f"   Summary: {summary}")
    print(f"   FACT count: {summary['FACT']}")
    print(f"   SPECULATION count: {summary['SPECULATION']}")
    print(f"   total_claims: {summary['total_claims']}")

    print("\nSUCCESS!")

except Exception as e:
    print(f"\nFAILED: {e}")
    import traceback
    traceback.print_exc()
