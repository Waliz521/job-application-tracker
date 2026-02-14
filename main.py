#!/usr/bin/env python3
"""CLI entry point. Run: python main.py sync | list | add | update | show | open"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import argparse
import webbrowser

from job_tracker.config import SPREADSHEET_ID
from job_tracker.sheet_loader import load_jobs
from job_tracker.db import (
    init_db,
    sync_from_sheet,
    list_jobs as db_list_jobs,
    add_job,
    update_job,
    get_job_by_row_id,
)


def cmd_sync(args):
    jobs = load_jobs(use_local_fallback=True)
    if not jobs:
        print("No data loaded. Ensure the sheet is shared as 'Anyone with the link can view',")
        print("or download it as CSV and save as jobs_export.csv in this folder.")
        return 1
    n = sync_from_sheet(jobs)
    print(f"Synced {n} job(s) from sheet.")
    return 0


def cmd_list(args):
    init_db()
    jobs = db_list_jobs(
        status=args.status or None,
        company=args.company or None,
        limit=args.limit,
    )
    if not jobs:
        print("No jobs found. Run: python main.py sync")
        return 0
    for j in jobs:
        row_id = j.get("row_id", "")
        company = (j.get("company_name") or "").strip()
        title = (j.get("job_title") or "").strip()
        status = (j.get("status") or "").strip()
        date = (j.get("application_date") or "").strip()
        print(f"  [{row_id}] {company} — {title}  |  {status}  |  {date}")
    print(f"\nTotal: {len(jobs)}")
    return 0


def cmd_add(args):
    init_db()
    job = {
        "id": args.id or "",
        "company_name": args.company or "",
        "job_title": args.title or "",
        "location": args.location or "",
        "job_link": args.link or "",
        "source": args.source or "",
        "application_date": args.date or "",
        "status": args.status or "Applied",
        "contact_info": args.contact or "",
        "follow_up_date": args.follow_up or "",
        "interview_dates": "",
        "application_notes": args.notes or "",
        "salary_range": "",
        "notes": "",
        "days_since_applied": "",
    }
    add_job(job)
    print("Added job:", job.get("company_name"), "—", job.get("job_title"))
    return 0


def cmd_update(args):
    row_id = int(args.row_id)
    updates = {}
    if args.status is not None:
        updates["status"] = args.status
    if args.follow_up is not None:
        updates["follow_up_date"] = args.follow_up
    if args.notes is not None:
        updates["notes"] = args.notes
    if not updates:
        print("Provide at least one of: --status, --follow-up, --notes")
        return 1
    ok = update_job(row_id, updates)
    print("Updated." if ok else "Job not found.")
    return 0 if ok else 1


def cmd_show(args):
    row_id = int(args.row_id)
    j = get_job_by_row_id(row_id)
    if not j:
        print("Job not found.")
        return 1
    for k, v in j.items():
        if k == "row_id":
            continue
        if v:
            print(f"  {k}: {v}")
    return 0


def cmd_open_sheet(args):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
    webbrowser.open(url)
    return 0


def main():
    p = argparse.ArgumentParser(description="Job Application Tracker")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("sync", help="Sync from Google Sheet / local CSV into DB").set_defaults(func=cmd_sync)

    list_p = sub.add_parser("list", help="List jobs")
    list_p.add_argument("--status", "-s", help="Filter by status")
    list_p.add_argument("--company", "-c", help="Filter by company name (substring)")
    list_p.add_argument("--limit", "-n", type=int, help="Max number of jobs")
    list_p.set_defaults(func=cmd_list)

    add_p = sub.add_parser("add", help="Add a job")
    add_p.add_argument("--company", "-c", required=True, help="Company name")
    add_p.add_argument("--title", "-t", required=True, help="Job title")
    add_p.add_argument("--location", "-l", help="Location")
    add_p.add_argument("--link", help="Job URL")
    add_p.add_argument("--source", help="Source (e.g. LinkedIn)")
    add_p.add_argument("--date", "-d", help="Application date (YYYY-MM-DD)")
    add_p.add_argument("--status", default="Applied", help="Status")
    add_p.add_argument("--contact", help="Contact email/name")
    add_p.add_argument("--follow-up", help="Follow-up date")
    add_p.add_argument("--notes", "-n", help="Notes")
    add_p.add_argument("--id", help="Optional ID")
    add_p.set_defaults(func=cmd_add)

    up_p = sub.add_parser("update", help="Update a job by row_id")
    up_p.add_argument("row_id", type=int, help="row_id from list")
    up_p.add_argument("--status", "-s", help="New status")
    up_p.add_argument("--follow-up", help="Follow-up date")
    up_p.add_argument("--notes", "-n", help="Notes")
    up_p.set_defaults(func=cmd_update)

    show_p = sub.add_parser("show", help="Show full job details")
    show_p.add_argument("row_id", type=int, help="row_id from list")
    show_p.set_defaults(func=cmd_show)

    sub.add_parser("open", help="Open Google Sheet in browser").set_defaults(func=cmd_open_sheet)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
