"""Anthropic Claude model wrapper.

Uses the official ``anthropic`` Python SDK. Defaults to ``claude-opus-4-6`` with
adaptive thinking and applies ``cache_control: ephemeral`` on the stable system
prompt so repeated turns in a session can read from the prompt cache.

If the SDK is not installed or no API key is available, ``generate`` returns
a clearly-marked stub so the pipeline stays functional in offline / demo mode
without silently pretending to be connected.
"""

from __future__ import annotations

from typing import Any

from db import settings_repository

DEFAULT_MODEL = "claude-opus-4-6"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_SYSTEM_PROMPT = (
    "You are SmartBaseAI, a multi-tenant assistant that answers user questions "
    "using the Context block provided below. Ground every answer in the Context. "
    "If the Context does not contain the answer, say you don't have that information "
    "rather than guessing. Prefer exact numeric values from the structured data "
    "section when present."
)

try:
    import anthropic  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    anthropic = None  # type: ignore


class AnthropicModel:
    """Generate text using the Anthropic Messages API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        **_: Any,
    ) -> None:
        self.api_key = api_key or settings_repository.get("anthropic_api_key")
        self.model_name = model_name or DEFAULT_MODEL
        self.max_tokens = max_tokens
        self._client: "anthropic.Anthropic | None" = None
        if anthropic is not None and self.api_key:
            try:
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except Exception:
                self._client = None

    def _split_prompt(self, prompt: str) -> tuple[str, str]:
        """Split a rendered prompt into (system_user_content).

        The orchestrator produces a single flat prompt string. For caching to
        be effective we want the stable system header in ``system`` and the
        per-turn Context + user question in ``messages``. We pass the whole
        rendered prompt as the user turn and use a static system prompt — the
        prompt itself already carries the Context.
        """
        return DEFAULT_SYSTEM_PROMPT, prompt

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if self._client is None:
            missing = "SDK not installed" if anthropic is None else "ANTHROPIC_API_KEY not set"
            return f"[Anthropic unavailable — {missing}] {self._preview(prompt)}"

        system_prompt, user_content = self._split_prompt(prompt)
        try:
            response = self._client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_content}],
            )
        except anthropic.AuthenticationError as e:  # type: ignore[attr-defined]
            return f"[Anthropic auth error] {e}"
        except anthropic.RateLimitError as e:  # type: ignore[attr-defined]
            return f"[Anthropic rate-limited] {e}"
        except anthropic.APIError as e:  # type: ignore[attr-defined]
            return f"[Anthropic API error {getattr(e, 'status_code', '?')}] {e}"
        except Exception as e:
            return f"[Anthropic unexpected error] {e}"

        parts: list[str] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "".join(parts).strip() or "[Anthropic returned no text]"

    @staticmethod
    def _preview(prompt: str) -> str:
        head = prompt.strip().splitlines()
        return head[-1][:120] if head else ""

    @staticmethod
    def ping(api_key: str | None = None) -> tuple[bool, str]:
        """Quick connectivity check — used by ``/admin/models/status``."""
        if anthropic is None:
            return False, "anthropic SDK not installed"
        key = api_key or settings_repository.get("anthropic_api_key")
        if not key:
            return False, "no API key configured"
        try:
            client = anthropic.Anthropic(api_key=key)
            client.models.list(limit=1)
            return True, "ok"
        except anthropic.AuthenticationError:  # type: ignore[attr-defined]
            return False, "invalid API key"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
