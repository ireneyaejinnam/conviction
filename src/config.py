"""
Filesystem locations, anchored to the repo root rather than the working
directory. DATA_DIR and CHROMA_DIR can be overridden with the
CONVICTION_DATA_DIR and CHROMA_DIR environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

# Load .env here so overrides in it apply before the paths below are computed.
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.environ.get("CONVICTION_DATA_DIR") or ROOT / "data")
CHROMA_DIR = Path(os.environ.get("CHROMA_DIR") or DATA_DIR / "chroma")
FILINGS_DIR = DATA_DIR / "filings"
DIFFS_DIR = DATA_DIR / "diffs"
EVAL_DIR = DATA_DIR / "eval"
WATCHLIST_PATH = DATA_DIR / "watchlist.json"
