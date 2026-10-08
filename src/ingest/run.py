"""
Reusable ingest entry points: one filing → chunks in Chroma.
"""
from src.ingest.edgar import fetch_filings
from src.ingest.parser import parse_filing
from src.chunk.section_aware import chunk_filing
from src.index.store import _chunk_id, embed_and_store, remove_stale_chunks


def ingest_one(ticker: str, filing_type: str = "10-K") -> int:
    # Fetch → parse → chunk → embed+store ONE filing, then drop this ticker's
    # chunks from older filings so the index holds only the latest one.
    # Returns chunk count.
    ticker = ticker.upper().strip()
    path = fetch_filings(ticker, filing_type, count=1)[0]
    sections = parse_filing(path, ticker)
    chunks = chunk_filing(sections)
    embed_and_store(chunks)
    remove_stale_chunks(ticker, filing_type, {_chunk_id(c.metadata) for c in chunks})
    return len(chunks)