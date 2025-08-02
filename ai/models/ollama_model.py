
"""Wrapper for interacting with a local Ollama server."""

from __future__ import annotations

from typing import Any
import json

try:  # requests may not be installed in all environments
    import requests
except Exception:  # pragma: no cover - dependency missing
    requests = None  # type: ignore[misc]


class OllamaModel:
    """Generate text using an Ollama model if available."""

    def __init__(self, model_name: str = "llama3.2", base_url: str = "http://localhost:11434") -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return a response from Ollama or a fallback message."""
        if requests is not None:
            url = f"{self.base_url}/api/generate"
            payload = {"model": self.model_name, "prompt": prompt, "stream": False}
            try:
                r = requests.post(url, json=payload, timeout=10)
                r.raise_for_status()
                try:
                    data = r.json()
                    if isinstance(data, dict) and "response" in data:
                        return str(data["response"]).strip()
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
            except Exception:  # pragma: no cover - network failures or missing dep
                pass
        return f"[Ollama] Response to: {prompt}"

