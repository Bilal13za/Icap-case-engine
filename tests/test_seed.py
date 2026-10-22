"""Spec §18.13 (invalid records handled gracefully) and §18.14 (student work
preserved across re-seed), plus seed idempotency."""

import json
import sqlite3

import pytest

from .conftest import ROOT, seedmod
import dbcore


def _run_seed_with_data_dir(conn, data_dir):
    """Run seed.run_seed with _DATA_DIR pointed at a scratch directory."""
    old = seedmod._DATA_DIR
    seedmod._DATA_DIR = data_dir
    try:
        return seedmod.run_seed(conn)
    finally:
        seedmod._DATA_DIR = old


def _copy_data_file(tmp_path, name):
    src = ROOT / "data" / name
    dst = tmp_path / name
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return dst


def test_duplicate_pk_replaced_not_duplicated(unseeded_conn, tmp_path):
    """§18.13: a duplicate primary key is upserted (INSERT OR REPLACE), not
    duplicated and not an error."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    dst = _copy_data_file(data_dir, "syllabus.json")
    payload = json.loads(dst.read_text(encoding="utf-8"))
    papers = payload["papers"]
    papers.append(dict(papers[0]))  # exact duplicate PK
    dst.write_text(json.dumps(payload), encoding="utf-8")

    _run_seed_with_data_dir(unseeded_conn, data_dir)
    n = unseeded_conn.execute(
        "SELECT COUNT(*) AS n FROM Papers WHERE paper_id = ?", (papers[0]["paper_id"],)
    ).fetchone()["n"]
    assert n == 1


def test_bad_fk_handled_gracefully(unseeded_conn, tmp_path):
    """§18.13: a row with a dangling foreign key must not abort the seed or
    corrupt the database — it is skipped, everything valid is seeded."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # minimal file set: only syllabus.json with one bad-FK learning outcome
    payload = {
        "papers": [
            {"paper_id": "P-OK", "code": "T1", "title": "t",
             "verification_status": "verified_official"}
        ],
        "learning_outcomes": [
            {"lo_id": "LO-BAD", "paper_id": "P-DOES-NOT-EXIST",
             "description": "bad fk row", "verification_status": "verified_official"},
            {"lo_id": "LO-GOOD", "paper_id": "P-OK",
             "description": "good row", "verification_status": "verified_official"},
        ],
    }
    (data_dir / "syllabus.json").write_text(json.dumps(payload), encoding="utf-8")

    _run_seed_with_data_dir(unseeded_conn, data_dir)  # must not raise

    assert unseeded_conn.execute("SELECT COUNT(*) AS n FROM Papers").fetchone()["n"] == 1
    assert unseeded_conn.execute(
        "SELECT COUNT(*) AS n FROM LearningOutcomes WHERE lo_id='LO-GOOD'"
    ).fetchone()["n"] == 1
    assert unseeded_conn.execute(
        "SELECT COUNT(*) AS n FROM LearningOutcomes WHERE lo_id='LO-BAD'"
    ).fetchone()["n"] == 0


def test_seed_is_idempotent(conn, tmp_db):
    """Re-running the seed changes no row counts and creates no duplicates."""
    def counts(c):
        return {
            t: c.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
            for t in ("Papers", "LearningOutcomes", "Frameworks", "TriggerRules",
                      "CasePatterns", "Formulas", "PracticeQuestions")
        }

    before = counts(conn)
    conn.close()
    c2 = dbcore.get_conn(tmp_db)
    seedmod.run_seed(c2)
    c2.commit()
    after = counts(c2)
    c2.close()
    assert before == after


def test_student_attempts_preserved_across_reseed(conn, tmp_db):
    """§18.14: StudentAttempts and MistakeLog survive re-seeding untouched."""
    conn.execute(
        "INSERT INTO StudentAttempts (question_id, attempted_at, time_taken_min, "
        "marks_self, answer_text, notes) VALUES (?, ?, ?, ?, ?, ?)",
        ("Q-001", "2026-10-21T10:00:00", 25.0, 7.5, "my answer", "note"),
    )
    attempt_id = conn.execute("SELECT last_insert_rowid() AS i").fetchone()["i"]
    conn.execute(
        "INSERT INTO MistakeLog (attempt_id, topic, description, created_at, resolved)"
        " VALUES (?, ?, ?, ?, ?)",
        (attempt_id, "WACC", "mixed up nominal and effective rates",
         "2026-10-21T10:30:00", 0),
    )
    conn.commit()
    before_attempts = conn.execute("SELECT * FROM StudentAttempts").fetchall()
    before_mistakes = conn.execute("SELECT * FROM MistakeLog").fetchall()
    conn.close()

    c2 = dbcore.get_conn(tmp_db)
    seedmod.run_seed(c2)
    c2.commit()
    after_attempts = c2.execute("SELECT * FROM StudentAttempts").fetchall()
    after_mistakes = c2.execute("SELECT * FROM MistakeLog").fetchall()
    c2.close()

    assert [dict(r) for r in after_attempts] == [dict(r) for r in before_attempts]
    assert [dict(r) for r in after_mistakes] == [dict(r) for r in before_mistakes]


def test_seed_never_writes_student_tables():
    """The seed module refuses to touch protected tables by construction."""
    assert seedmod._PROTECTED_TABLES == {
        "StudentAttempts", "MistakeLog", "FlashcardProgress"}
    with pytest.raises(RuntimeError):
        seedmod._upsert_table(None, "StudentAttempts", [{"attempt_id": 1}])
    with pytest.raises(RuntimeError):
        seedmod._upsert_table(None, "FlashcardProgress", [{"card_id": "X"}])


def test_seed_data_contract(conn):
    """The seeded database honours the content contract: 30 rules, 24
    questions, 16 cases, and all three FTS indexes populated."""
    counts = {
        "TriggerRules": 30,
        "PracticeQuestions": 24,
        "CasePatterns": 16,
    }
    for table, want in counts.items():
        got = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        assert got == want, f"{table}: {got} rows, want {want}"
    for fts, want in [("case_fts", 16), ("framework_fts", 49), ("question_fts", 24)]:
        got = conn.execute(f"SELECT COUNT(*) AS n FROM {fts}").fetchone()["n"]
        assert got == want, f"{fts}: {got} rows, want {want}"
    # every trigger rule has at least one framework mapping
    unmapped = conn.execute(
        "SELECT rule_id FROM TriggerRules WHERE rule_id NOT IN "
        "(SELECT rule_id FROM RuleFrameworkMappings)"
    ).fetchall()
    assert not unmapped, f"rules without framework mappings: {[r['rule_id'] for r in unmapped]}"
