"""Spec §18.10: question-source verification — all questions original practice
questions (source_verified=0), no past-paper claims anywhere."""

import re

PAST_PAPER_RE = re.compile(r"past[\s\-]*papers?", re.IGNORECASE)
# denials such as "not an ICAP past paper" are not claims
DENIAL_RE = re.compile(r"not an? [^.,;]{0,40}?past[\s\-]*papers?", re.IGNORECASE)


def test_all_questions_source_verified_zero(conn):
    rows = conn.execute(
        "SELECT question_id, source_verified FROM PracticeQuestions"
    ).fetchall()
    assert len(rows) == 24, f"expected 24 questions, got {len(rows)}"
    for row in rows:
        assert row["source_verified"] in (0, "0", False, None), (
            f"{row['question_id']}: source_verified={row['source_verified']!r}, want 0"
        )


def test_no_past_paper_claims(conn):
    """Question text, source notes, answer outlines and rubrics must not claim
    to be (or be derived from) ICAP past papers."""
    texts = []
    for row in conn.execute(
        "SELECT question_id, question_text, source_note FROM PracticeQuestions"
    ):
        texts.append((f"PracticeQuestions.{row['question_id']}", row["question_text"]))
        texts.append((f"PracticeQuestions.{row['question_id']}.source_note", row["source_note"]))
    for row in conn.execute("SELECT outline_id, outline_text, note FROM AnswerOutlines"):
        texts.append((f"AnswerOutlines.{row['outline_id']}", row["outline_text"]))
        texts.append((f"AnswerOutlines.{row['outline_id']}.note", row["note"]))
    for row in conn.execute("SELECT rubric_id, rubric_json, note FROM MarkingRubrics"):
        texts.append((f"MarkingRubrics.{row['rubric_id']}", row["rubric_json"]))
        texts.append((f"MarkingRubrics.{row['rubric_id']}.note", row["note"]))
    offenders = []
    for where, text in texts:
        if not text:
            continue
        cleaned = DENIAL_RE.sub("", str(text))
        if PAST_PAPER_RE.search(cleaned):
            offenders.append(where)
    assert not offenders, f"past-paper claims found in: {offenders}"


def test_questions_carry_practice_rubric_disclaimer(conn):
    """Rubrics/notes must not be mistaken for official ICAP marking schemes."""
    notes = [
        (row["rubric_id"], str(row["note"] or ""))
        for row in conn.execute("SELECT rubric_id, note FROM MarkingRubrics")
    ]
    assert notes, "no marking rubrics seeded"
    for rid, note in notes:
        assert "official" not in note.lower() or "not official" in note.lower() or \
               "not the official" in note.lower() or "unofficial" in note.lower() or \
               "practice" in note.lower(), (
            f"{rid}: rubric note could be read as official: {note!r:.120}"
        )
