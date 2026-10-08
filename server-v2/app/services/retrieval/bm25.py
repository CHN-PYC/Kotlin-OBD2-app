import math
import re
from collections import Counter

from app.schemas.knowledge import KnowledgeChunk
from app.schemas.retrieval import RetrievedSource

_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_.-]+|[\u4e00-\u9fff]+")


def tokenize_for_bm25(text: str) -> list[str]:
    """Tokenize codes as words and Chinese runs as characters plus bigrams."""
    tokens: list[str] = []
    for match in _TOKEN_PATTERN.findall(text.lower()):
        if "\u4e00" <= match[0] <= "\u9fff":
            tokens.extend(match)
            tokens.extend(match[index : index + 2] for index in range(len(match) - 1))
        else:
            tokens.append(match)
    return tokens


class BM25Retriever:
    """Small in-memory BM25 index for the curated corpus, not a second database."""

    def __init__(self, chunks: list[KnowledgeChunk], *, k1: float = 1.5, b: float = 0.75) -> None:
        if not chunks:
            raise ValueError("BM25 corpus must not be empty")
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("BM25 requires k1 > 0 and 0 <= b <= 1")
        self._chunks = [chunk.model_copy(deep=True) for chunk in chunks]
        self._term_frequencies = [
            Counter(
                tokenize_for_bm25(
                    " ".join(
                        [
                            chunk.title,
                            chunk.section_title,
                            chunk.text,
                            *chunk.pid_tags,
                            *chunk.dtc_codes,
                        ]
                    )
                )
            )
            for chunk in chunks
        ]
        self._lengths = [sum(frequencies.values()) for frequencies in self._term_frequencies]
        self._average_length = sum(self._lengths) / len(self._lengths)
        self._k1 = k1
        self._b = b
        document_frequency: Counter[str] = Counter()
        for frequencies in self._term_frequencies:
            document_frequency.update(frequencies.keys())
        count = len(chunks)
        self._idf = {
            term: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    async def search(self, query_text: str, *, k: int) -> list[RetrievedSource]:
        if not query_text.strip():
            raise ValueError("query_text must not be blank")
        if type(k) is not int or k <= 0:
            raise ValueError("k must be a positive integer")
        query_terms = set(tokenize_for_bm25(query_text))
        scored: list[tuple[float, KnowledgeChunk]] = []
        for chunk, frequencies, length in zip(
            self._chunks, self._term_frequencies, self._lengths, strict=True
        ):
            score = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if frequency == 0:
                    continue
                denominator = frequency + self._k1 * (
                    1 - self._b + self._b * length / self._average_length
                )
                score += self._idf.get(term, 0.0) * frequency * (self._k1 + 1) / denominator
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [
            RetrievedSource(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                title=chunk.title,
                source_url=chunk.source_url,
                score=score,
                text=chunk.text,
                topic=chunk.topic,
                pid_tags=chunk.pid_tags,
                section_title=chunk.section_title,
            )
            for score, chunk in scored[:k]
        ]
