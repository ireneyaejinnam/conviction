from src.retrieve.search import search_with_usage
from src.generate.answer import answer


def build_filters(ticker=None, doc_type=None):
    """Build a Chroma `where` dict. Returns None when there's no filter."""
    clauses = []
    if ticker:
        clauses.append({"ticker": ticker.upper().strip()})
    if doc_type:
        clauses.append({"doc_type": doc_type})
    if not clauses:
        return None                       # Chroma: None means "no filter"
    if len(clauses) == 1:
        return clauses[0]                 # single equality: {"ticker": "NVDA"}
    return {"$and": clauses}              # 2+ conditions MUST be wrapped in $and


def ask(question, k=8, ticker=None, doc_type=None):
    question = question.strip() or None
    if not question:
        return {"answer": "Please provide a question.", "sources_used": [], "ok": False}

    if len(question) > 1000:
        return {"answer": "Question too long - try under 1000 chars.", "sources_used": [], "ok": False}

    filters = build_filters(ticker, doc_type)

    try:
        chunks, embed_tokens = search_with_usage(question, k=k, filters=filters)
    except Exception as e:
        return {"answer": f"Retrieval failed: {type(e).__name__}. "
                          f"Is the Chroma store built? Try `python -m scripts.ingest_watchlist`.",
                "sources_used": [], "ok": False}

    if not chunks:
        return {"answer": "No results found.", "sources_used": [], "ok": False}

    try:
        text, usage = answer(question, chunks)
    except Exception as e:
        return {"answer": f"Generation failed: {type(e).__name__}. "
                          f"Check your OpenAI API key and rate limits.",
                "sources_used": chunks, "ok": False}

    usage["embedding_tokens"] = embed_tokens
    return {"answer": text, "sources_used": chunks, "ok": True, "usage": usage}
