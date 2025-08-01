"""Generate final chatbot responses using the configured AI model."""

from __future__ import annotations

from typing import Iterable, Mapping

from ai import ModelManager


class ResponseGenerator:
    """Wrapper around :class:`ModelManager` for producing responses."""

    def __init__(self, tenant_id: str) -> None:
        self.manager = ModelManager(tenant_id)

    def _format_history(self, history: Iterable[Mapping[str, str]]) -> str:
        lines = []
        for item in history:
            role = item.get("role", "user")
            text = item.get("text", "")
            lines.append(f"{role.capitalize()}: {text}")
        return "\n".join(lines)

    def generate(self, prompt: str, history: Iterable[Mapping[str, str]] | None = None, **kwargs) -> str:
        """Generate a response using conversation history and prompt."""
        context = self._format_history(history or [])
        if context:
            full_prompt = f"{context}\nUser: {prompt}\nAssistant:"
        else:
            full_prompt = prompt
        return self.manager.generate(full_prompt, **kwargs)
