"""Chroma based vector store utilities."""

from typing import Iterable, List, Tuple
import os

try:
    import chromadb  # type: ignore
    from chromadb.utils import embedding_functions  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    chromadb = None  # type: ignore
    embedding_functions = None  # type: ignore

try:
    import torch  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    torch = None  # type: ignore


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

            device = "cuda" if torch and torch.cuda.is_available() else "cpu"
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                device=device,
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

                def get(self, include=None):
                    return {"documents": list(self.docs)}

            self.collection = _DummyCollection()

    def add_document(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        """Add a single document to the tenant collection."""
        if not metadata:
            metadata = {"doc_id": doc_id}
        self.collection.add(ids=[doc_id], documents=[text], metadatas=[metadata])

    def query(self, text: str, n_results: int = 3) -> dict:
        """Query the collection for similar documents (Chroma format)."""
        try:
            results = self.collection.query(query_texts=[text], n_results=n_results)
            documents = results.get("documents", [[]])
            if documents and isinstance(documents[0], list):
                documents = documents[0]
            # נחזיר עדיין dict, כדי לשמור תאימות
            return {"documents": [documents]}
        except Exception:
            return {"documents": [[]]}

    def keyword_search(self, query: str) -> list[str]:
        """Perform exact keyword match search on stored documents."""
        try:
            all_docs = self.collection.get(include=["documents"]).get("documents", [])
        except Exception:
            all_docs = getattr(self.collection, "docs", [])
        query_lower = query.lower()
        return [doc for doc in all_docs if query_lower in doc.lower()]

    def hybrid_query(self, query: str, n_results: int = 3) -> dict:
        """Combine semantic and keyword search results."""
        keyword_results = self.keyword_search(query)
        semantic_docs = self.query(query, n_results).get("documents", [[]])
        if semantic_docs and isinstance(semantic_docs[0], list):
            semantic_docs = semantic_docs[0]
        combined = list(dict.fromkeys(keyword_results + semantic_docs))
        return {"documents": [combined[:n_results]]}

    def store_info(self) -> dict:
        """Return metadata about the underlying vector collection.

        Used by the RAG visualizer to render a "Vector store" panel alongside
        the retrieval results — without this, there's no way to see how many
        vectors were searched or which embedding model produced them.
        """
        info: dict = {
            "collection_name": getattr(self.collection, "name", "documents"),
            "persist_path": self.persist_path,
            "tenant_id": self.tenant_id,
            "count": None,
            "embedding_model": None,
            "embedding_dim": None,
            "device": None,
        }
        try:
            info["count"] = int(self.collection.count())
        except Exception:
            try:
                # Fallback for the in-memory dummy collection
                docs = self.collection.get(include=["documents"])  # type: ignore[arg-type]
                info["count"] = len(docs.get("documents", []))
            except Exception:
                info["count"] = 0

        fn = getattr(self, "embedding_fn", None)
        if fn is not None:
            info["embedding_model"] = getattr(fn, "model_name", None) or type(fn).__name__
            try:
                import torch  # type: ignore

                info["device"] = (
                    "cuda" if getattr(torch.cuda, "is_available", lambda: False)() else "cpu"
                )
            except Exception:
                info["device"] = "cpu"
            try:
                probe = fn(["__dim_probe__"])
                if probe and isinstance(probe[0], (list, tuple)):
                    info["embedding_dim"] = len(probe[0])
            except Exception:
                pass
        return info

    def hybrid_query_trace(self, query: str, n_results: int = 3) -> dict:
        """Same as ``hybrid_query`` but returns the internal breakdown plus
        store metadata so the visualizer can show a real vector-search panel.

        We deliberately pull *more* semantic candidates than the caller asks
        for (``n_candidates = max(n_results * 4, 8)``) so the visualizer can
        render a ranked list of what the vector DB considered, not just the
        final top-K.
        """
        keyword_results = self.keyword_search(query)

        info = self.store_info()
        collection_size = info.get("count") or 0
        n_candidates = max(n_results * 4, 8)
        if collection_size:
            n_candidates = min(n_candidates, collection_size)

        semantic_docs: list[str] = []
        semantic_metas: list[dict] = []
        semantic_distances: list[float | None] = []
        try:
            raw = self.collection.query(
                query_texts=[query],
                n_results=max(n_candidates, 1),
                include=["documents", "metadatas", "distances"],
            )
            docs = raw.get("documents", [[]]) or [[]]
            metas = raw.get("metadatas", [[]]) or [[]]
            dists = raw.get("distances", [[]]) or [[]]
            if docs and isinstance(docs[0], list):
                semantic_docs = list(docs[0])
            if metas and isinstance(metas[0], list):
                semantic_metas = list(metas[0])
            if dists and isinstance(dists[0], list):
                semantic_distances = list(dists[0])
        except Exception:
            # Chroma may reject "include" on older versions or on empty stores.
            fallback = self.query(query, n_results).get("documents", [[]])
            if fallback and isinstance(fallback[0], list):
                semantic_docs = list(fallback[0])

        # Pad metas / distances so per-doc zip works in the caller.
        while len(semantic_metas) < len(semantic_docs):
            semantic_metas.append({})
        while len(semantic_distances) < len(semantic_docs):
            semantic_distances.append(None)

        keyword_entries = [
            {"document": doc, "metadata": {}, "score": None, "source": "keyword"}
            for doc in keyword_results
        ]
        semantic_entries = [
            {
                "document": doc,
                "metadata": meta or {},
                "score": dist,
                "source": "semantic",
            }
            for doc, meta, dist in zip(semantic_docs, semantic_metas, semantic_distances)
        ]

        # Combined, deduplicated by document identity, preserving keyword order first.
        seen: set[str] = set()
        combined: list[dict] = []
        for entry in keyword_entries + semantic_entries:
            key = entry["document"]
            if key in seen:
                continue
            seen.add(key)
            combined.append(entry)
        combined = combined[:n_results]

        return {
            "store": info,
            "query": query,
            "n_candidates": n_candidates,
            "n_results": n_results,
            "keyword": keyword_entries,
            "semantic": semantic_entries,  # full ranked candidate list
            "combined": combined,          # post-fusion top-K actually used
        }


