"""Chroma based vector store utilities."""

from typing import Iterable, List, Tuple
import os

try:
    import chromadb  # type: ignore
    from chromadb.utils import embedding_functions  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    chromadb = None  # type: ignore
    embedding_functions = None  # type: ignore


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


class TenantVectorStore:
    """Persistent vector store instance for a specific tenant."""

    def __init__(self, tenant_id: str, persist_dir: str = "vector_store") -> None:
        self.tenant_id = tenant_id
        self.persist_path = os.path.join(persist_dir, tenant_id)
        os.makedirs(self.persist_path, exist_ok=True)

        if chromadb is not None:
            self.client = chromadb.PersistentClient(path=self.persist_path)

            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

            self.collection = self.client.get_or_create_collection(
                name="documents",
                embedding_function=self.embedding_fn,
            )
        else:  # pragma: no cover - fallback when chromadb is missing
            self.client = None

            class _DummyCollection:
                def __init__(self) -> None:
                    self.docs: list[str] = []

                def add(self, ids, documents, metadatas):
                    for doc in documents:
                        self.docs.append(doc)

                def query(self, query_texts, n_results=3):
                    return {"documents": [self.docs[:n_results]]}

            self.collection = _DummyCollection()

    def add_document(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        """Add a single document to the tenant collection."""
        if not metadata:
            metadata = {"doc_id": doc_id}
        self.collection.add(ids=[doc_id], documents=[text], metadatas=[metadata])

    def query(self, text: str, n_results: int = 3) -> dict:
        """Query the collection for similar documents."""
        return self.collection.query(query_texts=[text], n_results=n_results)
