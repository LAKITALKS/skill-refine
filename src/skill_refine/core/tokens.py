"""Simple token/word estimation utilities.

NOTE: Token counts are rough heuristics (~1.33 tokens per whitespace-delimited
word). They do NOT reflect any specific model's tokenizer. Use them for
order-of-magnitude comparisons, not as exact values.
"""


def estimate_tokens(text: str) -> int:
    """Return a rough token estimate. This is a heuristic, not an exact count."""
    words = len(text.split())
    return int(words * 1.33)


def count_words(text: str) -> int:
    """Count whitespace-delimited words in text."""
    return len(text.split())
