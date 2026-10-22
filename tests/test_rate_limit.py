import src.api.limits as limits
from tests.conftest import COMPLETION_TOKENS, EMBED_TOKENS, PROMPT_TOKENS, bearer

ASK = {"question": "What are the supply risks?", "ticker": "NVDA"}
TOKENS_PER_ASK = EMBED_TOKENS + PROMPT_TOKENS + COMPLETION_TOKENS


def test_hourly_limit(client, make_key):
    plaintext, _ = make_key(rph=3)
    for i in range(3):
        r = client.post("/ask", json=ASK, headers=bearer(plaintext))
        assert r.status_code == 200, (i, r.text)
    r = client.post("/ask", json=ASK, headers=bearer(plaintext))
    assert r.status_code == 429
    retry_after = r.headers["Retry-After"]
    assert retry_after.isdigit()
    assert 1 <= int(retry_after) <= 3600


def test_daily_token_budget(client, make_key):
    # Budget smaller than one request: the first succeeds, then the key is over.
    plaintext, _ = make_key(daily_tokens=TOKENS_PER_ASK - 1)
    assert client.post("/ask", json=ASK, headers=bearer(plaintext)).status_code == 200
    r = client.post("/ask", json=ASK, headers=bearer(plaintext))
    assert r.status_code == 429
    assert "daily token budget" in r.json()["error"]
    assert int(r.headers["Retry-After"]) >= 1


def test_global_cap_applies_to_other_keys(client, make_key, monkeypatch):
    monkeypatch.setattr(limits, "GLOBAL_DAILY_TOKENS", TOKENS_PER_ASK)
    first, _ = make_key(name="first")
    second, _ = make_key(name="second")
    assert client.post("/ask", json=ASK, headers=bearer(first)).status_code == 200
    r = client.post("/ask", json=ASK, headers=bearer(second))
    assert r.status_code == 429
    assert "global" in r.json()["error"]
    assert int(r.headers["Retry-After"]) >= 1
