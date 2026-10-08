from collections.abc import Callable


def validate_token_budget(
    text: str,
    *,
    count_tokens: Callable[[str], int],
    max_tokens: int,
) -> int:
    """Return token count if within budget; otherwise raise ValueError.

    Reject blank text, non-positive budgets, and negative counts. Count the
    original text exactly once, without stripping or truncating it. A count
    equal to max_tokens is valid. Let counter exceptions propagate.

    The caller must supply the matching model tokenizer, with automatic
    truncation disabled and required special tokens/prefixes accounted for.
    """
    # 1. Reject blank text and max_tokens <= 0 before calling count_tokens.
    # 2. Call count_tokens(text) once and store its returned integer.
    # 3. Reject a negative count or a count exceeding max_tokens.
    # 4. Return the count. Do not change text to make it fit.
    if not text.strip() or (max_tokens <= 0):
        raise ValueError("empty text or error max_tokens")
    count = count_tokens(text)
    if count < 0 or count > max_tokens:
        raise ValueError("Token count is negative or exceeds budget")
    return count
