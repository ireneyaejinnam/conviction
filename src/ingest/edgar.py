"""
EDGAR filing downloader that wraps sec-edgar-downloader library
to fetch SEC filings for a certain ticker then return path to the
most recent filing's document.
"""

from __future__ import annotations
import os
from pathlib import Path
from sec_edgar_downloader import Downloader

from src.config import FILINGS_DIR

def parse_user_agent(var_str: str):
    """
    parse EDGAR_USER_AGENT env var to a tuple to pass
    into SEC (required id/name and email).
    """

    if not var_str or not var_str.strip():
        raise RuntimeError("EDGAR_USER_AGENT not set.")
    
    vars = var_str.strip().rsplit(maxsplit=1)

    if len(vars) != 2 or "@" not in vars[1]:
        raise RuntimeError("Invalid EDGAR_USER_AGENT.")
    
    return vars[0], vars[1]

def fetch_filing(
    ticker: str,
    filing_type: str = "10-K",
    limit: int = 1,
    filings_dir: Path | None = None,
):
    """
    Download the most recent filing by type given a ticker
    then return the path to the document.
    """
    
    ticker = ticker.upper().strip()
    filings_dir = filings_dir or FILINGS_DIR
    filings_dir.mkdir(parents=True, exist_ok=True)

    name, email = parse_user_agent(os.environ.get("EDGAR_USER_AGENT",""))

    downloaded = Downloader(name, email, str(filings_dir))

    num_downloaded = downloaded.get(filing_type, ticker,
                                    limit=limit,
                                    download_details=False)
    
    if num_downloaded == 0:
        raise FileNotFoundError("Failed to find filings.")
    
    root_dir = filings_dir / "sec-edgar-filings" / ticker / filing_type

    if not root_dir.exists():
        raise FileNotFoundError("Failed to find expected directory.")
    
    accession_dirs = sorted((d for d in root_dir.iterdir() if d.is_dir()), reverse=True)

    if not accession_dirs:
        raise FileNotFoundError("Download reported success but no filing directories exist.")

    latest_dir = accession_dirs[0]
    submission_file = latest_dir / "full-submission.txt"

    if not submission_file.exists():
        txt_files = list(latest_dir.glob("*.txt"))
        if not txt_files:
            raise FileNotFoundError("No submission file found.")
        submission_file = txt_files[0]

    return submission_file

def _user_agent():
    # .env format: EDGAR_USER_AGENT=Yaejin Nam your.email@domain.com
    ua = os.environ.get("EDGAR_USER_AGENT", "")
    parts = ua.rsplit(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]              # (company/name, email)
    return "Conviction Research", "research@example.com"


def fetch_recent_filings(ticker, filing_type="10-K", limit=2, dest=FILINGS_DIR):
    """Download the `limit` most recent filings; return list of primary-doc paths."""
    ticker = ticker.upper().strip()
    name, email = _user_agent()
    dl = Downloader(name, email, str(dest))
    dl.get(filing_type, ticker, limit=limit, download_details=True)

    base = Path(dest) / "sec-edgar-filings" / ticker / filing_type
    paths = []
    for accession_dir in sorted(base.iterdir()):
        if not accession_dir.is_dir():
            continue
        primary = accession_dir / "primary-document.html"   # sec-edgar-downloader v5 convention
        if primary.exists():
            paths.append(str(primary))
        else:
            fs = accession_dir / "full-submission.txt"       # fallback
            if fs.exists():
                paths.append(str(fs))
    return paths