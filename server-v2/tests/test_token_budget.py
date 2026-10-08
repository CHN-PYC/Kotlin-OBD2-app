import pytest

from app.services.knowledge.token_budget import validate_token_budget


@pytest.mark.parametrize("count", [4, 5])
def test_accepts_within_budget_and_counts_original_text_once(count: int) -> None:
    calls: list[str] = []

    def fake_counter(text: str) -> int:
        # Deliberately not a tokenizer: test the budget rule independently of a model.
        calls.append(text)
        return count

    text = "  Evidence with a safety note.  "
    assert validate_token_budget(text, count_tokens=fake_counter, max_tokens=5) == count
    assert calls == [text]


def test_rejects_over_budget() -> None:
    with pytest.raises(ValueError):
        validate_token_budget("Evidence", count_tokens=lambda text: 6, max_tokens=5)


@pytest.mark.parametrize("text,budget", [(" ", 5), ("Evidence", 0), ("Evidence", -1)])
def test_rejects_invalid_input_before_counting(text: str, budget: int) -> None:
    def counter_must_not_run(value: str) -> int:
        pytest.fail("Invalid input must be rejected before tokenization")

    with pytest.raises(ValueError):
        validate_token_budget(text, count_tokens=counter_must_not_run, max_tokens=budget)


def test_rejects_negative_counter_result() -> None:
    with pytest.raises(ValueError):
        validate_token_budget("Evidence", count_tokens=lambda text: -1, max_tokens=5)


def test_does_not_hide_tokenizer_failure() -> None:
    def broken_counter(text: str) -> int:
        raise OSError("Tokenizer unavailable")

    with pytest.raises(OSError, match="Tokenizer unavailable"):
        validate_token_budget("Evidence", count_tokens=broken_counter, max_tokens=5)
