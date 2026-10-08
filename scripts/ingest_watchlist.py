import argparse
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from src.analyze.risk_diff import cached_diff_files, compute_risk_diff, save_risk_diff
from src.config import WATCHLIST_PATH
from src.ingest.run import ingest_one
from src.index.store import get_collection

load_dotenv()

def load_watchlist(path=WATCHLIST_PATH):
    return json.loads(Path(path).read_text())["tickers"]

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Ingest the watchlist and precompute risk diffs.")
    p.add_argument("--refresh-diffs", action="store_true",
                   help="Recompute risk diffs even if a cached diff exists")
    args = p.parse_args()

    tickers = load_watchlist()
    print(f"Ingesting {len(tickers)} tickers: {tickers}")
    for i, ticker in enumerate(tickers):
        try:
            n = ingest_one(ticker, "10-K")
            print(f"  {ticker}: {n} chunks ingested")
        except Exception as e:                       # one bad fetch shouldn't kill the loop
            print(f"  {ticker}: FAILED — {e}")

        existing = cached_diff_files(ticker)
        if existing and not args.refresh_diffs:
            print(f"  {ticker}: diff cached ({existing[0].name}), skipping")
        else:
            time.sleep(1)                            # be polite to EDGAR (avoid 429s)
            try:
                path = save_risk_diff(compute_risk_diff(ticker))
                print(f"  {ticker}: diff saved to {path.name}")
            except Exception as e:
                print(f"  {ticker}: diff FAILED — {e}")

        if i < len(tickers) - 1:
            time.sleep(1)
    print(f"Done. Collection holds {get_collection().count()} chunks total.")
