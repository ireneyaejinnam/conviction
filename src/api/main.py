"""
HTTP API over the pipeline. Every endpoint except /health needs
"Authorization: Bearer <key>" with a key from scripts/create_key.py.

Run: uvicorn src.api.main:app --port 8000
"""

from __future__ import annotations

import json

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.analyze.risk_diff import load_risk_diff
from src.api.keys import lookup
from src.config import WATCHLIST_PATH
from src.generate.refusal import is_refusal
from src.index.store import _chunk_id
from src.pipeline import ask

app = FastAPI(title="Conviction API")


@app.exception_handler(HTTPException)
def http_error(request: Request, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code, headers=exc.headers)


def require_key(authorization: str | None = Header(default=None)) -> dict:
    scheme, _, key = (authorization or "").partition(" ")
    row = lookup(key.strip()) if scheme.lower() == "bearer" and key.strip() else None
    if row is None:
        raise HTTPException(401, "invalid or missing API key", headers={"WWW-Authenticate": "Bearer"})
    return row


def watchlist() -> list[str]:
    return json.loads(WATCHLIST_PATH.read_text())["tickers"]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    ticker: str | None = None
    k: int = Field(default=8, ge=1, le=12)


class Source(BaseModel):
    n: int
    ticker: str
    item: str
    item_title: str
    filing_date: str
    chunk_id: str
    text: str


class AskResponse(BaseModel):
    answer: str
    refused: bool
    sources: list[Source]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tickers")
def tickers(key: dict = Depends(require_key)):
    return {"tickers": watchlist()}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(body: AskRequest, key: dict = Depends(require_key)):
    ticker = body.ticker.upper().strip() if body.ticker else None
    if ticker and ticker not in watchlist():
        raise HTTPException(422, f"unknown ticker {ticker!r}; see GET /tickers")

    res = ask(body.question, k=body.k, ticker=ticker)
    if not res["ok"]:
        raise HTTPException(502, res["answer"])

    sources = []
    for n, c in enumerate(res["sources_used"], 1):
        m = c["metadata"]
        sources.append(Source(n=n, ticker=m["ticker"], item=m["item"], item_title=m["item_title"],
                              filing_date=m.get("filing_date", "n/a"), chunk_id=_chunk_id(m),
                              text=c["text"]))
    return AskResponse(answer=res["answer"], refused=is_refusal(res["answer"]), sources=sources)


@app.get("/risk-diff/{ticker}")
def risk_diff(ticker: str, key: dict = Depends(require_key)):
    d = load_risk_diff(ticker)
    if d is None:
        raise HTTPException(404, f"no cached risk diff for {ticker.upper()}; "
                                 f"run python -m scripts.ingest_watchlist to compute it")
    return d
