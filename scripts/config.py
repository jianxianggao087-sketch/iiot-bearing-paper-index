from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_ENV_FILE = ROOT / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _name, _value = _line.split("=", 1)
            os.environ.setdefault(_name.strip(), _value.strip().strip("\"'"))

DB_PATH = ROOT / "data" / "papers.db"
PAPERS_JSON = ROOT / "src" / "data" / "papers.json"
META_JSON = ROOT / "src" / "data" / "meta.json"

API_BASE = "https://api.openalex.org/works"
API_KEY = os.getenv("OPENALEX_API_KEY", "").strip()
MAILTO = os.getenv("OPENALEX_MAILTO", "").strip()

PER_PAGE = 100
MAX_PAGES_PER_QUERY = int(os.getenv("MAX_PAGES_PER_QUERY", "8"))
DISPLAY_YEARS = int(os.getenv("DISPLAY_YEARS", "5"))
MIN_REMAINING_CREDITS = int(os.getenv("MIN_REMAINING_CREDITS", "50"))
SYNC_MODE = os.getenv("SYNC_MODE", "rescan").strip().lower()

REQUEST_TIMEOUT = 30
MAX_RETRIES = 4

SELECT_FIELDS = ",".join([
    "id", "doi", "title", "authorships", "primary_location", "best_oa_location",
    "publication_year", "publication_date", "cited_by_count", "type", "open_access",
    "is_retracted",
])

BASE_FILTERS = [
    "type:article",
    "has_oa_accepted_or_published_version:true",
    "primary_location.source.type:journal",
]

QUERIES = [
    {
        "id": "bearing-iiot-core",
        "search": (
            '("bearing" OR "bearings" OR "rolling element bearing" OR "ball bearing" '
            'OR "roller bearing" OR "rolling bearing") '
            'AND ("industrial internet of things" OR "IIoT" OR "edge computing" '
            'OR "edge intelligence" OR "digital twin" OR "industry 4.0" '
            'OR "cloud-edge" OR "condition monitoring network") '
            'AND ("fault diagnosis" OR "fault detection" OR "fault identification" '
            'OR "condition monitoring" OR "prognostics" OR "remaining useful life")'
        ),
    },
    {
        "id": "bearing-intelligent-diagnosis",
        "search": (
            '("bearing fault" OR "bearing faults" OR "rolling bearing fault" '
            'OR "rolling element bearing fault") '
            'AND ("deep learning" OR "convolutional neural network" OR "transfer learning" '
            'OR "graph neural network" OR "transformer" OR "digital twin" '
            'OR "edge deployment" OR "lightweight model")'
        ),
    },
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def window_start(today: date | None = None) -> str:
    """Return the lower bound of the rolling display window."""
    today = today or date.today()
    try:
        start = today.replace(year=today.year - DISPLAY_YEARS)
    except ValueError:
        start = today.replace(year=today.year - DISPLAY_YEARS, day=28)
    return start.isoformat()
