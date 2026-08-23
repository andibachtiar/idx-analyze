#!/usr/bin/env python3
"""Quick verification script."""
import sys

sys.path.insert(0, '/var/www/idx-scraper/python')

print("Testing imports...")
try:
    from ai.prompts.technical import (
        TechnicalAnalysisResult,
        analyze_stock_technicals,
        generate_technical_prompt,
        get_technical_analysis_with_llm,
    )
    print("✓ Technical prompts imported successfully")
except Exception as e:
    print(f"✗ Technical prompts import failed: {e}")

try:
    from ai.prompts.valuation import (
        ValuationResult,
        WACCCalculation,
        analyze_stock_valuation,
    )
    print("✓ Valuation prompts imported successfully")
except Exception as e:
    print(f"✗ Valuation prompts import failed: {e}")

try:
    from ai.prompts import (
        COMPARISON_PROMPT,
        SYSTEM_PROMPT,
    )
    from ai.prompts import (
        TechnicalAnalysisResult as TAResult,
    )
    from ai.prompts import (
        analyze_stock_technicals as analyze_tech,
    )
    print("✓ Combined prompts module imported successfully")
except Exception as e:
    print(f"✗ Combined prompts import failed: {e}")

print("\nDone!")
