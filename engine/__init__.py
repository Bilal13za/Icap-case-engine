"""Deterministic case-analysis engines (pure Python, no Streamlit)."""

from .rules import (
    CAUTION_TEXT,
    Fact,
    RuleMatch,
    evaluate_rules,
    load_rules,
)
from .frameworks import (
    DECISION_TYPES,
    FrameworkRecommendation,
    recommend_frameworks,
)
from .recommendations import build_recommendation

__all__ = [
    "CAUTION_TEXT",
    "Fact",
    "RuleMatch",
    "evaluate_rules",
    "load_rules",
    "DECISION_TYPES",
    "FrameworkRecommendation",
    "recommend_frameworks",
    "build_recommendation",
]
