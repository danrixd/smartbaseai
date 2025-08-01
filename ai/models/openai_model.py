"""Simplified OpenAI language model wrapper."""

from typing import Any


class OpenAIModel:
    """Generate text using the OpenAI API (mocked)."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return a deterministic response for the prompt."""
        return f"[OpenAI] Response to: {prompt}"
