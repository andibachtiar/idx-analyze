"""Add yfinance cash-flow / interest fields to financial_ratios (D3).

The IDX ratio source leaves gross profit, cash, interest expense, operating cash
flow and capex empty, so the analysis engine cannot compute gross margin,
interest coverage, net debt/EBITDA or FCF margin. These columns are filled by
the yfinance enrichment scraper for the latest ratio row.

Multiple statements yield the same values in the same IDX billing convention
(monetary figures in IDR billions), so interest_coverage / net_debt_to_ebitda /
fcf_margin stay derivable deterministically from the stored components.
"""

name = "202609050015_add_cashflow_fields_to_financial_ratios"


def up(cursor) -> None:
    cursor.execute(
        "ALTER TABLE financial_ratios ADD COLUMN IF NOT EXISTS interest_expense NUMERIC"
    )
    cursor.execute(
        "ALTER TABLE financial_ratios ADD COLUMN IF NOT EXISTS operating_cash_flow NUMERIC"
    )
    cursor.execute(
        "ALTER TABLE financial_ratios ADD COLUMN IF NOT EXISTS capital_expenditures NUMERIC"
    )


def down(cursor) -> None:
    cursor.execute(
        "ALTER TABLE financial_ratios DROP COLUMN IF EXISTS capital_expenditures"
    )
    cursor.execute(
        "ALTER TABLE financial_ratios DROP COLUMN IF EXISTS operating_cash_flow"
    )
    cursor.execute(
        "ALTER TABLE financial_ratios DROP COLUMN IF EXISTS interest_expense"
    )
