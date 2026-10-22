"""Deterministic recommendation builder.

Assembles a structured recommendation from the student's OWN inputs only:
the selected option, confirmed facts, calculation summaries, assumptions,
implementation steps, KPIs and review timing. No claims are invented -- every
sentence is built from supplied strings.

Pure Python: no Streamlit, no AI/LLM, no network.
"""

from __future__ import annotations

from typing import Any

_REQUIRED_OPTION_KEYS = (
    "option_id",
    "description",
    "financial_impact",
    "nonfinancial_benefits",
    "costs",
    "risks",
    "assumptions",
    "evidence",
)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    s = str(value).strip()
    return [s] if s else []


def _first_nonblank(*values: Any) -> str:
    for v in values:
        s = str(v).strip() if v is not None else ""
        if s:
            return s
    return ""


def build_recommendation(
    *,
    selected_option_id: str,
    options: list[dict],
    confirmed_fact_ids: list[str],
    calc_summaries: list[str],
    key_assumption: str,
    conditions_for_change: list[str],
    implementation_steps: list[str],
    kpis: list[str],
    review_timing: str,
) -> dict:
    """Build a recommendation dict from supplied inputs only.

    Returns ``{"title", "sections", "rendered_text"}``. Raises ValueError if
    ``options`` or ``confirmed_fact_ids`` is empty, if ``selected_option_id``
    is not among the options, or if an option dict lacks required keys.
    """
    if not options:
        raise ValueError("options must not be empty")
    if not confirmed_fact_ids:
        raise ValueError("confirmed_fact_ids must not be empty")

    for i, opt in enumerate(options):
        missing_keys = [k for k in _REQUIRED_OPTION_KEYS if k not in opt]
        if missing_keys:
            raise ValueError(
                f"options[{i}] is missing required keys: {', '.join(missing_keys)}"
            )

    option_ids = [str(o["option_id"]) for o in options]
    if str(selected_option_id) not in option_ids:
        raise ValueError(
            f"selected_option_id {selected_option_id!r} not in options "
            f"{option_ids}"
        )
    selected = next(o for o in options if str(o["option_id"]) == str(selected_option_id))
    others = [o for o in options if str(o["option_id"]) != str(selected_option_id)]

    sid = str(selected["option_id"])
    description = str(selected["description"]).strip()
    reason = _first_nonblank(
        selected.get("evidence"),
        selected.get("financial_impact"),
        selected.get("nonfinancial_benefits"),
        "the supplied option analysis",
    )
    assumption = str(key_assumption).strip() or "the key assumptions holding"

    sentences = [f"Option {sid} is preferable because {reason}."]
    calc_lines = [s for s in (calc_summaries or []) if str(s).strip()]
    if calc_lines:
        sentences.append(f"The financial analysis indicates {calc_lines[0].strip()}.")
    sentences.append(f"However, the decision depends on {assumption}.")

    steps = [s for s in (implementation_steps or []) if str(s).strip()]
    kpi_list = [k for k in (kpis or []) if str(k).strip()]
    if steps and kpi_list:
        sentences.append(f"Management should {steps[0].strip()} and monitor {kpi_list[0].strip()}.")
    elif steps:
        sentences.append(f"Management should {steps[0].strip()}.")
    elif kpi_list:
        sentences.append(f"Management should monitor {kpi_list[0].strip()}.")

    executive_summary = " ".join(sentences)

    alternatives = []
    for o in others:
        risks = _as_list(o.get("risks"))
        risk_txt = risks[0] if risks else "no key risk supplied"
        alternatives.append(
            f"Option {o['option_id']}: {str(o['description']).strip()} -- "
            f"financial impact: {str(o['financial_impact']).strip()}; "
            f"key risk: {risk_txt}."
        )

    sections: dict[str, Any] = {
        "recommended_option": f"Option {sid}: {description}",
        "executive_summary": executive_summary,
        "supporting_facts": [str(f) for f in confirmed_fact_ids],
        "financial_analysis": calc_lines,
        "key_assumption": str(key_assumption).strip(),
        "selected_option_risks": _as_list(selected.get("risks")),
        "alternatives_considered": alternatives,
        "conditions_for_change": [str(c).strip() for c in (conditions_for_change or []) if str(c).strip()],
        "implementation_steps": steps,
        "kpis": kpi_list,
        "review_timing": str(review_timing).strip(),
    }

    lines = [
        f"# Recommendation: Option {sid}" + (f" -- {description}" if description else ""),
        "",
        "## Executive summary",
        executive_summary,
        "",
        "## Supporting facts",
    ]
    lines += [f"- {f}" for f in sections["supporting_facts"]]
    lines += ["", "## Financial analysis"]
    lines += [f"- {c}" for c in calc_lines] if calc_lines else ["- No quantified analysis supplied."]
    lines += ["", "## Key assumption", sections["key_assumption"] or "Not supplied."]
    lines += ["", "## Risks of the recommended option"]
    lines += [f"- {r}" for r in sections["selected_option_risks"]] or ["- None supplied."]
    lines += ["", "## Alternatives considered"]
    lines += [f"- {a}" for a in alternatives] or ["- None."]
    lines += ["", "## Conditions that would change this recommendation"]
    lines += [f"- {c}" for c in sections["conditions_for_change"]] or ["- None supplied."]
    lines += ["", "## Implementation steps"]
    lines += [f"{i + 1}. {s}" for i, s in enumerate(steps)] or ["- None supplied."]
    lines += ["", "## KPIs to monitor"]
    lines += [f"- {k}" for k in kpi_list] or ["- None supplied."]
    lines += ["", "## Review timing", sections["review_timing"] or "Not supplied."]

    return {
        "title": f"Recommendation: Option {sid}" + (f" -- {description}" if description else ""),
        "sections": sections,
        "rendered_text": "\n".join(lines),
    }
