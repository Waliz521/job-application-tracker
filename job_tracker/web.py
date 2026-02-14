"""Web view: build HTML and run HTTP server for the job tracker."""

import html
import http.server
import os
import socketserver
from datetime import date, datetime

from job_tracker.db import init_db, list_jobs, sync_from_sheet
from job_tracker.sheet_loader import load_jobs

PORT = int(os.environ.get("PORT", 8000))
SYNC_ON_LOAD = os.environ.get("SYNC_ON_LOAD", "1").lower() in ("1", "true", "yes")


def _days_since_applied(app_date: str) -> str:
    """Return days since application date, or empty string if invalid/missing."""
    if not (app_date or app_date.strip()):
        return ""
    try:
        dt = datetime.strptime(app_date.strip()[:10], "%Y-%m-%d").date()
        return str((date.today() - dt).days)
    except (ValueError, TypeError):
        return ""


def build_html(jobs: list[dict]) -> str:
    def esc(s: str) -> str:
        return html.escape(str(s or "").strip())

    rows = []
    for j in jobs:
        company = esc(j.get("company_name"))
        title = esc(j.get("job_title"))
        location = esc(j.get("location"))
        status = esc(j.get("status"))
        date_val = esc(j.get("application_date"))
        link = (j.get("job_link") or "").strip()
        id_val = esc(j.get("id"))
        days = (j.get("days_since_applied") or "").strip() or _days_since_applied(j.get("application_date") or "")
        days_cell = esc(days) if days else "—"
        link_cell = f'<a href="{esc(link)}" target="_blank" rel="noopener">Link</a>' if link else "—"
        is_rejected = status.lower() == "rejected"
        row_class = ' class="rejected"' if is_rejected else ""
        rows.append(
            f"<tr{row_class}><td>{id_val}</td><td>{company}</td><td>{title}</td>"
            f"<td>{location}</td><td>{status}</td><td>{date_val}</td><td>{days_cell}</td><td>{link_cell}</td></tr>"
        )
    body = "\n".join(rows) if rows else "<tr><td colspan='8'>No jobs yet. Run: python main.py sync</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Job Application Tracker</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
      margin: 0;
      min-height: 100vh;
      background: linear-gradient(145deg, #0d1117 0%, #161b22 40%, #21262d 100%);
      color: #e6edf3;
      padding: clamp(0.75rem, 4vw, 2.5rem);
      font-size: clamp(14px, 2vw, 15px);
      line-height: 1.5;
    }}
    .wrap {{ max-width: 1000px; margin: 0 auto; width: 100%; }}
    h1 {{
      font-weight: 700;
      font-size: clamp(1.35rem, 4vw, 1.85rem);
      letter-spacing: -0.02em;
      color: #2dd4bf;
      margin: 0 0 1.25rem 0;
      text-shadow: 0 0 24px rgba(45, 212, 191, 0.3);
    }}
    .table-wrap {{
      background: rgba(22, 27, 34, 0.85);
      border-radius: 12px;
      overflow-x: auto;
      overflow-y: hidden;
      -webkit-overflow-scrolling: touch;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
      border: 1px solid rgba(45, 212, 191, 0.12);
    }}
    table {{
      width: 100%;
      min-width: 720px;
      border-collapse: collapse;
      font-weight: 500;
    }}
    th {{
      font-weight: 600;
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #2dd4bf;
      background: rgba(13, 17, 23, 0.95);
      padding: 0.75rem 0.6rem;
      text-align: left;
      border-bottom: 1px solid rgba(45, 212, 191, 0.25);
      white-space: nowrap;
    }}
    td {{
      padding: 0.75rem 0.6rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }}
    td:nth-child(1), td:nth-child(6), td:nth-child(7), td:nth-child(8) {{
      white-space: nowrap;
    }}
    th:nth-child(6) {{ min-width: 6rem; }}
    th:nth-child(7) {{ min-width: 5.5rem; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: rgba(45, 212, 191, 0.06); }}
    tr:nth-child(even) td {{ background: rgba(0, 0, 0, 0.15); }}
    tr:nth-child(even):hover td {{ background: rgba(45, 212, 191, 0.08); }}
    tr.rejected td {{
      background: rgba(180, 60, 60, 0.22) !important;
      color: rgba(255, 220, 220, 0.95);
    }}
    tr.rejected:hover td {{ background: rgba(180, 60, 60, 0.32) !important; }}
    a {{ color: #5eead4; text-decoration: none; font-weight: 500; }}
    a:hover {{ color: #99f6e4; text-decoration: underline; }}
    @media (max-width: 768px) {{
      body {{ padding: 0.75rem; }}
      .table-wrap {{ border-radius: 8px; }}
      th, td {{ padding: 0.6rem 0.5rem; font-size: 0.9rem; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Job Application Tracker</h1>
    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>Company</th><th>Job Title</th><th>Location</th><th>Status</th><th>Applied</th><th>Days Since Applied</th><th>Link</th></tr></thead>
        <tbody>{body}</tbody>
      </table>
    </div>
  </div>
</body>
</html>"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        init_db()
        if SYNC_ON_LOAD:
            try:
                sheet_data = load_jobs(use_local_fallback=True)
                if sheet_data:
                    sync_from_sheet(sheet_data)
            except Exception:
                pass
        jobs = list_jobs()
        html_bytes = build_html(jobs).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_bytes)))
        self.end_headers()
        self.wfile.write(html_bytes)

    def log_message(self, format, *args):
        pass


def run_server(open_browser: bool = True):
    init_db()
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    with socketserver.TCPServer((host, PORT), _Handler) as httpd:
        url = f"http://localhost:{PORT}" if host == "127.0.0.1" else f"http://0.0.0.0:{PORT}"
        print(f"Open in browser: {url}")
        if open_browser and host == "127.0.0.1":
            import webbrowser
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
