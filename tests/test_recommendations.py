"""Recommendation builder contract (ValueError on empty confirmations/options)
and spec §18.8 (decision-comparison weights: sum to 100, no invented weights).

Note: build_recommendation takes no weights parameter — weighting lives in the
Decision Comparator screen (app layer) and the EvaluationCriteria table. The
data-level invariant (weights sum to 100 per case) is tested here; the UI
validation is covered when app.py lands.
"""

import pytest

from .conftest import call_build_recommendation
from engine.recommendations import build_recommendation


def test_empty_confirmed_facts_raises_valueerror():
    """Contract: build_recommendation raises ValueError on empty confirmations."""
    with pytest.raises(ValueError):
        call_build_recommendation(confirmed_fact_ids=[])


def test_empty_options_raises_valueerror():
    with pytest.raises(ValueError):
        call_build_recommendation(options=[])


def test_unknown_selected_option_raises_valueerror():
    with pytest.raises(ValueError):
        call_build_recommendation(selected_option_id="Z")


def test_option_missing_keys_raises_valueerror():
    with pytest.raises(ValueError):
        call_build_recommendation(options=[{"option_id": "A"}])


def test_recommendation_built_from_supplied_inputs_only():
    result = call_build_recommendation()
    assert set(result) == {"title", "sections", "rendered_text"}
    assert "Option B" in result["title"]
    assert "Option B" in result["sections"]["recommended_option"]
    # evidence takes precedence over financial_impact as the stated reason
    assert "Option B is preferable because Case analysis." in result["rendered_text"]
    # supplied calc summaries and facts are carried through verbatim
    assert "NPV is positive at the 10% discount rate" in result["rendered_text"]
    assert result["sections"]["supporting_facts"] == ["fact-1: receivables days rising"]
    assert result["rendered_text"].startswith("# Recommendation: Option B")


def test_alternatives_considered_lists_rejected_options():
    result = call_build_recommendation()
    alts = result["sections"]["alternatives_considered"]
    assert len(alts) == 1 and "Option A" in alts[0]


def test_evaluation_criteria_weights_sum_to_100(conn):
    """§18.8 (data level): where a case has evaluation criteria, the weights
    must sum to 100 — the comparator must not invent weights."""
    rows = conn.execute(
        "SELECT case_id, SUM(weight) AS total, COUNT(*) AS n "
        "FROM EvaluationCriteria GROUP BY case_id"
    ).fetchall()
    if not rows:
        pytest.skip("no evaluation criteria seeded yet")
    for row in rows:
        assert abs(row["total"] - 100) < 1e-9, (
            f"case {row['case_id']}: criteria weights sum to {row['total']}, want 100"
        )
