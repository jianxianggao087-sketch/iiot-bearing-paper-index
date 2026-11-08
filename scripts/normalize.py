from __future__ import annotations

import json

DOI_PREFIXES = (
    "https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/",
)
BEARING_TERMS = (
    "bearing", "bearings", "rolling element", "outer race", "inner race",
    "ball bearing", "roller bearing", "rolling bearing",
)
FALSE_POSITIVE_TERMS = (
    "load-bearing", "load bearing", "bearing capacity", "bearing wall",
    "bearing pressure", "childbearing", "water-bearing", "bearing-only",
)


def version_status(work: dict) -> str:
    locations = [work.get("primary_location"), work.get("best_oa_location")]
    locations = [loc for loc in locations if isinstance(loc, dict)]
    for loc in locations:
        if loc.get("version") == "publishedVersion" or loc.get("is_published") is True:
            return "published"
    for loc in locations:
        if loc.get("version") == "acceptedVersion" or loc.get("is_accepted") is True:
            return "accepted"
    return "unknown"


def bare_doi(work: dict) -> str | None:
    raw = work.get("doi")
    if not raw:
        loc = work.get("primary_location") or {}
        raw = loc.get("doi") if isinstance(loc, dict) else None
    if not raw:
        return None
    raw = raw.strip()
    for prefix in DOI_PREFIXES:
        if raw.lower().startswith(prefix):
            raw = raw[len(prefix):]
            break
    return raw.strip() or None


def pick_title(work: dict) -> str:
    return (work.get("title") or work.get("display_name") or "").strip() or "Untitled"


def pick_journal(work: dict) -> tuple[str | None, str | None]:
    primary = work.get("primary_location") or {}
    best = work.get("best_oa_location") or {}
    for location in (primary, best):
        if not isinstance(location, dict):
            continue
        source = location.get("source") or {}
        if isinstance(source, dict) and source.get("display_name"):
            return source["display_name"], source.get("issn_l")
    raw_name = primary.get("raw_source_name") if isinstance(primary, dict) else None
    return raw_name or None, None


def pick_authors(work: dict) -> list[str]:
    names = []
    for authorship in work.get("authorships") or []:
        author = (authorship or {}).get("author") or {}
        name = author.get("display_name")
        if name and name.strip():
            names.append(name.strip())
    return names


def is_relevant(title: str) -> tuple[bool, str | None]:
    lowered = (title or "").lower()
    if any(term in lowered for term in FALSE_POSITIVE_TERMS):
        return False, "false_positive_phrase"
    if not any(term in lowered for term in BEARING_TERMS):
        return False, "no_bearing_term_in_title"
    return True, None


def normalize(work: dict, *, now: str, query_id: str) -> dict | None:
    work_id = (work.get("id") or "").rsplit("/", 1)[-1]
    if not work_id:
        return None

    title = pick_title(work)
    relevant, reason = is_relevant(title)
    journal, issn = pick_journal(work)
    pub_date = work.get("publication_date")
    year = work.get("publication_year") or (int(pub_date[:4]) if pub_date else None)
    retracted = bool(work.get("is_retracted"))
    if retracted:
        relevant, reason = False, "retracted"

    open_access = work.get("open_access") or {}
    return {
        "openalex_id": work_id,
        "doi": bare_doi(work),
        "title": title,
        "authors": json.dumps(pick_authors(work), ensure_ascii=False),
        "journal": journal,
        "journal_issn": issn,
        "publication_year": year,
        "publication_date": pub_date,
        "version_status": version_status(work),
        "cited_by_count": work.get("cited_by_count") or 0,
        "oa_status": open_access.get("oa_status") if isinstance(open_access, dict) else None,
        "is_retracted": 1 if retracted else 0,
        "found_by": query_id,
        "first_seen_at": now,
        "last_updated_at": now,
        "excluded": 0 if relevant else 1,
        "exclude_reason": reason,
    }
