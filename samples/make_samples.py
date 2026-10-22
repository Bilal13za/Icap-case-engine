#!/usr/bin/env python3
"""Generate the three end-to-end sample analyses in samples/.

Each sample drives the REAL engines (rules -> frameworks -> calculations ->
recommendation) and writes:
  <slug>-analysis.md       the worked analysis in Markdown
  <slug>-workings.csv      calculation workings (CSV)
  <slug>-workings.xlsx      calculation workings (formatted Excel)

Usage:  python samples/make_samples.py   (from the project root)
"""

from __future__ import annotations

import csv
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import dbcore
from calcs.calculations import run_calculation
from engine.frameworks import recommend_frameworks
from engine.recommendations import build_recommendation
from engine.rules import Fact, evaluate_rules, load_rules

SAMPLES_DIR = HERE


# ------------------------------------------------------------------ helpers
def seed_scratch_db() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="case-engine-samples-"))
    db = tmp / "case_engine.db"
    dbcore.init_db(db)
    return db


def fired_rule(rule_id: str, facts: list[Fact]):
    rules = load_rules()
    rule = next(r for r in rules if r["rule_id"] == rule_id)
    matches = evaluate_rules(facts, rules)
    match = next(m for m in matches if m.rule_id == rule_id)
    return rule, match


def mapped_frameworks(conn, rule_id: str):
    return [
        (r["framework_id"], r["rationale"])
        for r in conn.execute(
            "SELECT framework_id, rationale FROM RuleFrameworkMappings WHERE rule_id = ?",
            (rule_id,),
        )
    ]


def write_csv(path: Path, tables: list[tuple[str, list[list[str]]]]):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        for title, rows in tables:
            w.writerow([title])
            w.writerows(rows)
            w.writerow([])


def write_excel(path: Path, tables: list[tuple[str, list[list[str]]]]):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    first = True
    for title, rows in tables:
        ws = wb.active if first else wb.create_sheet()
        first = False
        ws.title = title[:31]
        ws.append([title])
        ws["A1"].font = Font(bold=True, size=12)
        if rows:
            ws.append(rows[0])
            for cell in ws[2]:
                cell.font = Font(bold=True)
            for row in rows[1:]:
                ws.append(row)
        ws.column_dimensions["A"].width = 52
        ws.column_dimensions["B"].width = 22
    wb.save(path)


def calc_table(name: str, result) -> tuple[str, list[list[str]]]:
    rows = [["Step", "Detail"]]
    for i, step in enumerate(result.steps, 1):
        rows.append([f"{i}", step])
    if isinstance(result.result, dict):
        for key, value in result.result.items():
            rows.append([f"Result: {key}", f"{value}"])
        rows.append(["Result unit", result.result_unit])
    else:
        rows.append(["Result", f"{result.result} {result.result_unit}".strip()])
    rows.append(["Interpretation", result.interpretation])
    return name, rows


def option(oid, description, financial_impact, risks):
    return {
        "option_id": oid,
        "description": description,
        "financial_impact": financial_impact,
        "nonfinancial_benefits": "See analysis",
        "costs": "See analysis",
        "risks": risks,
        "assumptions": "Key assumptions hold",
        "evidence": "Case facts and calculations below",
    }


