# Content Verification Report — ICAP Business Case Analysis and Decision Engine

Report date: 2026-10-21
Scope: everything this application teaches or asserts about the ICAP syllabus, papers,
standards, and practice material. Full source detail lives in
`SYLLABUS_VERIFICATION.md` (project root); this file summarises what was verified,
how the labelling was applied, and what remains unverified.

## 1. What was verified against official ICAP sources

| # | Claim in the app | Verification | Source |
|---|---|---|---|
| 1 | ICAP Education and Training Scheme 2025 is the current scheme | **Verified official** | https://icap.org.pk/learn-about-ca/entry-routes/full-time-scheme/ and https://icap.org.pk/students/study-resources/ (2025 scheme listed first; 2021 kept as prior scheme) |
| 2 | CAF-7 is "Business Insights and Analysis" under Scheme 2025 | **Verified official** | Official ICAP FAQ PDF "FAQs on education scheme", mapping table 2025 → 2021: CAF-7 Business Insights and Analysis ← CAF-6 Managerial and Financial Analysis |
| 3 | CFAP-4 under Scheme 2025 is "Strategic Business Finance" (renamed from "Business Finance Decisions") | **Verified official** | Same official ICAP FAQ mapping table: CFAP 4 Strategic Business Finance ← CFAP-4 Business Finance Decisions |
| 4 | CAF-6 Managerial and Financial Analysis (2021): competency, grid A/B/C, weightage bands, teaching hours 110–130, technical competencies with proficiency/testing levels, Specific Examinable Knowledge Reference (SWOT, Porter's Five Forces, PLC, BCG, Tucker's 5-question model, AAA 7-step model, ISO 31000, CAPM, hedging instruments) | **Verified official** | ICAP Directive 1.01 (Revised 2024), official PDF (90 pages, downloaded from icap.org.pk 2026-10-21); extracts stored in `syllabus/2021-caf6-mfa-directive1.01-rev2024.txt` |
| 5 | CFAP-4 Business Finance Decisions (2021): competency, grid 1/2/3, weightage bands, teaching hours 110–130, learning outcomes A-1…C-2 with proficiency/testing levels, Specific Examinable Knowledge Reference (NPV, APV, IRR, MIRR, EIRR, payback, capital rationing, PI, valuation methods, APT, WACC/DDM/CAPM/FCF, debt valuation, dividend theories, capital structure theories, portfolio selection, hedging instruments, liquidity/credit risk) | **Verified official** | ICAP Directive 1.01 (Revised 2024), official PDF; extracts stored in `syllabus/2021-cfap4-bfd-directive1.01-rev2024.txt` |

Learning outcomes, topics, and concepts transcribed from the Directive extracts carry
`verification_status = verified_official`,
`official_source = "ICAP Directive 1.01 (Revised 2024), Education and Training Scheme 2021"`,
and `effective_date = "2024-11-07"` (directive creation date).

## 2. Labelling applied to non-official content

- **2025 papers (CAF-7 BIA, CFAP-4 Strategic Business Finance)** — topic mappings carried
  forward from the verified 2021 predecessors are labelled `provisional_predecessor`, with the
  UI note: "Detailed 2025 syllabus pending official publication; mapped from verified 2021
  predecessor." No 2025 learning outcome, weightage, or syllabus reference was invented.
- **"CAPM and Budgeting removed from CAF-7"** — a third-party blog summary of the proposed
  scheme claims this; it is **secondary and unverified**. The content is kept but labelled
  `unverified`, and the UI must not present the removal as fact.
- **Frameworks not named in the Directive knowledge references** (e.g. value chain, Ansoff
  matrix) — labelled `supplementary`, with the note "supplementary business framework —
  examinability not verified".
- **Practice questions** — all 24 are original practice questions: `source_verified = 0`,
  `verification_status = supplementary` (original teaching material, not official),
  with source notes stating they are not ICAP past papers.
  Model answers are "answer outlines"; rubrics are "practice rubrics — not official ICAP
  marking schemes".

## 3. What was NOT verified (explicit)

1. **The detailed Scheme 2025 syllabus** (grid + learning-outcome level for CAF-7 BIA and
   CFAP-4 Strategic Business Finance). ICAP publishes it behind the student login; it was not
   publicly fetchable as of 2026-10-21. All 2025 rows are therefore provisional mappings.
