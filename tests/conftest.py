"""Shared fixtures and contract adapters for the ICAP Case Engine test suite.

The suite tests the contracts from the build brief against the real module
APIs (engine/rules.py, engine/frameworks.py, engine/recommendations.py,
calcs/calculations.py, dbcore.py, seed.py).

DB isolation: every test that touches the database uses a tmp-dir database via
``dbcore.init_db(tmp_path / "case_engine.db")``. The real user database is
never touched.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import dbcore  # noqa: E402
import seed as seedmod  # noqa: E402


# ---------------------------------------------------------------- fixtures
@pytest.fixture()
def tmp_db(tmp_path):
    """Path to an isolated database file."""
    return tmp_path / "case_engine.db"


@pytest.fixture()
def conn(tmp_db):
    """Seeded sqlite3 connection to an isolated database."""
    dbcore.init_db(tmp_db)
    connection = dbcore.get_conn(tmp_db)
    yield connection
    connection.close()


@pytest.fixture()
def unseeded_conn(tmp_db):
    """Connection to an isolated database with schema but no seed content."""
    import sqlite3

    schema = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
    connection = sqlite3.connect(str(tmp_db))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(schema)
    connection.commit()
    yield connection
    connection.close()


# ---------------------------------------------------------------- rules
def make_fact(name, value=None, trend=None):
    """Construct engine.rules.Fact for a fact_key."""
    from engine.rules import Fact

    return Fact(fact_key=name, value=value, trend=trend)


def _trigger_fact(trigger):
    """Build one Fact satisfying a single trigger dict."""
    key = trigger["fact_key"]
    if "trend" in trigger:
        return make_fact(key, trend=trigger["trend"])
    if "equals" in trigger:
        return make_fact(key, value=trigger["equals"])
    if "in" in trigger:
        allowed = trigger["in"]
        assert allowed, f"trigger 'in' list empty for {key}"
        return make_fact(key, value=allowed[0])
    for op in ("gt", "gte", "lt", "lte"):
        if op in trigger:
            bound = Decimal(str(trigger[op]))
            if op == "gt":
                return make_fact(key, value=bound + 1)
            if op == "gte":
                return make_fact(key, value=bound)
            if op == "lt":
                return make_fact(key, value=bound - 1)
            return make_fact(key, value=bound)
    # bare {"fact_key": K}: satisfied by a present fact
    return make_fact(key, value="observed")


def facts_firing(rule):
    """Build a fact list satisfying ALL of the rule's triggers."""
    import json as _json

    triggers = rule.get("triggers", [])
    if isinstance(triggers, str):
        triggers = _json.loads(triggers)
    facts = [_trigger_fact(t) for t in triggers if isinstance(t, dict)]
    if not facts:
        raise AssertionError(f"Rule {rule.get('rule_id')!r} has no usable triggers")
    return facts


def find_rule(rules, *keywords):
    """First rule whose title mentions all keywords (case-insensitive)."""
    for rule in rules:
        if all(k.lower() in str(rule.get("title", "")).lower() for k in keywords):
            return rule
    raise AssertionError(
        f"No rule with keywords {keywords}; titles: {[r.get('title') for r in rules]}"
    )


# ---------------------------------------------------------------- frameworks
def decision_types():
    from engine.frameworks import DECISION_TYPES

    if isinstance(DECISION_TYPES, dict):
        return list(DECISION_TYPES.keys())
    return list(DECISION_TYPES)


# ---------------------------------------------------------------- calculations
def calc_ids():
    from calcs.calculations import list_calculations

    return [entry["calc_id"] for entry in list_calculations()]


def find_calc(keyword):
    hits = [c for c in calc_ids() if keyword.lower() in c.lower()]
    if not hits:
        raise AssertionError(f"No calculation id containing {keyword!r}; have: {calc_ids()}")
    return hits[0]


def calc_input_names(calc_id):
    """Required input names for a calculation."""
    from calcs.calculations import missing_inputs

    return list(missing_inputs(calc_id, {}))


def run_calc(calc_id, **inputs):
    from calcs.calculations import run_calculation

    return run_calculation(calc_id, **inputs)


# ---------------------------------------------------------------- recommendations
def _option(oid, description, financial_impact="Improves cash flow"):
    return {
        "option_id": oid,
        "description": description,
        "financial_impact": financial_impact,
        "nonfinancial_benefits": "Lower risk",
        "costs": "Implementation cost",
        "risks": ["Execution risk"],
        "assumptions": ["Assumptions hold"],
        "evidence": "Case analysis",
    }


def call_build_recommendation(**overrides):
    """Call build_recommendation with sane defaults, overridable per test."""
    from engine.recommendations import build_recommendation

    kwargs = dict(
        selected_option_id="B",
        options=[
            _option("A", "Status quo"),
            _option("B", "Invest", financial_impact="Positive NPV of Rs 21m"),
        ],
        confirmed_fact_ids=["fact-1: receivables days rising"],
        calc_summaries=["NPV is positive at the 10% discount rate"],
        key_assumption="The 10% discount rate remains appropriate",
        conditions_for_change=["Cost overrun above 15%"],
        implementation_steps=["Obtain board approval"],
        kpis=["Payback period"],
        review_timing="Quarterly review",
    )
    kwargs.update(overrides)
    return build_recommendation(**kwargs)
