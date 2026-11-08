import json
from pathlib import Path

from scripts.normalize import is_relevant, normalize, version_status

FIXTURE = Path(__file__).parent / "fixtures" / "work_sample.json"


def work_sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_standard_work_normalizes_fields():
    record = normalize(work_sample(), now="2026-11-08T00:00:00Z", query_id="sample")
    assert record["openalex_id"] == "W4388774485"
    assert record["doi"] == "10.1016/j.ymssp.2024.111234"
    assert record["publication_year"] == 2024
    assert record["journal"] == "Mechanical Systems and Signal Processing"
    assert json.loads(record["authors"]) == ["Wei Zhang", "Li Chen", "Ming Sun", "Hao Wang"]


def test_journal_fallback_and_missing_journal():
    work = work_sample()
    work["primary_location"] = None
    work["best_oa_location"] = {"source": {"display_name": "Fallback Journal"}}
    assert normalize(work, now="n", query_id="q")["journal"] == "Fallback Journal"
    work["best_oa_location"] = None
    assert normalize(work, now="n", query_id="q")["journal"] is None


def test_empty_authors_and_eight_authors_are_preserved():
    work = work_sample()
    work["authorships"] = []
    assert json.loads(normalize(work, now="n", query_id="q")["authors"]) == []
    work["authorships"] = [{"author": {"display_name": f"Author {i}"}} for i in range(8)]
    assert len(json.loads(normalize(work, now="n", query_id="q")["authors"])) == 8


def test_relevance_gate_examples():
    assert is_relevant("Load-bearing capacity of masonry walls") == (False, "false_positive_phrase")
    assert is_relevant("Bearing fault diagnosis using CNN") == (True, None)
    assert is_relevant("Deep learning for fault diagnosis") == (False, "no_bearing_term_in_title")


def test_version_status_examples():
    assert version_status({"primary_location": {"version": "publishedVersion"}}) == "published"
    assert version_status({"primary_location": {"version": "acceptedVersion", "is_published": False}}) == "accepted"
    assert version_status({}) == "unknown"


def test_missing_doi_still_normalizes_and_retracted_is_excluded():
    work = work_sample()
    work["doi"] = None
    work["is_retracted"] = True
    record = normalize(work, now="n", query_id="q")
    assert record["doi"] is None
    assert record["excluded"] == 1
    assert record["exclude_reason"] == "retracted"
