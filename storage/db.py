import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    url TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    pub_date TEXT NOT NULL,
    category TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_url TEXT NOT NULL REFERENCES reports(url),
    name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    mom_change REAL,
    yoy_change REAL,
    UNIQUE(report_url, name)
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_url TEXT NOT NULL,
    kind TEXT NOT NULL,
    content_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(report_url, kind)
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def report_exists(conn: sqlite3.Connection, url: str) -> bool:
    row = conn.execute("SELECT 1 FROM reports WHERE url = ?", (url,)).fetchone()
    return row is not None


def insert_report(conn: sqlite3.Connection, report) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO reports (url, title, pub_date, category, raw_text) "
        "VALUES (?, ?, ?, ?, ?)",
        (report.url, report.title, report.pub_date.isoformat(), report.category, report.raw_text),
    )
    conn.commit()


def insert_indicator(conn: sqlite3.Connection, indicator) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO indicators (report_url, name, value, unit, mom_change, yoy_change) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            indicator.report_url,
            indicator.name,
            indicator.value,
            indicator.unit,
            indicator.mom_change,
            indicator.yoy_change,
        ),
    )
    conn.commit()


def analysis_exists(conn: sqlite3.Connection, report_url: str, kind: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM analyses WHERE report_url = ? AND kind = ?", (report_url, kind)
    ).fetchone()
    return row is not None


def insert_analysis(conn: sqlite3.Connection, analysis) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO analyses (report_url, kind, content_json) VALUES (?, ?, ?)",
        (analysis.report_url, analysis.kind, analysis.content_json),
    )
    conn.commit()
