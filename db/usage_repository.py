"""Per-tenant/user LLM usage tracking for rate limiting + cost display.

Tracks token counts per request tagged with tenant, user, provider, model,
plus wall-clock latency. Writes to ``data/system.db#llm_usage``. The admin
can see daily rollups; the rate-limit middleware uses the day's total
token count against a per-tenant cap (default: unlimited).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("data/system.db")

# Approximate blended prices per 1M tokens (USD). Used for the admin
# display only — NOT authoritative. Replace with Anthropic/OpenAI model
# prices for your actual plan.
PRICES_PER_1M = {
    "anthropic": {
        "claude-opus-4-6": {"input": 5.0, "output": 25.0},
        "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
        "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    },
    "openai": {
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "gpt-4o": {"input": 2.5, "output": 10.0},
    },
    "ollama": {},  # free, local
}


def _init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            username TEXT NOT NULL,
            provider TEXT NOT NULL,
            model_name TEXT NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cache_read_tokens INTEGER NOT NULL DEFAULT 0,
            cache_create_tokens INTEGER NOT NULL DEFAULT 0,
            latency_ms REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_usage_tenant ON llm_usage(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_usage_day ON llm_usage(created_at)")
    return conn


def record(
    *,
    tenant_id: str,
    username: str,
    provider: str,
    model_name: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_create_tokens: int = 0,
    latency_ms: float = 0.0,
) -> None:
    conn = _init_db()
    try:
        conn.execute(
            """
            INSERT INTO llm_usage (
                tenant_id, username, provider, model_name,
                input_tokens, output_tokens, cache_read_tokens, cache_create_tokens,
                latency_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                username,
                provider,
                model_name,
                int(input_tokens or 0),
                int(output_tokens or 0),
                int(cache_read_tokens or 0),
                int(cache_create_tokens or 0),
                float(latency_ms or 0),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def today_token_total(tenant_id: str) -> int:
    """Total billable tokens (input + output) for this tenant today (UTC)."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = _init_db()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(input_tokens + output_tokens), 0)
            FROM llm_usage
            WHERE tenant_id = ? AND substr(created_at, 1, 10) = ?
            """,
            (tenant_id, day),
        ).fetchone()
        return int(row[0] or 0)
    finally:
        conn.close()


def estimate_cost_usd(
    provider: str, model_name: str, input_tokens: int, output_tokens: int
) -> float:
    prices = PRICES_PER_1M.get(provider, {}).get(model_name)
    if not prices:
        return 0.0
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


def rollup(limit: int = 30) -> list[dict]:
    """Per-tenant per-day aggregate for the admin Usage view."""
    conn = _init_db()
    try:
        rows = conn.execute(
            """
            SELECT
                substr(created_at, 1, 10) AS day,
                tenant_id,
                provider,
                model_name,
                SUM(input_tokens) AS input_t,
                SUM(output_tokens) AS output_t,
                SUM(cache_read_tokens) AS cache_read_t,
                SUM(cache_create_tokens) AS cache_create_t,
                COUNT(*) AS request_count,
                AVG(latency_ms) AS avg_latency_ms
            FROM llm_usage
            GROUP BY day, tenant_id, provider, model_name
            ORDER BY day DESC, tenant_id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        cost = estimate_cost_usd(r[2], r[3], int(r[4] or 0), int(r[5] or 0))
        out.append(
            {
                "day": r[0],
                "tenant_id": r[1],
                "provider": r[2],
                "model_name": r[3],
                "input_tokens": int(r[4] or 0),
                "output_tokens": int(r[5] or 0),
                "cache_read_tokens": int(r[6] or 0),
                "cache_create_tokens": int(r[7] or 0),
                "request_count": int(r[8] or 0),
                "avg_latency_ms": float(r[9] or 0),
                "est_cost_usd": round(cost, 4),
            }
        )
    return out
