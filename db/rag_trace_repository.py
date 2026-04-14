"""Persistent storage for RAG visualizer traces.

A saved trace captures the full /chat/trace response for a single query so
it can be reloaded later without re-running the pipeline. Useful for:

* Sharing a "look at this retrieval behavior" example with someone else
* Demonstrating RAG quality on expensive LLM backends (Claude/OpenAI) once,
  then showing the result in perpetuity without spending tokens
* Keeping a regression set of interesting queries for each tenant

Stored in data/system.db alongside users/settings. One row per trace; the
full trace JSON goes into the ``trace_json`` column so that reload is a pure
table read with no re-ingest.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path("data/system.db")


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            title TEXT NOT NULL,
            query TEXT NOT NULL,
            reply TEXT NOT NULL,
            trace_json TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_traces_tenant ON rag_traces(tenant_id)")
    return conn


def save_trace(
    *,
    tenant_id: str,
    title: str,
    query: str,
    reply: str,
    trace: dict[str, Any],
    created_by: str,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    conn = _conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO rag_traces (tenant_id, title, query, reply, trace_json, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                title or query[:80],
                query,
                reply or "",
                json.dumps(trace, ensure_ascii=False),
                created_by,
                now,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def list_traces(tenant_id: str | None = None) -> list[dict]:
    """Return metadata rows only (no trace_json) for the sidebar list."""
    conn = _conn()
    try:
        if tenant_id:
            rows = conn.execute(
                """
                SELECT id, tenant_id, title, query, created_by, created_at, length(reply) AS reply_len
                FROM rag_traces
                WHERE tenant_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (tenant_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, tenant_id, title, query, created_by, created_at, length(reply) AS reply_len
                FROM rag_traces
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r[0],
            "tenant_id": r[1],
            "title": r[2],
            "query": r[3],
            "created_by": r[4],
            "created_at": r[5],
            "reply_len": r[6],
        }
        for r in rows
    ]


def get_trace(trace_id: int) -> dict | None:
    conn = _conn()
    try:
        row = conn.execute(
            """
            SELECT id, tenant_id, title, query, reply, trace_json, created_by, created_at
            FROM rag_traces WHERE id = ?
            """,
            (trace_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    try:
        trace = json.loads(row[5])
    except Exception:
        trace = {}
    return {
        "id": row[0],
        "tenant_id": row[1],
        "title": row[2],
        "query": row[3],
        "reply": row[4],
        "trace": trace,
        "created_by": row[6],
        "created_at": row[7],
    }


def delete_trace(trace_id: int) -> bool:
    conn = _conn()
    try:
        cur = conn.execute("DELETE FROM rag_traces WHERE id = ?", (trace_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
