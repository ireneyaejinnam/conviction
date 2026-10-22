import json

from tests.conftest import bearer

QUESTION = "How exposed is the company to export restrictions on data center GPUs?"


def _log_lines(out: str) -> list[dict]:
    lines = []
    for raw in out.splitlines():
        try:
            parsed = json.loads(raw)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            lines.append((raw, parsed))
    return lines


def test_one_json_line_per_request(client, make_key, capsys):
    plaintext, _ = make_key()
    capsys.readouterr()                   # drop anything printed during setup
    r = client.post("/ask", json={"question": QUESTION, "ticker": "NVDA"}, headers=bearer(plaintext))
    assert r.status_code == 200
    out = capsys.readouterr().out

    lines = _log_lines(out)
    assert len(lines) == 1, out
    raw, line = lines[0]
    assert line["request_id"] == r.headers["X-Request-ID"]
    assert line["status"] == 200
    assert line["q_len"] == len(QUESTION)
    assert plaintext not in raw
    assert QUESTION not in raw
