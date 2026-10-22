"""Spec §18.1 (rule matching), §18.2 (alternative explanations + indicator-vs-cause
caution), §18.5 (no firing on absent facts)."""

import pytest

from .conftest import facts_firing, find_rule, make_fact
from engine.rules import CAUTION_TEXT, evaluate_rules, load_rules


def test_load_rules_returns_30_rules():
    rules = load_rules()
    assert len(rules) == 30, f"expected 30 rules, got {len(rules)}"


def _fired_ids(matches):
    return [m.rule_id for m in matches]


def test_working_capital_pressure_rule_fires():
    """Brief example 1: working-capital pressure facts fire RULE-001."""
    rules = load_rules()
    rule = find_rule(rules, "working", "capital")
    matches = evaluate_rules(facts_firing(rule), rules)
    assert rule["rule_id"] in _fired_ids(matches)


def test_capacity_constraint_rule_fires():
    """Brief example 2: capacity-constraint facts fire RULE-002."""
    rules = load_rules()
    rule = find_rule(rules, "capacity")
    matches = evaluate_rules(facts_firing(rule), rules)
    assert rule["rule_id"] in _fired_ids(matches)


def test_rule_does_not_fire_on_absent_facts():
    """§18.5: with no facts at all, nothing fires."""
    assert evaluate_rules([], load_rules()) == []


def test_rule_does_not_fire_on_unrelated_facts():
    """§18.5: facts for one rule must not fire an unrelated rule."""
    rules = load_rules()
    wc_rule = find_rule(rules, "working", "capital")
    other = next(r for r in rules if r["rule_id"] != wc_rule["rule_id"])
    matches = evaluate_rules(facts_firing(other), rules)
    assert wc_rule["rule_id"] not in _fired_ids(matches)


def test_rule_never_fires_on_missing_fact_key():
    """A trigger whose fact_key is absent is never satisfied (no guessing)."""
    rules = load_rules()
    rule = find_rule(rules, "working", "capital")
    facts = facts_firing(rule)
    matches = evaluate_rules(facts[1:], rules)  # drop the first trigger's fact
    assert rule["rule_id"] not in _fired_ids(matches)


def test_fired_rule_has_three_or_more_alternative_explanations():
    """§18.2: every fired rule offers >= 3 alternative explanations."""
    rules = load_rules()
    for keywords in [("working", "capital"), ("capacity",), ("make", "buy")]:
        rule = find_rule(rules, *keywords)
        matches = evaluate_rules(facts_firing(rule), rules)
        match = next(m for m in matches if m.rule_id == rule["rule_id"])
        assert len(match.alternative_explanations) >= 3, (
            f"rule {rule['rule_id']} fired with only "
            f"{len(match.alternative_explanations)} alternative explanations"
        )


def test_fired_rule_carries_indicator_vs_cause_caution():
    """§18.2: the indicator-vs-cause caution is present on fired rules."""
    rules = load_rules()
    rule = find_rule(rules, "working", "capital")
    matches = evaluate_rules(facts_firing(rule), rules)
    match = next(m for m in matches if m.rule_id == rule["rule_id"])
    caution = match.caution.lower()
    assert "indicator" in caution and "cause" in caution, (
        f"caution text missing indicator-vs-cause wording: {match.caution!r}"
    )
    assert match.caution == CAUTION_TEXT


def test_partial_facts_do_not_fire():
    """A rule whose triggers are only half-satisfied must not fire (AND logic)."""
    rules = load_rules()
    rule = find_rule(rules, "working", "capital")
    facts = facts_firing(rule)
    assert len(facts) >= 2
    matches = evaluate_rules(facts[:1], rules)
    assert rule["rule_id"] not in _fired_ids(matches)


def test_evaluate_rules_defaults_to_loaded_rules():
    """evaluate_rules(facts) without rules= still evaluates (loads rules.json)."""
    rules = load_rules()
    rule = find_rule(rules, "capacity")
    matches = evaluate_rules(facts_firing(rule))
    assert rule["rule_id"] in _fired_ids(matches)


def test_fact_marked_not_present_never_satisfies():
    """A fact explicitly marked present=False must not satisfy its trigger."""
    from engine.rules import Fact

    rules = load_rules()
    rule = find_rule(rules, "capacity")
    facts = facts_firing(rule)
    facts[0] = Fact(fact_key=facts[0].fact_key, value=facts[0].value,
                    trend=facts[0].trend, present=False)
    matches = evaluate_rules(facts, rules)
    assert rule["rule_id"] not in _fired_ids(matches)
