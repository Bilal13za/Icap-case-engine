"""Spec §18.3: framework selection — multi-framework allowed, relevance reasons,
unsuitable_when, missing-information readiness."""

import pytest

from .conftest import decision_types
from engine.frameworks import DECISION_TYPES, recommend_frameworks


def test_decision_types_nonempty():
    assert isinstance(DECISION_TYPES, dict) and DECISION_TYPES


def test_multi_framework_allowed():
    """§18.3: a broad decision may legitimately suggest several frameworks."""
    recs = recommend_frameworks("capital_investment", [])
    assert len(recs) >= 2, f"expected several frameworks, got {len(recs)}"
    ids = [r.framework_id for r in recs]
    assert len(set(ids)) == len(ids), "duplicate framework recommendations"


def test_every_recommendation_has_relevance_reason():
    for dt in ["working_capital", "capital_investment", "make_or_buy", "risk_management"]:
        for fw in recommend_frameworks(dt, ["some input"]):
            assert fw.relevance_reason and fw.relevance_reason.strip(), (
                f"{dt}: framework {fw.framework_id} recommended without a relevance reason"
            )


def test_every_recommendation_states_unsuitable_when():
    for dt in ["working_capital", "capital_investment", "make_or_buy", "risk_management"]:
        for fw in recommend_frameworks(dt, ["some input"]):
            assert fw.unsuitable_when and fw.unsuitable_when.strip(), (
                f"{dt}: framework {fw.framework_id} recommended without unsuitable_when"
            )


def test_missing_inputs_reported_not_crashed():
    """§18.3/§18.5: with no inputs available, every framework reports
    readiness='missing_info' and lists the missing inputs — never raises."""
    for dt in ["working_capital", "capital_investment", "make_or_buy"]:
        recs = recommend_frameworks(dt, [])
        assert recs
        for fw in recs:
            assert fw.readiness == "missing_info", (
                f"{dt}/{fw.framework_id}: readiness={fw.readiness!r} with no inputs"
            )
            assert fw.missing, (
                f"{dt}/{fw.framework_id}: missing inputs not listed"
            )
            assert set(fw.missing) <= set(fw.inputs_needed)


def test_readiness_turns_ready_when_inputs_available():
    """Supplying every needed input flips readiness to 'ready'."""
    recs = recommend_frameworks("working_capital", [])
    fw = recs[0]
    ready_recs = recommend_frameworks("working_capital", list(fw.inputs_needed))
    ready = next(r for r in ready_recs if r.framework_id == fw.framework_id)
    assert ready.readiness == "ready"
    assert ready.missing == []


def test_recommendations_deterministic():
    first = [f.framework_id for f in recommend_frameworks("valuation", ["x"])]
    second = [f.framework_id for f in recommend_frameworks("valuation", ["x"])]
    assert first == second


def test_unknown_decision_type_returns_empty():
    assert recommend_frameworks("not_a_decision_type", []) == []


def test_framework_ids_match_catalogue(conn):
    """Recommended FW-* ids exist in the seeded Frameworks catalogue."""
    catalogue = {r["framework_id"] for r in conn.execute("SELECT framework_id FROM Frameworks")}
    for dt in decision_types():
        for fw in recommend_frameworks(dt, []):
            assert fw.framework_id in catalogue, (
                f"{dt}: {fw.framework_id} not in Frameworks table"
            )
