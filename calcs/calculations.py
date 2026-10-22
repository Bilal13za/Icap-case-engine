"""Deterministic calculation library for the ICAP case engine.

Every calculation runs on ``decimal.Decimal`` with ROUND_HALF_UP:
currency results to 2dp, rates/percentages to 4dp (percentages are returned
as percent numbers, e.g. 9.4400 means 9.44%).

Conventions (documented per calculation in its assumptions):
- Rate inputs (discount rates, growth rates, cost of capital, tax rates) are
  decimal fractions: 0.10 means 10%.
- Percentage RESULTS are percent numbers: a result of 40.0000 with unit "%"
  means 40%.
- Cash flows occur at year-end unless stated; ``cash_flows[0]`` is the
  time-0 flow (usually the initial outlay, entered negative).
- Working-capital day counts use a 365-day year unless overridden.

Syllabus tags: "verified" = within the examinable scope of the 2021
Directive 1.01 (Revised 2024) syllabuses (CAF-6 Managerial and Financial
Analysis / CFAP-4 Business Finance Decisions, predecessors of 2025's CAF-7
Business Insights and Analysis and CFAP-4 Strategic Business Finance -- see
SYLLABUS_VERIFICATION.md; 2025 detailed learning outcomes are provisional
until officially published). "supplementary" = beyond examinable scope,
included for practice only.

Pure Python: no Streamlit, no AI/LLM, no network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, DivisionByZero, InvalidOperation, ROUND_HALF_UP, localcontext
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Rounding / formatting helpers
# ---------------------------------------------------------------------------

CURRENCY_DP = 2   # money
RATE_DP = 4       # rates and percentages (as percent numbers)
RATIO_DP = 2      # plain ratios / "times"
DAYS_DP = 2
YEARS_DP = 2
UNITS_DP = 2


def _q(value: Decimal, dp: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP)


def _money(value: Decimal) -> Decimal:
    """Currency result, 2dp."""
    return _q(value, CURRENCY_DP)


def _pct(fraction: Decimal) -> Decimal:
    """Decimal fraction -> percent number, 4dp (0.0944 -> 9.4400)."""
    return _q(fraction * Decimal(100), RATE_DP)


def _f2(value: Decimal) -> str:
    return f"{value:,.2f}"


def _f4(value: Decimal) -> str:
    return f"{value:,.4f}"


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


class MissingInputError(Exception):
    """Raised when required inputs are absent. Never invents defaults."""

    def __init__(self, missing: list[str]):
        self.missing: list[str] = list(missing)
        super().__init__(
            "Missing required input(s): " + ", ".join(self.missing)
        )


@dataclass
class CalcResult:
    calc_id: str
    name: str
    formula: str
    inputs: dict
    input_units: dict
    assumptions: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    result: Any = None  # Decimal or dict[str, Decimal]
    result_unit: str = ""
    interpretation: str = ""
    limitations: list[str] = field(default_factory=list)
    validation_status: str = ""


# ---------------------------------------------------------------------------
# Input conversion
# ---------------------------------------------------------------------------


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _to_decimal(name: str, value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"Input '{name}' must be numeric, got {value!r}")
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        raise ValueError(f"Input '{name}' must be numeric, got {value!r}")


def _convert(name: str, value: Any, spec: dict) -> Any:
    if name in spec.get("numeric_lists", ()):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"Input '{name}' must be a list of numbers")
        return [_to_decimal(f"{name}[{i}]", v) for i, v in enumerate(value)]
    if name in spec.get("text_lists", ()):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"Input '{name}' must be a list")
        return [str(v) for v in value]
    return _to_decimal(name, value)


# ---------------------------------------------------------------------------
# Business / performance calculations
# ---------------------------------------------------------------------------


def _calc_pct_change(*, old_value: Decimal, new_value: Decimal) -> dict:
    if old_value == 0:
        raise ValueError("old_value is zero; percentage change is undefined")
    change = (new_value - old_value) / old_value
    result = _pct(change)
    direction = "increased" if change > 0 else "decreased" if change < 0 else "is unchanged"
    return {
        "result": result,
        "steps": [
            f"Change = {_f2(new_value)} \u2212 {_f2(old_value)} = {_f2(new_value - old_value)}",
            f"% change = {_f2(new_value - old_value)} \u00f7 {_f2(old_value)} \u00d7 100 = {_f4(result)}%",
        ],
        "interpretation": (
            f"The value {direction} by {abs(result):,.4f}% from {_f2(old_value)} "
            f"to {_f2(new_value)}. Judge whether the size of the move is material "
            f"before drawing conclusions."
        ),
        "result_unit": "%",
    }


def _calc_cagr(*, begin_value: Decimal, end_value: Decimal, periods: Decimal) -> dict:
    if begin_value <= 0 or end_value <= 0:
        raise ValueError("begin_value and end_value must be positive for CAGR")
    if periods <= 0:
        raise ValueError("periods must be positive")
    with localcontext() as ctx:
        ctx.prec = 28
        rate = (end_value / begin_value) ** (Decimal(1) / periods) - 1
    result = _pct(rate)
    return {
        "result": result,
        "steps": [
            f"CAGR = ({_f2(end_value)} \u00f7 {_f2(begin_value)})^(1 \u00f7 {_f2(periods)}) \u2212 1",
            f"CAGR = {_f4(result)}%",
        ],
        "interpretation": (
            f"The value grew at a compound annual rate of {_f4(result)}% over "
            f"{_f2(periods)} periods. Compare with inflation, market growth and "
            f"the cost of capital to judge the performance."
        ),
        "result_unit": "%",
    }


def _calc_contribution(*, sales_revenue: Decimal, variable_costs: Decimal) -> dict:
    result = _money(sales_revenue - variable_costs)
    return {
        "result": result,
        "steps": [
            f"Contribution = {_f2(sales_revenue)} \u2212 {_f2(variable_costs)} = {_f2(result)}",
        ],
        "interpretation": (
            f"Each period's sales leave {_f2(result)} of contribution towards fixed "
            f"costs and profit. Decisions should be judged on this, not on "
            f"fully-absorbed profit."
        ),
        "result_unit": "currency",
    }


def _calc_cm_ratio(*, contribution: Decimal, sales_revenue: Decimal) -> dict:
    if sales_revenue == 0:
        raise ValueError("sales_revenue is zero; contribution margin ratio is undefined")
    result = _pct(contribution / sales_revenue)
    return {
        "result": result,
        "steps": [
            f"CM ratio = {_f2(contribution)} \u00f7 {_f2(sales_revenue)} \u00d7 100 = {_f4(result)}%",
        ],
        "interpretation": (
            f"{_f4(result)}p of every 1 of sales is contribution. A higher ratio "
            f"means profit responds more strongly to volume changes."
        ),
        "result_unit": "%",
    }


def _calc_breakeven_units(*, fixed_costs: Decimal, contribution_per_unit: Decimal) -> dict:
    if contribution_per_unit == 0:
        raise ValueError("contribution_per_unit is zero; breakeven is undefined")
    if contribution_per_unit < 0:
        raise ValueError("contribution_per_unit is negative; the product never breaks even")
    result = _q(fixed_costs / contribution_per_unit, UNITS_DP)
    return {
        "result": result,
        "steps": [
            f"Breakeven units = {_f2(fixed_costs)} \u00f7 {_f2(contribution_per_unit)} = {_f2(result)} units",
        ],
        "interpretation": (
            f"The business must sell {_f2(result)} units to cover all costs. "
            f"Compare with expected and capacity volumes to assess risk."
        ),
        "result_unit": "units",
    }


def _calc_breakeven_rev(*, fixed_costs: Decimal, cm_ratio: Decimal) -> dict:
    if cm_ratio == 0:
        raise ValueError("cm_ratio is zero; breakeven revenue is undefined")
    if cm_ratio < 0:
        raise ValueError("cm_ratio is negative; breakeven revenue is undefined")
    result = _money(fixed_costs / cm_ratio)
    return {
        "result": result,
        "steps": [
            f"Breakeven revenue = {_f2(fixed_costs)} \u00f7 {_f4(cm_ratio)} = {_f2(result)}",
            "Note: cm_ratio is entered as a decimal fraction (0.40 = 40%).",
        ],
        "interpretation": (
            f"Sales of {_f2(result)} exactly cover all costs. Useful for "
            f"multi-product settings where unit breakeven is meaningless."
        ),
        "result_unit": "currency",
    }


def _calc_margin_safety(*, actual_sales: Decimal, breakeven_sales: Decimal) -> dict:
    if actual_sales == 0:
        raise ValueError("actual_sales is zero; margin of safety is undefined")
    result = _pct((actual_sales - breakeven_sales) / actual_sales)
    return {
        "result": result,
        "steps": [
            f"Margin of safety = ({_f2(actual_sales)} \u2212 {_f2(breakeven_sales)}) "
            f"\u00f7 {_f2(actual_sales)} \u00d7 100 = {_f4(result)}%",
        ],
        "interpretation": (
            f"Sales can fall by {_f4(result)}% before losses begin. A thin margin "
            f"of safety means small demand shocks turn profit into loss."
        ),
        "result_unit": "%",
    }


def _calc_op_leverage(*, contribution: Decimal, operating_profit: Decimal) -> dict:
    if operating_profit == 0:
        raise ValueError("operating_profit is zero; degree of operating leverage is undefined")
    result = _q(contribution / operating_profit, RATIO_DP)
    return {
        "result": result,
        "steps": [
            f"DOL = {_f2(contribution)} \u00f7 {_f2(operating_profit)} = {_f2(result)}",
        ],
        "interpretation": (
            f"A 1% change in sales changes operating profit by about {_f2(result)}%. "
            f"High leverage magnifies both upside and downside."
        ),
        "result_unit": "ratio",
    }


def _calc_current_ratio(*, current_assets: Decimal, current_liabilities: Decimal) -> dict:
    if current_liabilities == 0:
        raise ValueError("current_liabilities is zero; current ratio is undefined")
    result = _q(current_assets / current_liabilities, RATIO_DP)
    return {
        "result": result,
        "steps": [
            f"Current ratio = {_f2(current_assets)} \u00f7 {_f2(current_liabilities)} = {_f2(result)}:1",
        ],
        "interpretation": (
            f"Current assets cover current liabilities {_f2(result)} times. Below "
            f"1.0 signals potential difficulty meeting short-term obligations."
        ),
        "result_unit": "times",
    }


def _calc_quick_ratio(
    *, current_assets: Decimal, inventory: Decimal, current_liabilities: Decimal
) -> dict:
    if current_liabilities == 0:
        raise ValueError("current_liabilities is zero; quick ratio is undefined")
    result = _q((current_assets - inventory) / current_liabilities, RATIO_DP)
    return {
        "result": result,
        "steps": [
            f"Quick assets = {_f2(current_assets)} \u2212 {_f2(inventory)} = {_f2(current_assets - inventory)}",
            f"Quick ratio = {_f2(current_assets - inventory)} \u00f7 {_f2(current_liabilities)} = {_f2(result)}:1",
        ],
        "interpretation": (
            f"Liquid assets (excluding inventory) cover current liabilities "
            f"{_f2(result)} times -- a stricter liquidity test than the current ratio."
        ),
        "result_unit": "times",
    }


def _calc_rec_days(*, receivables: Decimal, credit_sales: Decimal, days_in_year: Decimal) -> dict:
    if credit_sales == 0:
        raise ValueError("credit_sales is zero; receivable days is undefined")
    result = _q(receivables / credit_sales * days_in_year, DAYS_DP)
    return {
        "result": result,
        "steps": [
            f"Receivable days = {_f2(receivables)} \u00f7 {_f2(credit_sales)} "
            f"\u00d7 {_f2(days_in_year)} = {_f2(result)} days",
        ],
        "interpretation": (
            f"Customers take on average {_f2(result)} days to pay. Compare with "
            f"credit terms: a rising figure ties up cash and may signal "
            f"collection problems."
        ),
        "result_unit": "days",
    }


def _calc_pay_days(*, payables: Decimal, credit_purchases: Decimal, days_in_year: Decimal) -> dict:
    if credit_purchases == 0:
        raise ValueError("credit_purchases is zero; payable days is undefined")
    result = _q(payables / credit_purchases * days_in_year, DAYS_DP)
    return {
        "result": result,
        "steps": [
            f"Payable days = {_f2(payables)} \u00f7 {_f2(credit_purchases)} "
            f"\u00d7 {_f2(days_in_year)} = {_f2(result)} days",
        ],
        "interpretation": (
            f"The business takes on average {_f2(result)} days to pay suppliers. "
            f"Stretching payables frees cash but risks supplier relationships."
        ),
        "result_unit": "days",
    }


def _calc_inv_days(*, inventory: Decimal, cost_of_sales: Decimal, days_in_year: Decimal) -> dict:
    if cost_of_sales == 0:
        raise ValueError("cost_of_sales is zero; inventory days is undefined")
    result = _q(inventory / cost_of_sales * days_in_year, DAYS_DP)
    return {
        "result": result,
        "steps": [
            f"Inventory days = {_f2(inventory)} \u00f7 {_f2(cost_of_sales)} "
            f"\u00d7 {_f2(days_in_year)} = {_f2(result)} days",
        ],
        "interpretation": (
            f"Inventory sits on average {_f2(result)} days before sale. A rising "
            f"figure absorbs cash and may hide obsolete stock."
        ),
        "result_unit": "days",
    }


def _calc_ccc(*, receivable_days: Decimal, inventory_days: Decimal, payable_days: Decimal) -> dict:
    result = _q(receivable_days + inventory_days - payable_days, DAYS_DP)
    return {
        "result": result,
        "steps": [
            f"CCC = {_f2(receivable_days)} + {_f2(inventory_days)} \u2212 {_f2(payable_days)} "
            f"= {_f2(result)} days",
        ],
        "interpretation": (
            f"Cash is tied up for {_f2(result)} days between paying suppliers and "
            f"collecting from customers. A lengthening cycle is an early warning "
            f"of working-capital pressure."
        ),
        "result_unit": "days",
    }


def _calc_gross_margin(*, gross_profit: Decimal, revenue: Decimal) -> dict:
    if revenue == 0:
        raise ValueError("revenue is zero; gross margin is undefined")
    result = _pct(gross_profit / revenue)
    return {
        "result": result,
        "steps": [
            f"Gross margin = {_f2(gross_profit)} \u00f7 {_f2(revenue)} \u00d7 100 = {_f4(result)}%",
        ],
        "interpretation": (
            f"{_f4(result)}% of revenue remains after direct costs. A falling "
            f"gross margin points to pricing pressure or input-cost inflation."
        ),
        "result_unit": "%",
    }


def _calc_net_margin(*, profit_after_tax: Decimal, revenue: Decimal) -> dict:
    if revenue == 0:
        raise ValueError("revenue is zero; net margin is undefined")
    result = _pct(profit_after_tax / revenue)
    return {
        "result": result,
        "steps": [
            f"Net margin = {_f2(profit_after_tax)} \u00f7 {_f2(revenue)} \u00d7 100 = {_f4(result)}%",
        ],
        "interpretation": (
            f"{_f4(result)}p of every 1 of revenue becomes profit after tax. "
            f"Compare across periods and peers; check whether profit converts "
            f"to cash."
        ),
        "result_unit": "%",
    }


def _calc_roce(*, operating_profit: Decimal, capital_employed: Decimal) -> dict:
    if capital_employed == 0:
        raise ValueError("capital_employed is zero; ROCE is undefined")
    result = _pct(operating_profit / capital_employed)
    return {
        "result": result,
        "steps": [
            f"ROCE = {_f2(operating_profit)} \u00f7 {_f2(capital_employed)} \u00d7 100 = {_f4(result)}%",
        ],
        "interpretation": (
            f"The business earns {_f4(result)}% on long-term capital. Compare "
            f"with the cost of capital: ROCE persistently below it destroys value."
        ),
        "result_unit": "%",
    }


def _calc_roe(*, profit_after_tax: Decimal, equity: Decimal) -> dict:
    if equity == 0:
        raise ValueError("equity is zero; ROE is undefined")
    result = _pct(profit_after_tax / equity)
    return {
        "result": result,
        "steps": [
            f"ROE = {_f2(profit_after_tax)} \u00f7 {_f2(equity)} \u00d7 100 = {_f4(result)}%",
        ],
        "interpretation": (
            f"Shareholders earn {_f4(result)}% on their funds. High gearing can "
            f"inflate ROE, so read it alongside gearing and interest cover."
        ),
        "result_unit": "%",
    }


def _calc_asset_turnover(*, revenue: Decimal, total_assets: Decimal) -> dict:
    if total_assets == 0:
        raise ValueError("total_assets is zero; asset turnover is undefined")
    result = _q(revenue / total_assets, RATIO_DP)
    return {
        "result": result,
        "steps": [
            f"Asset turnover = {_f2(revenue)} \u00f7 {_f2(total_assets)} = {_f2(result)} times",
        ],
        "interpretation": (
            f"Each 1 of assets generates {_f2(result)} of revenue. Low turnover "
            f"suggests under-utilised or bloated assets."
        ),
        "result_unit": "times",
    }


def _calc_gearing(*, debt: Decimal, equity: Decimal) -> dict:
    capital = debt + equity
    if capital == 0:
        raise ValueError("debt + equity is zero; gearing is undefined")
    result = _pct(debt / capital)
    return {
        "result": result,
        "steps": [
            f"Gearing = {_f2(debt)} \u00f7 ({_f2(debt)} + {_f2(equity)}) \u00d7 100 = {_f4(result)}%",
            "Definition used: interest-bearing debt \u00f7 total capital (debt + equity), book values.",
        ],
        "interpretation": (
            f"{_f4(result)}% of capital is debt. Higher gearing raises financial "
            f"risk: check interest cover and debt covenants alongside."
        ),
        "result_unit": "%",
    }


def _calc_int_cover(*, operating_profit: Decimal, finance_cost: Decimal) -> dict:
    if finance_cost == 0:
        raise ValueError("finance_cost is zero; interest cover is undefined")
    result = _q(operating_profit / finance_cost, RATIO_DP)
    return {
        "result": result,
        "steps": [
            f"Interest cover = {_f2(operating_profit)} \u00f7 {_f2(finance_cost)} = {_f2(result)} times",
        ],
        "interpretation": (
            f"Operating profit covers interest {_f2(result)} times. Cover below "
            f"about 2-3 times (industry-dependent) signals distress risk if "
            f"profits dip."
        ),
        "result_unit": "times",
    }


# ---------------------------------------------------------------------------
# Finance calculations
# ---------------------------------------------------------------------------


def _check_growth_base(rate: Decimal, what: str = "discount_rate") -> Decimal:
    base = Decimal(1) + rate
    if base == 0:
        raise ValueError(f"{what} of -100% makes present values undefined")
    return base


def _calc_pv(*, future_value: Decimal, discount_rate: Decimal, periods: Decimal) -> dict:
    if periods < 0:
        raise ValueError("periods must not be negative")
    base = _check_growth_base(discount_rate)
    with localcontext() as ctx:
        ctx.prec = 28
        result = _money(future_value / (base ** periods))
    return {
        "result": result,
        "steps": [
            f"PV = {_f2(future_value)} \u00f7 (1 + {_f4(discount_rate)})^{_f2(periods)}",
            f"PV = {_f2(result)}",
        ],
        "interpretation": (
            f"{_f2(future_value)} received in {_f2(periods)} periods is worth "
            f"{_f2(result)} today at {_f4(discount_rate * 100)}%. Money today is "
            f"worth more than the same money later."
        ),
        "result_unit": "currency",
    }


def _calc_fv(*, present_value: Decimal, discount_rate: Decimal, periods: Decimal) -> dict:
    if periods < 0:
        raise ValueError("periods must not be negative")
    _check_growth_base(discount_rate)
    with localcontext() as ctx:
        ctx.prec = 28
        result = _money(present_value * ((Decimal(1) + discount_rate) ** periods))
    return {
        "result": result,
        "steps": [
            f"FV = {_f2(present_value)} \u00d7 (1 + {_f4(discount_rate)})^{_f2(periods)}",
            f"FV = {_f2(result)}",
        ],
        "interpretation": (
            f"{_f2(present_value)} invested today grows to {_f2(result)} in "
            f"{_f2(periods)} periods at {_f4(discount_rate * 100)}% per period."
        ),
        "result_unit": "currency",
    }


def _calc_annuity_pv(*, payment: Decimal, discount_rate: Decimal, periods: Decimal) -> dict:
    if periods < 0:
        raise ValueError("periods must not be negative")
    base = _check_growth_base(discount_rate)
    with localcontext() as ctx:
        ctx.prec = 28
        if discount_rate == 0:
            pv = payment * periods
        else:
            pv = payment * (Decimal(1) - base ** (-periods)) / discount_rate
        result = _money(pv)
    return {
        "result": result,
        "steps": [
            f"Annuity PV = {_f2(payment)} \u00d7 [1 \u2212 (1 + {_f4(discount_rate)})^(\u2212{_f2(periods)})] "
            f"\u00f7 {_f4(discount_rate)}",
            f"Annuity PV = {_f2(result)}",
        ],
        "interpretation": (
            f"A stream of {_f2(payment)} per period for {_f2(periods)} periods is "
            f"worth {_f2(result)} today. Use for valuing level cash-flow streams "
            f"such as lease payments."
        ),
        "result_unit": "currency",
    }


def _calc_annuity_fv(*, payment: Decimal, discount_rate: Decimal, periods: Decimal) -> dict:
    if periods < 0:
        raise ValueError("periods must not be negative")
    _check_growth_base(discount_rate)
    with localcontext() as ctx:
        ctx.prec = 28
        base = Decimal(1) + discount_rate
        if discount_rate == 0:
            fv = payment * periods
        else:
            fv = payment * ((base ** periods) - Decimal(1)) / discount_rate
        result = _money(fv)
    return {
        "result": result,
        "steps": [
            f"Annuity FV = {_f2(payment)} \u00d7 [(1 + {_f4(discount_rate)})^{_f2(periods)} \u2212 1] "
            f"\u00f7 {_f4(discount_rate)}",
            f"Annuity FV = {_f2(result)}",
        ],
        "interpretation": (
            f"Investing {_f2(payment)} per period for {_f2(periods)} periods "
            f"accumulates to {_f2(result)}."
        ),
        "result_unit": "currency",
    }


def _npv_of(rate: Decimal, cash_flows: list[Decimal]) -> Decimal:
    total = Decimal(0)
    base = Decimal(1) + rate
    for t, cf in enumerate(cash_flows):
        total += cf / (base ** t)
    return total


def _calc_npv(*, discount_rate: Decimal, cash_flows: list[Decimal]) -> dict:
    if not cash_flows:
        raise ValueError("cash_flows must not be empty")
    _check_growth_base(discount_rate)
    with localcontext() as ctx:
        ctx.prec = 28
        discounted = [_q(cf / ((Decimal(1) + discount_rate) ** t), CURRENCY_DP)
                      for t, cf in enumerate(cash_flows)]
        result = _money(sum(discounted, Decimal(0)))
    steps = [
        f"NPV = \u03a3 CFt \u00f7 (1 + {_f4(discount_rate)})^t, t = 0..{len(cash_flows) - 1}",
    ]
    for t, (cf, dcf) in enumerate(zip(cash_flows, discounted)):
        steps.append(f"t={t}: {_f2(cf)} \u00f7 (1 + {_f4(discount_rate)})^{t} = {_f2(dcf)}")
    steps.append(f"NPV = {_f2(result)}")
    decision = "exceeds" if result > 0 else "equals" if result == 0 else "is below"
    return {
        "result": result,
        "steps": steps,
        "interpretation": (
            f"NPV is {_f2(result)}, which {decision} zero. On financial grounds "
            f"{'accept' if result > 0 else 'reject' if result < 0 else 'the project is marginal -- accept only if non-financial factors favour it'} "
            f"the project (for independent projects)."
        ),
        "result_unit": "currency",
    }


def _calc_irr(*, cash_flows: list[Decimal]) -> dict:
    if not cash_flows:
        raise ValueError("cash_flows must not be empty")
    cfs = list(cash_flows)
    candidates = [Decimal(x) for x in
                  ("-0.9", "-0.5", "-0.2", "-0.1", "0", "0.05", "0.1",
                   "0.2", "0.3", "0.5", "1", "2", "5", "10")]
    lo = hi = None
    for a, b in zip(candidates, candidates[1:]):
        try:
            with localcontext() as ctx:
                ctx.prec = 28
                na, nb = _npv_of(a, cfs), _npv_of(b, cfs)
        except (InvalidOperation, DivisionByZero, ValueError):
            continue
        if na == 0:
            lo = hi = a
            break
        if na * nb < 0:
            lo, hi = a, b
            break
    if lo is None:
        raise ValueError(
            "No sign change in NPV across the searched rate range "
            "(-90% to 1000%); IRR is undefined for these cash flows."
        )
    tol = Decimal("0.000001")
    blo, bhi = lo, hi  # original bracket, for the workings display
    with localcontext() as ctx:
        ctx.prec = 28
        n_lo = _npv_of(lo, cfs)
        iterations = 0
        for iterations in range(1, 201):
            mid = (lo + hi) / 2
            n_mid = _npv_of(mid, cfs)
            if abs(n_mid) < tol or (hi - lo) < tol:
                lo = hi = mid
                break
            if n_lo * n_mid < 0:
                hi = mid
            else:
                lo, n_lo = mid, n_mid
        irr = (lo + hi) / 2
    result = _pct(irr)
    return {
        "result": result,
        "steps": [
            f"Sign-change bracket found: r in [{_f4(blo * 100)}%, {_f4(bhi * 100)}%]",
            f"Bisection converged in {iterations} iteration(s) (tolerance 1e-6, max 200)",
            f"IRR = {_f4(result)}%",
        ],
        "interpretation": (
            f"The project's IRR is {_f4(result)}%. Accept if it exceeds the cost "
            f"of capital (for conventional cash flows and independent projects); "
            f"where IRR and NPV conflict, NPV governs."
        ),
        "result_unit": "%",
    }


def _payback_from_flows(flows: list[Decimal], label: str) -> tuple[Decimal, list[str]]:
    cum = Decimal(0)
    for t, cf in enumerate(flows):
        prev = cum
        cum += cf
        if t == 0 and cum >= 0:
            return _q(Decimal(0), YEARS_DP), [f"Cumulative cash flow is {_f2(cum)} at t=0: payback = 0 years"]
        if t > 0 and prev < 0 <= cum:
            if cf <= 0:
                raise ValueError(f"{label}: cumulative flow reaches zero on a non-positive flow; payback undefined")
            pb = _q(Decimal(t - 1) + (-prev) / cf, YEARS_DP)
            steps = [
                f"Cumulative flow turns positive between t={t - 1} ({_f2(prev)}) and t={t} ({_f2(cum)})",
                f"Payback = {t - 1} + {_f2(-prev)} \u00f7 {_f2(cf)} = {_f2(pb)} years",
            ]
            return pb, steps
    raise ValueError(
        f"{label}: cumulative cash flow never reaches zero -- the project does "
        "not pay back within the forecast period."
    )


def _calc_payback(*, cash_flows: list[Decimal]) -> dict:
    if not cash_flows:
        raise ValueError("cash_flows must not be empty")
    result, steps = _payback_from_flows(list(cash_flows), "Payback")
    return {
        "result": result,
        "steps": ["Payback = first t where cumulative cash flow \u2265 0"] + steps,
        "interpretation": (
            f"The initial outlay is recovered after {_f2(result)} years. Shorter "
            f"is better for liquidity and risk, but payback ignores the time "
            f"value of money and post-payback flows."
        ),
        "result_unit": "years",
    }


def _calc_discounted_payback(*, discount_rate: Decimal, cash_flows: list[Decimal]) -> dict:
    if not cash_flows:
        raise ValueError("cash_flows must not be empty")
    _check_growth_base(discount_rate)
    with localcontext() as ctx:
        ctx.prec = 28
        discounted = [cf / ((Decimal(1) + discount_rate) ** t)
                      for t, cf in enumerate(cash_flows)]
    result, steps = _payback_from_flows(discounted, "Discounted payback")
    return {
        "result": result,
        "steps": [f"Discounted at {_f4(discount_rate * 100)}%; then first t where cumulative discounted flow \u2265 0"] + steps,
        "interpretation": (
            f"The outlay is recovered after {_f2(result)} years in present-value "
            f"terms. An improvement on simple payback, but it still ignores "
            f"cash flows after payback."
        ),
        "result_unit": "years",
    }


def _calc_wacc(
    *,
    cost_equity: Decimal,
    cost_debt: Decimal,
    tax_rate: Decimal,
    market_value_equity: Decimal,
    market_value_debt: Decimal,
) -> dict:
    total = market_value_equity + market_value_debt
    if total == 0:
        raise ValueError("market values sum to zero; WACC weights are undefined")
    wacc = (market_value_equity / total) * cost_equity + \
           (market_value_debt / total) * cost_debt * (Decimal(1) - tax_rate)
    result = _pct(wacc)
    return {
        "result": result,
        "steps": [
            f"Weights: E/V = {_f2(market_value_equity)} \u00f7 {_f2(total)} = {_f4(market_value_equity / total)}, "
            f"D/V = {_f2(market_value_debt)} \u00f7 {_f2(total)} = {_f4(market_value_debt / total)}",
            f"WACC = {_f4(market_value_equity / total)} \u00d7 {_f4(cost_equity)} + "
            f"{_f4(market_value_debt / total)} \u00d7 {_f4(cost_debt)} \u00d7 (1 \u2212 {_f4(tax_rate)})",
            f"WACC = {_f4(result)}%",
        ],
        "interpretation": (
            f"The blended cost of capital is {_f4(result)}%. Use it as the "
            f"discount rate for NPV and as the hurdle rate: projects must earn "
            f"at least this to create value."
        ),
        "result_unit": "%",
    }


def _calc_capm(*, risk_free_rate: Decimal, beta: Decimal, market_return: Decimal) -> dict:
    ke = risk_free_rate + beta * (market_return - risk_free_rate)
    result = _pct(ke)
    return {
        "result": result,
        "steps": [
            f"Ke = {_f4(risk_free_rate)} + {_f4(beta)} \u00d7 ({_f4(market_return)} \u2212 {_f4(risk_free_rate)})",
            f"Ke = {_f4(result)}%",
            "Note: rates entered as decimal fractions (0.05 = 5%).",
        ],
        "interpretation": (
            f"The CAPM cost of equity is {_f4(result)}%. It prices only "
            f"systematic risk (beta {_f4(beta)}); firm-specific risk is assumed "
            f"diversified away."
        ),
        "result_unit": "%",
    }


def _calc_cost_debt(
    *,
    annual_interest: Decimal,
    issue_price: Decimal,
    redemption_price: Decimal,
    periods: Decimal,
    tax_rate: Decimal,
) -> dict:
    if periods <= 0:
        raise ValueError("periods must be positive")
    if issue_price + redemption_price == 0:
        raise ValueError("issue_price + redemption_price is zero; approximation undefined")
    pre_tax = (annual_interest + (redemption_price - issue_price) / periods) / \
              ((redemption_price + issue_price) / 2)
    after_tax = pre_tax * (Decimal(1) - tax_rate)
    result = _pct(after_tax)
    return {
        "result": result,
        "steps": [
            f"Approx pre-tax Kd = [{_f2(annual_interest)} + ({_f2(redemption_price)} \u2212 {_f2(issue_price)}) "
            f"\u00f7 {_f2(periods)}] \u00f7 [({_f2(redemption_price)} + {_f2(issue_price)}) \u00f7 2]",
            f"Approx pre-tax Kd = {_f4(pre_tax * 100)}%",
            f"After-tax Kd = {_f4(pre_tax * 100)}% \u00d7 (1 \u2212 {_f4(tax_rate)}) = {_f4(result)}%",
        ],
        "interpretation": (
            f"The effective after-tax cost of this redeemable debt is about "
            f"{_f4(result)}%. It is an approximation -- the true yield to "
            f"maturity needs IRR-style iteration."
        ),
        "result_unit": "%",
    }


def _check_probabilities(probabilities: list[Decimal], what: str) -> None:
    if not probabilities:
        raise ValueError(f"{what}: probabilities must not be empty")
    total = sum(probabilities, Decimal(0))
    if abs(total - 1) > Decimal("0.000001"):
        raise ValueError(
            f"{what}: probabilities sum to {_f4(total)}, not 1.0000"
        )


def _calc_ev(*, outcomes: list[Decimal], probabilities: list[Decimal]) -> dict:
    if len(outcomes) != len(probabilities):
        raise ValueError("outcomes and probabilities must have the same length")
    _check_probabilities(probabilities, "Expected value")
    ev = sum((p * x for p, x in zip(probabilities, outcomes)), Decimal(0))
    result = _money(ev)
    steps = ["EV = \u03a3 (probability \u00d7 outcome)"]
    for p, x in zip(probabilities, outcomes):
        steps.append(f"{_f4(p)} \u00d7 {_f2(x)} = {_f2(_money(p * x))}")
    steps.append(f"EV = {_f2(result)}")
    return {
        "result": result,
        "steps": steps,
        "interpretation": (
            f"The probability-weighted expected outcome is {_f2(result)}. Use it "
            f"to compare risky alternatives, but remember it is an average -- "
            f"the worst case may still be unacceptable."
        ),
        "result_unit": "currency",
    }


def _calc_sensitivity(
    *,
    base_npv: Decimal,
    npv_after_1pct_increase: Decimal,
    variable_current_value: Decimal,
) -> dict:
    delta = npv_after_1pct_increase - base_npv
    if base_npv == 0:
        raise ValueError("base_npv is zero; percentage sensitivity is undefined")
    if variable_current_value == 0:
        raise ValueError("variable_current_value is zero; breakeven value is undefined")
    if delta == 0:
        raise ValueError("NPV does not change with the variable; sensitivity is zero and no breakeven exists")
    sensitivity = _q(delta / base_npv * 100, RATE_DP)
    slope = delta / (Decimal("0.01") * variable_current_value)
    breakeven = _money(variable_current_value - base_npv / slope)
    result = {"sensitivity_pct": sensitivity, "breakeven_value": breakeven}
    return {
        "result": result,
        "steps": [
            f"\u0394NPV for +1% in variable = {_f2(npv_after_1pct_increase)} \u2212 {_f2(base_npv)} = {_f2(delta)}",
            f"Sensitivity = {_f2(delta)} \u00f7 {_f2(base_npv)} \u00d7 100 = {_f4(sensitivity)}% change in NPV per 1% change in variable",
            f"Slope \u2248 {_f2(delta)} \u00f7 (1% \u00d7 {_f2(variable_current_value)}) = {_f4(slope)} per unit",
            f"Breakeven value \u2248 {_f2(variable_current_value)} \u2212 {_f2(base_npv)} \u00f7 {_f4(slope)} = {_f2(breakeven)}",
        ],
        "interpretation": (
            f"A 1% move in the variable moves NPV by {_f4(sensitivity)}%; NPV "
            f"falls to zero if the variable reaches {_f2(breakeven)}. Focus "
            f"estimation effort and risk responses on the most sensitive variables."
        ),
        "result_unit": "% (sensitivity); currency (breakeven value)",
    }


def _calc_scenario_npv(*, scenario_npvs: list[Decimal], probabilities: list[Decimal]) -> dict:
    if len(scenario_npvs) != len(probabilities):
        raise ValueError("scenario_npvs and probabilities must have the same length")
    _check_probabilities(probabilities, "Scenario NPV")
    expected = sum((p * n for p, n in zip(probabilities, scenario_npvs)), Decimal(0))
    result = _money(expected)
    steps = ["Expected NPV = \u03a3 (probability \u00d7 scenario NPV)"]
    for i, (p, n) in enumerate(zip(probabilities, scenario_npvs), 1):
        steps.append(f"Scenario {i}: {_f4(p)} \u00d7 {_f2(n)} = {_f2(_money(p * n))}")
    steps.append(f"Expected NPV = {_f2(result)}")
    worst = min(scenario_npvs)
    return {
        "result": result,
        "steps": steps,
        "interpretation": (
            f"The probability-weighted NPV is {_f2(result)}; the worst scenario "
            f"NPV is {_f2(_money(worst))}. Decide on the expected value but "
            f"check the business could survive the worst case."
        ),
        "result_unit": "currency",
    }


def _calc_gordon(*, dividend_next: Decimal, cost_equity: Decimal, growth_rate: Decimal) -> dict:
    if cost_equity <= growth_rate:
        raise ValueError("cost_equity must exceed growth_rate; otherwise the Gordon model gives a meaningless value")
    result = _money(dividend_next / (cost_equity - growth_rate))
    return {
        "result": result,
        "steps": [
            f"P0 = {_f2(dividend_next)} \u00f7 ({_f4(cost_equity)} \u2212 {_f4(growth_rate)})",
            f"P0 = {_f2(result)}",
            "Note: rates entered as decimal fractions (0.10 = 10%).",
        ],
        "interpretation": (
            f"The Gordon model values the share at {_f2(result)}. It is highly "
            f"sensitive to the growth assumption -- small changes in g move the "
            f"value a lot."
        ),
        "result_unit": "currency",
    }


def _calc_pe_val(*, earnings_per_share: Decimal, pe_ratio: Decimal) -> dict:
    result = _money(earnings_per_share * pe_ratio)
    return {
        "result": result,
        "steps": [
            f"Value per share = {_f2(earnings_per_share)} \u00d7 {_f2(pe_ratio)} = {_f2(result)}",
        ],
        "interpretation": (
            f"The P/E-based value is {_f2(result)} per share. The answer is only "
            f"as good as the chosen P/E -- justify it with genuinely comparable "
            f"companies."
        ),
        "result_unit": "currency",
    }


def _calc_asset_val(*, total_assets: Decimal, total_liabilities: Decimal, shares_outstanding: Decimal) -> dict:
    if shares_outstanding == 0:
        raise ValueError("shares_outstanding is zero; value per share is undefined")
    nav = total_assets - total_liabilities
    result = _money(nav / shares_outstanding)
    return {
        "result": result,
        "steps": [
            f"Net assets = {_f2(total_assets)} \u2212 {_f2(total_liabilities)} = {_f2(nav)}",
            f"Value per share = {_f2(nav)} \u00f7 {_f2(shares_outstanding)} = {_f2(result)}",
        ],
        "interpretation": (
            f"The asset-basis value is {_f2(result)} per share -- a floor value "
            f"useful for asset-heavy businesses, but it ignores future earnings "
            f"power and uses book values."
        ),
        "result_unit": "currency",
    }


def _calc_relevant_cost(*, costs_a: list[Decimal], costs_b: list[Decimal]) -> dict:
    if not costs_a or not costs_b:
        raise ValueError("costs_a and costs_b must each contain at least one cost")
    total_a = _money(sum(costs_a, Decimal(0)))
    total_b = _money(sum(costs_b, Decimal(0)))
    diff = _money(total_a - total_b)
    cheaper = "B" if diff > 0 else "A" if diff < 0 else "neither -- they cost the same"
    return {
        "result": {"total_a": total_a, "total_b": total_b, "difference_a_minus_b": diff},
        "steps": [
            f"Total relevant cost A = {' + '.join(_f2(c) for c in costs_a)} = {_f2(total_a)}",
            f"Total relevant cost B = {' + '.join(_f2(c) for c in costs_b)} = {_f2(total_b)}",
            f"Difference (A \u2212 B) = {_f2(diff)}",
            "Only future incremental cash costs belong here: exclude sunk costs and allocated fixed overhead.",
        ],
        "interpretation": (
            f"On relevant costs alone, option {cheaper} is cheaper "
            f"({f'by {_f2(abs(diff))}' if diff != 0 else 'identical cost'}). "
            f"Now weigh non-financial factors before deciding."
        ),
        "result_unit": "currency (all amounts)",
    }


def _calc_makebuy(
    *,
    units: Decimal,
    buy_price: Decimal,
    variable_cost_make: Decimal,
    specific_fixed_cost_make: Decimal,
    opportunity_cost: Decimal,
) -> dict:
    if units < 0:
        raise ValueError("units must not be negative")
    total_make = _money(units * variable_cost_make + specific_fixed_cost_make + opportunity_cost)
    total_buy = _money(units * buy_price)
    saving = _money(total_buy - total_make)
    verdict = "making" if saving > 0 else "buying" if saving < 0 else "neither"
    return {
        "result": {
            "total_make_cost": total_make,
            "total_buy_cost": total_buy,
            "saving_from_making": saving,
        },
        "steps": [
            f"Make: {_f2(units)} \u00d7 {_f2(variable_cost_make)} + {_f2(specific_fixed_cost_make)} "
            f"(specific fixed) + {_f2(opportunity_cost)} (opportunity) = {_f2(total_make)}",
            f"Buy: {_f2(units)} \u00d7 {_f2(buy_price)} = {_f2(total_buy)}",
            f"Saving from making = {_f2(total_buy)} \u2212 {_f2(total_make)} = {_f2(saving)}",
        ],
        "interpretation": (
            f"Making in-house is cheaper by {_f2(saving)} -- prefer {verdict} on "
            f"cost grounds. Confirm quality, reliability and strategic "
            f"considerations before switching."
            if saving != 0 else
            "Both options cost the same on relevant costs -- decide on non-financial factors."
        ),
        "result_unit": "currency (all amounts)",
    }


def _calc_special_order(
    *,
    units: Decimal,
    special_price: Decimal,
    variable_cost_per_unit: Decimal,
    incremental_fixed_cost: Decimal,
    lost_contribution: Decimal,
) -> dict:
    if units < 0:
        raise ValueError("units must not be negative")
    revenue = _money(units * special_price)
    cost = _money(units * variable_cost_per_unit + incremental_fixed_cost + lost_contribution)
    profit = _money(revenue - cost)
    return {
        "result": {
            "incremental_revenue": revenue,
            "incremental_cost": cost,
            "incremental_profit": profit,
        },
        "steps": [
            f"Incremental revenue = {_f2(units)} \u00d7 {_f2(special_price)} = {_f2(revenue)}",
            f"Incremental cost = {_f2(units)} \u00d7 {_f2(variable_cost_per_unit)} + "
            f"{_f2(incremental_fixed_cost)} + {_f2(lost_contribution)} (lost contribution) = {_f2(cost)}",
            f"Incremental profit = {_f2(revenue)} \u2212 {_f2(cost)} = {_f2(profit)}",
        ],
        "interpretation": (
            f"The order adds {_f2(profit)} of profit -- "
            f"{'accept' if profit > 0 else 'reject' if profit < 0 else 'it is marginal; accept only for strategic reasons'} "
            f"on financial grounds, provided spare capacity truly exists and "
            f"existing customers will not demand the lower price."
        ),
        "result_unit": "currency (all amounts)",
    }


def _calc_limiting_factor(
    *,
    product_names: list[str],
    contribution_per_unit: list[Decimal],
    limiting_factor_per_unit: list[Decimal],
) -> dict:
    names = [str(n) for n in product_names]
    cpus = list(contribution_per_unit)
    lpus = list(limiting_factor_per_unit)
    if not names:
        raise ValueError("at least one product is required")
    if not (len(names) == len(cpus) == len(lpus)):
        raise ValueError(
            "product_names, contribution_per_unit and limiting_factor_per_unit "
            "must have the same length"
        )
    rows = []
    for name, cpu, lpu in zip(names, cpus, lpus):
        if lpu <= 0:
            raise ValueError(f"limiting factor per unit for {name!r} must be positive")
        rows.append({"name": name, "cpu": cpu, "lpu": lpu, "per_unit": cpu / lpu})
    rows.sort(key=lambda r: r["per_unit"], reverse=True)
    result = {r["name"]: Decimal(i + 1) for i, r in enumerate(rows)}
    steps = ["Rank by contribution per unit of limiting factor:"]
    for i, r in enumerate(rows, 1):
        steps.append(
            f"{i}. {r['name']}: {_f2(r['cpu'])} \u00f7 {_f2(r['lpu'])} = {_f4(r['per_unit'])} per limiting-factor unit"
        )
    top = rows[0]["name"]
    return {
        "result": result,
        "steps": steps,
        "interpretation": (
            f"Allocate the scarce resource to {top} first, then down the "
            f"ranking until the constraint or demand is exhausted. Re-check "
            f"when demand limits or the bottleneck change."
        ),
        "result_unit": "rank (1 = produce first)",
    }


def _calc_material_var(
    *,
    standard_price: Decimal,
    actual_price: Decimal,
    actual_quantity: Decimal,
    standard_quantity: Decimal,
) -> dict:
    price_var = _money((standard_price - actual_price) * actual_quantity)
    usage_var = _money((standard_quantity - actual_quantity) * standard_price)
    total = _money(price_var + usage_var)

    def _flag(v: Decimal) -> str:
        return "F" if v > 0 else "A" if v < 0 else "-"

    return {
        "result": {
            "price_variance": price_var,
            "usage_variance": usage_var,
            "total_variance": total,
        },
        "steps": [
            f"Price variance = ({_f2(standard_price)} \u2212 {_f2(actual_price)}) \u00d7 {_f2(actual_quantity)} "
            f"= {_f2(price_var)} {_flag(price_var)}",
            f"Usage variance = ({_f2(standard_quantity)} \u2212 {_f2(actual_quantity)}) \u00d7 {_f2(standard_price)} "
            f"= {_f2(usage_var)} {_flag(usage_var)}",
            f"Total = {_f2(price_var)} + {_f2(usage_var)} = {_f2(total)} {_flag(total)}",
            "Sign convention: positive = favourable (F), negative = adverse (A).",
        ],
        "interpretation": (
            f"Material price variance {_f2(price_var)} {_flag(price_var)}, usage "
            f"variance {_f2(usage_var)} {_flag(usage_var)}. Investigate the "
            f"adverse variance's cause (price negotiation, quality, wastage) "
            f"and who controls it."
        ),
        "result_unit": "currency (all amounts); positive = favourable",
    }


def _calc_labour_var(
    *,
    standard_rate: Decimal,
    actual_rate: Decimal,
    actual_hours: Decimal,
    standard_hours: Decimal,
) -> dict:
    rate_var = _money((standard_rate - actual_rate) * actual_hours)
    eff_var = _money((standard_hours - actual_hours) * standard_rate)
    total = _money(rate_var + eff_var)

    def _flag(v: Decimal) -> str:
        return "F" if v > 0 else "A" if v < 0 else "-"

    return {
        "result": {
            "rate_variance": rate_var,
            "efficiency_variance": eff_var,
            "total_variance": total,
        },
        "steps": [
            f"Rate variance = ({_f2(standard_rate)} \u2212 {_f2(actual_rate)}) \u00d7 {_f2(actual_hours)} "
            f"= {_f2(rate_var)} {_flag(rate_var)}",
            f"Efficiency variance = ({_f2(standard_hours)} \u2212 {_f2(actual_hours)}) \u00d7 {_f2(standard_rate)} "
            f"= {_f2(eff_var)} {_flag(eff_var)}",
            f"Total = {_f2(rate_var)} + {_f2(eff_var)} = {_f2(total)} {_flag(total)}",
            "Sign convention: positive = favourable (F), negative = adverse (A).",
        ],
        "interpretation": (
            f"Labour rate variance {_f2(rate_var)} {_flag(rate_var)}, efficiency "
            f"variance {_f2(eff_var)} {_flag(eff_var)}. A favourable rate "
            f"variance paired with adverse efficiency may mean cheaper, "
            f"less-skilled labour -- investigate the trade-off."
        ),
        "result_unit": "currency (all amounts); positive = favourable",
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def _spec(
    name: str,
    formula: str,
    required: list[str],
    optional: dict[str, str],
    units: dict[str, str],
    category: str,
    syllabus_tag: str,
    assumptions: list[str],
    limitations: list[str],
    func: Callable[..., dict],
    numeric_lists: tuple[str, ...] = (),
    text_lists: tuple[str, ...] = (),
) -> dict:
    return {
        "name": name,
        "formula": formula,
        "required": required,
        "optional": optional,
        "units": units,
        "category": category,
        "syllabus_tag": syllabus_tag,
        "assumptions": assumptions,
        "limitations": limitations,
        "func": func,
        "numeric_lists": numeric_lists,
        "text_lists": text_lists,
    }


_A_YEAR_END = "Cash flows occur at year-end."
_A_365 = "A 365-day year is used unless days_in_year is overridden."
_A_FRACTION = "Rates are entered as decimal fractions (0.10 = 10%)."
_A_BOOK = "Book values are used; market values may differ."
_A_POS_FAV = "Positive variance = favourable (F); negative = adverse (A)."

REGISTRY: dict[str, dict] = {
    # -- performance -------------------------------------------------------
    "CALC-PCT-CHANGE": _spec(
        "Percentage change", "% change = (New \u2212 Old) \u00f7 Old \u00d7 100",
        ["old_value", "new_value"], {},
        {"old_value": "currency", "new_value": "currency"},
        "performance", "verified", [],
        ["Meaningless if the base value is tiny or volatile.",
         "Shows the size of a move, never its cause."],
        _calc_pct_change),
    "CALC-CAGR": _spec(
        "Compound annual growth rate", "CAGR = (End \u00f7 Begin)^(1 \u00f7 n) \u2212 1",
        ["begin_value", "end_value", "periods"], {},
        {"begin_value": "currency", "end_value": "currency", "periods": "periods"},
        "performance", "verified",
        ["Growth is assumed smooth between the endpoints."],
        ["Hides volatility between the start and end points.",
         "Sensitive to the choice of start/end period."],
        _calc_cagr),
    "CALC-GROSS-MARGIN": _spec(
        "Gross profit margin", "Gross margin = Gross profit \u00f7 Revenue \u00d7 100",
        ["gross_profit", "revenue"], {},
        {"gross_profit": "currency", "revenue": "currency"},
        "performance", "verified", [],
        ["Mix changes can move the margin without any price/cost change.",
         "Accounting policy choices (e.g. cost allocation) affect comparability."],
        _calc_gross_margin),
    "CALC-NET-MARGIN": _spec(
        "Net profit margin", "Net margin = Profit after tax \u00f7 Revenue \u00d7 100",
        ["profit_after_tax", "revenue"], {},
        {"profit_after_tax": "currency", "revenue": "currency"},
        "performance", "verified", [],
        ["One-off items can distort a single year's margin.",
         "Profit is not cash -- check operating cash flow too."],
        _calc_net_margin),
    "CALC-ROCE": _spec(
        "Return on capital employed", "ROCE = Operating profit \u00f7 Capital employed \u00d7 100",
        ["operating_profit", "capital_employed"], {},
        {"operating_profit": "currency", "capital_employed": "currency"},
        "performance", "verified",
        ["Operating profit = profit before interest and tax.",
         "Capital employed = total assets \u2212 current liabilities (equivalently equity + non-current liabilities)."],
        ["Book values may understate capital for asset-light businesses.",
         "A single year's ROCE can be distorted by timing of investment."],
        _calc_roce),
    "CALC-ROE": _spec(
        "Return on equity", "ROE = Profit after tax \u00f7 Equity \u00d7 100",
        ["profit_after_tax", "equity"], {},
        {"profit_after_tax": "currency", "equity": "currency"},
        "performance", "verified", [],
        ["High gearing inflates ROE -- read with gearing and interest cover.",
         "Share buybacks shrink equity and flatter ROE."],
        _calc_roe),
    "CALC-ASSET-TURNOVER": _spec(
        "Asset turnover", "Asset turnover = Revenue \u00f7 Total assets",
        ["revenue", "total_assets"], {},
        {"revenue": "currency", "total_assets": "currency"},
        "performance", "verified", [],
        ["Asset-light models show high turnover by construction.",
         "Old, fully-depreciated assets flatter the ratio."],
        _calc_asset_turnover),
    # -- breakeven / CVP ----------------------------------------------------
    "CALC-CONTRIBUTION": _spec(
        "Contribution", "Contribution = Sales \u2212 Variable costs",
        ["sales_revenue", "variable_costs"], {},
        {"sales_revenue": "currency", "variable_costs": "currency"},
        "breakeven_cvp", "verified",
        ["Costs are correctly split into fixed and variable."],
        ["The fixed/variable split is judgemental in practice.",
         "Ignores limiting factors and step-fixed costs."],
        _calc_contribution),
    "CALC-CM-RATIO": _spec(
        "Contribution margin ratio", "CM ratio = Contribution \u00f7 Sales \u00d7 100",
        ["contribution", "sales_revenue"], {},
        {"contribution": "currency", "sales_revenue": "currency"},
        "breakeven_cvp", "verified", [],
        ["Assumes constant price and variable cost per unit.",
         "A single ratio hides mix effects across products."],
        _calc_cm_ratio),
    "CALC-BREAKEVEN-UNITS": _spec(
        "Breakeven point (units)", "Breakeven units = Fixed costs \u00f7 Contribution per unit",
        ["fixed_costs", "contribution_per_unit"], {},
        {"fixed_costs": "currency", "contribution_per_unit": "currency per unit"},
        "breakeven_cvp", "verified",
        ["Constant selling price and variable cost per unit.",
         "Single product, or a constant sales mix."],
        ["Reality is rarely linear: prices, costs and mix move.",
         "Ignores the time value of money and risk."],
        _calc_breakeven_units),
    "CALC-BREAKEVEN-REV": _spec(
        "Breakeven point (revenue)", "Breakeven revenue = Fixed costs \u00f7 CM ratio",
        ["fixed_costs", "cm_ratio"], {},
        {"fixed_costs": "currency", "cm_ratio": "decimal fraction (0.40 = 40%)"},
        "breakeven_cvp", "verified",
        ["Constant CM ratio across the relevant range."],
        ["Useful for multi-product firms but still assumes a stable mix.",
         "Static: one point in time, no uncertainty."],
        _calc_breakeven_rev),
    "CALC-MARGIN-SAFETY": _spec(
        "Margin of safety", "MoS = (Actual sales \u2212 Breakeven sales) \u00f7 Actual sales \u00d7 100",
        ["actual_sales", "breakeven_sales"], {},
        {"actual_sales": "currency", "breakeven_sales": "currency"},
        "breakeven_cvp", "verified", [],
        ["Depends on the breakeven estimate being right.",
         "A percentage can hide a dangerously small absolute cushion."],
        _calc_margin_safety),
    "CALC-OP-LEVERAGE": _spec(
        "Degree of operating leverage", "DOL = Contribution \u00f7 Operating profit",
        ["contribution", "operating_profit"], {},
        {"contribution": "currency", "operating_profit": "currency"},
        "breakeven_cvp", "supplementary",
        ["Cost structure is fixed in the short run."],
        ["Supplementary: beyond core examinable scope; use for intuition on risk.",
         "Only valid for small changes around current volume."],
        _calc_op_leverage),
    # -- liquidity -----------------------------------------------------------
    "CALC-CURRENT-RATIO": _spec(
        "Current ratio", "Current ratio = Current assets \u00f7 Current liabilities",
        ["current_assets", "current_liabilities"], {},
        {"current_assets": "currency", "current_liabilities": "currency"},
        "liquidity", "verified", [],
        ["A point-in-time snapshot; window-dressing is possible.",
         "Says nothing about the quality/liquidity of the current assets."],
        _calc_current_ratio),
    "CALC-QUICK-RATIO": _spec(
        "Quick (acid-test) ratio", "Quick ratio = (Current assets \u2212 Inventory) \u00f7 Current liabilities",
        ["current_assets", "inventory", "current_liabilities"], {},
        {"current_assets": "currency", "inventory": "currency", "current_liabilities": "currency"},
        "liquidity", "verified",
        ["Inventory is the least liquid current asset and is excluded."],
        ["Still a snapshot; receivables quality matters too.",
         "Over-conservative for businesses with fast-moving inventory."],
        _calc_quick_ratio),
    # -- working capital ------------------------------------------------------
    "CALC-REC-DAYS": _spec(
        "Receivable days", "Receivable days = Receivables \u00f7 Credit sales \u00d7 365",
        ["receivables", "credit_sales"], {"days_in_year": "365"},
        {"receivables": "currency", "credit_sales": "currency", "days_in_year": "days"},
        "working_capital", "verified", [_A_365],
        ["Uses year-end receivables; an average is better if balances swing.",
         "Assumes sales are spread evenly through the year."],
        _calc_rec_days),
    "CALC-PAY-DAYS": _spec(
        "Payable days", "Payable days = Payables \u00f7 Credit purchases \u00d7 365",
        ["payables", "credit_purchases"], {"days_in_year": "365"},
        {"payables": "currency", "credit_purchases": "currency", "days_in_year": "days"},
        "working_capital", "verified", [_A_365],
        ["If credit purchases are unknown, cost of sales is a rough proxy.",
         "Year-end payables may not represent the average."],
        _calc_pay_days),
    "CALC-INV-DAYS": _spec(
        "Inventory days", "Inventory days = Inventory \u00f7 Cost of sales \u00d7 365",
        ["inventory", "cost_of_sales"], {"days_in_year": "365"},
        {"inventory": "currency", "cost_of_sales": "currency", "days_in_year": "days"},
        "working_capital", "verified", [_A_365],
        ["Averages hide slow-moving or obsolete lines -- age the stock too.",
         "Seasonal businesses need average, not year-end, inventory."],
        _calc_inv_days),
    "CALC-CCC": _spec(
        "Cash conversion cycle", "CCC = Receivable days + Inventory days \u2212 Payable days",
        ["receivable_days", "inventory_days", "payable_days"], {},
        {"receivable_days": "days", "inventory_days": "days", "payable_days": "days"},
        "working_capital", "verified", [],
        ["Inputs should be computed on a consistent basis.",
         "A negative CCC (common in retail) is not automatically good."],
        _calc_ccc),
    # -- gearing ----------------------------------------------------------------
    "CALC-GEARING": _spec(
        "Gearing", "Gearing = Debt \u00f7 (Debt + Equity) \u00d7 100",
        ["debt", "equity"], {},
        {"debt": "currency", "equity": "currency"},
        "gearing", "verified", [_A_BOOK,
         "Debt = interest-bearing debt; this build uses debt \u00f7 total capital."],
        ["Book values differ from market values.",
         "Off-balance-sheet obligations are missed."],
        _calc_gearing),
    "CALC-INT-COVER": _spec(
        "Interest cover", "Interest cover = Operating profit \u00f7 Finance cost",
        ["operating_profit", "finance_cost"], {},
        {"operating_profit": "currency", "finance_cost": "currency"},
        "gearing", "verified", [],
        ["Uses profit, not cash -- check cash interest cover too.",
         "A single good year can mask a deteriorating trend."],
        _calc_int_cover),
    # -- time value ---------------------------------------------------------------
    "CALC-PV": _spec(
        "Present value", "PV = FV \u00f7 (1 + r)^n",
        ["future_value", "discount_rate", "periods"], {},
        {"future_value": "currency", "discount_rate": "decimal fraction", "periods": "periods"},
        "time_value", "verified", [_A_FRACTION, "Single lump sum received after n periods."],
        ["The answer depends entirely on the chosen discount rate.",
         "Ignores risk beyond what the rate captures."],
        _calc_pv),
    "CALC-FV": _spec(
        "Future value", "FV = PV \u00d7 (1 + r)^n",
        ["present_value", "discount_rate", "periods"], {},
        {"present_value": "currency", "discount_rate": "decimal fraction", "periods": "periods"},
        "time_value", "verified", [_A_FRACTION, "Single lump sum invested for n periods."],
        ["Compounding at a constant rate is an idealisation.",
         "Nominal vs real rates must not be mixed."],
        _calc_fv),
    "CALC-ANNUITY-PV": _spec(
        "Annuity present value", "PV = PMT \u00d7 [1 \u2212 (1+r)^\u2212n] \u00f7 r",
        ["payment", "discount_rate", "periods"], {},
        {"payment": "currency per period", "discount_rate": "decimal fraction", "periods": "periods"},
        "time_value", "verified", [_A_FRACTION, "Ordinary annuity: payments at each period-end."],
        ["For payments at period-start (annuity due), adjust by \u00d7 (1+r).",
         "Assumes level payments and a constant rate."],
        _calc_annuity_pv),
    "CALC-ANNUITY-FV": _spec(
        "Annuity future value", "FV = PMT \u00d7 [(1+r)^n \u2212 1] \u00f7 r",
        ["payment", "discount_rate", "periods"], {},
        {"payment": "currency per period", "discount_rate": "decimal fraction", "periods": "periods"},
        "time_value", "verified", [_A_FRACTION, "Ordinary annuity: payments at each period-end."],
        ["For payments at period-start (annuity due), adjust by \u00d7 (1+r).",
         "Assumes level payments and a constant rate."],
        _calc_annuity_fv),
    # -- capital appraisal ----------------------------------------------------------
    "CALC-NPV": _spec(
        "Net present value", "NPV = \u03a3 CFt \u00f7 (1+r)^t",
        ["discount_rate", "cash_flows"], {},
        {"discount_rate": "decimal fraction", "cash_flows": "list of currency amounts (t=0 first)"},
        "capital_appraisal", "verified", [_A_FRACTION, _A_YEAR_END,
         "cash_flows[0] is the time-0 flow (usually the initial outlay, negative)."],
        ["Result is only as good as the cash-flow forecasts and the discount rate.",
         "Ignores non-financial and strategic factors; use alongside them."],
        _calc_npv, numeric_lists=("cash_flows",)),
    "CALC-IRR": _spec(
        "Internal rate of return", "IRR = r where \u03a3 CFt \u00f7 (1+r)^t = 0",
        ["cash_flows"], {},
        {"cash_flows": "list of currency amounts (t=0 first)"},
        "capital_appraisal", "verified",
        ["Bisection on Decimal: tolerance 1e-6, max 200 iterations.",
         "Unique IRR assumes conventional cash flows (one sign change).",
         "cash_flows[0] is the time-0 flow (usually negative)."],
        ["Multiple IRRs are possible with non-conventional cash flows.",
         "Where IRR and NPV conflict (scale/timing), NPV governs.",
         "Implicitly assumes reinvestment at the IRR itself."],
        _calc_irr, numeric_lists=("cash_flows",)),
    "CALC-PAYBACK": _spec(
        "Payback period", "Payback = first t where cumulative cash flow \u2265 0",
        ["cash_flows"], {},
        {"cash_flows": "list of currency amounts (t=0 first)"},
        "capital_appraisal", "verified",
        ["Cash flows occur at year-end; payback within a year is pro-rated linearly."],
        ["Ignores the time value of money.",
         "Ignores all cash flows after payback.",
         "Biased against longer-term projects."],
        _calc_payback, numeric_lists=("cash_flows",)),
    "CALC-DISCOUNTED-PAYBACK": _spec(
        "Discounted payback period", "Discounted payback = first t where cumulative discounted flow \u2265 0",
        ["discount_rate", "cash_flows"], {},
        {"discount_rate": "decimal fraction", "cash_flows": "list of currency amounts (t=0 first)"},
        "capital_appraisal", "verified", [_A_FRACTION,
         "Flows are discounted before cumulating; within-year pro-rating is linear."],
        ["Still ignores cash flows after payback.",
         "Choice of discount rate drives the answer."],
        _calc_discounted_payback, numeric_lists=("cash_flows",)),
    "CALC-SENSITIVITY": _spec(
        "Sensitivity analysis (one variable)",
        "Sensitivity = \u0394NPV \u00f7 base NPV \u00d7 100 per 1% input change; breakeven \u2248 X\u2080 \u2212 NPV\u2080 \u00f7 slope",
        ["base_npv", "npv_after_1pct_increase", "variable_current_value"], {},
        {"base_npv": "currency", "npv_after_1pct_increase": "currency",
         "variable_current_value": "currency (or units of the variable)"},
        "capital_appraisal", "verified",
        ["Linearity: NPV responds linearly near the base case.",
         "Ceteris paribus: all other variables held constant."],
        ["One variable at a time -- misses interactions between variables.",
         "Says nothing about how likely the breakeven move is."],
        _calc_sensitivity),
    "CALC-SCENARIO-NPV": _spec(
        "Scenario (probability-weighted) NPV", "Expected NPV = \u03a3 (probability \u00d7 scenario NPV)",
        ["scenario_npvs", "probabilities"], {},
        {"scenario_npvs": "list of currency amounts", "probabilities": "list of decimal fractions"},
        "capital_appraisal", "verified",
        ["Probabilities are exhaustive and sum to 1 (enforced).",
         "Scenarios are mutually exclusive and internally consistent."],
        ["Probabilities are subjective estimates.",
         "Averages hide the pain of the worst case -- check survivability."],
        _calc_scenario_npv, numeric_lists=("scenario_npvs", "probabilities")),
    # -- cost of capital ---------------------------------------------------------------
    "CALC-WACC": _spec(
        "Weighted average cost of capital", "WACC = (E/V)\u00d7Ke + (D/V)\u00d7Kd\u00d7(1\u2212T)",
        ["cost_equity", "cost_debt", "tax_rate", "market_value_equity", "market_value_debt"], {},
        {"cost_equity": "decimal fraction", "cost_debt": "decimal fraction (pre-tax)",
         "tax_rate": "decimal fraction", "market_value_equity": "currency",
         "market_value_debt": "currency"},
        "cost_of_capital", "verified", [_A_FRACTION,
         "Market-value weights; cost_debt is the pre-tax cost."],
        ["Market values move; WACC is a snapshot.",
         "Assumes the financing mix stays constant.",
         "Tax shield assumes sufficient taxable profit."],
        _calc_wacc),
    "CALC-CAPM": _spec(
        "CAPM cost of equity", "Ke = Rf + \u03b2 \u00d7 (Rm \u2212 Rf)",
        ["risk_free_rate", "beta", "market_return"], {},
        {"risk_free_rate": "decimal fraction", "beta": "decimal number",
         "market_return": "decimal fraction"},
        "cost_of_capital", "verified", [_A_FRACTION,
         "Beta measures systematic risk only; firm-specific risk is assumed diversified away."],
        ["Betas are estimated from history and are unstable.",
         "Single-factor model: misses size, value and other priced risks."],
        _calc_capm),
    "CALC-COST-DEBT": _spec(
        "Effective cost of debt (approximation)",
        "Kd \u2248 [Interest + (Redemption \u2212 Issue) \u00f7 n] \u00f7 [(Redemption + Issue) \u00f7 2], after tax \u00d7 (1\u2212T)",
        ["annual_interest", "issue_price", "redemption_price", "periods", "tax_rate"], {},
        {"annual_interest": "currency", "issue_price": "currency", "redemption_price": "currency",
         "periods": "periods", "tax_rate": "decimal fraction"},
        "cost_of_capital", "supplementary", [_A_FRACTION,
         "Straight-line amortisation of premium/discount: an approximation."],
        ["Supplementary: beyond core examinable scope.",
         "The true yield to maturity needs IRR-style iteration.",
         "Ignores issue costs and tax-timing effects."],
        _calc_cost_debt),
    # -- risk ---------------------------------------------------------------------------
    "CALC-EV": _spec(
        "Expected value", "EV = \u03a3 (probability \u00d7 outcome)",
        ["outcomes", "probabilities"], {},
        {"outcomes": "list of currency amounts", "probabilities": "list of decimal fractions"},
        "risk_analysis", "verified",
        ["Probabilities are exhaustive and sum to 1 (enforced)."],
        ["An average that may never occur -- consider the distribution.",
         "Ignores risk attitude; a risk-averse decision-maker needs more."],
        _calc_ev, numeric_lists=("outcomes", "probabilities")),
    # -- valuation --------------------------------------------------------------------------
    "CALC-GORDON": _spec(
        "Gordon growth model value", "P\u2080 = D\u2081 \u00f7 (Ke \u2212 g)",
        ["dividend_next", "cost_equity", "growth_rate"], {},
        {"dividend_next": "currency", "cost_equity": "decimal fraction",
         "growth_rate": "decimal fraction"},
        "valuation", "verified", [_A_FRACTION,
         "Constant perpetual dividend growth; requires Ke > g (enforced)."],
        ["Extremely sensitive to the growth assumption.",
         "Useless for non-dividend payers or unstable growers."],
        _calc_gordon),
    "CALC-PE-VAL": _spec(
        "P/E-based valuation", "Value per share = EPS \u00d7 P/E ratio",
        ["earnings_per_share", "pe_ratio"], {},
        {"earnings_per_share": "currency", "pe_ratio": "multiple"},
        "valuation", "verified", [],
        ["The answer is only as good as the chosen P/E multiple.",
         "Needs genuinely comparable companies; earnings must be maintainable."],
        _calc_pe_val),
    "CALC-ASSET-VAL": _spec(
        "Asset-basis valuation", "Value/share = (Total assets \u2212 Total liabilities) \u00f7 Shares",
        ["total_assets", "total_liabilities", "shares_outstanding"], {},
        {"total_assets": "currency", "total_liabilities": "currency",
         "shares_outstanding": "shares"},
        "valuation", "verified", [_A_BOOK],
        ["Ignores future earnings power and intangibles.",
         "A floor value, not a going-concern value."],
        _calc_asset_val),
    # -- relevant costing -----------------------------------------------------------------------
    "CALC-RELEVANT-COST": _spec(
        "Relevant cost comparison", "Choose the option with the lower total relevant cost",
        ["costs_a", "costs_b"], {},
        {"costs_a": "list of currency amounts (option A)",
         "costs_b": "list of currency amounts (option B)"},
        "relevant_costing", "verified",
        ["Only future incremental cash costs are included.",
         "Sunk costs and unavoidable allocated overhead are excluded."],
        ["Non-financial factors (quality, risk, strategy) are outside this calc.",
         "Misclassifying avoidable vs unavoidable costs flips the answer."],
        _calc_relevant_cost, numeric_lists=("costs_a", "costs_b")),
    "CALC-MAKEBUY": _spec(
        "Make-or-buy comparison",
        "Make cost = units\u00d7variable + specific fixed + opportunity; Buy cost = units\u00d7price",
        ["units", "buy_price", "variable_cost_make"],
        {"specific_fixed_cost_make": "0", "opportunity_cost": "0"},
        {"units": "units", "buy_price": "currency per unit",
         "variable_cost_make": "currency per unit",
         "specific_fixed_cost_make": "currency", "opportunity_cost": "currency"},
        "relevant_costing", "verified",
        ["General fixed overhead is unavoidable and excluded.",
         "Opportunity cost captures the best alternative use of released capacity."],
        ["Supplier reliability and quality are outside this calc.",
         "Assumes the supplier price holds for the whole volume."],
        _calc_makebuy),
    "CALC-SPECIAL-ORDER": _spec(
        "Special order incremental profit",
        "Incremental profit = units\u00d7(price \u2212 VC) \u2212 incremental fixed \u2212 lost contribution",
        ["units", "special_price", "variable_cost_per_unit"],
        {"incremental_fixed_cost": "0", "lost_contribution": "0"},
        {"units": "units", "special_price": "currency per unit",
         "variable_cost_per_unit": "currency per unit",
         "incremental_fixed_cost": "currency", "lost_contribution": "currency"},
        "relevant_costing", "verified",
        ["Spare capacity exists, or displaced sales are captured in lost_contribution.",
         "The special price does not leak to existing customers."],
        ["Accepting may set a precedent on pricing.",
         "Strategic/customer-relationship effects are outside this calc."],
        _calc_special_order),
    "CALC-LIMITING-FACTOR": _spec(
        "Limiting-factor ranking", "Rank by contribution \u00f7 limiting factor per unit (highest first)",
        ["product_names", "contribution_per_unit", "limiting_factor_per_unit"], {},
        {"product_names": "list of names",
         "contribution_per_unit": "list of currency amounts",
         "limiting_factor_per_unit": "list of factor units"},
        "relevant_costing", "verified",
        ["One binding constraint; demand limits still apply per product."],
        ["With several simultaneous constraints, linear programming is needed.",
         "Ranking ignores demand interdependencies."],
        _calc_limiting_factor,
        numeric_lists=("contribution_per_unit", "limiting_factor_per_unit"),
        text_lists=("product_names",)),
    # -- variances -------------------------------------------------------------------------------
    "CALC-MATERIAL-VAR": _spec(
        "Material variances",
        "Price var = (SP\u2212AP)\u00d7AQ; Usage var = (SQ\u2212AQ)\u00d7SP",
        ["standard_price", "actual_price", "actual_quantity", "standard_quantity"], {},
        {"standard_price": "currency", "actual_price": "currency",
         "actual_quantity": "quantity", "standard_quantity": "quantity"},
        "variances", "verified", [_A_POS_FAV,
         "SP/AP per unit of material; AQ/SQ in the same quantity units."],
        ["Standards may be outdated or badly set.",
         "Price and usage variances interact (cheap material, more waste).",
         "Investigate controllability before blaming a manager."],
        _calc_material_var),
    "CALC-LABOUR-VAR": _spec(
        "Labour variances",
        "Rate var = (SR\u2212AR)\u00d7AH; Efficiency var = (SH\u2212AH)\u00d7SR",
        ["standard_rate", "actual_rate", "actual_hours", "standard_hours"], {},
        {"standard_rate": "currency", "actual_rate": "currency",
         "actual_hours": "hours", "standard_hours": "hours"},
        "variances", "verified", [_A_POS_FAV,
         "SR/AR per hour; AH/SH in hours for the actual output."],
        ["Standards may be outdated or badly set.",
         "Rate/efficiency trade off (cheaper labour, slower work).",
         "Investigate controllability before blaming a manager."],
        _calc_labour_var),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_calculation(calc_id: str, **inputs: Any) -> CalcResult:
    """Run a calculation by id.

    Validates that all required inputs are present (raising
    MissingInputError listing them -- defaults are NEVER invented for
    required inputs), converts inputs via Decimal(str(v)), computes, and
    returns a CalcResult with workings, interpretation and limitations.
    """
    try:
        spec = REGISTRY[calc_id]
    except KeyError:
        raise KeyError(f"Unknown calculation id: {calc_id!r}") from None

    missing = [r for r in spec["required"] if _is_missing(inputs.get(r))]
    if missing:
        raise MissingInputError(missing)

    converted: dict[str, Any] = {}
    for name in spec["required"]:
        converted[name] = _convert(name, inputs[name], spec)
    for name, default in spec["optional"].items():
        converted[name] = _convert(name, inputs.get(name, default), spec)

    out = spec["func"](**converted)
    assumptions = list(spec["assumptions"]) + list(out.get("assumptions", []))
    limitations = list(spec["limitations"]) + list(out.get("limitations", []))
    return CalcResult(
        calc_id=calc_id,
        name=spec["name"],
        formula=spec["formula"],
        inputs=converted,
        input_units=dict(spec["units"]),
        assumptions=assumptions,
        steps=list(out["steps"]),
        result=out["result"],
        result_unit=out["result_unit"],
        interpretation=out["interpretation"],
        limitations=limitations,
        validation_status="validated",
    )


def missing_inputs(calc_id: str, provided: dict) -> list[str]:
    """List the required input names absent from ``provided``."""
    try:
        spec = REGISTRY[calc_id]
    except KeyError:
        raise KeyError(f"Unknown calculation id: {calc_id!r}") from None
    provided = provided or {}
    return [r for r in spec["required"] if _is_missing(provided.get(r))]


def list_calculations() -> list[dict]:
    """Catalogue of calculations: calc_id, name, category, syllabus_tag."""
    return [
        {
            "calc_id": cid,
            "name": spec["name"],
            "category": spec["category"],
            "syllabus_tag": spec["syllabus_tag"],
        }
        for cid, spec in REGISTRY.items()
    ]
