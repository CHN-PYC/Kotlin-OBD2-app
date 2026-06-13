from __future__ import annotations

import json
import pickle
from math import sqrt
from pathlib import Path

import numpy as np

from app.core.config import FAISS_DIR
from app.core.constants import KB_INDEX_FILE


class VectorStoreService:
    """Local vector store with optional FAISS support later.

    Current implementation persists:
    - chunk ids
    - dense TF-IDF matrix (json)
    - fitted sklearn vectorizer (pickle)

    This keeps the index lifecycle real and lets retrieval work now.
    """

    def __init__(self) -> None:
        self.index_path = FAISS_DIR / KB_INDEX_FILE
        self.vectorizer_path = FAISS_DIR / "tfidf_vectorizer.pkl"

    def write_index(self, vectors: list[list[float]] | np.ndarray, chunk_ids: list[str], vectorizer) -> None:
        matrix = np.asarray(vectors, dtype=np.float32)
        payload = {
            "chunk_ids": chunk_ids,
            "matrix": matrix.tolist(),
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        with self.vectorizer_path.open("wb") as f:
            pickle.dump(vectorizer, f)

    def index_exists(self) -> bool:
        return self.index_path.exists() and self.vectorizer_path.exists()

    def read_index(self) -> tuple[list[str], np.ndarray]:
        if not self.index_exists():
            return [], np.zeros((0, 0), dtype=np.float32)
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        chunk_ids = payload.get("chunk_ids", [])
        matrix = np.asarray(payload.get("matrix", []), dtype=np.float32)
        return chunk_ids, matrix

    def load_vectorizer(self):
        if not self.vectorizer_path.exists():
            return None
        with self.vectorizer_path.open("rb") as f:
            return pickle.load(f)

    def search(self, query_vector: list[float] | np.ndarray, top_k: int = 5) -> list[tuple[str, float]]:
        chunk_ids, matrix = self.read_index()
        if matrix.size == 0 or len(chunk_ids) == 0:
            return []

        q = np.asarray(query_vector, dtype=np.float32)
        if q.size == 0:
            return []

        scores = [self.cosine_similarity(q, row) for row in matrix]
        ranked = sorted(zip(chunk_ids, scores), key=lambda item: item[1], reverse=True)
        return ranked[:top_k]

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        dot = float(np.dot(a, b))
        norm_a = sqrt(float(np.dot(a, a))) or 1.0
        norm_b = sqrt(float(np.dot(b, b))) or 1.0
        return dot / (norm_a * norm_b)
