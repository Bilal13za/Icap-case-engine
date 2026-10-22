"""Deterministic framework recommender.

Maps a decision type to 1-4 framework IDs from the fixed FW-* catalogue,
each with a relevance reason, the inputs it needs, and when it is unsuitable.
Readiness is computed deterministically from the student's available inputs:
a framework is "ready" only when every needed input is available
(case-insensitive substring match); otherwise readiness is "missing_info"
with the missing inputs listed. A calculation/framework is NEVER recommended
merely because it exists.

Pure Python: no Streamlit, no AI/LLM, no network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DECISION_TYPES: dict[str, str] = {
    "external_analysis": "External analysis",
    "internal_analysis": "Internal analysis",
    "ethical_decision": "Ethical decision",
    "performance_analysis": "Performance analysis",
    "working_capital": "Working capital",
    "budgeting": "Budgeting",
    "capital_investment": "Capital investment",
    "financing_choice": "Financing choice",
    "valuation": "Valuation",
    "ma_appraisal": "M&A appraisal",
    "risk_management": "Risk management",
    "hedging": "Hedging",
    "portfolio": "Portfolio",
    "make_or_buy": "Make or buy",
    "special_order": "Special order",
    "product_mix": "Product mix",
    "pricing": "Pricing",
    "costing_decision": "Costing decision",
    "capacity": "Capacity",
}


@dataclass
class FrameworkRecommendation:
    framework_id: str
    name: str
    relevance_reason: str
    inputs_needed: list[str] = field(default_factory=list)
    unsuitable_when: str = ""
    readiness: str = "missing_info"  # "ready" | "missing_info"
    missing: list[str] = field(default_factory=list)


# Deterministic mapping table: decision_type -> list of framework entries.
# Framework IDs are the fixed FW-* catalogue IDs (seeded by Builder A in
# data/frameworks.json); names below are fallbacks if that file is absent.
_FRAMEWORK_TABLE: dict[str, list[dict]] = {
    "external_analysis": [
        {
            "framework_id": "FW-PESTEL",
            "name": "PESTEL analysis",
            "relevance_reason": (
                "Structures the macro-environmental factors (political, economic, "
                "social, technological, environmental, legal) that shape the decision."
            ),
            "inputs_needed": ["key macro factors", "industry context"],
            "unsuitable_when": "The decision is purely internal with no material external drivers.",
        },
        {
            "framework_id": "FW-PORTER5",
            "name": "Porter's five forces",
            "relevance_reason": (
                "Assesses industry attractiveness and competitive pressure from rivals, "
                "entrants, substitutes, suppliers and customers."
            ),
            "inputs_needed": ["industry structure", "competitor information"],
            "unsuitable_when": "The decision does not depend on industry or competitive dynamics.",
        },
        {
            "framework_id": "FW-STAKEHOLDER",
            "name": "Stakeholder analysis",
            "relevance_reason": (
                "Identifies who is affected by the decision and how much influence "
                "each stakeholder has over it."
            ),
            "inputs_needed": ["stakeholder list", "stakeholder interests"],
            "unsuitable_when": "Stakeholder impacts are trivial or already fully understood.",
        },
    ],
    "internal_analysis": [
        {
            "framework_id": "FW-SWOT",
            "name": "SWOT analysis",
            "relevance_reason": (
                "Organises internal strengths/weaknesses against external "
                "opportunities/threats into a single view."
            ),
            "inputs_needed": ["internal capabilities", "external factors"],
            "unsuitable_when": "Used alone as the whole analysis -- it classifies but does not quantify.",
        },
        {
            "framework_id": "FW-VALUECHAIN",
            "name": "Value chain analysis",
            "relevance_reason": (
                "Breaks activities into primary and support activities to locate "
                "cost and differentiation advantages."
            ),
            "inputs_needed": ["activity cost breakdown", "process map"],
            "unsuitable_when": "Activity-level cost data is unavailable.",
        },
        {
            "framework_id": "FW-BUSMODEL",
            "name": "Business model canvas",
            "relevance_reason": (
                "Maps how the business creates, delivers and captures value across "
                "nine building blocks."
            ),
            "inputs_needed": ["revenue model", "customer segments", "key resources"],
            "unsuitable_when": "The question is narrowly financial rather than strategic.",
        },
    ],
    "ethical_decision": [
        {
            "framework_id": "FW-TUCKER5",
            "name": "Tucker's 5-question ethical model",
            "relevance_reason": (
                "Applies Tucker's five questions as a structured ethical "
                "decision-making sequence (see the framework library for the model's steps)."
            ),
            "inputs_needed": ["facts of the situation", "affected parties"],
            "unsuitable_when": "The issue has no ethical dimension and is purely technical.",
        },
        {
            "framework_id": "FW-AAA7",
            "name": "AAA 7-step ethical decision model",
            "relevance_reason": (
                "Applies the American Accounting Association 7-step model for "
                "ethical decision-making (see the framework library for the model's steps)."
            ),
            "inputs_needed": ["facts of the situation", "ethical principles at stake"],
            "unsuitable_when": "The issue has no ethical dimension and is purely technical.",
        },
        {
            "framework_id": "FW-STAKEHOLDER",
            "name": "Stakeholder analysis",
            "relevance_reason": (
                "Maps who gains, who loses and who must be told, which an ethical "
                "recommendation must address."
            ),
            "inputs_needed": ["stakeholder list", "stakeholder interests"],
            "unsuitable_when": "Stakeholder impacts are trivial or already fully understood.",
        },
    ],
    "performance_analysis": [
        {
            "framework_id": "FW-RATIO",
            "name": "Ratio analysis",
            "relevance_reason": (
                "Quantifies profitability, liquidity, efficiency and gearing from "
                "the financial statements."
            ),
            "inputs_needed": ["financial statements", "comparative figures"],
            "unsuitable_when": "Statements are unavailable or unreliable.",
        },
        {
            "framework_id": "FW-TREND",
            "name": "Trend analysis",
            "relevance_reason": (
                "Shows the direction of key figures over several periods so a "
                "single year's ratios are not misread."
            ),
            "inputs_needed": ["multi-period financial data"],
            "unsuitable_when": "Only one period of data exists.",
        },
        {
            "framework_id": "FW-BENCHMARK",
            "name": "Benchmarking",
            "relevance_reason": (
                "Compares performance against competitors or industry averages to "
                "judge whether a ratio is good or bad."
            ),
            "inputs_needed": ["peer or industry data"],
            "unsuitable_when": "No comparable peer or industry data exists.",
        },
        {
            "framework_id": "FW-VARIANCE",
            "name": "Variance analysis",
            "relevance_reason": (
                "Explains the gap between actual and budgeted performance by "
                "price, usage and volume effects."
            ),
            "inputs_needed": ["budget figures", "actual figures", "standards"],
            "unsuitable_when": "No budget or standard was set.",
        },
    ],
    "working_capital": [
        {
            "framework_id": "FW-WCAP",
            "name": "Working-capital cycle analysis",
            "relevance_reason": (
                "Measures the cash conversion cycle (receivable days + inventory "
                "days - payable days) to find where cash is trapped."
            ),
            "inputs_needed": ["receivables", "inventory", "payables", "sales/purchases"],
            "unsuitable_when": "The business has no meaningful working-capital cycle (e.g. pure services, cash sales).",
        },
        {
            "framework_id": "FW-RATIO",
            "name": "Ratio analysis",
            "relevance_reason": (
                "Liquidity and efficiency ratios (current, quick, turnover days) "
                "quantify working-capital pressure."
            ),
            "inputs_needed": ["financial statements", "comparative figures"],
            "unsuitable_when": "Statements are unavailable or unreliable.",
        },
        {
            "framework_id": "FW-TREND",
            "name": "Trend analysis",
            "relevance_reason": (
                "Tracks working-capital ratios over time to distinguish a trend "
                "from a one-off movement."
            ),
            "inputs_needed": ["multi-period financial data"],
            "unsuitable_when": "Only one period of data exists.",
        },
    ],
    "budgeting": [
        {
            "framework_id": "FW-VARIANCE",
            "name": "Variance analysis",
            "relevance_reason": (
                "Compares actuals against budget/flexed budget to identify "
                "controllable adverse variances."
            ),
            "inputs_needed": ["budget figures", "actual figures", "standards"],
            "unsuitable_when": "No budget or standard was set.",
        },
        {
            "framework_id": "FW-KPI",
            "name": "KPI scorecard",
            "relevance_reason": (
                "Translates the budget into a small set of measurable targets "
                "for monitoring and accountability."
            ),
            "inputs_needed": ["strategic objectives", "measurable targets"],
            "unsuitable_when": "Objectives cannot be expressed as measurable targets.",
        },
    ],
    "capital_investment": [
        {
            "framework_id": "FW-CAPAPP",
            "name": "Capital appraisal",
            "relevance_reason": (
                "General investment-appraisal discipline: identify relevant cash "
                "flows, choose a discount rate, apply decision rules."
            ),
            "inputs_needed": ["project cash flows", "discount rate", "project life"],
            "unsuitable_when": "Cash flows cannot be estimated even approximately.",
        },
        {
            "framework_id": "FW-NPV",
            "name": "NPV appraisal",
            "relevance_reason": (
                "Discounts all relevant cash flows at the cost of capital; "
                "accept if NPV > 0. Theoretically the strongest decision rule."
            ),
            "inputs_needed": ["project cash flows", "discount rate"],
            "unsuitable_when": "The discount rate cannot be estimated.",
        },
        {
            "framework_id": "FW-SENS",
            "name": "Sensitivity analysis",
            "relevance_reason": (
                "Tests how far key variables can move before the decision "
                "changes, exposing the riskiest assumptions."
            ),
            "inputs_needed": ["base-case NPV model", "key variable ranges"],
            "unsuitable_when": "The base-case model itself is not built yet.",
        },
        {
            "framework_id": "FW-SCENARIO",
            "name": "Scenario analysis",
            "relevance_reason": (
                "Values the project under coherent best/base/worst cases with "
                "probabilities for an expected NPV."
            ),
            "inputs_needed": ["scenario cash flows", "scenario probabilities"],
            "unsuitable_when": "Scenarios cannot be defined or weighted.",
        },
    ],
    "financing_choice": [
        {
            "framework_id": "FW-WACC",
            "name": "WACC estimation",
            "relevance_reason": (
                "Estimates the blended cost of capital used as the discount rate "
                "and as the benchmark any financing must beat."
            ),
            "inputs_needed": ["cost of equity", "cost of debt", "tax rate", "market values"],
            "unsuitable_when": "Market values of debt and equity are unobtainable.",
        },
        {
            "framework_id": "FW-FINCHOICE",
            "name": "Financing-choice analysis",
            "relevance_reason": (
                "Compares debt vs equity (vs hybrids) on cost, risk, control, "
                "covenants and flexibility."
            ),
            "inputs_needed": ["financing options", "cash flow forecasts"],
            "unsuitable_when": "Only one financing source is realistically available.",
        },
        {
            "framework_id": "FW-CAPM",
            "name": "CAPM cost of equity",
            "relevance_reason": (
                "Estimates the cost of equity from systematic risk "
                "(Ke = Rf + beta x (Rm - Rf))."
            ),
            "inputs_needed": ["risk-free rate", "beta", "market return"],
            "unsuitable_when": "No reliable beta or market return estimate exists.",
        },
    ],
    "valuation": [
        {
            "framework_id": "FW-VALUATION",
            "name": "Business valuation",
            "relevance_reason": (
                "General valuation discipline: choose the method(s) suited to "
                "the purpose and triangulate the answer."
            ),
            "inputs_needed": ["valuation purpose", "financial data"],
            "unsuitable_when": "The valuation purpose is undefined.",
        },
        {
            "framework_id": "FW-EV",
            "name": "Expected value analysis",
            "relevance_reason": (
                "Weights possible outcomes by their probabilities where the "
                "future is uncertain."
            ),
            "inputs_needed": ["possible outcomes", "probabilities"],
            "unsuitable_when": "Probabilities cannot be estimated or outcomes listed.",
        },
        {
            "framework_id": "FW-SCENARIO",
            "name": "Scenario analysis",
            "relevance_reason": (
                "Values the business under coherent scenarios to show the range "
                "rather than a false single point."
            ),
            "inputs_needed": ["scenario cash flows", "scenario probabilities"],
            "unsuitable_when": "Scenarios cannot be defined or weighted.",
        },
    ],
    "ma_appraisal": [
        {
            "framework_id": "FW-VALUATION",
            "name": "Business valuation",
            "relevance_reason": (
                "Values the target standalone and with synergies to set a "
                "walk-away price."
            ),
            "inputs_needed": ["target financials", "synergy estimates"],
            "unsuitable_when": "Target financial information is unavailable.",
        },
        {
            "framework_id": "FW-SCENARIO",
            "name": "Scenario analysis",
            "relevance_reason": (
                "Tests the deal price against synergy realisation scenarios, "
                "including synergy failure."
            ),
            "inputs_needed": ["synergy scenarios", "scenario probabilities"],
            "unsuitable_when": "Synergy claims cannot be quantified.",
        },
        {
            "framework_id": "FW-RISKISO",
            "name": "Risk management (ISO 31000)",
            "relevance_reason": (
                "Identifies, assesses and plans responses for integration, "
                "cultural and deal risks."
            ),
            "inputs_needed": ["risk list", "due diligence findings"],
            "unsuitable_when": "No due-diligence information exists to assess risks from.",
        },
        {
            "framework_id": "FW-STAKEHOLDER",
            "name": "Stakeholder analysis",
            "relevance_reason": (
                "Maps shareholders, staff, customers and regulators whose "
                "support the deal needs."
            ),
            "inputs_needed": ["stakeholder list", "stakeholder interests"],
            "unsuitable_when": "Stakeholder impacts are trivial or already fully understood.",
        },
    ],
    "risk_management": [
        {
            "framework_id": "FW-RISKISO",
            "name": "Risk management (ISO 31000)",
            "relevance_reason": (
                "Structured identify-assess-treat-monitor cycle for the risk register."
            ),
            "inputs_needed": ["risk list", "likelihood and impact estimates"],
            "unsuitable_when": "Risks have not been identified at all.",
        },
        {
            "framework_id": "FW-SENS",
            "name": "Sensitivity analysis",
            "relevance_reason": (
                "Quantifies which variables the outcome is most sensitive to, "
                "focusing risk responses."
            ),
            "inputs_needed": ["base-case model", "key variable ranges"],
            "unsuitable_when": "The base-case model itself is not built yet.",
        },
        {
            "framework_id": "FW-SCENARIO",
            "name": "Scenario analysis",
            "relevance_reason": (
                "Explores coherent futures and their probability-weighted impact."
            ),
            "inputs_needed": ["scenario definitions", "scenario probabilities"],
            "unsuitable_when": "Scenarios cannot be defined or weighted.",
        },
    ],
    "hedging": [
        {
            "framework_id": "FW-HEDGE",
            "name": "Hedging analysis",
            "relevance_reason": (
                "Compares hedging instruments (forwards, futures, options, swaps) "
                "on cost, protection and flexibility for the exposure."
            ),
            "inputs_needed": ["exposure amount and timing", "currency/rate details"],
            "unsuitable_when": "The exposure is immaterial or naturally hedged.",
        },
        {
            "framework_id": "FW-RISKISO",
            "name": "Risk management (ISO 31000)",
            "relevance_reason": (
                "Places the hedge inside the wider risk-appetite and limit framework."
            ),
            "inputs_needed": ["risk list", "risk appetite"],
            "unsuitable_when": "No risk framework exists to anchor the hedge decision.",
        },
    ],
    "portfolio": [
        {
            "framework_id": "FW-PORTFOLIO",
            "name": "Portfolio analysis",
            "relevance_reason": (
                "Evaluates the mix of investments/businesses on risk-return and "
                "diversification."
            ),
            "inputs_needed": ["expected returns", "risk measures", "correlations"],
            "unsuitable_when": "Only a single investment is under consideration.",
        },
        {
            "framework_id": "FW-RISKRET",
            "name": "Risk-return analysis",
            "relevance_reason": (
                "Trades expected return against risk (e.g. CAPM-based required returns)."
            ),
            "inputs_needed": ["expected returns", "beta or risk measures"],
            "unsuitable_when": "Risk cannot be measured even approximately.",
        },
    ],
    "make_or_buy": [
        {
            "framework_id": "FW-MAKEBUY",
            "name": "Make-or-buy analysis",
            "relevance_reason": (
                "Compares in-house production cost against the supplier price, "
                "including released capacity and strategic factors."
            ),
            "inputs_needed": ["in-house costs", "supplier quote", "capacity position"],
            "unsuitable_when": "In-house production is not a realistic alternative.",
        },
        {
            "framework_id": "FW-RELCOST",
            "name": "Relevant costing",
            "relevance_reason": (
                "Strips out sunk and unavoidable costs so only incremental costs "
                "drive the comparison."
            ),
            "inputs_needed": ["cost breakdown", "avoidable vs unavoidable split"],
            "unsuitable_when": "Cost behaviour (fixed/variable, avoidable/unavoidable) is unknown.",
        },
        {
            "framework_id": "FW-CAPACITY",
            "name": "Capacity analysis",
            "relevance_reason": (
                "Checks whether released capacity has a profitable alternative use."
            ),
            "inputs_needed": ["capacity utilisation", "alternative uses"],
            "unsuitable_when": "Capacity is not a constraint in either option.",
        },
    ],
    "special_order": [
        {
            "framework_id": "FW-SPECIAL",
            "name": "Special-order analysis",
            "relevance_reason": (
                "Tests whether a one-off order at a special price adds incremental "
                "profit given spare capacity."
            ),
            "inputs_needed": ["special price", "variable cost", "spare capacity"],
            "unsuitable_when": "There is no spare capacity without displacing existing sales.",
        },
        {
            "framework_id": "FW-RELCOST",
            "name": "Relevant costing",
            "relevance_reason": (
                "Ensures only incremental costs (plus any lost contribution) are "
                "charged to the order."
            ),
            "inputs_needed": ["cost breakdown", "avoidable vs unavoidable split"],
            "unsuitable_when": "Cost behaviour (fixed/variable, avoidable/unavoidable) is unknown.",
        },
        {
            "framework_id": "FW-CONTRIB",
            "name": "Contribution analysis",
            "relevance_reason": (
                "Computes contribution per order to confirm the price covers "
                "variable cost."
            ),
            "inputs_needed": ["selling price", "variable cost"],
            "unsuitable_when": "Variable cost per unit is unknown.",
        },
    ],
    "product_mix": [
        {
            "framework_id": "FW-PRODMIX",
            "name": "Product-mix optimisation",
            "relevance_reason": (
                "Allocates scarce resources across products to maximise total contribution."
            ),
            "inputs_needed": ["contribution per product", "resource usage", "demand limits"],
            "unsuitable_when": "No resource is scarce.",
        },
        {
            "framework_id": "FW-LIMITING",
            "name": "Limiting-factor analysis",
            "relevance_reason": (
                "Ranks products by contribution per unit of the limiting factor "
                "to find the optimal mix."
            ),
            "inputs_needed": ["contribution per unit", "limiting-factor usage"],
            "unsuitable_when": "No limiting factor exists.",
        },
        {
            "framework_id": "FW-CONTRIB",
            "name": "Contribution analysis",
            "relevance_reason": (
                "Computes the unit contributions that feed the ranking."
            ),
            "inputs_needed": ["selling price", "variable cost"],
            "unsuitable_when": "Variable cost per unit is unknown.",
        },
    ],
    "pricing": [
        {
            "framework_id": "FW-PRICING",
            "name": "Pricing analysis",
            "relevance_reason": (
                "Compares cost-plus, market-based and value-based approaches for "
                "the pricing decision."
            ),
            "inputs_needed": ["cost data", "market prices", "customer value insight"],
            "unsuitable_when": "Price is fully regulated or contractually fixed.",
        },
        {
            "framework_id": "FW-BREAKEVEN",
            "name": "Breakeven analysis",
            "relevance_reason": (
                "Shows the volume needed at any candidate price to cover costs."
            ),
            "inputs_needed": ["fixed costs", "variable cost per unit", "price"],
            "unsuitable_when": "Cost structure is unknown.",
        },
        {
            "framework_id": "FW-CONTRIB",
            "name": "Contribution analysis",
            "relevance_reason": (
                "Checks the contribution margin each price point leaves."
            ),
            "inputs_needed": ["selling price", "variable cost"],
            "unsuitable_when": "Variable cost per unit is unknown.",
        },
    ],
    "costing_decision": [
        {
            "framework_id": "FW-RELCOST",
            "name": "Relevant costing",
            "relevance_reason": (
                "Identifies the future incremental cash flows relevant to the "
                "costing choice."
            ),
            "inputs_needed": ["cost breakdown", "avoidable vs unavoidable split"],
            "unsuitable_when": "Cost behaviour (fixed/variable, avoidable/unavoidable) is unknown.",
        },
        {
            "framework_id": "FW-CONTRIB",
            "name": "Contribution analysis",
            "relevance_reason": (
                "Shows how each alternative affects total contribution."
            ),
            "inputs_needed": ["selling price", "variable cost"],
            "unsuitable_when": "Variable cost per unit is unknown.",
        },
        {
            "framework_id": "FW-VARIANCE",
            "name": "Variance analysis",
            "relevance_reason": (
                "If standards exist, explains where actual costs deviated and why."
            ),
            "inputs_needed": ["budget figures", "actual figures", "standards"],
            "unsuitable_when": "No budget or standard was set.",
        },
    ],
    "capacity": [
        {
            "framework_id": "FW-CAPACITY",
            "name": "Capacity analysis",
            "relevance_reason": (
                "Quantifies utilisation, bottlenecks and the cost of the "
                "capacity constraint."
            ),
            "inputs_needed": ["capacity data", "demand forecast"],
            "unsuitable_when": "Capacity is clearly not the binding constraint.",
        },
        {
            "framework_id": "FW-BREAKEVEN",
            "name": "Breakeven analysis",
            "relevance_reason": (
                "Shows what volume the (expanded) capacity must achieve to pay "
                "for itself."
            ),
            "inputs_needed": ["fixed costs", "variable cost per unit", "price"],
            "unsuitable_when": "Cost structure is unknown.",
        },
        {
            "framework_id": "FW-LIMITING",
            "name": "Limiting-factor analysis",
            "relevance_reason": (
                "Identifies the true bottleneck when several resources look tight."
            ),
            "inputs_needed": ["resource usage per unit", "resource availability"],
            "unsuitable_when": "Only one resource could plausibly bind.",
        },
    ],
}


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_framework_names(rules_path: str | Path | None) -> dict[str, str]:
    """Best-effort load of framework_id -> name from a metadata JSON file.

    Accepts either a list of {"framework_id"|"id", "name"} dicts or a plain
    {"FW-X": "Name"} mapping. Any failure falls back to the in-code names.
    """
    candidates: list[Path] = []
    if rules_path is not None:
        candidates.append(Path(rules_path))
    candidates.append(_project_root() / "data" / "frameworks.json")
    for candidate in candidates:
        try:
            if not candidate.is_file():
                continue
            with open(candidate, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            names: dict[str, str] = {}
            if isinstance(data, dict):
                items = data.items()
                for key, value in items:
                    if isinstance(value, dict) and "name" in value:
                        names[str(key)] = str(value["name"])
                    elif isinstance(value, str):
                        names[str(key)] = value
            elif isinstance(data, list):
                for row in data:
                    if not isinstance(row, dict):
                        continue
                    fid = row.get("framework_id", row.get("id"))
                    if fid and "name" in row:
                        names[str(fid)] = str(row["name"])
            if names:
                return names
        except (OSError, ValueError):
            continue
    return {}


def _input_available(needed: str, available_inputs: list[str]) -> bool:
    """Case-insensitive substring match in either direction."""
    n = needed.strip().lower()
    if not n:
        return True
    for raw in available_inputs:
        a = str(raw).strip().lower()
        if not a:
            continue
        if n in a or a in n:
            return True
    return False


def recommend_frameworks(
    decision_type: str,
    available_inputs: list[str],
    rules_path: str | Path | None = None,
) -> list[FrameworkRecommendation]:
    """Recommend frameworks for ``decision_type`` with readiness flags.

    ``rules_path`` optionally points at a framework-metadata JSON file used to
    override the in-code framework names (defaults to data/frameworks.json
    when present). Unknown decision types return an empty list.
    """
    entries = _FRAMEWORK_TABLE.get(decision_type, [])
    name_overrides = _load_framework_names(rules_path)
    available = list(available_inputs or [])
    out: list[FrameworkRecommendation] = []
    for entry in entries:
        needed = list(entry.get("inputs_needed", []))
        missing = [n for n in needed if not _input_available(n, available)]
        out.append(
            FrameworkRecommendation(
                framework_id=entry["framework_id"],
                name=name_overrides.get(entry["framework_id"], entry["name"]),
                relevance_reason=entry["relevance_reason"],
                inputs_needed=needed,
                unsuitable_when=entry["unsuitable_when"],
                readiness="ready" if not missing else "missing_info",
                missing=missing,
            )
        )
    return out
