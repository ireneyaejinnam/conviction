import json
import time
from pathlib import Path
from dotenv import load_dotenv
from src.config import WATCHLIST_PATH
from src.ingest.run import ingest_one
from src.index.store import get_collection

load_dotenv()

def load_watchlist(path=WATCHLIST_PATH):
    return json.loads(Path(path).read_text())["tickers"]

if __name__ == "__main__":
    tickers = load_watchlist()
    print(f"Ingesting {len(tickers)} tickers: {tickers}")
    for i, ticker in enumerate(tickers):
        try:
            n = ingest_one(ticker, "10-K")
            print(f"  {ticker}: {n} chunks ingested")
        except Exception as e:                       # one bad fetch shouldn't kill the loop
            print(f"  {ticker}: FAILED — {e}")
        if i < len(tickers) - 1:
            time.sleep(1)                            # be polite to EDGAR (avoid 429s)
    print(f"Done. Collection holds {get_collection().count()} chunks total.")