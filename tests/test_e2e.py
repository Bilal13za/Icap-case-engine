"""Three end-to-end analyses driving the full chain:
facts -> rules -> frameworks -> calculations -> recommendation."""

from decimal import Decimal

from .conftest import (
    call_build_recommendation,
    facts_firing,
    find_rule,
    run_calc,
)
from engine.frameworks import recommend_frameworks
from engine.rules import evaluate_rules, load_rules


def _mapped_frameworks(conn, rule_id):
    return [
        r["framework_id"]
        for r in conn.execute(
            "SELECT framework_id FROM RuleFrameworkMappings WHERE rule_id = ?",
            (rule_id,),
        )
    ]


def test_e2e_working_capital_case(conn):
    """Working-capital pressure: facts -> RULE-001 -> frameworks -> receivable
    days -> recommendation."""
    rules = load_rules()
    rule = find_rule(rules, "working", "capital")

    # 1. facts -> rules
    matches = evaluate_rules(facts_firing(rule), rules)
    assert rule["rule_id"] in [m.rule_id for m in matches]

    # 2. rules -> frameworks (DB mapping grounds the choice; engine suggests too)
    mapped = _mapped_frameworks(conn, rule["rule_id"])
    assert mapped, f"no RuleFrameworkMappings for {rule['rule_id']}"
    recs = recommend_frameworks("working_capital", ["receivables", "inventory"])
    assert recs
    assert all(r.relevance_reason.strip() for r in recs)
    assert any(r.framework_id in mapped for r in recs)

    # 3. frameworks -> calculations
    res = run_calc("CALC-REC-DAYS", receivables=120000, credit_sales=1460000)
    assert res.result == Decimal("30")

    # 4. -> recommendation, carrying the quantified finding
    rec = call_build_recommendation(
        calc_summaries=[f"Receivable days are {res.result}, well above terms"],
    )
    assert "Receivable days are 30" in rec["rendered_text"]


def test_e2e_make_or_buy_decision(conn):
    """Make-or-buy: facts -> RULE-009 -> frameworks -> make/buy comparison ->
    recommendation."""
    rules = load_rules()
    rule = find_rule(rules, "make", "buy")

    matches = evaluate_rules(facts_firing(rule), rules)
    assert rule["rule_id"] in [m.rule_id for m in matches]

    mapped = _mapped_frameworks(conn, rule["rule_id"])
    assert mapped
    recs = recommend_frameworks("make_or_buy", ["in-house costs", "supplier quote"])
    assert recs and all(r.relevance_reason.strip() for r in recs)

    res = run_calc("CALC-MAKEBUY", units=1000, buy_price=20,
                   variable_cost_make=12, specific_fixed_cost_make=5000,
                   opportunity_cost=0)
    assert res.result["total_make_cost"] == Decimal("17000")
    assert res.result["total_buy_cost"] == Decimal("20000")
    assert res.result["saving_from_making"] == Decimal("3000")

    rec = call_build_recommendation(
        calc_summaries=["Making saves Rs 3,000 on relevant costs"],
    )
    assert "Rs 3,000" in rec["rendered_text"]


def test_e2e_capital_investment_decision(conn):
    """Capital investment: facts -> RULE-008 -> frameworks -> NPV/IRR/payback
    -> recommendation."""
    rules = load_rules()
    rule = find_rule(rules, "irr")

    matches = evaluate_rules(facts_firing(rule), rules)
    assert rule["rule_id"] in [m.rule_id for m in matches]

    recs = recommend_frameworks("capital_investment", ["project cash flows"])
    assert len(recs) >= 2 and all(r.relevance_reason.strip() for r in recs)

    cash_flows = [-1000, 300, 400, 500]
    npv = run_calc("CALC-NPV", discount_rate=Decimal("0.10"), cash_flows=cash_flows)
    irr = run_calc("CALC-IRR", cash_flows=cash_flows)
    payback = run_calc("CALC-PAYBACK", cash_flows=cash_flows)
    assert npv.result == Decimal("-21.03")
    assert Decimal("8") < irr.result < Decimal("9.5"), f"IRR {irr.result} off"
    assert payback.result == Decimal("2.60")

    rec = call_build_recommendation(
        calc_summaries=[
            f"NPV is {npv.result} at 10%; IRR is {irr.result}%; "
            f"payback is {payback.result} years"
        ],
    )
    assert "NPV is -21.03" in rec["rendered_text"]
