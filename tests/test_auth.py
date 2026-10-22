import src.api.keys as keys
from tests.conftest import bearer


def test_no_header_401(client):
    assert client.get("/tickers").status_code == 401


def test_malformed_header_401(client, make_key):
    plaintext, _ = make_key()
    for header in [plaintext, f"Basic {plaintext}", "Bearer", "Bearer   "]:
        r = client.get("/tickers", headers={"Authorization": header})
        assert r.status_code == 401, header


def test_unknown_key_401(client, make_key):
    make_key()
    assert client.get("/tickers", headers=bearer("cv_not-a-real-key")).status_code == 401


def test_revoked_key_401(client, make_key):
    plaintext, _ = make_key(name="soon-revoked")
    assert client.get("/tickers", headers=bearer(plaintext)).status_code == 200
    assert keys.revoke("soon-revoked")
    assert client.get("/tickers", headers=bearer(plaintext)).status_code == 401


def test_valid_key_200(client, make_key):
    plaintext, _ = make_key()
    r = client.get("/tickers", headers=bearer(plaintext))
    assert r.status_code == 200
    assert "tickers" in r.json()


def test_health_needs_no_key(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_plaintext_key_not_stored(make_key):
    plaintext, _ = make_key()
    with keys.connect() as conn:
        rows = conn.execute("SELECT * FROM api_keys").fetchall()
    assert rows
    for row in rows:
        for value in tuple(row):
            assert plaintext not in str(value)
    # The file itself shouldn't contain it either.
    assert plaintext.encode() not in keys.DB_PATH.read_bytes()
