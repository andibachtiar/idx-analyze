"""Add Result-Validator score columns to research_candidates (Phase 18k).

Lets the Research tab rank/filter deterministic research candidates by the
quality of their saved AI report (the Result-Validator confidence score). The
score is stamped onto the matching candidate rows whenever ``research_analyze``
(or the ESG/auto-analyze pipeline) saves a validated report for that ticker.

The store method ``_ensure_research_validator_columns`` is an idempotent guard
so the API works even before/without the migration runner applying this file.
"""

name = "202609090018_add_validator_columns_to_research_candidates"


def up(cursor) -> None:
    cursor.execute(
        "ALTER TABLE research_candidates "
        "ADD COLUMN IF NOT EXISTS validator_score NUMERIC(5, 2)"
    )
    cursor.execute(
        "ALTER TABLE research_candidates "
        "ADD COLUMN IF NOT EXISTS validator_tier VARCHAR(20)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS research_candidates_validity_idx "
        "ON research_candidates(validator_score DESC NULLS LAST)"
    )


def down(cursor) -> None:
    cursor.execute(
        "ALTER TABLE research_candidates DROP COLUMN IF EXISTS validator_score"
    )
    cursor.execute(
        "ALTER TABLE research_candidates DROP COLUMN IF EXISTS validator_tier"
    )
