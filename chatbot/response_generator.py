"""Generate responses using a retrieval augmented prompt."""

from __future__ import annotations

import requests
from typing import Iterable, Mapping

from ai.rag_pipeline import RAGPipeline


class OllamaModel:
    """Wrapper for calling a local Ollama server."""

    def __init__(self, model_name: str = "llama3.2", base_url: str = "http://localhost:11434") -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {"model": self.model_name, "prompt": prompt}
        try:
            r = requests.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            return data.get("response", "").strip()
        except Exception as e:  # pragma: no cover - network issues
            return f"[Ollama Error] {e}"


class ResponseGenerator:
    """Combine RAG retrieval and model generation."""

    def __init__(self, tenant_id: str, model_type: str = "ollama", model_name: str = "llama3.2") -> None:
        self.tenant_id = tenant_id
        self.rag = RAGPipeline(tenant_id=tenant_id)
        if model_type == "ollama":
            self.model = OllamaModel(model_name=model_name)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

    def generate_response(self, user_message: str, history: Iterable[Mapping[str, str]] | None = None) -> str:
        prompt = self.rag.augment_prompt(user_message, history)
        return self.model.generate(prompt)
