"""Spec §18.9: syllabus versioning — verified_official for 2021 rows,
provisional_predecessor for 2025 rows, labels survive re-seeding."""

import re

import pytest

from .conftest import seedmod

ALLOWED = {"verified_official", "provisional_predecessor", "supplementary", "unverified"}

# tables carrying a verification_status column (per db/schema.sql)
STATUS_TABLES = [
    "Papers",
    "SyllabusVersions",
    "LearningOutcomes",
    "Topics",
    "Concepts",
    "Frameworks",
    "CasePatterns",
    "Formulas",
    "PracticeQuestions",
]


def _cols(conn, table):
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]


def test_all_statuses_in_allowed_set(conn):
    for table in STATUS_TABLES:
        rows = conn.execute(f"SELECT verification_status FROM {table}").fetchall()
        assert rows, f"{table} has no rows"
        for row in rows:
            assert row["verification_status"] in ALLOWED, (
                f"{table}: bad verification_status {row['verification_status']!r}"
            )


def test_verified_official_rows_cite_source(conn):
    """Every verified_official row must name its official source (where the
    schema provides a source column)."""
    for table in STATUS_TABLES:
        cols = _cols(conn, table)
        source_col = next(
            (c for c in ("official_source", "source_ref", "source_url") if c in cols), None
        )
        if source_col is None:
            continue
        bad = conn.execute(
            f"SELECT COUNT(*) AS n FROM {table} "
            f"WHERE verification_status='verified_official' "
            f"AND ({source_col} IS NULL OR TRIM({source_col})='')"
        ).fetchone()["n"]
        assert bad == 0, f"{table}: {bad} verified_official rows with empty {source_col}"


def _scheme_of(conn, paper_id):
    row = conn.execute(
        "SELECT scheme, code FROM Papers WHERE paper_id = ?", (paper_id,)
    ).fetchone()
    if row and row["scheme"]:
        return str(row["scheme"])
    # fall back to the id/code text itself
    text = str(paper_id) + str(row["code"] if row else "")
    if "2025" in text:
        return "2025"
    if "2021" in text:
        return "2021"
    return ""


def test_2021_rows_verified_official(conn):
    """2021-scheme syllabus rows must be verified_official."""
    los = conn.execute(
        "SELECT lo_id, paper_id, verification_status FROM LearningOutcomes"
    ).fetchall()
    assert los, "no learning outcomes seeded"
    for lo in los:
        if "2021" in _scheme_of(conn, lo["paper_id"]):
            assert lo["verification_status"] == "verified_official", (
                f"{lo['lo_id']}: 2021 row labelled {lo['verification_status']!r}"
            )


def test_2025_rows_provisional_predecessor(conn):
    """2025-scheme syllabus rows must be provisional_predecessor — or unverified
    where they encode the disputed secondary claim (CAPM/budgeting removal).
    The detailed 2025 syllabus is not yet officially published."""
    los = conn.execute(
        "SELECT lo_id, paper_id, syllabus_ref, verification_status FROM LearningOutcomes"
    ).fetchall()
    found_2025 = False
    for lo in los:
        if "2025" in _scheme_of(conn, lo["paper_id"]):
            found_2025 = True
            assert lo["verification_status"] in (
                "provisional_predecessor", "unverified"), (
                f"{lo['lo_id']}: 2025 row labelled {lo['verification_status']!r}")
            if lo["verification_status"] == "unverified":
                # the unverified label is reserved for the disputed secondary
                # claim (CAPM B-3 / Budgeting grid C removed from CAF-7)
                assert lo["syllabus_ref"] in ("B-3", "C-1", "C-2", "C-3"), (
                    f"{lo['lo_id']}: unverified 2025 row outside the CAPM/budgeting claim")
    assert found_2025, "no 2025-scheme learning outcomes seeded"


def test_no_invented_2025_weightages(conn):
    """2025 Topics must not carry invented weightages presented as official."""
    rows = conn.execute(
        "SELECT t.topic_id, t.weightage, t.verification_status, p.scheme "
        "FROM Topics t LEFT JOIN Papers p ON t.paper_id = p.paper_id"
    ).fetchall()
    for r in rows:
        scheme = str(r["scheme"] or "")
        if "2025" in scheme or "2025" in str(r["topic_id"]):
            assert r["verification_status"] in (
                "provisional_predecessor", "unverified"), (
                f"{r['topic_id']}: 2025 topic labelled {r['verification_status']!r}")


def _snapshot(conn):
    snap = {}
    for table in STATUS_TABLES:
        pk = conn.execute(f"PRAGMA table_info({table})").fetchall()[0]["name"]
        for row in conn.execute(f"SELECT {pk} AS pk, verification_status FROM {table}"):
            snap[(table, row["pk"])] = row["verification_status"]
    return snap


def test_reseed_preserves_versions(conn, tmp_db):
    """Seed re-run keeps every verification_status label (no silent flips)."""
    before = _snapshot(conn)
    conn.close()
    # re-seed into the same file via a fresh connection
    import dbcore

    c2 = dbcore.get_conn(tmp_db)
    seedmod.run_seed(c2)
    c2.commit()
    after = _snapshot(c2)
    c2.close()
    assert before == after, "verification_status labels changed across re-seed"
