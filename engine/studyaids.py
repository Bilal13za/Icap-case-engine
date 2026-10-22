"""Deterministic study-aid helpers for the ICAP Case Engine.

Pure Python: no Streamlit, no network, no AI. Everything here is derived
from seeded content (Frameworks, FrameworkSteps, Formulas, TriggerRules) and
the recommendation template in engine/recommendations.py.

Contents:
- FORMULA_SHEET_GROUPS: explicit, auditable grouping of every formula into a
  quick-sheet by decision area. The grouping is an editorial navigation aid;
  the formulas themselves are unchanged.
- DECK_LABELS / CARD_TYPE_LABELS: display labels for flashcard decks/types.
- RECOMMENDATION_CHECKLIST: the 11 sections of the recommendation template
  (engine/recommendations.py) as an interactive checklist.
- ANSWER_QUALITY_ITEMS: the canonical 9-point exam answer-quality checklist
  (also used by the Exam Practice screen).
- MINDMAP_BRANCHES + mindmap_html(): offline collapsible mind-map renderer.
"""

from __future__ import annotations

import html as _html
import json

# ---------------------------------------------------------------------------
# Formula quick-sheet groups: (sheet title, primary paper deck, [formula_ids])
# Every formula in data/formulas.json appears in exactly one group (tested).
# The paper column is a navigation hint only -- many formulas apply to both
# papers; it is NOT an ICAP examinability claim.
# ---------------------------------------------------------------------------
FORMULA_SHEET_GROUPS: list[tuple[str, str, list[str]]] = [
    ("Investment appraisal", "CFAP-4", [
        "FORM-NPV", "FORM-IRR", "FORM-PAYBACK", "FORM-DISCOUNTED-PAYBACK",
        "FORM-SENSITIVITY", "FORM-SCENARIO-NPV",
    ]),
    ("Cost of capital & valuation", "CFAP-4", [
        "FORM-WACC", "FORM-CAPM", "FORM-COST-DEBT", "FORM-GORDON",
        "FORM-PE-VAL", "FORM-ASSET-VAL", "FORM-EV",
    ]),
    ("Time value of money", "CFAP-4", [
        "FORM-PV", "FORM-FV", "FORM-ANNUITY-PV", "FORM-ANNUITY-FV",
    ]),
    ("Breakeven & CVP analysis", "CAF-6", [
        "FORM-CONTRIBUTION", "FORM-CM-RATIO", "FORM-BREAKEVEN-UNITS",
        "FORM-BREAKEVEN-REV", "FORM-MARGIN-SAFETY", "FORM-OP-LEVERAGE",
    ]),
    ("Working capital & liquidity", "CAF-6", [
        "FORM-CURRENT-RATIO", "FORM-QUICK-RATIO", "FORM-REC-DAYS",
        "FORM-PAY-DAYS", "FORM-INV-DAYS", "FORM-CCC",
    ]),
    ("Profitability & gearing ratios", "CAF-6", [
        "FORM-GROSS-MARGIN", "FORM-NET-MARGIN", "FORM-ROCE", "FORM-ROE",
        "FORM-ASSET-TURNOVER", "FORM-GEARING", "FORM-INT-COVER",
    ]),
    ("Relevant costing & short-term decisions", "CAF-6", [
        "FORM-RELEVANT-COST", "FORM-MAKEBUY", "FORM-SPECIAL-ORDER",
        "FORM-LIMITING-FACTOR",
    ]),
    ("Variances", "CAF-6", [
        "FORM-MATERIAL-VAR", "FORM-LABOUR-VAR",
    ]),
    ("Growth & trend analysis", "CAF-6", [
        "FORM-PCT-CHANGE", "FORM-CAGR",
    ]),
]


def formula_group_of(formula_id: str) -> tuple[str, str] | None:
    """Return (sheet title, paper deck) for a formula_id, or None."""
    for title, paper, ids in FORMULA_SHEET_GROUPS:
        if formula_id in ids:
            return title, paper
    return None


# ---------------------------------------------------------------------------
# Flashcard decks / card types
# ---------------------------------------------------------------------------
DECK_LABELS = {
    "CAF-6": "CAF-6 / CAF-7 — Business analysis",
    "CFAP-4": "CFAP-4 — Business finance",
    "GENERAL": "General",
}

CARD_TYPE_LABELS = {
    "definition": "Definitions",
    "application": "When to use",
    "limitations": "Limitations & mistakes",
    "steps": "Procedure steps",
    "formula": "Formula recall",
    "interpretation": "Interpret results",
    "rule_signal": "Indicator → issue",
}

VALID_VERIFICATION_STATUSES = frozenset({
    "verified_official",
    "provisional_predecessor",
    "supplementary",
    "unverified",
})

# ---------------------------------------------------------------------------
# Checklists
# ---------------------------------------------------------------------------
# Mirrors the sections dict built by engine/recommendations.py
# build_recommendation(): the app's own recommendation structure, surfaced as
# an interactive checklist.
RECOMMENDATION_CHECKLIST: list[tuple[str, str]] = [
    ("recommended_option", "Preferred option stated clearly"),
    ("executive_summary", "Executive summary written"),
    ("supporting_facts", "Supporting case facts cited"),
    ("financial_analysis", "Financial analysis / calculations included"),
    ("key_assumption", "Key assumption stated explicitly"),
    ("selected_option_risks", "Risks of the preferred option addressed"),
    ("alternatives_considered", "Alternatives considered and compared"),
    ("conditions_for_change", "Conditions under which the recommendation would change"),
    ("implementation_steps", "Implementation steps set out"),
    ("kpis", "KPIs / performance indicators defined"),
    ("review_timing", "Review timing set"),
]

