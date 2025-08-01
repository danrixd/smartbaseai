"""Simplified retrieval augmented generation pipeline."""

from typing import Iterable, List, Optional, Sequence

from .embeddings import LocalEmbeddings, OpenAIEmbeddings, HuggingFaceEmbeddings
from .vector_stores import FaissStore
from .models import OpenAIModel


class RAGPipeline:
    """Coordinate embedding, retrieval and generation steps."""

    def __init__(
        self,
        embedder: Optional[object] = None,
        vector_store: Optional[object] = None,
        model: Optional[object] = None,
    ) -> None:
        self.embedder = embedder or LocalEmbeddings()
        self.vector_store = vector_store or FaissStore()
        self.model = model or OpenAIModel()

    def add_documents(self, texts: Sequence[str], metadata: Optional[Sequence[dict]] = None) -> None:
        """Add documents to the vector store."""
        metadata = metadata or [{} for _ in texts]
        embeddings = self.embedder.embed(texts)
        self.vector_store.add(embeddings, metadata)

    def answer(self, question: str, top_k: int = 3) -> str:
        """Return a generated answer using retrieved context."""
        query_emb = self.embedder.embed([question])[0]
        results = self.vector_store.query(query_emb, top_k)
        context = "\n".join(meta.get("text", "") for meta, _ in results)
        prompt = f"{context}\nQuestion: {question}\nAnswer:"
        return self.model.generate(prompt)