# ------------------------------------------------------------------ sample 1
def sample_working_capital(conn) -> tuple[str, list]:
    facts = [
        Fact("revenue", trend="up"),
        Fact("cash_balance", trend="down"),
        Fact("receivables_growth_vs_sales", value="faster"),
    ]
    rule, match = fired_rule("RULE-001", facts)
    fws = recommend_frameworks("working_capital", ["receivables", "inventory", "payables"])
    mapped = dict(mapped_frameworks(conn, "RULE-001"))

    calcs = [
        ("Receivable days", run_calculation("CALC-REC-DAYS", receivables=120000, credit_sales=1460000)),
        ("Inventory days", run_calculation("CALC-INV-DAYS", inventory=200000, cost_of_sales=1100000)),
        ("Payable days", run_calculation("CALC-PAY-DAYS", payables=90000, credit_purchases=800000)),
        ("Cash conversion cycle", run_calculation("CALC-CCC", receivable_days=Decimal("30.00"),
                                                 inventory_days=Decimal("66.36"), payable_days=Decimal("41.06"))),
        ("Current ratio", run_calculation("CALC-CURRENT-RATIO", current_assets=500000, current_liabilities=420000)),
    ]

    rec = build_recommendation(
        selected_option_id="WC-TIGHTEN",
        options=[
            option("WC-TIGHTEN", "Tighten working-capital management",
                   "Frees an estimated Rs 1.2m of cash", ["Customer pushback on stricter terms"]),
            option("WC-BORROW", "Fund the gap with short-term borrowing",
                   "Covers the shortfall at ~14% markup", ["Rising finance cost", "Covenant risk"]),
        ],
        confirmed_fact_ids=[
            "Revenue is growing (trend: up)",
            "Cash balance is falling (trend: down)",
            "Receivables are growing faster than sales",
            "Receivable days = 30.00; inventory days = 66.36; payable days = 41.06",
        ],
        calc_summaries=[
            "Cash conversion cycle is 55.30 days and lengthening",
            "Current ratio is 1.19 times — thin cover",
        ],
        key_assumption="Sales growth continues at the current pace",
        conditions_for_change=["Receivable days rising above 45", "Bank withdrawing the overdraft facility"],
        implementation_steps=["Set formal credit limits and collection targets",
                              "Review slow-moving inventory lines monthly"],
        kpis=["Receivable days", "Cash conversion cycle", "Overdraft utilisation"],
        review_timing="Monthly for the next two quarters",
    )

    fw_lines = "\n".join(
        f"- **{f.framework_id}** ({f.name}) — {f.relevance_reason}\n"
        f"  - *Not suitable when:* {f.unsuitable_when}\n"
        f"  - *Readiness:* {f.readiness}"
        + (f" (missing: {', '.join(f.missing)})" if f.missing else "")
        + (f"\n  - *Why it fits this rule:* {mapped[f.framework_id]}" if f.framework_id in mapped else "")
        for f in fws
    )
    calc_lines = "\n".join(
        f"### {name}\n" + "\n".join(f"- {s}" for s in r.steps)
        + f"\n- **Result: {r.result} {r.result_unit}**\n- *{r.interpretation}*\n"
        for name, r in calcs
    )
    md = f"""# Sample 1 — Working-capital pressure (Al-Noor Textiles, fictional)

## Facts
- Revenue is growing strongly (trend: up).
- Cash balance is falling (trend: down).
- Receivables are growing **faster** than sales.
- Supporting figures (Rs 000): receivables 120,000; credit sales 1,460,000;
  inventory 200,000; cost of sales 1,100,000; payables 90,000;
  credit purchases 800,000; current assets 500,000; current liabilities 420,000.

## Issues recognised
**{match.rule_id} — {match.title}**
- {match.interpretation}
- *Alternative explanations considered:* {"; ".join(match.alternative_explanations)}
- *Caution:* {match.caution}

## Frameworks
{fw_lines}

## Calculations (full workings in the CSV/Excel files)
{calc_lines}
## Alternatives considered
{rec["sections"]["alternatives_considered"][0]}

## Recommendation
{rec["rendered_text"]}

---
*Content labels: rule and case content is supplementary teaching material;
syllabus references are verified_official (2021) / provisional_predecessor (2025).*
"""
    tables = [calc_table(name, r) for name, r in calcs]
    return md, tables


