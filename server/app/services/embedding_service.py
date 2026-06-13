from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass
class EmbeddingBundle:
    matrix: np.ndarray
    vectorizer: TfidfVectorizer


class EmbeddingService:
    """Local TF-IDF embedding service.

    This provides a real lexical-semantic retrieval baseline while keeping
    a simple contract that can later be swapped for dense embeddings.
    """

    def fit_transform(self, texts: Iterable[str], max_features: int = 4096) -> EmbeddingBundle:
        corpus = [text.strip() for text in texts if text and text.strip()]
        vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=max_features,
            token_pattern=r"(?u)\b\w+\b",
        )

        if not corpus:
            return EmbeddingBundle(matrix=np.zeros((0, 0), dtype=np.float32), vectorizer=vectorizer)

        matrix = vectorizer.fit_transform(corpus).astype(np.float32)
        return EmbeddingBundle(matrix=matrix.toarray(), vectorizer=vectorizer)

    def transform_query(self, query: str, vectorizer: TfidfVectorizer) -> np.ndarray:
        vocabulary = getattr(vectorizer, "vocabulary_", None)
        if not vocabulary:
            return np.zeros((0,), dtype=np.float32)
        matrix = vectorizer.transform([query]).astype(np.float32)
        return matrix.toarray()[0]
