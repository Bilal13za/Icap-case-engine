"""Spec §18.4 (formula accuracy vs hand-computed values), §18.5 (missing inputs),
§18.6 (unit/sign handling), §18.7 (sensitivity).

Note on units: rate inputs are decimal fractions (0.10 = 10%) and percentage
RESULTS are percent numbers (9.4400 = 9.44%) — see calcs/calculations.py.
"""

from decimal import Decimal

import pytest

from .conftest import calc_ids, calc_input_names, find_calc, run_calc
from calcs.calculations import MissingInputError


# ------------------------------------------------------------- catalogue
def test_core_calculations_present():
    ids = calc_ids()
    for cid in ["CALC-NPV", "CALC-IRR", "CALC-WACC", "CALC-CAPM",
                "CALC-BREAKEVEN-UNITS", "CALC-REC-DAYS", "CALC-LABOUR-VAR",
                "CALC-PAYBACK", "CALC-SENSITIVITY"]:
        assert cid in ids, f"{cid} missing from calculation catalogue"


def test_missing_inputs_lists_required_names():
    assert calc_input_names("CALC-NPV") == ["discount_rate", "cash_flows"]


def test_missing_input_error_lists_missing():
    """§18.5: MissingInputError names every missing input; nothing is invented."""
    with pytest.raises(MissingInputError) as excinfo:
        run_calc("CALC-NPV")
    assert excinfo.value.missing == ["discount_rate", "cash_flows"]
    with pytest.raises(MissingInputError) as excinfo:
        run_calc("CALC-NPV", discount_rate=Decimal("0.10"))
    assert excinfo.value.missing == ["cash_flows"]


def test_results_are_decimal():
    """Build notes require Decimal arithmetic for money/rate calculations."""
    res = run_calc("CALC-NPV", discount_rate=Decimal("0.10"),
                   cash_flows=[-1000, 300, 400, 500])
    assert isinstance(res.result, Decimal)
    assert res.validation_status == "validated"
    assert res.steps, "no workings steps returned"
    assert res.interpretation.strip()


# ------------------------------------------------------------- §18.4 accuracy
def test_npv_accuracy():
    # hand-computed per-term (module quantizes each discounted flow to 2dp):
    # -1000.00 + 272.73 + 330.58 + 375.66 = -21.03
    res = run_calc("CALC-NPV", discount_rate=Decimal("0.10"),
                   cash_flows=[-1000, 300, 400, 500])
    assert res.result == Decimal("-21.03"), f"NPV {res.result} != -21.03"
    assert res.result_unit == "currency"


def test_irr_accuracy():
    # -1000 + 400 x annuity(3y, r) = 0 -> r ~= 9.70% (percent number)
    res = run_calc("CALC-IRR", cash_flows=[-1000, 400, 400, 400])
    assert Decimal("9") < res.result < Decimal("10.5"), f"IRR {res.result} off"
    # verify by plugging back: NPV at the computed IRR must be ~0
    npv = run_calc("CALC-NPV", discount_rate=res.result / 100,
                   cash_flows=[-1000, 400, 400, 400])
    assert abs(npv.result) < Decimal("0.05"), f"NPV at IRR = {npv.result}, want ~0"


def test_wacc_accuracy():
    # 0.6 x 0.12 + 0.4 x 0.06 x (1 - 0.30) = 0.0888 -> 8.8800%
    res = run_calc("CALC-WACC", cost_equity=Decimal("0.12"), cost_debt=Decimal("0.06"),
                   tax_rate=Decimal("0.30"), market_value_equity=600,
                   market_value_debt=400)
    assert res.result == Decimal("8.88"), f"WACC {res.result} != 8.88"
    assert res.result_unit == "%"


def test_capm_accuracy():
    # 0.05 + 1.2 x (0.11 - 0.05) = 0.122 -> 12.2000%
    res = run_calc("CALC-CAPM", risk_free_rate=Decimal("0.05"), beta=Decimal("1.2"),
                   market_return=Decimal("0.11"))
    assert res.result == Decimal("12.2"), f"CAPM {res.result} != 12.2"


def test_breakeven_accuracy():
    # 50,000 / (25 - 15) = 5,000 units
    res = run_calc("CALC-BREAKEVEN-UNITS", fixed_costs=50000, contribution_per_unit=10)
    assert res.result == Decimal("5000"), f"breakeven {res.result} != 5000"
    assert res.result_unit == "units"


