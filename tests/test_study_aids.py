"""Study Aids: flashcards, mind maps, formula sheets, checklists.

Every card/map must trace to seeded source data and carry a valid
verification_status. Student progress must survive re-seeding.
"""

import ast
import json

import pytest

from .conftest import ROOT, seedmod
from engine import studyaids as sa


def _cards(conn):
    return conn.execute("SELECT * FROM Flashcards").fetchall()


def test_card_count_sanity(conn):
    """~180-220 cards expected from the deterministic generator."""
    n = conn.execute("SELECT COUNT(*) AS n FROM Flashcards").fetchone()["n"]
    assert 180 <= n <= 240, f"unexpected card count: {n}"


def test_no_empty_fronts_backs(conn):
    bad = conn.execute(
        "SELECT card_id FROM Flashcards "
        "WHERE front IS NULL OR TRIM(front) = '' "
        "OR back IS NULL OR TRIM(back) = ''"
    ).fetchall()
    assert not bad, f"cards with empty text: {[r['card_id'] for r in bad]}"


def test_card_references_valid(conn):
    """Every card references real source rows and has a valid status."""
    for c in _cards(conn):
        cid = c["card_id"]
        if c["framework_id"]:
            assert conn.execute(
                "SELECT 1 FROM Frameworks WHERE framework_id = ?",
                (c["framework_id"],)).fetchone(), cid
        if c["formula_id"]:
            assert conn.execute(
                "SELECT 1 FROM Formulas WHERE formula_id = ?",
                (c["formula_id"],)).fetchone(), cid
        if c["rule_id"]:
            assert conn.execute(
                "SELECT 1 FROM TriggerRules WHERE rule_id = ?",
                (c["rule_id"],)).fetchone(), cid
        assert c["verification_status"] in sa.VALID_VERIFICATION_STATUSES, cid
        assert c["card_type"] in sa.CARD_TYPE_LABELS, cid
        if c["verification_status"] == "verified_official":
            assert (c["official_source"] or "").strip(), cid


def test_card_status_inherited_from_source(conn):
    """Spot-check: a card's status equals its source framework's status."""
    row = conn.execute(
        "SELECT c.verification_status AS cs, f.verification_status AS fs "
        "FROM Flashcards c JOIN Frameworks f "
        "ON f.framework_id = c.framework_id "
        "WHERE c.card_id = 'FC-FW-SWOT-DEF'").fetchone()
    assert row is not None
    assert row["cs"] == row["fs"] == "verified_official"


def test_mindmap_catalogue(conn):
    """27 maps: all 22 verified frameworks + 5 key supplementary."""
    maps = conn.execute("SELECT * FROM MindMaps").fetchall()
    assert len(maps) == 27
    verified_fw = {r["framework_id"] for r in conn.execute(
        "SELECT framework_id FROM Frameworks "
        "WHERE verification_status = 'verified_official'")}
    assert len(verified_fw) == 22
    mapped = {m["framework_id"] for m in maps}
    assert verified_fw <= mapped, "every verified framework needs a map"
    for m in maps:
        assert m["verification_status"] in sa.VALID_VERIFICATION_STATUSES


def test_mindmap_html_generates_for_every_map(conn):
    """Offline HTML renders for every map without error."""
    for m in conn.execute("SELECT * FROM MindMaps").fetchall():
        fw = conn.execute(
            "SELECT * FROM Frameworks WHERE framework_id = ?",
            (m["framework_id"],)).fetchone()
        steps = conn.execute(
            "SELECT * FROM FrameworkSteps WHERE framework_id = ? ORDER BY step_no",
            (m["framework_id"],)).fetchall()
        order = json.loads(m["branch_order_json"]) if m["branch_order_json"] else None
        html_doc = sa.mindmap_html(dict(fw), [dict(s) for s in steps], order)
        import html as _htmlmod
        assert _htmlmod.escape(fw["name"]) in html_doc
        assert "<details" in html_doc and "</details>" in html_doc
        # No external resources: must work fully offline.
        assert "http://" not in html_doc and "https://" not in html_doc
        assert "<script" not in html_doc.lower()


def test_formula_sheet_groups_cover_all_formulas(conn):
    """Every formula appears in exactly one quick-sheet group."""
    fids = [r["formula_id"] for r in conn.execute("SELECT formula_id FROM Formulas")]
    seen: list[str] = []
    for _title, _paper, ids in sa.FORMULA_SHEET_GROUPS:
        seen.extend(ids)
    assert sorted(seen) == sorted(fids), "sheet groups must partition all formulas"
    assert len(seen) == len(set(seen)), "no formula in two groups"


