from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone

from . import config
from .db import connect, init_schema, upsert_paper
from .normalize import normalize
from .openalex import OpenAlexClient, OpenAlexError


def _run_started() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ"), now.date().isoformat()


def _query_params(query: dict, window: str, mode: str, watermark: str | None) -> dict:
    filters = [*config.BASE_FILTERS, f"from_publication_date:{window}"]
    if mode == "incremental" and watermark:
        filters.append(f"from_updated_date:{watermark}")
    return {
        "filter": ",".join(filters),
        "search.title_and_abstract": query["search"],
        "select": config.SELECT_FIELDS,
        "per_page": config.PER_PAGE,
    }


def fetch() -> int:
    started_at, run_date = _run_started()
    window = config.window_start()
    mode = config.SYNC_MODE
    if mode not in ("rescan", "incremental"):
        raise ValueError("SYNC_MODE 必须为 rescan 或 incremental")

    init_schema()
    client = OpenAlexClient()
    fetched = inserted = updated = excluded = 0
    seen: set[str] = set()
    successful_queries = 0
    failures: list[str] = []
    started = time.monotonic()

    with connect() as conn:
        total_before = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        row = conn.execute("SELECT value FROM sync_state WHERE key='last_successful_updated_date'").fetchone()
        watermark = row[0] if row else None
        try:
            for query in config.QUERIES:
                params = _query_params(query, window, mode, watermark)
                next_cursor: str | None = "*" if config.API_KEY else None
                page = 1
                query_ok = False
                for _ in range(config.MAX_PAGES_PER_QUERY):
                    if client.remaining is not None and client.remaining < config.MIN_REMAINING_CREDITS:
                        print(f"[budget] remaining={client.remaining} below threshold; stopping pagination")
                        break
                    page_params = dict(params)
                    if config.API_KEY:
                        if next_cursor is None:
                            break
                        page_params["cursor"] = next_cursor
                    else:
                        page_params["page"] = page

                    try:
                        payload = client.fetch_page(page_params)
                        results = payload.get("results") or []
                        meta = payload.get("meta") or {}
                        cost = meta.get("cost_usd", 0) or 0
                        total_count = meta.get("count", 0) or 0
                        print(
                            f"[query {query['id']}] page {page}/{config.MAX_PAGES_PER_QUERY} "
                            f"count={total_count} cost=${cost:.4f} remaining={client.remaining}"
                        )
                        query_ok = True
                        successful_queries += 1 if page == 1 else 0
                        for work in results:
                            fetched += 1
                            record = normalize(work, now=config.utc_now_iso(), query_id=query["id"])
                            if not record:
                                continue
                            excluded += int(record["excluded"] == 1)
                            exists = conn.execute(
                                "SELECT 1 FROM papers WHERE openalex_id=?", (record["openalex_id"],)
                            ).fetchone()
                            upsert_paper(conn, record)
                            if record["openalex_id"] not in seen:
                                seen.add(record["openalex_id"])
                                if exists:
                                    updated += 1
                                else:
                                    inserted += 1

                        if not results:
                            break
                        if config.API_KEY:
                            next_cursor = meta.get("next_cursor")
                            if not next_cursor:
                                break
                        elif page * config.PER_PAGE >= 10000:
                            break
                        page += 1
                        time.sleep(0.2)
                    except (OpenAlexError, ValueError, TypeError) as exc:
                        failures.append(f"{query['id']}: {exc}")
                        print(f"[query {query['id']}] failed: {exc}")
                        break

                if not query_ok and not any(failure.startswith(query["id"] + ":") for failure in failures):
                    failures.append(f"{query['id']}: stopped before first successful page")

            if successful_queries == 0:
                raise OpenAlexError("所有查询均失败；事务已回滚。 " + " | ".join(failures))

            if mode == "incremental":
                conn.execute(
                    "INSERT INTO sync_state(key, value) VALUES('last_successful_updated_date', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (run_date,),
                )
            finished_at = config.utc_now_iso()
            conn.execute(
                "INSERT INTO sync_state(key, value) VALUES('last_successful_run_at', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (finished_at,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        total_after = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]

    elapsed = time.monotonic() - started
    print(f"[{started_at}] mode={mode} window={window}..{run_date}")
    print(
        f"[summary] fetched={fetched} unique={len(seen)} inserted={inserted} updated={updated} "
        f"excluded={excluded} total={total_after} (before={total_before})"
    )
    print(f"[summary] remaining_credits={client.remaining} elapsed={elapsed:.1f}s")
    if failures:
        print("[partial] " + " | ".join(failures))
    return 0


def main() -> None:
    try:
        fetch()
    except Exception as exc:
        print(f"[fatal] {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
