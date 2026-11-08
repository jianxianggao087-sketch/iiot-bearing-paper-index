import json
import sqlite3

import pytest

from scripts.db import connect, init_schema, upsert_paper, visible_papers
from scripts.normalize import normalize


def sample(excluded=0):
    return normalize({
        "id": "https://openalex.org/W1",
        "doi": "https://doi.org/10.1234/example",
        "title": "Bearing fault diagnosis",
        "authorships": [],
        "publication_date": "2024-01-01",
        "publication_year": 2024,
    }, now="2026-01-01T00:00:00Z", query_id="test") | {"excluded": excluded}


def test_schema_is_idempotent(tmp_path):
    path = tmp_path / "papers.db"
    init_schema(path)
    init_schema(path)
    with connect(path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"papers", "sync_state", "runs"} <= tables


def test_upsert_preserves_first_seen_and_updates_metrics(tmp_path):
    path = tmp_path / "papers.db"
    init_schema(path)
    with connect(path) as conn:
        record = sample()
        upsert_paper(conn, record)
        for count in (5, 10):
            upsert_paper(conn, record | {"first_seen_at": "later", "last_updated_at": "later", "cited_by_count": count})
        row = conn.execute("SELECT * FROM papers").fetchone()
        assert conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0] == 1
        assert row["first_seen_at"] == record["first_seen_at"]
        assert row["cited_by_count"] == 10


def test_version_check_and_excluded_export_filter(tmp_path):
    path = tmp_path / "papers.db"
    init_schema(path)
    with connect(path) as conn:
        upsert_paper(conn, sample(excluded=1))
        assert visible_papers(conn, "2020-01-01") == []
        bad = sample() | {"version_status": "draft"}
        with pytest.raises(sqlite3.IntegrityError):
            upsert_paper(conn, bad)
