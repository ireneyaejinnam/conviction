"""
Seed an empty data dir: ingest the watchlist and cache the risk diffs.
If the Chroma collection already has chunks, print stats and do nothing.
Run once, by hand (never at container startup):
    docker compose exec app python -m scripts.seed
"""

import subprocess
import sys

from src.index.store import get_collection
from scripts import stats


def main():
    if get_collection().count() > 0:
        print("already seeded")
        stats.main()
        return
    subprocess.run([sys.executable, "-m", "scripts.ingest_watchlist"], check=True)


if __name__ == "__main__":
    main()
