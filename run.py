import argparse
import json
import time

import httpx

from analyzer.agent import analyze_cross, analyze_single
from scraper.list_page import iter_new_urls
from scraper.detail_page import fetch_detail, HEADERS
from extractor.indicators import extract_indicators
from models import Analysis
from storage.db import (
    analysis_exists,
    get_connection,
    insert_analysis,
    insert_indicator,
    insert_report,
    report_exists,
)


def fetch_new(max_pages: int = 20, limit: int | None = None) -> int:
    conn = get_connection()
    known_urls = {row["url"] for row in conn.execute("SELECT url FROM reports")}

    count = 0
    with httpx.Client(follow_redirects=True) as client:
        for url in iter_new_urls(known_urls, max_pages=max_pages):
            if report_exists(conn, url):
                continue
            report = fetch_detail(url, client)
            if report is None:
                print(f"[skip] failed to parse {url}")
                continue
            insert_report(conn, report)
            print(f"[ok] {report.pub_date.date()} {report.category:>4} {report.title}")
            count += 1
            time.sleep(1.5)
            if limit and count >= limit:
                break
    conn.close()
    return count


def extract_all() -> int:
    conn = get_connection()
    rows = conn.execute("SELECT url, raw_text FROM reports").fetchall()
    total = 0
    for row in rows:
        indicators = extract_indicators(row["url"], row["raw_text"])
        for indicator in indicators:
            insert_indicator(conn, indicator)
        total += len(indicators)
    conn.close()
    return total


def analyze_new_singles(limit: int | None = None) -> int:
    conn = get_connection()
    rows = conn.execute("SELECT url, title, pub_date, category, raw_text FROM reports").fetchall()
    count = 0
    for row in rows:
        if analysis_exists(conn, row["url"], "single"):
            continue
        output = analyze_single(row["title"], row["pub_date"], row["category"], row["raw_text"])
        insert_analysis(conn, Analysis(row["url"], "single", json.dumps(output, ensure_ascii=False)))
        print(f"[analyzed] {row['pub_date'][:10]} {row['title']}")
        count += 1
        if limit and count >= limit:
            break
    conn.close()
    return count


def analyze_month_cross(month: str, force: bool = False) -> bool:
    conn = get_connection()
    cross_key = f"cross:{month}"
    if not force and analysis_exists(conn, cross_key, "cross"):
        conn.close()
        return False

    reports = [
        dict(r)
        for r in conn.execute(
            "SELECT title, pub_date, category, raw_text FROM reports "
            "WHERE substr(pub_date, 1, 7) = ? ORDER BY pub_date",
            (month,),
        ).fetchall()
    ]
    if not reports:
        conn.close()
        return False

    indicators = [
        dict(r)
        for r in conn.execute(
            """SELECT i.name, i.value, i.unit, substr(r.pub_date, 1, 10) as pub_date
               FROM indicators i JOIN reports r ON i.report_url = r.url
               WHERE substr(r.pub_date, 1, 7) <= ?
               ORDER BY r.pub_date DESC LIMIT 300""",
            (month,),
        ).fetchall()
    ]

    output = analyze_cross(month, reports, indicators)
    insert_analysis(conn, Analysis(cross_key, "cross", json.dumps(output, ensure_ascii=False)))
    conn.close()
    return True


def latest_month() -> str | None:
    conn = get_connection()
    row = conn.execute("SELECT MAX(substr(pub_date, 1, 7)) as m FROM reports").fetchone()
    conn.close()
    return row["m"] if row else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-only", action="store_true")
    parser.add_argument("--extract", action="store_true", help="run indicator extraction over stored reports")
    parser.add_argument("--analyze", action="store_true", help="run single-report analysis over unanalyzed reports")
    parser.add_argument("--analyze-cross", action="store_true", help="run cross-report synthesis for the latest month")
    parser.add_argument("--limit", type=int, default=None, help="cap number of new reports fetched/analyzed")
    parser.add_argument("--max-pages", type=int, default=20)
    args = parser.parse_args()

    if args.fetch_only:
        n = fetch_new(max_pages=args.max_pages, limit=args.limit)
        print(f"\nFetched {n} new reports.")

    if args.extract:
        n = extract_all()
        print(f"\nExtracted {n} indicators.")

    if args.analyze:
        n = analyze_new_singles(limit=args.limit)
        print(f"\nAnalyzed {n} reports.")

    if args.analyze_cross:
        month = latest_month()
        if month is None:
            print("\nNo reports in db, skipping cross analysis.")
        else:
            done = analyze_month_cross(month, force=True)
            print(f"\nCross analysis for {month}: {'done' if done else 'skipped'}.")
