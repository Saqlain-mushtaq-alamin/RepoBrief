"""Token counting wrapper using tiktoken.

Provides a simple interface to count tokens for any string,
using the cl100k_base encoding (used by GPT-4, Claude, and most modern LLMs).
"""

from __future__ import annotations

from functools import lru_cache

import tiktoken


@lru_cache(maxsize=1)
def _get_encoding(encoding_name: str = "cl100k_base") -> tiktoken.Encoding:
    """Get (and cache) a tiktoken encoding.

    Args:
        encoding_name: Name of the tiktoken encoding. Default is cl100k_base
                       (used by GPT-4, Claude 3, and most modern models).

    Returns:
        The tiktoken Encoding object.
    """
    return tiktoken.get_encoding(encoding_name)


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count the number of tokens in a string.

    Falls back to character-based estimation if tiktoken is unavailable.

    Args:
        text: The text to tokenize.
        encoding_name: The tiktoken encoding to use.

    Returns:
        Number of tokens in the text.
    """
    if not text:
        return 0
    try:
        enc = _get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        # Fallback: rough character-based estimate
        return estimate_tokens_fast(text)


def estimate_tokens_fast(text: str) -> int:
    """Fast (approximate) token count based on character count.

    Useful for rough estimates without the overhead of actual tokenization.
    Rule of thumb: ~4 characters per token for English text / code.

    Args:
        text: The text to estimate.

    Returns:
        Approximate number of tokens.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)
