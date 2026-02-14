"""Vercel serverless handler: loads jobs from Google Sheet and returns HTML."""

import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Ensure project root is on path when Vercel runs from api/
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from job_tracker.sheet_loader import load_jobs
from job_tracker.web import build_html


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        jobs = load_jobs(use_local_fallback=False)
        try:
            jobs = sorted(jobs, key=lambda j: int(j.get("id") or 0))
        except (ValueError, TypeError):
            pass
        html = build_html(jobs)
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass
