"""Generate final chatbot responses using the configured AI model."""

from __future__ import annotations

from typing import Iterable, Mapping

from ai import ModelManager, RAGPipeline
from ai.embeddings import (
    LocalEmbeddings,
    OpenAIEmbeddings,
    HuggingFaceEmbeddings,
)
from ai.vector_stores import FaissStore, ChromaStore, PineconeStore
from config.tenant_config import TenantConfig


class ResponseGenerator:
    """Wrapper around :class:`ModelManager` for producing responses."""

    EMBEDDER_MAP = {
        "local": LocalEmbeddings,
        "openai": OpenAIEmbeddings,
        "huggingface": HuggingFaceEmbeddings,
    }

    VECTOR_STORE_MAP = {
        "faiss": FaissStore,
        "chroma": ChromaStore,
        "pinecone": PineconeStore,
    }

    def __init__(
        self,
        tenant_id: str | None = None,
        model_type: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        if tenant_id is not None and model_type is None:
            self.config = TenantConfig.get(tenant_id)
        else:
            # minimal config when specifying model explicitly
            self.config = {
                "model": model_type or "openai",
                "model_config": {"model_name": model_name} if model_name else {},
            }

        self.use_rag = self.config.get("rag_enabled", False)
        self.manager = ModelManager(
            tenant_id or "explicit",
            model_type=self.config.get("model"),
            model_config=self.config.get("model_config"),
        )
        if self.use_rag:
            embedder_name = self.config.get("embedder", "local")
            vector_name = self.config.get("vector_store", "faiss")
            embedder_cls = self.EMBEDDER_MAP.get(embedder_name, LocalEmbeddings)
            vector_cls = self.VECTOR_STORE_MAP.get(vector_name, FaissStore)
            self.pipeline = RAGPipeline(
                embedder=embedder_cls(),
                vector_store=vector_cls(),
                model=self.manager.model,
            )
        else:
            self.pipeline = None

    def _format_history(self, history: Iterable[Mapping[str, str]]) -> str:
        lines = []
        for item in history:
            role = item.get("role", "user")
            text = item.get("text", "")
            lines.append(f"{role.capitalize()}: {text}")
        return "\n".join(lines)

    def generate(
        self,
        prompt: str,
        history: Iterable[Mapping[str, str]] | None = None,
        **kwargs,
    ) -> str:
        """Generate a response using conversation history and prompt."""
        if self.use_rag and self.pipeline is not None:
            return self.pipeline.answer(prompt, **kwargs)

        context = self._format_history(history or [])
        if context:
            full_prompt = f"{context}\nUser: {prompt}\nAssistant:"
        else:
            full_prompt = prompt
        return self.manager.generate(full_prompt, **kwargs)

    # Backwards compatible helper used by API layer
    def generate_response(
        self,
        prompt: str,
        history: Iterable[Mapping[str, str]] | None = None,
        **kwargs,
    ) -> str:
        return self.generate(prompt, history, **kwargs)
