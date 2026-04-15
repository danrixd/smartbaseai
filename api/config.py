"""Runtime configuration loaded from ``.env``.

This module is deliberately strict: for the provider credentials listed in
``ENV_ONLY_KEYS``, the ``.env`` file is treated as the **only** source of
truth. Shell/system environment variables leaking into the process are
explicitly unset after load so that removing a key from ``.env`` really
removes it, and so that tests or demos run against the committed ``.env``
rather than whatever happens to be in the operator's shell.

``SECRET_KEY`` itself still falls back to a default for test ergonomics.
"""

from __future__ import annotations

import os

try:
    from dotenv import dotenv_values, load_dotenv
except Exception:  # pragma: no cover - optional dependency
    dotenv_values = None  # type: ignore[assignment]
    load_dotenv = None  # type: ignore[assignment]

# Provider-credential keys that must come from .env only. Any pre-existing
# shell value for these is wiped so it can't be picked up by os.getenv()
# later. SECRET_KEY and JWT_ALGORITHM are intentionally NOT in this set —
# they fall through to shell env or the hard-coded fallback.
ENV_ONLY_KEYS = {
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OLLAMA_BASE_URL",
}


def _load_env_strict() -> None:
    """Load ``.env`` and strip any ENV_ONLY_KEYS that came from the shell.

    Idempotent — safe to call on every import. When ``python-dotenv`` is not
    installed this degrades to a no-op and we fall back to whatever the shell
    provides (which is fine for the dev fallback path; prod installs pin
    ``python-dotenv`` in requirements.txt).
    """
    if dotenv_values is None or load_dotenv is None:
        return

    dotenv_map = dotenv_values(".env") or {}

    for key in ENV_ONLY_KEYS:
        if key in dotenv_map:
            # .env supplies a value — let load_dotenv push it into os.environ
            # unconditionally, even if the shell already had one.
            continue
        # .env does NOT supply this key — make sure no shell value leaks.
        os.environ.pop(key, None)

    # Now actually populate os.environ from .env. override=True ensures values
    # in .env win over any shell value for keys that appear in .env.
    load_dotenv(override=True)


_load_env_strict()

SECRET_KEY: str = os.getenv("SECRET_KEY", "super_secret")
ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
