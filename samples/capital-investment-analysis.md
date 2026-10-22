# Sample 3 — Capital investment appraisal (Indus Foods expansion, fictional)

## Facts
- Two mutually exclusive expansion options; Project X: outlay Rs 10,000,000,
  inflows Rs 3.0m / 4.0m / 5.0m over years 1–3.
- The IRR ranking and the NPV ranking of the options **disagree**
  (appraisal conflict: scale/timing differences).
- Cost of capital: 12%.

## Issues recognised
**RULE-008 — IRR vs NPV conflict on mutually exclusive projects**
- The two methods disagree, usually because of differences in project scale or cash-flow timing, or the reinvestment assumption buried in IRR. NPV at the cost of capital is the theoretically superior rule.
- *Alternative explanations considered:* Projects differ greatly in scale (IRR is a percentage, NPV is absolute).; Cash-flow timing differences favour the earlier-returning project under IRR.; The IRR reinvestment assumption is unrealistic for this business.; One project's cash flows are less certain than the other's.
- *Caution:* Indicator only — not a proven cause. Rule out alternative explanations before concluding.

## Frameworks
- **FW-CAPAPP** (Capital appraisal) — General investment-appraisal discipline: identify relevant cash flows, choose a discount rate, apply decision rules.
  - *Not suitable when:* Cash flows cannot be estimated even approximately.
  - *Why it fits this rule:* General appraisal discipline for the comparison.
- **FW-NPV** (NPV appraisal) — Discounts all relevant cash flows at the cost of capital; accept if NPV > 0. Theoretically the strongest decision rule.
  - *Not suitable when:* The discount rate cannot be estimated.
  - *Why it fits this rule:* NPV at the cost of capital is the governing rule.
- **FW-SENS** (Sensitivity analysis) — Tests how far key variables can move before the decision changes, exposing the riskiest assumptions.
  - *Not suitable when:* The base-case model itself is not built yet.
- **FW-SCENARIO** (Scenario analysis) — Values the project under coherent best/base/worst cases with probabilities for an expected NPV.
  - *Not suitable when:* Scenarios cannot be defined or weighted.

## Calculations (full workings in the CSV/Excel files)
### Net present value
- NPV = Σ CFt ÷ (1 + 0.1200)^t, t = 0..3
- t=0: -10,000,000.00 ÷ (1 + 0.1200)^0 = -10,000,000.00
- t=1: 3,000,000.00 ÷ (1 + 0.1200)^1 = 2,678,571.43
- t=2: 4,000,000.00 ÷ (1 + 0.1200)^2 = 3,188,775.51
- t=3: 5,000,000.00 ÷ (1 + 0.1200)^3 = 3,558,901.24
- NPV = -573,751.82
- **Result: -573751.82 currency**

### Internal rate of return
- Sign-change bracket found: r in [5.0000%, 10.0000%]
- Bisection converged in 17 iteration(s) (tolerance 1e-6, max 200)
- IRR = 8.8964%
- **Result: 8.8964 %**

### Payback period
- Payback = first t where cumulative cash flow ≥ 0
- Cumulative flow turns positive between t=2 (-3,000,000.00) and t=3 (2,000,000.00)
- Payback = 2 + 3,000,000.00 ÷ 5,000,000.00 = 2.60 years
- **Result: 2.60 years**

## Alternatives considered
Option ACCEPT: Accept the expansion project -- financial impact: Captures strategic market share; key risk: Negative NPV of Rs 573,751.82 at 12%.

## Recommendation
# Recommendation: Option REJECT -- Reject the expansion project

## Executive summary
Option REJECT is preferable because Case facts and calculations below. The financial analysis indicates NPV is Rs -573,751.82 at the 12% discount rate. However, the decision depends on The 12% cost of capital reflects project risk. Management should Communicate the decision with the financial analysis and monitor Actual vs forecast cash flows of alternative projects.

## Supporting facts
- Initial outlay Rs 10,000,000; inflows Rs 3.0m / 4.0m / 5.0m
- NPV at 12% is Rs -573,751.82
- IRR is 8.8964% — below the 12% cost of capital

## Financial analysis
- NPV is Rs -573,751.82 at the 12% discount rate
- Payback is 2.60 years

## Key assumption
The 12% cost of capital reflects project risk

## Risks of the recommended option
- Foregone strategic positioning

## Alternatives considered
- Option ACCEPT: Accept the expansion project -- financial impact: Captures strategic market share; key risk: Negative NPV of Rs 573,751.82 at 12%.

## Conditions that would change this recommendation
- Discount rate falling below the IRR
- Cash inflows revised upwards by >10%

## Implementation steps
1. Communicate the decision with the financial analysis
2. Revisit if strategic assumptions change

## KPIs to monitor
- Actual vs forecast cash flows of alternative projects

## Review timing
At the next capital-budgeting round

---
*Content labels: rule and case content is supplementary teaching material;
syllabus references are verified_official (2021) / provisional_predecessor (2025).*
