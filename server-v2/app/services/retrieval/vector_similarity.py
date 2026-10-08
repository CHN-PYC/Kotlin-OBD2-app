import math


def _unit_vector(vector: list[float]) -> list[float]:
    if not vector or any(not math.isfinite(value) for value in vector):
        raise ValueError("Vector must be nonempty and contain only finite values")
    scale = max(abs(value) for value in vector)
    if scale == 0:
        raise ValueError("Cosine similarity is undefined for a zero vector")
    # Scaling first preserves direction and avoids overflow with very large components.
    scaled = [value / scale for value in vector]
    length = math.hypot(*scaled)
    return [value / length for value in scaled]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compare vector directions without changing the input lists."""
    if len(left) != len(right):
        raise ValueError("Vectors must have the same dimension")
    left_unit = _unit_vector(left)
    right_unit = _unit_vector(right)
    score = math.fsum(a * b for a, b in zip(left_unit, right_unit, strict=True))
    # Floating-point rounding can place an otherwise valid cosine just outside [-1, 1].
    return max(-1.0, min(1.0, score))
