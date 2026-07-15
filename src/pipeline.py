from src.retrieve.search import search
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
    filters = build_filters(ticker=ticker, doc_type=doc_type)
    chunks = search(question, k=k, filters=filters)
    text = answer(question, chunks)
    return {"answer": text, "sources_used": chunks}