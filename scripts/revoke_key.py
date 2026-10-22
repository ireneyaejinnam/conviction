"""
Revoke an API key by name.
Usage: python -m scripts.revoke_key --name "<name>"
"""

import argparse
import sys

from src.api.keys import revoke

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Revoke an API key.")
    p.add_argument("--name", required=True)
    args = p.parse_args()

    if not revoke(args.name):
        print(f"No active key named {args.name!r}.")
        sys.exit(1)
    print(f"Revoked key {args.name!r}.")
