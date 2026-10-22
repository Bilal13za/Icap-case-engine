# Build Notes — ICAP Business Case Analysis and Decision Engine

Conventions from previous builds for this user (MUST follow):

## Stack
- Python 3.11+, Streamlit (local interface), SQLite (with FTS5 for search), openpyxl (Excel), pytest.
- **No PyYAML** — a previous Windows build failed on the C-extension install; use stdlib `json` for
  all settings/config/rule files.
- **No AI/LLM/cloud/paid APIs anywhere in the app.** Deterministic rules, decision tables,
  formulas, templates only. Never claim NLP understanding of free text.
- Decimal-safe arithmetic: use `decimal.Decimal` for money/rate calculations; define rounding
  rules explicitly (ROUND_HALF_UP, 2dp for currency, 4dp for rates/percentages unless stated).
- 8 GB RAM target: keep memory footprint small, no heavy dependencies.

## Windows packaging (follow ~/workspace/audit-risk-library/run_windows.bat pattern)
- `run_windows.bat`: winget-installs Python if missing, creates venv, pip installs from
  requirements.txt, waits for the Streamlit server, then opens the browser automatically.
- Ship as a ZIP with the app folder + launcher + README. First launch = extract + double-click.
- Data dir: `%LOCALAPPDATA%\<AppName>` for the SQLite DB and student work (keeps it out of the
  read-only program folder; enables backup/restore).

## Layout
- `app/` — Streamlit app (single app with sidebar navigation or multipage; keep simple).
- `engine/` — rule engine, framework selection, recommendation templates (pure Python, no Streamlit imports); `studyaids.py` holds formula sheet groups, checklist item lists, and the offline mind-map HTML renderer.
- `tools/gen_study_aids.py` — deterministic generator for `data/flashcards.json` + `data/mindmaps.json` from existing seed JSON; re-running reproduces outputs byte-for-byte. New seed files must be added to `seed.py` `_FILES`/`_TABLE_ORDER`; new student tables to `_PROTECTED_TABLES`.
- Schema migrations: `dbcore.init_db()` re-applies the (fully idempotent) schema on every start and re-seeds when the study-aids tables are missing/empty — bump `SCHEMA_VERSION` when the schema changes.
- `calcs/` — calculation library (pure Python, Decimal-based).
- `data/` — versioned seed content as JSON (editable without code changes): syllabus, frameworks,
  rules, cases, questions. A `seed.py` loads JSON into SQLite.
- `db/` — schema.sql; the app creates/extends the DB on first run (migrations, not wipe).
- `tests/` — pytest, incl. end-to-end tests.
- `docs/` — this file, SYLLABUS_VERIFICATION.md, VERIFICATION.md (content verification report),
  ROADMAP.md, README.md (install + offline instructions).
- `sample_workpapers/` or `samples/` — 3 worked end-to-end sample analyses + exported CSV/Excel.

## Data rules
- Seed content carries `verification_status`, `official_source`, `effective_date`, `review_status`
  on every row (per SYLLABUS_VERIFICATION.md §5). UI must surface these labels.
- Student work (attempts, mistake log, tags) lives in separate tables from seed content; seeding
  must never wipe student tables. Backup/restore = copy the SQLite file (+ export JSON).
- Exports: CSV + formatted Excel (openpyxl) of case analyses and calculation workings.

## Testing bar
- pytest suite covering the brief's 14 areas + 3 end-to-end tests (working capital, make-or-buy,
  capital investment). All green before packaging.

## UI screens (per brief §16)
Case Explorer · Scenario Analyzer · Framework Finder · Calculation Workbench ·
Decision Comparator · Recommendation Builder · Exam Practice · Revision Dashboard · Export.
Keep the interface clean and simple; Streamlit-native widgets are fine.
