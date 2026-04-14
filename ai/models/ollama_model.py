"""Wrapper for interacting with a local Ollama server."""

from __future__ import annotations

import json
from typing import Any

from db import settings_repository

DEFAULT_BASE_URL = "http://localhost:11434"

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - dependency missing
    requests = None  # type: ignore


class OllamaModel:
    """Generate text using an Ollama model if available."""

    def __init__(
        self,
        model_name: str = "llama3.2",
        base_url: str | None = None,
        **_: Any,
    ) -> None:
        self.model_name = model_name
        self.base_url = (
            base_url
            or settings_repository.get("ollama_base_url")
            or DEFAULT_BASE_URL
        ).rstrip("/")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return a response from Ollama or a fallback message."""
        if requests is None:
            return "[Ollama unavailable — requests not installed]"
        url = f"{self.base_url}/api/generate"
        payload = {"model": self.model_name, "prompt": prompt, "stream": False}
        try:
            r = requests.post(url, json=payload, timeout=30)
            r.raise_for_status()
            try:
                data = r.json()
                if isinstance(data, dict) and "response" in data:
                    return str(data["response"]).strip() or "[Ollama returned no text]"
            except ValueError:
                text = ""
                for line in r.text.splitlines():
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    text += obj.get("response", "")
                    if obj.get("done"):
                        break
                if text:
                    return text.strip()
        except Exception as e:  # network failure, bad response, etc.
            return f"[Ollama unreachable at {self.base_url}] {type(e).__name__}: {e}"
        return "[Ollama returned unexpected response shape]"

    @staticmethod
    def ping(base_url: str | None = None) -> tuple[bool, str]:
        """Quick connectivity check — used by ``/admin/models/status``."""
        if requests is None:
            return False, "requests not installed"
        url = (
            base_url
            or settings_repository.get("ollama_base_url")
            or DEFAULT_BASE_URL
        ).rstrip("/") + "/api/tags"
        try:
            r = requests.get(url, timeout=3)
            r.raise_for_status()
            data = r.json()
            models = data.get("models", []) if isinstance(data, dict) else []
            return True, f"ok ({len(models)} models available)"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