# Canonical 9-point exam answer-quality checklist (also used by Exam Practice).
ANSWER_QUALITY_ITEMS: list[str] = [
    "Identified the core business issue / requirement precisely",
    "Applied a relevant framework or technique correctly",
    "Showed all calculations with clear workings",
    "Stated key assumptions explicitly",
    "Considered at least one alternative or sensitivity",
    "Addressed risks and limitations",
    "Reached a clear, justified recommendation / conclusion",
    "Presented the answer in a professional, structured format",
    "Completed within the suggested time",
]

# ---------------------------------------------------------------------------
# Mind maps
# ---------------------------------------------------------------------------
# Branch key -> display label. Branch content is resolved from the framework
# row (definition, purpose, appropriate_situations, required_inputs,
# limitations, common_mistakes, example) and its FrameworkSteps rows.
MINDMAP_BRANCHES: list[tuple[str, str]] = [
    ("definition", "Definition"),
    ("purpose", "Purpose"),
    ("when_to_use", "When to use"),
    ("required_inputs", "Required inputs"),
    ("steps", "Steps"),
    ("limitations", "Limitations"),
    ("common_mistakes", "Common mistakes"),
    ("example", "Worked example"),
]

_BADGE_COLORS = {
    "verified_official": "#1a7f37",
    "provisional_predecessor": "#9a6700",
    "supplementary": "#6e7681",
    "unverified": "#cf222e",
}
_BADGE_LABELS = {
    "verified_official": "Verified official",
    "provisional_predecessor": "Provisional — mapped from 2021 predecessor",
    "supplementary": "Supplementary",
    "unverified": "Unverified",
}


def _badge_html(status: str | None) -> str:
    color = _BADGE_COLORS.get((status or "").strip(), "#6e7681")
    label = _BADGE_LABELS.get((status or "").strip(), f"Status: {status or 'unknown'}")
    return (
        f'<span style="background:{color}1a;color:{color};border:1px solid {color}55;'
        f'padding:2px 10px;border-radius:12px;font-size:0.78em;font-weight:600;'
        f'white-space:nowrap;">{_html.escape(label)}</span>'
    )


def _branch_text(framework: dict, key: str) -> str:
    mapping = {
        "definition": framework.get("definition") or "",
        "purpose": framework.get("purpose") or "",
        "when_to_use": framework.get("appropriate_situations") or "",
        "required_inputs": framework.get("required_inputs") or "",
        "limitations": framework.get("limitations") or "",
        "common_mistakes": framework.get("common_mistakes") or "",
        "example": framework.get("example") or "",
    }
    return mapping.get(key, "")


def mindmap_html(framework: dict, steps: list[dict],
                 branch_order: list[str] | None = None) -> str:
    """Render a collapsible offline mind map for one framework.

    Pure HTML with <details>/<summary> -- no JavaScript, no CDN, works fully
    offline. Every leaf is the framework's own seeded text (HTML-escaped).
    """
    name = str(framework.get("name") or "Framework")
    order = branch_order or [b[0] for b in MINDMAP_BRANCHES]
    labels = dict(MINDMAP_BRANCHES)

    parts: list[str] = []
    parts.append(
        '<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'
        'max-width:960px;line-height:1.55;">'
    )
    parts.append(
        f'<h3 style="margin:0 0 4px 0;">{_html.escape(name)} '
        f'{_badge_html(framework.get("verification_status"))}</h3>'
    )
    parts.append(
        '<p style="color:#666;font-size:0.85em;margin:0 0 12px 0;">'
        'Click a branch to expand or collapse it. All content is drawn from '
        'the framework library — no external sources needed.</p>'
    )

    branch_no = 0
    for key in order:
        label = labels.get(key, key)
        if key == "steps":
            ordered = sorted(steps, key=lambda s: s.get("step_no") or 0)
            if not ordered:
                continue
            items = []
            for s in ordered:
                title = _html.escape(str(s.get("title") or ""))
                desc = _html.escape(str(s.get("description") or ""))
                formula = s.get("formula")
                fhtml = (f' <code style="background:#f6f8fa;padding:1px 6px;'
                         f'border-radius:4px;">{_html.escape(str(formula))}</code>'
                         if formula else "")
                items.append(f"<li><b>{title}</b> — {desc}{fhtml}</li>")
            body = f"<ol style='margin:6px 0 6px 18px;padding:0;'>{''.join(items)}</ol>"
            n_steps = len(ordered)
            subtitle = f" ({n_steps} step{'s' if n_steps != 1 else ''})"
        else:
            text = _branch_text(framework, key).strip()
            if not text:
                continue
            body = f"<p style='margin:6px 0;'>{_html.escape(text)}</p>"
            subtitle = ""
        branch_no += 1
        parts.append(
            '<details style="border:1px solid #d0d7de;border-radius:8px;'
            'margin:0 0 8px 0;padding:8px 12px;background:#fff;">'
            f'<summary style="cursor:pointer;font-weight:600;">'
            f"{branch_no} · {_html.escape(label)}{_html.escape(subtitle)}</summary>"
            f'<div style="margin-top:6px;">{body}</div>'
            "</details>"
        )
    parts.append("</div>")
    return "".join(parts)


def mindmap_branch_order_json() -> list[str]:
    """Default branch order stored per map in MindMaps.branch_order_json."""
    return [b[0] for b in MINDMAP_BRANCHES]
