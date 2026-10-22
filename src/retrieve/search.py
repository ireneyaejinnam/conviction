"""
Retrieval: embed a query and return the most similar chunks from Chroma.

Reuses the embedding function from src.index.store so the same model is
used for indexing and querying — a hard requirement for vector search to
work correctly.
"""

from __future__ import annotations

import time

from src.index.store import embed_query, get_collection


def search(
    query: str,
    k: int = 8,
    filters: dict | None = None,
) -> list[dict]:
    """
    Embed `query` and return the top-k most similar chunks.

    Args:
        query: natural-language question.
        k: number of chunks to return.
        filters: optional Chroma `where` clause for metadata filtering.
            Examples:
              {"ticker": "NVDA"}
              {"item": "Item 1A"}
              {"ticker": {"$in": ["NVDA", "AMD"]}}

    Returns:
        List of dicts, ordered from most to least similar, each with:
          - text: the chunk's text
          - metadata: the chunk's metadata dict
          - distance: cosine distance (lower = more similar; 0 = identical)
    """
    return search_with_usage(query, k, filters)[0]


def search_with_usage(
    query: str,
    k: int = 8,
    filters: dict | None = None,
) -> tuple[list[dict], dict]:
    """
    Same as search(), plus an info dict: embedding_tokens (as reported by
    OpenAI), embed_ms and retrieve_ms.
    """
    if not query.strip():
        raise ValueError("search() called with empty query")

    # Embed the query with the same model used at indexing time.
    t0 = time.perf_counter()
    query_embedding, embed_tokens = embed_query(query)
    t1 = time.perf_counter()

    collection = get_collection()

    raw = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        where=filters,
    )
    info = {"embedding_tokens": embed_tokens,
            "embed_ms": (t1 - t0) * 1000,
            "retrieve_ms": (time.perf_counter() - t1) * 1000}

    # Chroma returns each field as a list-of-lists (outer list per query;
    # we passed one query, so we always read index [0]).
    if not raw["ids"] or not raw["ids"][0]:
        return [], info

    results: list[dict] = []
    for text, metadata, distance in zip(
        raw["documents"][0],
        raw["metadatas"][0],
        raw["distances"][0],
    ):
        results.append({
            "text": text,
            "metadata": metadata,
            "distance": distance,
        })

    return results, info
