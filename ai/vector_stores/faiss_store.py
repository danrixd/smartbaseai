"""In-memory FAISS-like vector store (mocked)."""

from typing import Iterable, List, Tuple


class FaissStore:
    """Simplified FAISS store maintaining vectors in memory."""

    def __init__(self) -> None:
        self._vectors: List[List[float]] = []
        self._metadata: List[dict] = []

    def add(self, embeddings: Iterable[List[float]], metadata: Iterable[dict]) -> None:
        """Add embeddings with associated metadata."""
        for emb, meta in zip(embeddings, metadata):
            self._vectors.append(list(emb))
            self._metadata.append(dict(meta))

    def _distance(self, a: List[float], b: List[float]) -> float:
        return sum((x - y) ** 2 for x, y in zip(a, b))

    def query(self, embedding: List[float], top_k: int = 5) -> List[Tuple[dict, float]]:
        """Return top_k metadata items ranked by distance."""
        scores = [
            (meta, self._distance(vec, embedding))
            for vec, meta in zip(self._vectors, self._metadata)
        ]
        scores.sort(key=lambda x: x[1])
        return scores[:top_k]
