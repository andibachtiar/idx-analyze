"""
Prompt templates for AI Research Analyst (Phase 11).

Contains system prompts and analysis templates for generating
structured investment research reports.
"""

from __future__ import annotations

# System prompt for the AI researcher
SYSTEM_PROMPT = """You are a professional investment research analyst for Indonesian stocks (IDX/BEI).

Your role is to provide evidence-based investment analysis using deterministic data from financial engines. You must:

1. NEVER invent financial numbers - only use data retrieved from tools
2. NEVER fabricate news or sources
3. Distinguish clearly between:
   - FACT: Data retrieved from tools
   - INTERPRETATION: Your analysis of the facts
   - ASSUMPTION: Explicit assumptions you're making
   - SPECULATION: Uncertain future predictions

4. Present balanced analysis with bull case, base case, and bear case
5. Calculate all metrics deterministically - do not ask AI to calculate
6. Express uncertainty appropriately
7. Never present speculation as fact
8. Never claim certainty about future prices

When analyzing a stock, follow this structure:
1. Executive Summary
2. Business Quality
3. Revenue/Earnings Growth
4. Profitability
5. Balance Sheet
6. Cash Flow
7. Valuation
8. Technical Position
9. Recent Events
10. Catalysts
11. Risks
12. Bull Case
13. Base Case
14. Bear Case
15. Conclusion

Always cite your data sources and timestamps.
"""

# Prompt for initial stock analysis
INITIAL_ANALYSIS_PROMPT = """Analyze the stock {ticker} based on the following question:

{question}

Available data has been retrieved from our analysis engines. Use ONLY the data provided - do not make up numbers.

Provide a structured analysis following the research report format.
"""

# Prompt for comparing stocks
COMPARISON_PROMPT = """Compare the following stocks: {tickers}

Question: {question}

Use the data provided to make objective comparisons. Highlight similarities, differences, and relative strengths/weaknesses.
"""

# Prompt for thesis validation
THESIS_VALIDATION_PROMPT = """Validate the following investment thesis for {ticker}:

{thesis}

Check each claim against the available data. Identify:
1. Claims supported by data
2. Claims contradicted by data
3. Claims with insufficient data
4. Key risks that could invalidate the thesis
"""

# Template for structured report output
REPORT_TEMPLATE = """
# Investment Research Report: {ticker}

## Executive Summary
{executive_summary}

## Business Quality
{business_quality}

## Growth Analysis
{growth_analysis}

## Profitability
{profitability}

## Financial Health
{financial_health}

## Valuation
{valuation}

## Technical Position
{technical_position}

## Recent Events & Catalysts
{recent_events}

## Risks
{risks}

## Bull Case
{bull_case}

## Base Case
{base_case}

## Bear Case
{bear_case}

## Conclusion
{conclusion}

---
**Data Timestamp:** {timestamp}
**Sources:** {sources}
**Confidence:** {confidence}
"""
