"""Utility for routing queries to the correct tenant-specific data source.

``exact_lookup`` is the fast path the orchestrator uses when it detects a
specific entity in the user's message (a date, a date+time, or a ticker).
It tries to return a deterministic row from the tenant's structured store
so the LLM's answer can be grounded in the exact value, not retrieved prose.

Historical shape: fixed `market_data` table at `data/{tenant}.db` keyed by
a `YYYY-MM-DD HH:MM` date string.

New generalised shape: dispatches by tenant and table, supports:

* ``market_data(date, open, high, low, close, volume)`` — legacy (company
  vault, organization vault).
* ``daily_bars(ticker, date, open, high, low, close, volume)`` — the
  financebench tenant. Requires a ticker hint in the user message; matches
  ISO date-only (``YYYY-MM-DD``) OR ``YYYY-MM-DD HH:MM``.
* Any other table can be wired in by adding a resolver.

Retains backwards compatibility — the old signature still works, and
existing tests that monkey-patch ``TenantConfig`` and ``exact_lookup``
still pass.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Callable

from config.tenant_config import TenantConfig
from .connectors import (
    PostgresConnector,
    MySQLConnector,
    MongoDBConnector,
    APIConnector,
)


class QueryEngine:
    """Route queries to the appropriate connector based on tenant config."""

    CONNECTOR_MAP = {
        "postgres": PostgresConnector,
        "mysql": MySQLConnector,
        "mongodb": MongoDBConnector,
        "api": APIConnector,
    }

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        self.config = TenantConfig.get(tenant_id)
        db_type = self.config.get("db_type", "postgres")
        connector_cls = self.CONNECTOR_MAP.get(db_type)
        if connector_cls is None:
            raise ValueError(f"Unsupported db type: {db_type}")
        self.connector = connector_cls(self.config.get("db_config", {}))
        self.connector.connect()

    def execute(self, query: str, params=None):
        return self.connector.execute(query, params)

    def close(self) -> None:
        self.connector.close()


# ----------------------------------------------------------------------
# Pattern recognition


ISO_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
TICKER_PATTERN = re.compile(r"\b([A-Z]{1,5})\b")
# Common English words that happen to be 1-5 uppercase letters and should
# NOT be treated as ticker hints.
TICKER_STOPWORDS = {
    "A", "I", "IS", "IN", "OF", "ON", "AT", "AS", "BY", "TO", "IF", "IT",
    "OR", "SO", "DO", "NO", "US", "AM", "PM", "BE", "AN", "GO", "FY", "Q",
    "Q1", "Q2", "Q3", "Q4", "USD", "THE", "FOR", "AND", "WAS", "HAS",
    "ARE", "HOW", "WHO", "WHY", "WHAT", "WHEN",
}


def _detect_ticker(message: str) -> str | None:
    """Try to pull an uppercase stock ticker hint out of the message."""
    for m in TICKER_PATTERN.finditer(message):
        candidate = m.group(1)
        if candidate in TICKER_STOPWORDS:
            continue
        return candidate
    return None


# ----------------------------------------------------------------------
# Structured DB lookup resolvers


def _lookup_market_data(db_path: Path, date_str: str) -> dict:
    """Legacy path: one market_data table keyed by date string only."""
    if not db_path.exists():
        return {}
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM market_data WHERE date = ? LIMIT 1",
            (date_str,),
        )
        row = cur.fetchone()
        conn.close()
    except Exception:
        return {}
    if not row:
        return {}
    columns = ["date", "open", "high", "low", "close", "volume"]
    return dict(zip(columns, row))


def _lookup_daily_bars(
    db_path: Path,
    ticker: str,
    date_str: str,
) -> dict:
    """financebench path: daily_bars(ticker, date, open, high, low, close, volume).

    Accepts date-only (YYYY-MM-DD) or date+time (YYYY-MM-DD HH:MM) inputs
    and normalises to date-only for matching, since daily bars have no
    intraday resolution.
    """
    if not db_path.exists():
        return {}
    date_only = date_str[:10]
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT ticker, date, open, high, low, close, volume "
            "FROM daily_bars WHERE ticker = ? AND date = ? LIMIT 1",
            (ticker, date_only),
        )
        row = cur.fetchone()
        conn.close()
    except Exception:
        return {}
    if not row:
        return {}
    return {
        "ticker": row[0],
        "date": row[1],
        "open": row[2],
        "high": row[3],
        "low": row[4],
        "close": row[5],
        "volume": row[6],
        "table": "daily_bars",
    }


# ----------------------------------------------------------------------
# Main dispatcher


def exact_lookup(date_str: str, tenant_id: str, table: str = "market_data", **extra) -> dict:
    """Resolve an exact row for ``date_str`` in the tenant's structured DB.

    Tries in order:

    1. If ``tenant_id`` is a known financebench tenant AND a ticker hint is
       present in ``extra['ticker']`` or in ``extra['message']``, look it up
       in ``financebench.db#daily_bars``.
    2. Fall back to ``data/{tenant_id}.db#market_data`` keyed by the raw date
       string (legacy path).

    Returns an empty dict if nothing matches. Never raises — callers treat
    an empty result as "no exact match, fall through to RAG".
    """
    # Tier 1 — ticker-aware lookup for financebench
    if tenant_id == "financebench":
        ticker = extra.get("ticker")
        if not ticker and extra.get("message"):
            ticker = _detect_ticker(extra["message"])
        if ticker:
            row = _lookup_daily_bars(Path("data/financebench.db"), ticker, date_str)
            if row:
                return row

    # Tier 2 — legacy market_data path
    db_path = Path(f"data/{tenant_id}.db")
    return _lookup_market_data(db_path, date_str)
