"""Web server entry point. Run: python serve.py"""

import sys
from pathlib import Path

# Ensure project root is on path for job_tracker package
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from job_tracker.web import run_server

if __name__ == "__main__":
    run_server(open_browser=True)
