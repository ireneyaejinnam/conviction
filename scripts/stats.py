"""
Print what's in the index and the diff cache.
Usage: python -m scripts.stats
"""

from collections import Counter

from src.config import CHROMA_DIR, DIFFS_DIR
from src.index.store import get_collection


def main():
    col = get_collection()
    metas = col.get(include=["metadatas"])["metadatas"]
    print(f"Chroma: {CHROMA_DIR}")
    print(f"Total chunks: {col.count()}")

    filings = Counter(
        (m.get("ticker", "?"), m.get("filing_type", "?"), m.get("filing_date", "?"))
        for m in metas
    )
    print(f"\nDistinct filings: {len(filings)}")
    for (ticker, filing_type, filing_date), n in sorted(filings.items()):
        print(f"  {ticker:6} {filing_type:5} {filing_date}  {n} chunks")

    files = sorted(DIFFS_DIR.glob("*.json")) if DIFFS_DIR.exists() else []
    print(f"\nCached diffs in {DIFFS_DIR}: {len(files)}")
    for f in files:
        print(f"  {f.name}  {f.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
