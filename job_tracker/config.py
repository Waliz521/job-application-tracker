"""Configuration for Job Application Tracker."""

# Google Sheet: share as "Anyone with the link can view" for CSV export to work
SPREADSHEET_ID = "1cV6-vsbDZ8GAXDiLRQf--BaEzxXdcM5oWEqKLOqjVO8"
SHEET_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"
)

SHEET_COLUMNS = [
    "id",
    "company_name",
    "job_title",
    "location",
    "job_link",
    "source",
    "application_date",
    "status",
    "contact_info",
    "follow_up_date",
    "interview_dates",
    "application_notes",
    "salary_range",
    "notes",
    "days_since_applied",
]

LOCAL_CSV_PATH = "jobs_export.csv"
DB_PATH = "job_tracker.db"
