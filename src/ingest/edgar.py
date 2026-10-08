"""
EDGAR filing downloader that wraps sec-edgar-downloader library
to fetch SEC filings for a ticker and return paths to the most
recent filings' documents.
"""

from __future__ import annotations
import os
from pathlib import Path
from sec_edgar_downloader import Downloader

from src.config import FILINGS_DIR
from src.ingest.parser import _extract_filing_date

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

def _filed_date(submission: Path) -> str:
    # The SGML header sits in the first few KB; no need to read the whole file.
    with submission.open(encoding="utf-8", errors="replace") as f:
        return _extract_filing_date(f.read(4096))


def fetch_filings(
    ticker: str,
    filing_type: str = "10-K",
    count: int = 1,
    filings_dir: Path | None = None,
) -> list[Path]:
    """
    Download the `count` most recent filings of a type for a ticker and
    return their full-submission.txt paths, newest first.

    full-submission.txt is used rather than primary-document.html: both
    parse identically for every watchlist ticker, but the submission file
    carries the SGML header (filing date) itself and doesn't require
    download_details.
    """

    ticker = ticker.upper().strip()
    filings_dir = filings_dir or FILINGS_DIR
    filings_dir.mkdir(parents=True, exist_ok=True)

    name, email = parse_user_agent(os.environ.get("EDGAR_USER_AGENT", ""))

    downloader = Downloader(name, email, str(filings_dir))
    num_downloaded = downloader.get(filing_type, ticker,
                                    limit=count,
                                    download_details=False)

    if num_downloaded < count:
        raise FileNotFoundError(
            f"Expected {count} {filing_type} filings for {ticker}; EDGAR returned {num_downloaded}."
        )

    root_dir = filings_dir / "sec-edgar-filings" / ticker / filing_type
    if not root_dir.exists():
        raise FileNotFoundError("Failed to find expected directory.")

    submissions = [d / "full-submission.txt" for d in root_dir.iterdir()
                   if (d / "full-submission.txt").exists()]

    # Sort by the filed date in the header, not the accession number: the
    # accession prefix is the submitting agent's CIK, which can change by year.
    submissions.sort(key=_filed_date, reverse=True)

    if len(submissions) < count:
        raise FileNotFoundError(
            f"Download reported success but only {len(submissions)} submission files exist."
        )

    return submissions[:count]
