from __future__ import annotations

import json
from collections import Counter

from . import config
from .db import connect, init_schema, visible_papers


def export() -> None:
    init_schema()
    generated_at = config.utc_now_iso()
    start = config.window_start()
    end = generated_at[:10]
    with connect() as conn:
        rows = visible_papers(conn, start)
        authors_list = []
        papers = []
        year_counts: Counter[int] = Counter()
        journal_counts: Counter[str] = Counter()
        for row in rows:
            authors = json.loads(row["authors"] or "[]")
            year = row["publication_year"]
            journal = row["journal"]
            if year is not None:
                year_counts[int(year)] += 1
            if journal:
                journal_counts[journal] += 1
            doi = row["doi"]
            papers.append({
                "id": row["openalex_id"],
                "doi": doi,
                "title": row["title"],
                "authors": authors,
                "authorCount": len(authors),
                "journal": journal,
                "journalIssn": row["journal_issn"],
                "year": year,
                "date": row["publication_date"],
                "versionStatus": row["version_status"],
                "citedBy": row["cited_by_count"],
                "oaStatus": row["oa_status"],
                "url": f"https://doi.org/{doi}" if doi else None,
            })

    papers.sort(key=lambda paper: (paper["date"] or "", paper["citedBy"] or 0), reverse=True)
    years = [{"year": year, "count": year_counts[year]} for year in sorted(year_counts, reverse=True)]
    journals = [
        {"name": name, "count": count}
        for name, count in sorted(journal_counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= 2
    ]
    total = len(papers)
    with connect() as conn:
        row = conn.execute("SELECT value FROM sync_state WHERE key='last_successful_run_at'").fetchone()
        last_successful = row[0] if row else None

    papers_data = {
        "generatedAt": generated_at,
        "windowStart": start,
        "total": total,
        "papers": papers,
    }
    meta_data = {
        "generatedAt": generated_at,
        "total": total,
        "windowStart": start,
        "windowEnd": end,
        "lastSuccessfulRunAt": last_successful,
        "years": years,
        "journals": journals,
    }
    for path, data in ((config.PAPERS_JSON, papers_data), (config.META_JSON, meta_data)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"导出完成：papers={total} window={start}..{end} generatedAt={generated_at}")


def main() -> None:
    export()


if __name__ == "__main__":
    main()
