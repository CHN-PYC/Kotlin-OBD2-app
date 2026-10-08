from pathlib import Path

from tokenizers import Tokenizer


class LocalTokenCounter:
    """Count with a local tokenizer JSON, without model weights or network access."""

    def __init__(self, tokenizer_path: Path) -> None:
        if not tokenizer_path.is_file():
            raise FileNotFoundError(tokenizer_path)
        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        # Count the entire input. Saved tokenizer settings must not hide overflow.
        self._tokenizer.no_truncation()
        self._tokenizer.no_padding()

    def count_tokens(self, text: str) -> int:
        encoding = self._tokenizer.encode(text, add_special_tokens=True)
        return len(encoding.ids)
