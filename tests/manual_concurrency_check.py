"""
Concurrency check for the hourly request limit: 20 simultaneous reserve()
calls on a key with rph=3 must let exactly 3 through.

Uses a throwaway data dir and makes no OpenAI calls.
Usage: python -m tests.manual_concurrency_check
"""

import os
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

# Must be set before src.config is imported, since it computes DATA_DIR at import.
DATA_DIR = tempfile.mkdtemp(prefix="conviction-concurrency-")
os.environ["CONVICTION_DATA_DIR"] = DATA_DIR

from src.api.keys import create_key, lookup  # noqa: E402
from src.api.limits import LimitExceeded, reserve  # noqa: E402

THREADS = 20
RPH = 3


def attempt(key: dict) -> bool:
    try:
        reserve(key)
        return True
    except LimitExceeded:
        return False


def main() -> int:
    try:
        key = lookup(create_key("concurrency-check", RPH, 200_000))
        with ThreadPoolExecutor(THREADS) as ex:
            results = list(ex.map(lambda _: attempt(key), range(THREADS)))
    finally:
        shutil.rmtree(DATA_DIR, ignore_errors=True)

    ok = sum(results)
    print(f"{THREADS} simultaneous reserves, rph={RPH}: {ok} succeeded, {THREADS - ok} refused")
    if ok != RPH:
        print(f"FAIL: expected exactly {RPH} to succeed")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
