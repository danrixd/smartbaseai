"""Simplified Anthropic model wrapper."""

from typing import Any


class AnthropicModel:
    """Generate text using the Anthropic API (mocked)."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Return a deterministic response for the prompt."""
        return f"[Anthropic] Response to: {prompt}"
