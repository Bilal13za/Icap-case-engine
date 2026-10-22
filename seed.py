#!/usr/bin/env python3
"""Seed the ICAP Case Engine database from data/*.json.

Idempotent: every seed table is upserted with INSERT OR REPLACE keyed on its
primary key, so running this script twice neither duplicates nor wipes content.
The student tables (StudentAttempts, MistakeLog, FlashcardProgress) are NEVER
written to here.

Usage:
    python seed.py [db_path]

If db_path is omitted, the app data directory is used
(%LOCALAPPDATA%\\ICAP Case Engine on Windows, ~/.icap-case-engine elsewhere).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DATA_DIR = _HERE / "data"

# JSON top-level key -> database table, in dependency (FK) order.
_TABLE_ORDER: list[tuple[str, str]] = [
    ("sources", "Sources"),
    ("papers", "Papers"),
    ("syllabus_versions", "SyllabusVersions"),
    ("topics", "Topics"),
    ("learning_outcomes", "LearningOutcomes"),
    ("concepts", "Concepts"),
    ("frameworks", "Frameworks"),
    ("framework_steps", "FrameworkSteps"),
    ("case_patterns", "CasePatterns"),
    ("case_facts", "CaseFacts"),
    ("problem_patterns", "ProblemPatterns"),
    ("trigger_rules", "TriggerRules"),
    ("rule_framework_mappings", "RuleFrameworkMappings"),
    ("formulas", "Formulas"),
    ("calculation_examples", "CalculationExamples"),
    ("decision_options", "DecisionOptions"),
    ("evaluation_criteria", "EvaluationCriteria"),
    ("practice_questions", "PracticeQuestions"),
    ("answer_outlines", "AnswerOutlines"),
    ("marking_rubrics", "MarkingRubrics"),
    ("review_records", "ReviewRecords"),
    ("flashcards", "Flashcards"),
    ("mindmaps", "MindMaps"),
]

# JSON file -> the top-level keys it provides.
_FILES = [
    "syllabus.json",
    "frameworks.json",
    "concepts.json",
    "cases.json",
    "rules.json",
    "questions.json",
    "rule_frameworks.json",
    "formulas.json",
    "calculation_examples.json",
    "flashcards.json",
    "mindmaps.json",
]

# Files whose top-level JSON shape differs from the {table_key: [rows]}
# convention used by every other data file.
_LIST_FILE_TABLE = {
    "rules.json": "trigger_rules",  # bare JSON list of rule dicts
}
# Per-file renames applied before the table loop.
# Table-key renames: data-file top-level key -> seed table key.
_TABLE_KEY_REMAPS = {
    "questions.json": {"questions": "practice_questions"},
}
# Row-key renames: row-dict key -> DB column name (applied to every row of
# every table list in the file).
_ROW_KEY_REMAPS = {
    "rules.json": {"triggers": "triggers_json"},
}

# Tables seed.py is forbidden to touch under any circumstance.
_PROTECTED_TABLES = {"StudentAttempts", "MistakeLog", "FlashcardProgress"}

_FTS_REBUILDS = [
    ("case_fts", "CasePatterns",
     "case_id, title, business_context, industry, main_issue"),
    ("framework_fts", "Frameworks",
     "framework_id, name, definition, purpose"),
    ("question_fts", "PracticeQuestions",
     "question_id, question_text, topic_ref"),
]


def _load_json_file(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _normalise_payload(filename: str, payload: object) -> dict:
    """Reshape quirky-but-valid data files into {table_key: [rows]} form.

    - rules.json is a bare list -> wrapped as {"trigger_rules": [...]}.
    - questions.json uses top-level "questions" -> renamed "practice_questions".
    - rules.json rows use "triggers" -> renamed to the "triggers_json" column.
    - rule_frameworks.json is {rule_id: [framework_id, ...]} -> expanded into
      rule_framework_mappings rows with generated map_ids.
    - ProblemPatterns has no data file of its own: stub rows are derived from
      the pattern_ids referenced by the trigger rules so the FK from
      TriggerRules.pattern_id is satisfied.
    """
    if isinstance(payload, list):
        table_key = _LIST_FILE_TABLE.get(filename)
        if table_key is None:
            raise ValueError(f"{filename}: unexpected bare JSON list")
        payload = {table_key: payload}
    if not isinstance(payload, dict):
        raise ValueError(f"{filename}: expected a JSON object, got {type(payload).__name__}")

    for old_key, new_key in _TABLE_KEY_REMAPS.get(filename, {}).items():
        if old_key in payload:
            payload[new_key] = payload.pop(old_key)

    for old_key, new_key in _ROW_KEY_REMAPS.get(filename, {}).items():
        for rows in payload.values():
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict) and old_key in row:
                        row[new_key] = row.pop(old_key)

    if filename == "rule_frameworks.json":
        rows: list[dict] = []
        for rule_id, fw_entries in payload.items():
            for i, entry in enumerate(fw_entries or []):
                if isinstance(entry, dict):
                    fw_id = entry.get("framework_id")
                    rationale = entry.get("rationale", "")
                else:
                    fw_id = entry
                    rationale = ""
                rows.append({
                    "map_id": f"MAP-{rule_id}-{i + 1}",
                    "rule_id": rule_id,
                    "framework_id": fw_id,
                    "rationale": rationale,
                })
        payload = {"rule_framework_mappings": rows}

    rules = payload.get("trigger_rules") or []
    patterns: list[dict] = []
    seen: set[str] = set()
    for rule in rules:
        pid = rule.get("pattern_id") if isinstance(rule, dict) else None
        if pid and pid not in seen:
            seen.add(pid)
            patterns.append({
                "pattern_id": pid,
                "name": str(pid).replace("PAT-", "").replace("-", " ").title(),
                "description": "",
                "indicators": "[]",
            })
    if patterns:
        payload = {"problem_patterns": patterns, **payload}
    return payload


def _upsert_table(
    conn: sqlite3.Connection, table: str, rows: list[dict]
) -> tuple[int, list[tuple[str, str]]]:
    """INSERT OR REPLACE every row. Columns come from the JSON keys.

    A row that violates a constraint (e.g. a dangling foreign key) is skipped
    -- with a warning -- instead of aborting the whole seed, so one bad record
    can never wipe out or block the rest of the content. Returns
    (inserted_count, [(row_pk, error), ...]).
    """
    if table in _PROTECTED_TABLES:
        raise RuntimeError(f"seed.py must never write to protected table {table}")
    count = 0
    skipped: list[tuple[str, str]] = []
    for row in rows:
        cols = list(row.keys())
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
        values = [json.dumps(v) if isinstance(v, (dict, list)) else v
                  for v in (row[c] for c in cols)]
        try:
            conn.execute(sql, values)
        except sqlite3.IntegrityError as exc:
            skipped.append((str(row.get(cols[0])), str(exc)))
            continue
        count += 1
    return count, skipped


def rebuild_fts(conn: sqlite3.Connection) -> None:
    """Full rebuild of the FTS5 indexes from their base tables."""
    for fts_table, base_table, columns in _FTS_REBUILDS:
        conn.execute(f"DELETE FROM {fts_table}")
        conn.execute(
            f"INSERT INTO {fts_table} SELECT {columns} FROM {base_table}"
        )


def run_seed(conn: sqlite3.Connection) -> dict[str, int]:
    """Load every data file and upsert every seed table. Returns row counts.

    Rows that violate a database constraint are skipped with a stderr warning
    (see _upsert_table); they never abort the seed.
    """
    counts: dict[str, int] = {}
    skipped_total = 0
    for filename in _FILES:
        path = _DATA_DIR / filename
        if not path.exists():
            continue
        payload = _normalise_payload(filename, _load_json_file(path))
        for key, table in _TABLE_ORDER:
            rows = payload.get(key)
            if rows:
                n, skipped = _upsert_table(conn, table, rows)
                counts[table] = counts.get(table, 0) + n
                for pk, err in skipped:
                    skipped_total += 1
                    print(f"seed: skipped {table} row {pk}: {err}", file=sys.stderr)
    rebuild_fts(conn)
    conn.commit()
    if skipped_total:
        print(f"seed: {skipped_total} row(s) skipped due to constraint violations",
              file=sys.stderr)
    return counts


def main(argv: list[str]) -> int:
    from dbcore import get_conn, init_db  # noqa: PLC0415

    db_arg = argv[1] if len(argv) > 1 else None
    if db_arg is None:
        db_file = init_db()  # creates schema first; returns path
    else:
        db_file = Path(db_arg)
        conn = get_conn(db_file)
        conn.executescript((_HERE / "db" / "schema.sql").read_text(encoding="utf-8"))
        conn.close()
    conn = get_conn(db_file)
    try:
        counts = run_seed(conn)
    finally:
        conn.close()
    total = sum(counts.values())
    print(f"Seeded {total} rows into {db_file}")
    for table in sorted(counts):
        print(f"  {table}: {counts[table]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
