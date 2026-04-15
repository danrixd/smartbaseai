"""OpenAI GPT model wrapper.

Uses the official ``openai`` Python SDK (>=1.0). If the SDK is missing or no
API key is available, ``generate`` returns a clearly-marked stub so the
pipeline stays functional in offline / demo mode.
"""

from __future__ import annotations

from typing import Any

from db import settings_repository

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_SYSTEM_PROMPT = (
    "You are SmartBaseAI, a multi-tenant assistant that answers user questions "
    "using the Context block provided below. Ground every answer in the Context. "
    "If the Context does not contain the answer, say you don't have that information "
    "rather than guessing."
)

try:
    import openai  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    openai = None  # type: ignore


class OpenAIModel:
    """Generate text using the OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        **_: Any,
    ) -> None:
        self.api_key = api_key or settings_repository.get("openai_api_key")
        self.model_name = model_name or DEFAULT_MODEL
        self.max_tokens = max_tokens
        self._client: "openai.OpenAI | None" = None
        if openai is not None and self.api_key:
            try:
                self._client = openai.OpenAI(api_key=self.api_key)
            except Exception:
                self._client = None

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if self._client is None:
            missing = "SDK not installed" if openai is None else "OPENAI_API_KEY not set"
            return f"[OpenAI unavailable — {missing}]"

        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
        except openai.AuthenticationError as e:  # type: ignore[attr-defined]
            return f"[OpenAI auth error] {e}"
        except openai.RateLimitError as e:  # type: ignore[attr-defined]
            return f"[OpenAI rate-limited] {e}"
        except openai.APIError as e:  # type: ignore[attr-defined]
            return f"[OpenAI API error] {e}"
        except Exception as e:
            return f"[OpenAI unexpected error] {e}"

        try:
            return (response.choices[0].message.content or "").strip() or "[OpenAI returned no text]"
        except Exception:
            return "[OpenAI returned unexpected response shape]"

    @staticmethod
    def ping(api_key: str | None = None) -> tuple[bool, str]:
        if openai is None:
            return False, "openai SDK not installed"
        key = api_key or settings_repository.get("openai_api_key")
        if not key:
            return False, "no API key configured"
        try:
            client = openai.OpenAI(api_key=key)
            client.models.list()
            return True, "ok"
        except openai.AuthenticationError:  # type: ignore[attr-defined]
            return False, "invalid API key"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
