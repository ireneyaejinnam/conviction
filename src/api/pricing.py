"""
Model prices in USD per 1M tokens, used for cost_usd in the request log.

Source: https://platform.openai.com/docs/pricing (standard tier).
Update PRICES_CHECKED whenever these are re-checked. While any price is
None, cost_usd is logged as null rather than guessed.
"""

from __future__ import annotations

PRICES_CHECKED = None              # TODO: "YYYY-MM-DD"

GPT_4O_INPUT_PER_1M = None         # TODO
GPT_4O_OUTPUT_PER_1M = None        # TODO
EMBEDDING_3_SMALL_PER_1M = None    # TODO


def cost_usd(embedding_tokens: int, prompt_tokens: int, completion_tokens: int) -> float | None:
    prices = (EMBEDDING_3_SMALL_PER_1M, GPT_4O_INPUT_PER_1M, GPT_4O_OUTPUT_PER_1M)
    if any(p is None for p in prices):
        return None
    tokens = (embedding_tokens, prompt_tokens, completion_tokens)
    return round(sum(t * p for t, p in zip(tokens, prices)) / 1_000_000, 6)
