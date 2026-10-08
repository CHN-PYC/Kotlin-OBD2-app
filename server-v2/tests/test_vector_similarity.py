import pytest

from app.services.retrieval.vector_similarity import cosine_similarity


@pytest.mark.parametrize(
    "left,right,expected",
    [
        ([1.0, 0.0, 0.0], [2.0, 0.0, 0.0], 1.0),
        ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], 0.0),
        ([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], -1.0),
        ([1.0, 0.0, 0.0], [3.0, 4.0, 0.0], 0.6),
    ],
)
def test_known_directions(left: list[float], right: list[float], expected: float) -> None:
    assert cosine_similarity(left, right) == pytest.approx(expected)


def test_positive_scaling_does_not_change_score_or_modify_inputs() -> None:
    left, right = [1.0, 2.0, 3.0], [3.0, 1.0, -2.0]
    before = (left.copy(), right.copy())
    score = cosine_similarity(left, right)
    assert cosine_similarity([value * 10 for value in left], right) == pytest.approx(score)
    assert cosine_similarity(right, left) == pytest.approx(score)
    assert (left, right) == before


@pytest.mark.parametrize(
    "left,right",
    [
        ([], []),
        ([1.0], [1.0, 2.0]),
        ([0.0, 0.0], [1.0, 0.0]),
        ([1.0, 0.0], [0.0, 0.0]),
        ([float("nan")], [1.0]),
        ([1.0], [float("inf")]),
        ([float("-inf")], [1.0]),
    ],
)
def test_rejects_invalid_vectors(left: list[float], right: list[float]) -> None:
    with pytest.raises(ValueError):
        cosine_similarity(left, right)


@pytest.mark.parametrize("scale", [1e308, 1e-300])
def test_large_and_small_finite_values_do_not_overflow(scale: float) -> None:
    assert cosine_similarity([scale, scale], [1.0, 1.0]) == pytest.approx(1.0)
