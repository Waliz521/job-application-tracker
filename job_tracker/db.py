"""SQLite storage for job applications. Mirrors Google Sheet columns."""

import sqlite3
from pathlib import Path

from job_tracker.config import DB_PATH, SHEET_COLUMNS

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT,
    company_name TEXT,
    job_title TEXT,
    location TEXT,
    job_link TEXT,
    source TEXT,
    application_date TEXT,
    status TEXT,
    contact_info TEXT,
    follow_up_date TEXT,
    interview_dates TEXT,
    application_notes TEXT,
    salary_range TEXT,
    notes TEXT,
    days_since_applied TEXT
);
CREATE INDEX IF NOT EXISTS idx_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_company ON jobs(company_name);
"""


def get_connection(path: str | Path | None = None):
    path = path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection | None = None):
    if conn is None:
        conn = get_connection()
        try:
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()
    else:
        conn.executescript(SCHEMA)
        conn.commit()


def row_to_dict(row: sqlite3.Row) -> dict:
    d = {k: (row[k] or "") for k in row.keys() if k != "row_id"}
    d["row_id"] = row["row_id"]
    return d


def insert_jobs(jobs: list[dict], conn: sqlite3.Connection | None = None) -> int:
    if not jobs:
        return 0
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    init_db(conn)
    placeholders = ", ".join(["?" for _ in SHEET_COLUMNS])
    columns = ", ".join(SHEET_COLUMNS)
    for j in jobs:
        values = [str(j.get(c, "") or "").strip() for c in SHEET_COLUMNS]
        conn.execute(
            f"INSERT INTO jobs ({columns}) VALUES ({placeholders})",
            values,
        )
    conn.commit()
    if own_conn:
        conn.close()
    return len(jobs)


def clear_jobs(conn: sqlite3.Connection | None = None) -> None:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    init_db(conn)
    conn.execute("DELETE FROM jobs")
    conn.commit()
    if own_conn:
        conn.close()


def sync_from_sheet(jobs: list[dict], conn: sqlite3.Connection | None = None) -> int:
    clear_jobs(conn=conn)
    return insert_jobs(jobs, conn=conn)


def _build_where(status: str | None, company: str | None, limit: int | None) -> tuple[str, list]:
    where, params = [], []
    if status:
        where.append("status = ?")
        params.append(status)
    if company:
        where.append("company_name LIKE ?")
        params.append(f"%{company}%")
    sql = "SELECT * FROM jobs"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY CAST(id AS INTEGER) ASC, row_id ASC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return sql, params


def list_jobs(
    status: str | None = None,
    company: str | None = None,
    limit: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    sql, params = _build_where(status, company, limit)
    cur = conn.execute(sql, params)
    out = [row_to_dict(r) for r in cur.fetchall()]
    if own_conn:
        conn.close()
    return out


def add_job(job: dict, conn: sqlite3.Connection | None = None) -> None:
    insert_jobs([job], conn=conn)


def update_job(row_id: int, updates: dict, conn: sqlite3.Connection | None = None) -> bool:
    if not updates:
        return False
    allowed = set(SHEET_COLUMNS)
    sets = []
    params = []
    for k, v in updates.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            params.append(v)
    if not sets:
        return False
    params.append(row_id)
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    cur = conn.execute(
        f"UPDATE jobs SET {', '.join(sets)} WHERE row_id = ?",
        params,
    )
    conn.commit()
    ok = cur.rowcount > 0
    if own_conn:
        conn.close()
    return ok


def get_job_by_row_id(row_id: int, conn: sqlite3.Connection | None = None) -> dict | None:
    if conn is None:
        conn = get_connection()
        try:
            cur = conn.execute("SELECT * FROM jobs WHERE row_id = ?", (row_id,))
            row = cur.fetchone()
            return row_to_dict(row) if row else None
        finally:
            conn.close()
    cur = conn.execute("SELECT * FROM jobs WHERE row_id = ?", (row_id,))
    row = cur.fetchone()
    return row_to_dict(row) if row else None
