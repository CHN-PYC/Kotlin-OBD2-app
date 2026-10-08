from pathlib import Path

import pytest
from tokenizers import Tokenizer, models, pre_tokenizers, processors

from app.services.knowledge.token_budget import validate_token_budget
from app.services.knowledge.token_counter import LocalTokenCounter


@pytest.fixture
def tokenizer_path(tmp_path: Path) -> Path:
    # A tiny local tokenizer exercises the adapter, not BGE-M3 retrieval quality.
    tokenizer = Tokenizer(
        models.WordLevel({"[UNK]": 0, "[CLS]": 1, "[SEP]": 2, "hello": 3}, unk_token="[UNK]")
    )
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    tokenizer.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]", special_tokens=[("[CLS]", 1), ("[SEP]", 2)]
    )
    tokenizer.enable_truncation(max_length=3)
    tokenizer.enable_padding(length=10)
    path = tmp_path / "tokenizer.json"
    tokenizer.save(str(path))
    return path


def test_counts_special_tokens_without_saved_truncation_or_padding(tokenizer_path: Path) -> None:
    counter = LocalTokenCounter(tokenizer_path)
    assert counter.count_tokens("hello") == 3
    assert counter.count_tokens("hello hello hello") == 5
    assert counter.count_tokens("") == 2


def test_real_counter_adapter_is_accepted_by_budget_function(tokenizer_path: Path) -> None:
    counter = LocalTokenCounter(tokenizer_path)
    assert validate_token_budget("hello", count_tokens=counter.count_tokens, max_tokens=3) == 3
    with pytest.raises(ValueError):
        validate_token_budget("hello hello", count_tokens=counter.count_tokens, max_tokens=3)


def test_missing_tokenizer_does_not_fall_back_to_character_count(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        LocalTokenCounter(tmp_path / "missing.json")
