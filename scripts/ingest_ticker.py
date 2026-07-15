import sys
from dotenv import load_dotenv
from src.ingest.run import ingest_one
from src.index.store import get_collection

load_dotenv()

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    n = ingest_one(ticker, "10-K")
    print(f"{ticker}: {n} chunks ingested. Collection now holds {get_collection().count()} total.")