# ------------------------------------------------------------------ sample 2
def sample_make_or_buy(conn) -> tuple[str, list]:
    facts = [Fact("supplier_quote_below_cost", value=True)]
    rule, match = fired_rule("RULE-009", facts)
    fws = recommend_frameworks("make_or_buy", ["in-house costs", "supplier quote", "capacity position"])
    mapped = dict(mapped_frameworks(conn, "RULE-009"))

    res = run_calculation("CALC-MAKEBUY", units=100000, buy_price=18,
                          variable_cost_make=12, specific_fixed_cost_make=500000,
                          opportunity_cost=200000)

    rec = build_recommendation(
        selected_option_id="BUY",
        options=[
            option("BUY", "Outsource component C-12 to the supplier",
                   "Saves Rs 100,000 on relevant costs", ["Supplier reliability", "Quality risk"]),
            option("MAKE", "Continue in-house production",
                   "Keeps control of quality and scheduling", ["Higher relevant cost by Rs 100,000"]),
        ],
        confirmed_fact_ids=[
            "Supplier quote (Rs 18/unit) is below in-house cost",
            "Relevant make cost: 100,000 x 12 + 500,000 + 200,000 = Rs 1,900,000",
            "Buy cost: 100,000 x 18 = Rs 1,800,000",
        ],
        calc_summaries=["Buying is cheaper by Rs 100,000 on relevant costs"],
        key_assumption="The supplier holds the Rs 18 price for the full volume",
        conditions_for_change=["Supplier price rising above Rs 19/unit",
                               "In-house variable cost falling below Rs 11/unit"],
        implementation_steps=["Negotiate a 12-month fixed-price supply contract",
                              "Re-deploy released capacity to product D"],
        kpis=["Unit cost of C-12", "Supplier on-time delivery", "Defect rate"],
        review_timing="Quarterly, or on any price change",
    )

    fw_lines = "\n".join(
        f"- **{f.framework_id}** ({f.name}) — {f.relevance_reason}\n"
        f"  - *Not suitable when:* {f.unsuitable_when}"
        + (f"\n  - *Why it fits this rule:* {mapped[f.framework_id]}" if f.framework_id in mapped else "")
        for f in fws
    )
    md = f"""# Sample 2 — Make-or-buy (Pak Components Ltd, fictional)

## Facts
- An external supplier quotes **Rs 18/unit** for component C-12 (100,000 units p.a.).
- In-house: variable cost Rs 12/unit; specific fixed cost Rs 500,000 p.a.;
  released capacity could earn Rs 200,000 elsewhere (opportunity cost).
- General fixed overhead is unavoidable and excluded (sunk for this decision).

## Issues recognised
**{match.rule_id} — {match.title}**
- {match.interpretation}
- *Alternative explanations considered:* {"; ".join(match.alternative_explanations)}
- *Caution:* {match.caution}

## Frameworks
{fw_lines}

## Calculations (full workings in the CSV/Excel files)
### Make-or-buy comparison
{chr(10).join("- " + s for s in res.steps)}
- **Result: make Rs {res.result['total_make_cost']:,.2f}; buy Rs {res.result['total_buy_cost']:,.2f}; """
    f"""saving from making Rs {res.result['saving_from_making']:,.2f}**
- *{res.interpretation}*

## Alternatives considered
{rec["sections"]["alternatives_considered"][0]}

## Recommendation
{rec["rendered_text"]}

---
*Content labels: rule and case content is supplementary teaching material;
syllabus references are verified_official (2021) / provisional_predecessor (2025).*
"""
    return md, [calc_table("Make-or-buy comparison", res)]