2. **The claim that CAPM and Budgeting were removed from CAF-7** (third-party blog only).
3. **All practice questions** — original by design; none are past papers and none claim to be.
4. **Case studies** — fictionalised teaching cases; company names and numbers are illustrative.
5. **Supplementary frameworks** — standard business-school frameworks included for
   completeness; their examinability under ICAP papers is not verified.

## 4. Spot-check method

Automated (pytest suite, `tests/`), run against the seeded database:

- Every row in every seed table carries a `verification_status` in the allowed set
  `{verified_official, provisional_predecessor, supplementary, unverified}`.
- Every `verified_official` row has a non-empty `official_source`.
- Every 2021-scheme syllabus row is `verified_official`; every 2025-scheme syllabus row is
  `provisional_predecessor` (seed re-runs preserve these labels — tested).
- Every practice question has `source_verified = 0`; question text, source notes, and answer
  outlines are scanned for past-paper claims ("past paper", "ICAP past", "attempt 20xx" as a
  source claim) and the scan must find none.
- Formula worked examples are hand-verified in tests against independent recomputation
  (NPV, IRR, WACC, CAPM, breakeven, receivables days, labour variance).

Manual spot checks performed 2026-10-21: the Directive extracts in `syllabus/` were compared
line-by-line against the official PDF sections for CAF-6 and CFAP-4 (competency statements,
grid weightages, and the Specific Examinable Knowledge Reference lists match); the FAQ rename
mapping was read directly from the official PDF.

## 5. Maintenance

Re-run this verification when ICAP publishes the detailed Scheme 2025 syllabus: flip
`provisional_predecessor` rows to `verified_official` (or correct them), and update
`docs/ROADMAP.md` accordingly.

## 6. Study Aids (added 2026-10-21)

Flashcards (210), mind maps (27), formula quick-sheets (9 sheets / 44 formulas),
and checklists are generated **deterministically** from existing seed content —
`tools/gen_study_aids.py` reads `data/frameworks.json`, `data/formulas.json`,
`data/rules.json`, and `data/calculation_examples.json` and writes
`data/flashcards.json` / `data/mindmaps.json` byte-for-byte reproducibly.
No card or map text is hand-invented.

Labelling rules applied:

| # | Rule |
|---|---|
| 1 | Every flashcard inherits the `verification_status` of its source row (framework, formula, or trigger rule); every mind map inherits its framework's status. Statuses shown on badges: 93 cards + 22 maps `verified_official`, 117 cards + 5 maps `supplementary`. |
| 2 | Framework cards are built only from fields the source row actually has (e.g. FW-IRR has no `required_inputs`; its application card covers "when to use" only rather than inventing inputs). |
| 3 | Formula quick-sheet groupings (e.g. "Investment appraisal" → CFAP-4) are an **editorial navigation aid**, not an ICAP examinability claim; many formulas apply to both papers. The same applies to the paper decks that trigger-rule cards are filed under (`tools/gen_study_aids.py::PATTERN_PAPER`, documented in code). |
| 4 | Rule cards always carry the "indicator, not proven cause" caution with the rule's own alternative explanations and confirmation checklist. |
| 5 | The recommendation checklist surfaces the app's own template sections (`engine/recommendations.py`); the answer-quality checklist is the canonical 9-item list shared with Exam Practice (`engine/studyaids.py::ANSWER_QUALITY_ITEMS`; `app.py` keeps a byte-identical fallback — asserted by test). |
| 6 | `FlashcardProgress` is a student table: `seed.py` refuses to write to it (in `_PROTECTED_TABLES`, tested), re-seeding preserves progress (tested), and it is included in the SQLite-file backup like attempts and the mistake log. |
| 7 | Mind-map HTML is pure `<details>`/`<summary>` with inline CSS — no JavaScript, no CDN, no external URLs (asserted by test for every map). |

Automated checks (`tests/test_study_aids.py`): card count 180–240, no empty
fronts/backs, every card FK resolves to a real framework/formula/rule,
`verified_official` cards have a non-empty `official_source`, mind-map HTML
renders for all 27 maps, formula sheet groups partition all 44 formulas
exactly once, and a v1 database (pre-study-aids schema) is migrated by
`dbcore.init_db()` without losing seed content.
