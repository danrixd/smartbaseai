"""Key-value settings store backing the admin Settings UI.

Holds runtime configuration that should be editable without restarting the
backend — API keys, base URLs, default model choices. Values set here take
precedence over environment variables.

Secrets are stored in plaintext. That is acceptable for a single-operator
dev/demo deployment; for production, move the store to an encrypted backend
(KMS, Vault, SOPS) or at minimum encrypt the column at rest.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Dict, Iterable

DB_PATH = Path("data/system.db")

KNOWN_KEYS = {
    "anthropic_api_key",
    "openai_api_key",
    "ollama_base_url",
}


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    return conn


def get(key: str, default: str | None = None) -> str | None:
    """Return the stored setting, falling back to the matching env var, then default."""
    conn = _conn()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    finally:
        conn.close()
    if row and row[0]:
        return row[0]
    env_key = key.upper()
    return os.getenv(env_key, default)


def set_many(values: Dict[str, str]) -> None:
    """Upsert multiple settings. Empty string clears a setting (falls back to env)."""
    from datetime import datetime

    now = datetime.utcnow().isoformat()
    conn = _conn()
    try:
        for k, v in values.items():
            if k not in KNOWN_KEYS:
                continue
            if v == "":
                conn.execute("DELETE FROM settings WHERE key = ?", (k,))
            else:
                conn.execute(
                    "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (k, v, now),
                )
        conn.commit()
    finally:
        conn.close()


def all_masked() -> Dict[str, Dict[str, object]]:
    """Return every known setting with its value masked for display.

    Shape: ``{key: {"source": "db"|"env"|"unset", "has_value": bool, "preview": str}}``.
    Secrets are never returned in full — the UI only needs to confirm a value is present.
    """
    result: Dict[str, Dict[str, object]] = {}
    conn = _conn()
    try:
        rows = {
            k: v
            for k, v in conn.execute("SELECT key, value FROM settings").fetchall()
        }
    finally:
        conn.close()

    for key in KNOWN_KEYS:
        db_val = rows.get(key)
        env_val = os.getenv(key.upper())
        value = db_val or env_val
        if db_val:
            source = "db"
        elif env_val:
            source = "env"
        else:
            source = "unset"
        result[key] = {
            "source": source,
            "has_value": bool(value),
            "preview": _mask(value) if value and _is_secret(key) else (value or ""),
        }
    return result


def _is_secret(key: str) -> bool:
    return key.endswith("_api_key") or key.endswith("_token") or key.endswith("_secret")


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "••••"
    return f"{value[:4]}••••{value[-4:]}"
