#!/usr/bin/env python3
"""Deterministically generate study-aid seed files from existing seed data.

Reads : data/frameworks.json, data/formulas.json, data/rules.json,
        data/calculation_examples.json
Writes: data/flashcards.json, data/mindmaps.json

No content is invented: every card and map traces to a source row and
inherits that row's verification_status. Re-running reproduces the outputs
byte-for-byte (fixed ordering, sorted keys).

Flashcards
----------
Per framework (49): definition+purpose, when-to-use+inputs,
limitations+common-mistakes; plus one steps card per framework that has
procedure steps (15).
Per key formula: one recall card for every validated formula plus every
formula with a worked example; one interpretation card per worked example (6).
Per trigger rule (30): one indicators -> possible-issue card.
Target: ~200 cards.

Mind maps
---------
One map per verified_official framework (22) plus key supplementary
frameworks that carry procedure steps (5) = 27 maps. Each map stores its
branch order; leaf text is resolved from the Frameworks/FrameworkSteps rows
at render time (single source of truth).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from engine import studyaids as sa  # noqa: E402

DATA = ROOT / "data"

_TREND_WORDS = {"up": "increasing", "down": "decreasing", "flat": "flat / unchanged"}

# Editorial navigation grouping only (NOT an ICAP claim): which paper deck a
# trigger-rule card is filed under, based on the syllabus grid covering it.
PATTERN_PAPER = {
    "PAT-WORKING-CAPITAL": "CAF-6", "PAT-OVERTRADING": "CAF-6",
    "PAT-LIQUIDITY": "CAF-6", "PAT-INVENTORY": "CAF-6",
    "PAT-CAPACITY": "CAF-6", "PAT-MARGIN": "CAF-6",
    "PAT-VARIANCE": "CAF-6", "PAT-COST-OVERRUN": "CAF-6",
    "PAT-PROFIT-LESS-GROWTH": "CAF-6", "PAT-EARNINGS-QUALITY": "CAF-6",
    "PAT-OP-LEVERAGE-RISK": "CAF-6", "PAT-MAKEBUY": "CAF-6",
    "PAT-SPECIAL-ORDER": "CAF-6", "PAT-LIMITING-FACTOR": "CAF-6",
    "PAT-PRICING": "CAF-6", "PAT-ETHICS": "CAF-6",
    "PAT-SYSTEMS": "CAF-6", "PAT-DISRUPTION": "CAF-6",
    "PAT-NEW-ENTRANT": "CAF-6", "PAT-SUPPLIER-POWER": "CAF-6",
    "PAT-CUSTOMER-CONCENTRATION": "CAF-6",
    "PAT-STRATEGIC-NPV": "CFAP-4", "PAT-APPRAISAL-CONFLICT": "CFAP-4",
    "PAT-SENSITIVITY": "CFAP-4", "PAT-GEARING": "CFAP-4",
    "PAT-DIVIDEND": "CFAP-4", "PAT-RIGHTS-ISSUE": "CFAP-4",
    "PAT-MA-SYNERGY": "CFAP-4", "PAT-FX": "CFAP-4",
    "PAT-INTEREST-RATE": "CFAP-4",
}


def _load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _fw_paper_topic(related: str | None) -> tuple[str, str]:
    """Parse 'CAF-6/C; CFAP-4/1' -> ('CAF-6', 'C'). Empty -> ('GENERAL', '')."""
    if not (related or "").strip():
        return "GENERAL", ""
    first = related.split(";")[0].strip()
    bits = first.split("/")
    paper = bits[0].strip() or "GENERAL"
    topic = bits[1].strip() if len(bits) > 1 else ""
    return paper, topic


def _card(card_id: str, deck: str, front: str, back: str, card_type: str,
          verification_status: str, official_source: str,
          framework_id: str | None = None, formula_id: str | None = None,
          rule_id: str | None = None, topic: str = "",
          paper_code: str = "") -> dict:
    assert front.strip() and back.strip(), f"empty card text: {card_id}"
    assert verification_status in sa.VALID_VERIFICATION_STATUSES, card_id
    return {
        "card_id": card_id,
        "deck": deck,
        "front": front.strip(),
        "back": back.strip(),
        "framework_id": framework_id,
        "formula_id": formula_id,
        "rule_id": rule_id,
        "topic": topic,
        "paper_code": paper_code or deck,
        "card_type": card_type,
        "verification_status": verification_status,
        "official_source": official_source or "",
    }


def build_framework_cards(frameworks: list[dict],
                           steps_by_fw: dict[str, list[dict]]) -> list[dict]:
    cards: list[dict] = []
    for f in sorted(frameworks, key=lambda x: x["framework_id"]):
        fid = f["framework_id"]
        name = f["name"]
        paper, topic = _fw_paper_topic(f.get("related_topics"))
        vs = f["verification_status"]
        src = f.get("source_ref") or ""
        cards.append(_card(
            f"FC-{fid}-DEF", paper,
            f"Define **{name}** and state its purpose.",
            f"**Definition:** {f['definition']}\n\n**Purpose:** {f['purpose']}",
            "definition", vs, src, framework_id=fid, topic=topic, paper_code=paper))
        # Build the back only from fields the source row actually has.
        app_parts = [f"**When to use:** {f['appropriate_situations']}"]
        if (f.get("required_inputs") or "").strip():
            app_parts.append(f"**Inputs needed:** {f['required_inputs']}")
        cards.append(_card(
            f"FC-{fid}-APP", paper,
            f"When should **{name}** be used, and what inputs does it need?",
            "\n\n".join(app_parts),
            "application", vs, src, framework_id=fid, topic=topic, paper_code=paper))
        cards.append(_card(
            f"FC-{fid}-LIM", paper,
            f"State the key limitations of **{name}** and the mistakes "
            f"students commonly make with it.",
            f"**Limitations:** {f['limitations']}\n\n"
            f"**Common mistakes:** {f['common_mistakes']}",
            "limitations", vs, src, framework_id=fid, topic=topic, paper_code=paper))
        steps = sorted(steps_by_fw.get(fid, []), key=lambda s: s.get("step_no") or 0)
        if steps:
            lines = []
            for s in steps:
                line = f"{s['step_no']}. **{s['title']}** — {s['description']}"
                if s.get("formula"):
                    line += f"\n   Formula: `{s['formula']}`"
                lines.append(line)
            cards.append(_card(
                f"FC-{fid}-STEPS", paper,
                f"List the steps for applying **{name}**, in order.",
                "\n\n".join(lines),
                "steps", vs, src, framework_id=fid, topic=topic, paper_code=paper))
    return cards


def build_formula_cards(formulas: list[dict], examples: list[dict]) -> list[dict]:
    by_id = {f["formula_id"]: f for f in formulas}
    example_fids = {e["formula_id"] for e in examples}
    key_ids = sorted({f["formula_id"] for f in formulas
                      if f.get("validation_status") == "validated"} | example_fids)
    cards: list[dict] = []
    for fid in key_ids:
        f = by_id[fid]
        grp = sa.formula_group_of(fid)
        paper = grp[1] if grp else "GENERAL"
        inputs = "; ".join(
            f"{i['name']} ({i.get('unit', '')}) — {i.get('description', '')}".strip()
            for i in (f.get("inputs_json") or []))
        cards.append(_card(
            f"FC-{fid}", paper,
            f"State the formula for **{f['name']}** and its inputs.",
            f"**Formula:** {f['formula_text']}\n\n"
            f"**Inputs:** {inputs or '—'}\n\n"
            f"**Assumptions:** {f.get('assumptions') or '—'}\n\n"
            f"**Limitations:** {f.get('limitations') or '—'}\n\n"
            f"_Validation: {f.get('validation_status', 'unknown')}_",
            "formula", f["verification_status"],
            "ICAP Case Engine deterministic calculation library",
            formula_id=fid, paper_code=paper))
    for e in sorted(examples, key=lambda x: x["example_id"]):
        f = by_id.get(e["formula_id"], {})
        grp = sa.formula_group_of(e["formula_id"])
        paper = grp[1] if grp else "GENERAL"
        given = ", ".join(f"{k} = {v}" for k, v in
                          (e.get("inputs_json") or {}).items()
                          if k != "currency")
        cards.append(_card(
            f"FC-{e['example_id']}", paper,
            f"Worked example — **{f.get('name', e['formula_id'])}**: "
            f"given {given}, the result is {e.get('result_text', '')}. "
            f"What does it mean?",
            e.get("interpretation") or "",
            "interpretation", f.get("verification_status", "supplementary"),
            "ICAP Case Engine deterministic calculation library",
            formula_id=e["formula_id"], paper_code=paper))
    return cards


def _trigger_text(t: dict) -> str:
    fk = str(t.get("fact_key", "?")).replace("_", " ")
    if t.get("trend"):
        return f"{fk} is {_TREND_WORDS.get(t['trend'], t['trend'])}"
    if "equals" in t:
        return f"{fk}: {t['equals']}"
    return fk


def build_rule_cards(rules: list[dict]) -> list[dict]:
    cards: list[dict] = []
    for r in sorted(rules, key=lambda x: x["rule_id"]):
        triggers = r.get("triggers") or []
        paper = PATTERN_PAPER.get(r.get("pattern_id"), "GENERAL")
        front = ("Indicators observed:\n"
                 + "\n".join(f"• {_trigger_text(t)}" for t in triggers)
                 + "\n\nWhat possible issue do these indicators point to?")
        back = (f"**Possible issue:** {r['title']}\n\n"
                f"**Interpretation:** {r.get('interpretation', '')}\n\n"
                f"**Alternative explanations to rule out:**\n"
                + "\n".join(f"• {a}" for a in (r.get("alternative_explanations") or []))
                + "\n\n⚠️ An indicator is not a proven cause — confirm with: "
                + "; ".join(r.get("info_needed") or []))
        cards.append(_card(
            f"FC-{r['rule_id']}", paper, front, back, "rule_signal",
            "supplementary", r.get("rule_source") or "",
            rule_id=r["rule_id"], paper_code=paper))
    return cards


def build_flashcards() -> list[dict]:
    fw_data = _load("frameworks.json")
    frameworks = fw_data["frameworks"]
    steps_by_fw: dict[str, list[dict]] = {}
    for s in fw_data.get("framework_steps", []):
        steps_by_fw.setdefault(s["framework_id"], []).append(s)
    formulas = _load("formulas.json")["formulas"]
    examples = _load("calculation_examples.json")["calculation_examples"]
    rules = _load("rules.json")
    if isinstance(rules, dict):  # tolerate wrapped shape
        rules = rules.get("trigger_rules", [])
    cards = (build_framework_cards(frameworks, steps_by_fw)
             + build_formula_cards(formulas, examples)
             + build_rule_cards(rules))
    # Deterministic order, no duplicates.
    seen: set[str] = set()
    unique: list[dict] = []
    for c in sorted(cards, key=lambda x: x["card_id"]):
        if c["card_id"] not in seen:
            seen.add(c["card_id"])
            unique.append(c)
    return unique


def build_mindmaps() -> list[dict]:
    fw_data = _load("frameworks.json")
    frameworks = fw_data["frameworks"]
    with_steps = {s["framework_id"] for s in fw_data.get("framework_steps", [])}
    # All verified_official frameworks, plus supplementary ones that carry
    # procedure steps (the richest map content).
    chosen = [f for f in frameworks
              if f["verification_status"] == "verified_official"
              or f["framework_id"] in with_steps]
    maps = []
    for f in sorted(chosen, key=lambda x: x["framework_id"]):
        maps.append({
            "map_id": f"MM-{f['framework_id']}",
            "framework_id": f["framework_id"],
            "title": f"{f['name']} — mind map",
            "branch_order_json": sa.mindmap_branch_order_json(),
            "verification_status": f["verification_status"],
            "source_ref": f.get("source_ref") or "",
        })
    return maps


def main() -> int:
    cards = build_flashcards()
    maps = build_mindmaps()
    (DATA / "flashcards.json").write_text(
        json.dumps({"flashcards": cards}, indent=2, ensure_ascii=False,
                   sort_keys=True) + "\n", encoding="utf-8")
    (DATA / "mindmaps.json").write_text(
        json.dumps({"mindmaps": maps}, indent=2, ensure_ascii=False,
                   sort_keys=True) + "\n", encoding="utf-8")
    print(f"flashcards: {len(cards)}, mindmaps: {len(maps)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
