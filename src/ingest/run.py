"""
Reusable ingest entry points: one filing → chunks in Chroma.
"""
from src.ingest.edgar import fetch_filing
from src.ingest.parser import parse_filing
from src.chunk.section_aware import chunk_filing
from src.index.store import embed_and_store


def ingest_one(ticker: str, filing_type: str = "10-K") -> int:
    # Fetch → parse → chunk → embed+store ONE filing. Returns chunk count.
    ticker = ticker.upper().strip()
    path = fetch_filing(ticker, filing_type)
    sections = parse_filing(path, ticker)
    chunks = chunk_filing(sections)
    embed_and_store(chunks)
    return len(chunks)