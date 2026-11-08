from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import DB_PATH

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS papers (
    openalex_id TEXT PRIMARY KEY,
    doi TEXT,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '[]',
    journal TEXT,
    journal_issn TEXT,
    publication_year INTEGER,
    publication_date TEXT,
    version_status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (version_status IN ('published','accepted','unknown')),
    cited_by_count INTEGER NOT NULL DEFAULT 0,
    oa_status TEXT,
    is_retracted INTEGER NOT NULL DEFAULT 0,
    found_by TEXT,
    first_seen_at TEXT NOT NULL,
    last_updated_at TEXT NOT NULL,
    excluded INTEGER NOT NULL DEFAULT 0,
    exclude_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(publication_date DESC);
CREATE INDEX IF NOT EXISTS idx_papers_journal ON papers(journal);
CREATE INDEX IF NOT EXISTS idx_papers_visible ON papers(excluded, is_retracted, publication_date);
CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    mode TEXT NOT NULL,
    fetched INTEGER DEFAULT 0,
    inserted INTEGER DEFAULT 0,
    updated INTEGER DEFAULT 0,
    max_remaining INTEGER,
    status TEXT NOT NULL DEFAULT 'running'
);
"""

UPSERT_SQL = """
INSERT INTO papers (
    openalex_id, doi, title, authors, journal, journal_issn, publication_year,
    publication_date, version_status, cited_by_count, oa_status, is_retracted,
    found_by, first_seen_at, last_updated_at, excluded, exclude_reason
) VALUES (
    :openalex_id, :doi, :title, :authors, :journal, :journal_issn, :publication_year,
    :publication_date, :version_status, :cited_by_count, :oa_status, :is_retracted,
    :found_by, :first_seen_at, :last_updated_at, :excluded, :exclude_reason
)
ON CONFLICT(openalex_id) DO UPDATE SET
    doi=excluded.doi, title=excluded.title, authors=excluded.authors,
    journal=excluded.journal, journal_issn=excluded.journal_issn,
    publication_year=excluded.publication_year, publication_date=excluded.publication_date,
    version_status=excluded.version_status, cited_by_count=excluded.cited_by_count,
    oa_status=excluded.oa_status, is_retracted=excluded.is_retracted,
    last_updated_at=excluded.last_updated_at, excluded=excluded.excluded,
    exclude_reason=excluded.exclude_reason;
"""


def connect(path: str | Path = DB_PATH) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=DELETE;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_schema(path: str | Path = DB_PATH) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)


def upsert_paper(conn: sqlite3.Connection, paper: dict) -> None:
    conn.execute(UPSERT_SQL, paper)


def visible_papers(conn: sqlite3.Connection, window_start: str) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT openalex_id, doi, title, authors, journal, journal_issn,
                  publication_year, publication_date, version_status,
                  cited_by_count, oa_status
           FROM papers
           WHERE excluded=0 AND is_retracted=0 AND publication_date >= ? AND doi IS NOT NULL
           ORDER BY publication_date DESC, cited_by_count DESC""",
        (window_start,),
    ).fetchall()
