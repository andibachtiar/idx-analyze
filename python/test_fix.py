#!/usr/bin/env python3
"""Quick verification of fixes."""
import sys
import tempfile

sys.path.insert(0, '/var/www/idx-scraper/python')

print("=== Testing Memory Fix ===")
from ai.memory import (
    ResearchMemory,
    compare_research_theses,
    get_research_history,
    save_research_report,
)

with tempfile.TemporaryDirectory() as tmpdir:
    # Test 1: Save multiple reports via convenience function
    print("\n1. Testing save_research_report convenience function...")
    save_research_report("BBCA", {"test": 1}, storage_path=tmpdir)
    save_research_report("BBCA", {"test": 2}, storage_path=tmpdir)

    history = get_research_history("BBCA", storage_path=tmpdir)
    print(f"   Reports found: {len(history)}")
    assert len(history) == 2, f"Expected 2 reports, got {len(history)}"
    print("   PASS!")

    # Test 2: Compare theses
    print("\n2. Testing compare_research_theses...")
    report1 = {"confidence_score": 0.5, "overall_verdict": "Hold"}
    report2 = {"confidence_score": 0.8, "overall_verdict": "Buy"}
    save_research_report("BBCA", report1, storage_path=tmpdir)
    save_research_report("BBCA", report2, storage_path=tmpdir)

    comparison = compare_research_theses("BBCA", storage_path=tmpdir)
    print(f"   Comparison keys: {comparison.keys()}")
    assert "reports_analyzed" in comparison, "Missing 'reports_analyzed' key"
    assert comparison["reports_analyzed"] == 2, f"Expected 2, got {comparison['reports_analyzed']}"
    print("   PASS!")

print("\n=== All Memory Tests Passed! ===")
