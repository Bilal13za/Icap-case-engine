"""Deterministic trigger-rule engine.

A rule fires when ALL of its triggers match the supplied facts. Trigger
conditions use a small mini-language per trigger dict::

    {"fact_key": str, "equals": X}
    {"fact_key": str, "gt" | "lt" | "gte" | "lte": X}   # numeric, via Decimal
    {"fact_key": str, "in": [X, Y, ...]}
    {"fact_key": str, "trend": "up" | "down" | "flat"}

A trigger whose ``fact_key`` is missing (or whose fact is marked not present)
is NEVER satisfied -- the engine never assumes a fact.

Pure Python: no Streamlit, no AI/LLM, no network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

CAUTION_TEXT = (
    "Indicator only \u2014 not a proven cause. "
    "Rule out alternative explanations before concluding."
)


@dataclass
class Fact:
    """One observed case fact."""

    fact_key: str
    value: Any = None
    trend: str | None = None  # "up" / "down" / "flat"
    present: bool = True


@dataclass
class RuleMatch:
    """A rule whose triggers all matched the supplied facts."""

    rule_id: str
    title: str
    interpretation: str
    alternative_explanations: list[str] = field(default_factory=list)
    info_needed: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    recommended_analysis: list[str] = field(default_factory=list)
    source: str = ""
    review_status: str = "draft"
    caution: str = CAUTION_TEXT


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_data_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    if p.exists():
        return p
    return _project_root() / p


def load_rules(path: str | Path = "data/rules.json") -> list[dict]:
    """Load trigger rules from a JSON file (a JSON list of rule dicts).

    A relative ``path`` is resolved against the current working directory
    first, then against the project root.
    """
    resolved = _resolve_data_path(path)
    with open(resolved, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(
            f"Rule file {resolved} must contain a JSON list, "
            f"got {type(data).__name__}"
        )
    return data


def _as_decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise InvalidOperation("boolean is not numeric")
    return Decimal(str(value))


def _trigger_matches(facts: dict[str, Fact], trigger: dict) -> bool:
    """Check one trigger dict against the fact map."""
    key = trigger.get("fact_key")
    fact = facts.get(key) if isinstance(key, str) else None
    if fact is None or not fact.present:
        return False

    # Trend condition: {"fact_key": K, "trend": "up"}
    if "trend" in trigger:
        return fact.trend == trigger["trend"]

    if "equals" in trigger:
        return fact.value == trigger["equals"]

    if "in" in trigger:
        allowed = trigger["in"]
        try:
            return fact.value in allowed
        except TypeError:
            return False

    for op in ("gt", "lt", "gte", "lte"):
        if op in trigger:
            try:
                actual = _as_decimal(fact.value)
                bound = _as_decimal(trigger[op])
            except (InvalidOperation, ValueError, TypeError):
                return False
            if op == "gt":
                return actual > bound
            if op == "lt":
                return actual < bound
            if op == "gte":
                return actual >= bound
            return actual <= bound

    # Bare {"fact_key": K}: satisfied when the fact is present.
    return True


def _rule_to_match(rule: dict) -> RuleMatch:
    return RuleMatch(
        rule_id=str(rule.get("rule_id", "")),
        title=str(rule.get("title", "")),
        interpretation=str(rule.get("interpretation", "")),
        alternative_explanations=list(rule.get("alternative_explanations", [])),
        info_needed=list(rule.get("info_needed", [])),
        concepts=list(rule.get("relevant_concepts", [])),
        recommended_analysis=list(rule.get("recommended_analysis", [])),
        source=str(rule.get("rule_source", "")),
        review_status=str(rule.get("review_status", "draft")),
        caution=CAUTION_TEXT,
    )


def evaluate_rules(
    facts: list[Fact], rules: list[dict] | None = None
) -> list[RuleMatch]:
    """Return a RuleMatch for every rule whose triggers ALL match.

    ``facts`` is the student's confirmed fact list. ``rules`` defaults to the
    rules loaded from ``data/rules.json``. Evaluation order follows rule order.
    """
    if rules is None:
        rules = load_rules()
    fact_map = {f.fact_key: f for f in facts}
    matches: list[RuleMatch] = []
    for rule in rules:
        triggers = rule.get("triggers", [])
        if not isinstance(triggers, list):
            continue
        if all(_trigger_matches(fact_map, t) for t in triggers):
            matches.append(_rule_to_match(rule))
    return matches
