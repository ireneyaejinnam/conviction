"""
Vector store layer: embed chunks via OpenAI and persist them in Chroma.

Design notes:
  - One persistent Chroma collection ("filings") holds all chunks across
    all tickers and filing types. ticker / filing_type / filing_date /
    item are stored as filterable metadata.
  - Embedding is done explicitly here (not via Chroma's embedding_function)
    so we can batch, log progress, and keep the same model on the retrieval
    side without coupling Chroma to OpenAI.
  - upsert() is used so re-running ingestion replaces chunks at the same
    stable IDs rather than erroring on duplicates. This is what makes
    iteration on chunking/parsing fast.
"""

from __future__ import annotations

from pathlib import Path

import chromadb
from openai import OpenAI

from src.chunk.section_aware import Chunk


CHROMA_DIR = Path("data/chroma")
COLLECTION_NAME = "filings"

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536  # output dimension of text-embedding-3-small
EMBED_BATCH_SIZE = 100

_openai_client = None
_chroma_client = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI()
    return _openai_client


def _get_chroma() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _chroma_client


def get_collection():
    """Return the 'filings' collection, creating it if needed."""
    client = _get_chroma()
    # get_or_create handles both first run and subsequent runs.
    # We don't pass an embedding_function — we provide embeddings explicitly
    # at insert/query time, which keeps the store provider-agnostic.
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # cosine similarity for embeddings
    )


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts via OpenAI. Order of output matches input."""
    client = _get_openai()
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    # The API returns objects in input order, but sort by index to be safe.
    items = sorted(resp.data, key=lambda d: d.index)
    return [item.embedding for item in items]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed an arbitrary list of texts, batching as needed.
    Exposed because Block 8 (retrieve) will use it for query embedding too.
    """
    embeddings: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start:start + EMBED_BATCH_SIZE]
        embeddings.extend(_embed_batch(batch))
    return embeddings


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _chunk_id(meta):
    # Stable id. doc_type is included so filings & transcripts can never collide.
    # (doc_type doesn't exist until Wednesday; .get(...,'10-K') keeps this safe today.)
    return (
        f"{meta['ticker']}_{meta.get('doc_type', '10-K')}_"
        f"{meta.get('filing_date', 'na')}_{meta['item']}_{meta['chunk_idx']}"
    )

def embed_and_store(chunks, batch_size=100):
    """
    Embed all chunks via OpenAI and upsert them into the 'filings' collection.

    Uses upsert so re-running on the same filing replaces chunks at the same
    IDs instead of erroring on duplicates. This makes iterating on the
    parser/chunker fast.
    """
    col = get_collection()
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        texts = [c.text for c in batch]
        metas = [c.metadata for c in batch]
        ids = [_chunk_id(m) for m in metas]
        embeddings = _embed_batch(texts)
        col.upsert(                       # CHANGED: was col.add(...)
            documents=texts,
            embeddings=embeddings,
            metadatas=metas,
            ids=ids,
        )