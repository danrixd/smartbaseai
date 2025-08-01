"""HuggingFace based embedding generator."""

from hashlib import sha1
from typing import Iterable, List


class HuggingFaceEmbeddings:
    """Generate embeddings using a HuggingFace model (mocked)."""

    def __init__(self, model_name: str = "distilbert-base", dimension: int = 3) -> None:
        self.model_name = model_name
        self.dimension = dimension

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        """Return deterministic embeddings for the given texts."""
        result: List[List[float]] = []
        for text in texts:
            digest = sha1(text.encode("utf-8")).digest()
            vector = [b / 255 for b in digest[: self.dimension]]
            result.append(vector)
        return result
