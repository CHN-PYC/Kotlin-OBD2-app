import re


def clean_text(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip()