def test_checklists_defined():
    assert len(sa.RECOMMENDATION_CHECKLIST) == 11
    assert len(sa.ANSWER_QUALITY_ITEMS) == 9
    assert len({k for k, _ in sa.RECOMMENDATION_CHECKLIST}) == 11


def test_answer_quality_items_match_app_fallback():
    """app.py's literal fallback must stay identical to the canonical list."""
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    fallback = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "SELF_ASSESS_ITEMS":
                    cond = node.value
                    if isinstance(cond, ast.IfExp):
                        fallback = ast.literal_eval(cond.orelse)
    assert fallback is not None, "SELF_ASSESS_ITEMS fallback not found in app.py"
    assert fallback == sa.ANSWER_QUALITY_ITEMS


def test_flashcard_progress_is_protected():
    assert "FlashcardProgress" in seedmod._PROTECTED_TABLES
    # _upsert_table refuses protected tables directly:
    import sqlite3
    conn = sqlite3.connect(":memory:")
    with pytest.raises(RuntimeError):
        seedmod._upsert_table(conn, "FlashcardProgress", [{"card_id": "X"}])
    conn.close()


def test_seed_idempotent_and_progress_survives(conn):
    """Re-seeding neither duplicates cards nor wipes student tables."""
    conn.execute(
        "INSERT INTO StudentAttempts(question_id, attempted_at) VALUES ('Q-1', 'now')")
    conn.execute(
        "INSERT INTO MistakeLog(topic, description) VALUES ('t', 'd')")
    first_card = conn.execute(
        "SELECT card_id FROM Flashcards ORDER BY card_id LIMIT 1").fetchone()["card_id"]
    conn.execute(
        "INSERT INTO FlashcardProgress(card_id, status, reps, last_seen) "
        "VALUES (?, 'known', 3, 'now')", (first_card,))
    conn.commit()
    before = conn.execute("SELECT COUNT(*) AS n FROM Flashcards").fetchone()["n"]

    seedmod.run_seed(conn)

    after = conn.execute("SELECT COUNT(*) AS n FROM Flashcards").fetchone()["n"]
    assert before == after, "re-seed must not duplicate cards"
    assert conn.execute("SELECT COUNT(*) AS n FROM StudentAttempts").fetchone()["n"] == 1
    assert conn.execute("SELECT COUNT(*) AS n FROM MistakeLog").fetchone()["n"] == 1
    prow = conn.execute(
        "SELECT status, reps FROM FlashcardProgress WHERE card_id = ?",
        (first_card,)).fetchone()
    assert prow is not None and prow["status"] == "known" and prow["reps"] == 3


def test_migration_adds_study_aids_tables(tmp_path):
    """A v1 database (no study-aids tables) gains them via init_db."""
    import dbcore
    db = tmp_path / "v1.db"
    schema = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
    # Simulate v1: schema without the study-aids tables, seeded with v1 files.
    v1_schema = schema.split("-- ------------------------------------------------------------- Study aids --")[0]
    import sqlite3
    c = sqlite3.connect(str(db))
    c.executescript(v1_schema)
    c.commit()
    c.close()

    import seed as seedmod2
    old_files, old_order = seedmod2._FILES, seedmod2._TABLE_ORDER
    seedmod2._FILES = [f for f in old_files if f not in ("flashcards.json", "mindmaps.json")]
    seedmod2._TABLE_ORDER = [t for t in old_order if t[1] not in ("Flashcards", "MindMaps")]
    try:
        c = sqlite3.connect(str(db))
        seedmod2.run_seed(c)
        c.close()
    finally:
        seedmod2._FILES, seedmod2._TABLE_ORDER = old_files, old_order

    dbcore.init_db(db)  # must migrate + seed study aids, keep Papers row
    c2 = dbcore.get_conn(db)
    try:
        assert c2.execute("SELECT COUNT(*) AS n FROM Flashcards").fetchone()["n"] >= 180
        assert c2.execute("SELECT COUNT(*) AS n FROM MindMaps").fetchone()["n"] == 27
        assert c2.execute("SELECT COUNT(*) AS n FROM Papers").fetchone()["n"] == 4
    finally:
        c2.close()
