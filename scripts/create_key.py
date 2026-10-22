"""
Create an API key. The plaintext is printed once; only its hash is stored.
Usage: python -m scripts.create_key --name "<name>" [--rph 30] [--daily-tokens 200000]
"""

import argparse
import sqlite3
import sys

from src.api.keys import DB_PATH, create_key

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Create an API key.")
    p.add_argument("--name", required=True, help="Unique name for the key holder")
    p.add_argument("--rph", type=int, default=30, help="Requests per hour")
    p.add_argument("--daily-tokens", type=int, default=200_000, help="Daily token budget")
    args = p.parse_args()

    try:
        key = create_key(args.name, args.rph, args.daily_tokens)
    except sqlite3.IntegrityError:
        print(f"A key named {args.name!r} already exists in {DB_PATH}.")
        sys.exit(1)

    print(f"Created key {args.name!r} (rph={args.rph}, daily_tokens={args.daily_tokens}) in {DB_PATH}")
    print(f"\n  {key}\n")
    print("Save it now. It can't be shown again; only its hash is stored.")
