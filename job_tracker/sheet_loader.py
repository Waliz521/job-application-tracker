"""Load job applications from Google Sheets (CSV export) or local CSV."""

import csv
import io
import urllib.request
from pathlib import Path

from job_tracker.config import SHEET_CSV_URL, SHEET_COLUMNS, LOCAL_CSV_PATH

HEADER_MAP = {
    "ID": "id",
    "Company Name": "company_name",
    "Job Title": "job_title",
    "Location": "location",
    "Job Link/URL": "job_link",
    "Source": "source",
    "Application Date": "application_date",
    "Status": "status",
    "Contact Name/Info": "contact_info",
    "Follow-up Date": "follow_up_date",
    "Interview Date(s)": "interview_dates",
    "Salary Range": "salary_range",
    "Notes": "notes",
    "Days Since Applied": "days_since_applied",
}


def _normalize_row(raw_headers: list[str], row: list[str]) -> dict:
    out = {col: "" for col in SHEET_COLUMNS}
    for i, raw in enumerate(raw_headers):
        h = raw.strip()
        key = HEADER_MAP.get(h)
        if key:
            out[key] = (row[i] if i < len(row) else "").strip()
        elif i == 11:
            out["application_notes"] = (row[i] if i < len(row) else "").strip()
    return out


def fetch_from_sheet_url() -> list[dict]:
    req = urllib.request.Request(SHEET_CSV_URL, headers={"User-Agent": "JobTracker/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        text = r.read().decode("utf-8", errors="replace")
    if not text.strip():
        return []
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    raw_headers = [h.strip().lstrip("\ufeff") for h in rows[0]]
    return [
        _normalize_row(raw_headers, row)
        for row in rows[1:]
        if any(cell.strip() for cell in row)
    ]


def load_from_local_csv(path: str | Path | None = None) -> list[dict]:
    path = path or Path(LOCAL_CSV_PATH)
    path = Path(path)
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        return []
    raw_headers = [h.strip().lstrip("\ufeff") for h in rows[0]]
    return [
        _normalize_row(raw_headers, row)
        for row in rows[1:]
        if any(cell.strip() for cell in row)
    ]


def load_jobs(use_local_fallback: bool = True) -> list[dict]:
    try:
        data = fetch_from_sheet_url()
        if data:
            return data
    except Exception:
        pass
    if use_local_fallback:
        data = load_from_local_csv()
        if data:
            return data
    return []