# ------------------------------------------------------------------ sample 3
def sample_capital_investment(conn) -> tuple[str, list]:
    facts = [Fact("appraisal_conflict", value="irr_npv")]
    rule, match = fired_rule("RULE-008", facts)
    fws = recommend_frameworks("capital_investment", ["project cash flows", "discount rate"])
    mapped = dict(mapped_frameworks(conn, "RULE-008"))

    flows = [-10000000, 3000000, 4000000, 5000000]
    npv = run_calculation("CALC-NPV", discount_rate=Decimal("0.12"), cash_flows=flows)
    irr = run_calculation("CALC-IRR", cash_flows=flows)
    payback = run_calculation("CALC-PAYBACK", cash_flows=flows)

    rec = build_recommendation(
        selected_option_id="REJECT",
        options=[
            option("REJECT", "Reject the expansion project",
                   "Avoids a negative-NPV investment", ["Foregone strategic positioning"]),
            option("ACCEPT", "Accept the expansion project",
                   "Captures strategic market share", [f"Negative NPV of Rs {abs(npv.result):,.2f} at 12%"]),
        ],
        confirmed_fact_ids=[
            "Initial outlay Rs 10,000,000; inflows Rs 3.0m / 4.0m / 5.0m",
            f"NPV at 12% is Rs {npv.result:,.2f}",
            f"IRR is {irr.result}% — below the 12% cost of capital",
        ],
        calc_summaries=[
            f"NPV is Rs {npv.result:,.2f} at the 12% discount rate",
            f"Payback is {payback.result} years",
        ],
        key_assumption="The 12% cost of capital reflects project risk",
        conditions_for_change=["Discount rate falling below the IRR",
                               "Cash inflows revised upwards by >10%"],
        implementation_steps=["Communicate the decision with the financial analysis",
                              "Revisit if strategic assumptions change"],
        kpis=["Actual vs forecast cash flows of alternative projects"],
        review_timing="At the next capital-budgeting round",
    )

    fw_lines = "\n".join(
        f"- **{f.framework_id}** ({f.name}) — {f.relevance_reason}\n"
        f"  - *Not suitable when:* {f.unsuitable_when}"
        + (f"\n  - *Why it fits this rule:* {mapped[f.framework_id]}" if f.framework_id in mapped else "")
        for f in fws
    )
    calc_lines = "\n".join(
        f"### {name}\n" + "\n".join(f"- {s}" for s in r.steps)
        + f"\n- **Result: {r.result} {r.result_unit}**\n"
        for name, r in [("Net present value", npv), ("Internal rate of return", irr),
                        ("Payback period", payback)]
    )
    md = f"""# Sample 3 — Capital investment appraisal (Indus Foods expansion, fictional)

## Facts
- Two mutually exclusive expansion options; Project X: outlay Rs 10,000,000,
  inflows Rs 3.0m / 4.0m / 5.0m over years 1–3.
- The IRR ranking and the NPV ranking of the options **disagree**
  (appraisal conflict: scale/timing differences).
- Cost of capital: 12%.

## Issues recognised
**{match.rule_id} — {match.title}**
- {match.interpretation}
- *Alternative explanations considered:* {"; ".join(match.alternative_explanations)}
- *Caution:* {match.caution}

## Frameworks
{fw_lines}

## Calculations (full workings in the CSV/Excel files)
{calc_lines}
## Alternatives considered
{rec["sections"]["alternatives_considered"][0]}

## Recommendation
{rec["rendered_text"]}

---
*Content labels: rule and case content is supplementary teaching material;
syllabus references are verified_official (2021) / provisional_predecessor (2025).*
"""
    tables = [calc_table(n, r) for n, r in
              [("Net present value", npv), ("Internal rate of return", irr),
               ("Payback period", payback)]]
    return md, tables


# ------------------------------------------------------------------ main
def main() -> None:
    db = seed_scratch_db()
    conn = dbcore.get_conn(db)
    try:
        samples = [
            ("working-capital", sample_working_capital(conn)),
            ("make-or-buy", sample_make_or_buy(conn)),
            ("capital-investment", sample_capital_investment(conn)),
        ]
    finally:
        conn.close()

    for slug, (md, tables) in samples:
        (SAMPLES_DIR / f"{slug}-analysis.md").write_text(md, encoding="utf-8")
        write_csv(SAMPLES_DIR / f"{slug}-workings.csv", tables)
        write_excel(SAMPLES_DIR / f"{slug}-workings.xlsx", tables)
        print(f"wrote {slug}-analysis.md / {slug}-workings.csv / {slug}-workings.xlsx")
    print("done.")


if __name__ == "__main__":
    main()
