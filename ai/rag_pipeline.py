"""Simplified retrieval augmented generation pipeline."""

from typing import Iterable, List, Optional, Sequence, Mapping

from .embeddings import LocalEmbeddings, OpenAIEmbeddings, HuggingFaceEmbeddings
from .vector_stores import FaissStore
from .vector_stores.chroma_store import TenantVectorStore
from .models import OpenAIModel


class RAGPipeline:
    """Coordinate embedding, retrieval and generation steps."""

    def __init__(
        self,
        embedder: Optional[object] = None,
        vector_store: Optional[object] = None,
        model: Optional[object] = None,
        tenant_id: str | None = None,
    ) -> None:
        if tenant_id:
            self.store = TenantVectorStore(tenant_id)
            self.embedder = None
            self.vector_store = None
        else:
            self.embedder = embedder or LocalEmbeddings()
            self.vector_store = vector_store or FaissStore()
            self.store = None
        self.model = model or OpenAIModel()

    def add_documents(self, texts: Sequence[str], metadata: Optional[Sequence[dict]] = None) -> None:
        """Add documents to the configured vector store."""
        metadata = metadata or [{} for _ in texts]
        if self.store is not None:
            for idx, text in enumerate(texts):
                doc_id = metadata[idx].get("id", f"doc{idx}")
                self.store.add_document(doc_id, text, metadata[idx])
        else:
            embeddings = self.embedder.embed(texts)
            self.vector_store.add(embeddings, metadata)

    def retrieve_context(self, query: str, top_k: int = 3) -> str:
        """Retrieve contextual documents for a query."""
        if self.store is not None:
            results = self.store.hybrid_query(query, n_results=top_k)
            documents = results.get("documents", [[]])
            if documents and isinstance(documents[0], list):
                documents = documents[0]
            return "\n".join(documents)

        query_emb = self.embedder.embed([query])[0]
        results = self.vector_store.query(query_emb, top_k)
        return "\n".join(meta.get("text", "") for meta, _ in results)

    def augment_prompt(self, query: str, history: Iterable[Mapping[str, str]] | None = None, top_k: int = 3) -> str:
        """Combine retrieved context, history and query into a prompt."""
        context = self.retrieve_context(query, top_k=top_k)
        history_text = ""
        if history:
            history_text = "\n".join(f"{m['role']}: {m['text']}" for m in history)
        return f"""
Context:
{context}

Conversation:
{history_text}

User: {query}
Assistant:"""

    def answer(self, question: str, top_k: int = 3, history: Iterable[Mapping[str, str]] | None = None) -> str:
        """Return a generated answer using retrieved context."""
        if self.store is not None:
            prompt = self.augment_prompt(question, history=history, top_k=top_k)
            return self.model.generate(prompt)

        query_emb = self.embedder.embed([question])[0]
        results = self.vector_store.query(query_emb, top_k)
        context = "\n".join(meta.get("text", "") for meta, _ in results)
        prompt = f"{context}\nQuestion: {question}\nAnswer:"
        return self.model.generate(prompt)
