"""Wrapper for interacting with a local Ollama server."""

from __future__ import annotations

from typing import Any

try:  # the optional dependency may not be installed in some environments
    from ollama import Client, RequestError, ResponseError
except Exception:  # pragma: no cover - dependency missing
    Client = None  # type: ignore


class OllamaModel:
    """Generate text using an Ollama model if available."""

    def __init__(self, model_name: str = "llama3") -> None:
        self.model_name = model_name
        self.client = Client() if Client is not None else None

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return a response from Ollama or a fallback message."""
        if self.client is not None:
            try:
                resp = self.client.generate(model=self.model_name, prompt=prompt)
                return resp.response
            except (RequestError, ResponseError, ConnectionError):
                pass
            except Exception:  # pragma: no cover - unexpected failures
                pass
        return f"[Ollama] Response to: {prompt}"

