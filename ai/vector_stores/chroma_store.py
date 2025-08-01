"""In-memory Chroma-like vector store (mocked)."""

from typing import Iterable, List, Tuple


class ChromaStore:
    """Simplified Chroma store maintaining vectors in memory."""

    def __init__(self) -> None:
        self._vectors: List[List[float]] = []
        self._metadata: List[dict] = []

    def add(self, embeddings: Iterable[List[float]], metadata: Iterable[dict]) -> None:
        """Add embeddings along with metadata."""
        for emb, meta in zip(embeddings, metadata):
            self._vectors.append(list(emb))
            self._metadata.append(dict(meta))

    def _distance(self, a: List[float], b: List[float]) -> float:
        return sum((x - y) ** 2 for x, y in zip(a, b))

    def query(self, embedding: List[float], top_k: int = 5) -> List[Tuple[dict, float]]:
        """Return closest metadata entries to the embedding."""
        scored = [
            (meta, self._distance(vec, embedding))
            for vec, meta in zip(self._vectors, self._metadata)
        ]
        scored.sort(key=lambda x: x[1])
        return scored[:top_k]
