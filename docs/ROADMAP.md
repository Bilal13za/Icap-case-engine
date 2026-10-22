# Roadmap — ICAP Business Case Analysis and Decision Engine

## Near term (content verification)

1. **2025 detailed syllabus update path.** When ICAP publishes the detailed (grid +
   learning-outcome level) syllabus for Scheme 2025 behind the student login:
   - transcribe CAF-7 BIA and CFAP-4 Strategic Business Finance grids into
     `data/syllabus.json` as new `SyllabusVersions` rows,
   - re-map or correct every `provisional_predecessor` LearningOutcome/Topic row, flipping
     verified rows to `verified_official` with the new `official_source` and `effective_date`,
   - resolve the open CAPM/budgeting question for CAF-7 (currently `unverified`) and either
     verify or drop the removal claim,
   - re-run the pytest suite (the syllabus-versioning tests enforce the labelling rules) and
     update `docs/VERIFICATION.md`.
2. **Rule review workflow.** `TriggerRules.review_status` currently ships as `draft` for new
   rules. Add an in-app (or scripted) review pass: a reviewer marks rules
   `reviewed`, records the reviewer/date in `ReviewRecords`, and the UI surfaces the status.
   Draft rules should be visually distinguished until reviewed.
3. **Teacher-feedback capture.** The schema has `ReviewRecords` (entity_type/entity_id) —
   wire it to a simple "flag this content" action in the app so Bilal (or a teacher) can log
   corrections against specific rules, frameworks, questions, or LOs, and track resolution.

## Content expansion

4. **More cases and rules.** Grow `data/cases.json` beyond the initial 16 toward 30+,
   prioritising: group/cash-flow statements analysis, Islamic finance structures, dividend
   policy cases, M&A valuation cases, and risk-management scenarios — all mapped to the
   verified 2021 grids.
5. **More practice questions.** Add questions per topic with the same labelling discipline
   (`source_verified = 0`, "not a past paper" notes); keep answer outlines and practice rubrics
   clearly unofficial.
6. **Additional frameworks.** Candidates: McKinsey 7S, PESTLE (as distinct from PEST),
   balanced scorecard, Kraljic matrix for procurement cases — all as `supplementary` until
   examinability is verified.
7. **Calculation library growth.** MIRR, EIRR, APV, profitability index, economic order
   quantity, learning-curve labour cost, and money-market hedge workings — each with
   hand-verified worked examples in `CalculationExamples`.

## App and engineering

8. **Export history.** Keep a log of exported workings (CSV/Excel) per case attempt so
   Bilal can revisit earlier analyses.
9. **Revision scheduler.** The Revision Dashboard currently reads the MistakeLog; add
   spaced-repetition scheduling over weak topics.
10. **Backup/restore in-app.** One-click DB backup to a chosen folder (today: manual copy of
    `%LOCALAPPDATA%\ICAP Case Engine\case_engine.db` — see README).
11. **Performance budget.** Keep the app within the 8 GB RAM target: no new heavy
    dependencies; keep the engine/calcs/dbcore layers free of Streamlit and network imports
    (enforced by the offline-operation test).

## Non-goals

- No AI/LLM/cloud features — the app stays deterministic and offline by design.
- No past-paper reproduction — practice questions remain original.
