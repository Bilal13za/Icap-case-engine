"""Core database access for the ICAP Business Case Analysis and Decision Engine.

- Data directory: %LOCALAPPDATA%\\ICAP Case Engine on Windows,
  ~/.icap-case-engine on other platforms.
- Database file: case_engine.db
- Uses stdlib sqlite3 only (no YAML, no external services).
- init_db() applies the schema (idempotent -- every statement is CREATE ...
  IF NOT EXISTS, so older databases are migrated safely), seeds content when
  seed tables are empty or the study-aids tables are missing/empty, and
  records the schema version. Seeding NEVER touches student tables
  (StudentAttempts, MistakeLog, FlashcardProgress).
"""

from __future__ import annotations

import datetime as _dt
import os
import sqlite3
from pathlib import Path

APP_DIR_NAME = "ICAP Case Engine"
DB_FILENAME = "case_engine.db"
SCHEMA_VERSION = 2

_SCHEMA_SQL = None


def app_data_dir() -> Path:
    """Return the per-user data directory for the app."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_DIR_NAME
    return Path.home() / ".icap-case-engine"


def db_path() -> Path:
    """Full path to the SQLite database file."""
    return app_data_dir() / DB_FILENAME


def get_conn(db: str | Path | None = None) -> sqlite3.Connection:
    """Open a connection to the app database (sqlite3, Row factory)."""
    path = Path(db) if db is not None else db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _load_schema_sql() -> str:
    global _SCHEMA_SQL
    if _SCHEMA_SQL is None:
        here = Path(__file__).resolve().parent
        schema_file = here / "db" / "schema.sql"
        _SCHEMA_SQL = schema_file.read_text(encoding="utf-8")
    return _SCHEMA_SQL


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _seed_tables_empty(conn: sqlite3.Connection) -> bool:
    """True when no seed content is present (checked on Papers)."""
    if not _table_exists(conn, "Papers"):
        return True
    row = conn.execute("SELECT COUNT(*) AS n FROM Papers").fetchone()
    return (row["n"] if row else 0) == 0


def _study_aids_missing(conn: sqlite3.Connection) -> bool:
    """True when the study-aids tables are absent or unseeded.

    Lets databases created before schema v2 pick up the Flashcards/MindMaps
    content on next launch without touching student tables.
    """
    if not _table_exists(conn, "Flashcards"):
        return True
    row = conn.execute("SELECT COUNT(*) AS n FROM Flashcards").fetchone()
    return (row["n"] if row else 0) == 0


def init_db(db: str | Path | None = None) -> Path:
    """Create schema, seed content, and stamp the schema version.

    Idempotent: safe to call on every app start. Never modifies the student
    tables (StudentAttempts, MistakeLog).
    """
    path = Path(db) if db is not None else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_conn(path)
    try:
        # The schema script is fully idempotent (CREATE ... IF NOT EXISTS),
        # so applying it on every start safely migrates older databases.
        conn.executescript(_load_schema_sql())

        if _seed_tables_empty(conn) or _study_aids_missing(conn):
            # Import lazily to avoid a hard dependency at import time.
            import seed as _seed  # noqa: PLC0415

            _seed.run_seed(conn)

        conn.execute(
            "INSERT OR REPLACE INTO SchemaVersion(version, applied_at) VALUES (?, ?)",
            (SCHEMA_VERSION, _dt.datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()
    return path


def schema_version(conn: sqlite3.Connection) -> int | None:
    """Return the recorded schema version, or None if not recorded."""
    if not _table_exists(conn, "SchemaVersion"):
        return None
    row = conn.execute(
        "SELECT version FROM SchemaVersion ORDER BY version DESC LIMIT 1"
    ).fetchone()
    return row["version"] if row else None