def test_receivables_days_accuracy():
    # 120,000 / 1,460,000 x 365 = 30 days
    res = run_calc("CALC-REC-DAYS", receivables=120000, credit_sales=1460000)
    assert res.result == Decimal("30"), f"receivable days {res.result} != 30"
    assert res.result_unit == "days"


def test_labour_variance_accuracy():
    # std 100h @ 50 vs actual 110h @ 52:
    # rate var = (50-52) x 110 = -220; efficiency var = (100-110) x 50 = -500
    res = run_calc("CALC-LABOUR-VAR", standard_rate=50, actual_rate=52,
                   actual_hours=110, standard_hours=100)
    assert res.result["rate_variance"] == Decimal("-220")
    assert res.result["efficiency_variance"] == Decimal("-500")
    assert res.result["total_variance"] == Decimal("-720")


def test_payback_accuracy():
    # cumulative: -700, -300, +200 -> 2 + 300/500 = 2.6 years
    res = run_calc("CALC-PAYBACK", cash_flows=[-1000, 300, 400, 500])
    assert res.result == Decimal("2.60"), f"payback {res.result} != 2.60"


# ------------------------------------------------------------- §18.6 units/signs
def test_negative_cashflows_accepted():
    """Negative cashflows are legitimate and must not be rejected."""
    res = run_calc("CALC-NPV", discount_rate=Decimal("0.10"),
                   cash_flows=[-500, -200, -100])
    assert res.result < 0


def test_rate_convention_documented_explicitly():
    """Rate inputs that are decimal fractions document the convention explicitly
    (spec §18.6: unit handling must be explicit, never silently ambiguous)."""
    from calcs.calculations import REGISTRY

    # inputs that are fractional rates (0.10 = 10%), not currency-per-unit rates
    FRACTIONAL_RATES = {
        "discount_rate", "growth_rate", "tax_rate", "cost_equity", "cost_debt",
        "risk_free_rate", "market_return",
    }
    checked = 0
    for cid, spec in REGISTRY.items():
        for inp in spec["required"]:
            if inp in FRACTIONAL_RATES:
                checked += 1
                unit = spec["units"].get(inp, "")
                assert "decimal" in unit.lower(), (
                    f"{cid}.{inp}: unit {unit!r} does not state decimal fraction"
                )
    assert checked > 0
    # also visible on the public result object
    res = run_calc("CALC-NPV", discount_rate=Decimal("0.10"),
                   cash_flows=[-1000, 300, 400, 500])
    assert "decimal" in res.input_units["discount_rate"].lower()


def test_percent_style_rate_not_silently_normalised():
    """A rate entered as 10 (percent-style) is interpreted literally per the
    documented decimal convention — never silently re-read as 10%."""
    good = run_calc("CALC-NPV", discount_rate=Decimal("0.10"),
                    cash_flows=[-1000, 300, 400, 500])
    literal = run_calc("CALC-NPV", discount_rate=Decimal("10"),
                       cash_flows=[-1000, 300, 400, 500])
    assert abs(literal.result - good.result) > Decimal("1"), (
        "percent-style rate was silently normalised to a plausible value"
    )


# ------------------------------------------------------------- §18.7 sensitivity
def test_sensitivity_calculation():
    # base NPV 1000; +1% in the variable moves NPV to 950
    # sensitivity = -50/1000 x 100 = -5% per 1%; breakeven at 60,000
    res = run_calc("CALC-SENSITIVITY", base_npv=1000,
                   npv_after_1pct_increase=950, variable_current_value=50000)
    assert res.result["sensitivity_pct"] == Decimal("-5")
    assert res.result["breakeven_value"] == Decimal("60000")
    assert res.steps, "no sensitivity workings returned"


def test_sensitivity_responds_to_inputs():
    low = run_calc("CALC-SENSITIVITY", base_npv=1000,
                   npv_after_1pct_increase=950, variable_current_value=50000)
    high = run_calc("CALC-SENSITIVITY", base_npv=1000,
                    npv_after_1pct_increase=900, variable_current_value=50000)
    assert low.result["sensitivity_pct"] != high.result["sensitivity_pct"]
    assert high.result["sensitivity_pct"] == Decimal("-10")
