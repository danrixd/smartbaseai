"""Local embedding generation utilities."""

from hashlib import md5
from typing import Iterable, List


class LocalEmbeddings:
    """Generate embeddings using a local algorithm."""

    def __init__(self, dimension: int = 3) -> None:
        self.dimension = dimension

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        """Return deterministic local embeddings for the provided texts."""
        vectors: List[List[float]] = []
        for text in texts:
            digest = md5(text.encode("utf-8")).digest()
            vector = [b / 255 for b in digest[: self.dimension]]
            vectors.append(vector)
        return vectors
