import httpx

import src.api.client as api_client


def _capture(monkeypatch):
    seen = {}

    def fake_request(method, url, headers=None, json=None, timeout=None):
        seen["headers"] = headers
        return httpx.Response(200, json={"ok": True}, headers={"X-Request-ID": "rid"})

    monkeypatch.setattr(api_client.httpx, "request", fake_request)
    return seen


def test_demo_key_used_without_user_key(monkeypatch):
    monkeypatch.setenv("DEMO_API_KEY", "cv_demo")
    seen = _capture(monkeypatch)
    for user_key in (None, "", "   "):
        assert api_client.call("GET", "/tickers", user_key=user_key).ok
        assert seen["headers"] == {"Authorization": "Bearer cv_demo"}


def test_user_key_overrides_demo_key(monkeypatch):
    monkeypatch.setenv("DEMO_API_KEY", "cv_demo")
    seen = _capture(monkeypatch)
    assert api_client.call("GET", "/tickers", user_key=" cv_mine ").ok
    assert seen["headers"] == {"Authorization": "Bearer cv_mine"}


def test_no_header_when_no_key_at_all(monkeypatch):
    monkeypatch.delenv("DEMO_API_KEY", raising=False)
    seen = _capture(monkeypatch)
    api_client.call("GET", "/tickers")
    assert seen["headers"] == {}
