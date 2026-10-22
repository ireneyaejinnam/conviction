"""
Shared fixtures. Nothing here touches the network or needs an OpenAI key:
the OpenAI client and the Chroma collection are replaced with fakes, and
each test gets its own empty app.db in a temporary DATA_DIR.
"""

import os
import tempfile
from types import SimpleNamespace

# Set before src.config is imported: it reads these at import time, and
# load_dotenv() doesn't override variables that are already set.
os.environ["CONVICTION_DATA_DIR"] = tempfile.mkdtemp(prefix="conviction-tests-")
os.environ["OPENAI_API_KEY"] = "sk-test-not-a-real-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import src.api.keys as keys  # noqa: E402
import src.api.limits as limits  # noqa: E402
import src.generate.answer as answer_mod  # noqa: E402
import src.index.store as store  # noqa: E402
import src.retrieve.search as search_mod  # noqa: E402
from src.api.main import app  # noqa: E402

EMBED_TOKENS = 7
PROMPT_TOKENS = 1200
COMPLETION_TOKENS = 150


class FakeOpenAI:
    """Stands in for openai.OpenAI: embeddings.create and chat.completions.create."""

    def __init__(self, *args, **kwargs):
        self.embeddings = SimpleNamespace(create=self._embed)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat))

    def _embed(self, model, input):
        return SimpleNamespace(
            data=[SimpleNamespace(index=i, embedding=[0.1] * 8) for i in range(len(input))],
            usage=SimpleNamespace(total_tokens=EMBED_TOKENS),
        )

    def _chat(self, model, messages, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Supply is concentrated [Source 1]."))],
            usage=SimpleNamespace(prompt_tokens=PROMPT_TOKENS, completion_tokens=COMPLETION_TOKENS),
        )


class FakeCollection:
    def query(self, query_embeddings, n_results, where=None):
        meta = {"ticker": "NVDA", "filing_type": "10-K", "filing_date": "2026-02-25",
                "item": "Item 1A", "item_title": "Risk Factors", "doc_type": "10-K", "chunk_idx": 0}
        return {"ids": [["c0"]], "documents": [["We depend on a few suppliers."]],
                "metadatas": [[meta]], "distances": [[0.21]]}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Fresh app.db per test, fake OpenAI and Chroma everywhere."""
    monkeypatch.setattr(keys, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(store, "_openai_client", FakeOpenAI())
    monkeypatch.setattr(answer_mod, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(search_mod, "get_collection", lambda: FakeCollection())
    monkeypatch.setattr(limits, "GLOBAL_DAILY_TOKENS", 1_000_000)
    return tmp_path


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def make_key():
    """Create a key and return (plaintext, row)."""
    def _make(name="test", rph=100, daily_tokens=200_000):
        plaintext = keys.create_key(name, rph, daily_tokens)
        return plaintext, keys.lookup(plaintext)
    return _make


def bearer(key: str) -> dict:
    return {"Authorization": f"Bearer {key}"}
