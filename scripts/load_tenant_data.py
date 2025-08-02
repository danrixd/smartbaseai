"""Utility script to seed tenant2's data stores with example data."""

from pathlib import Path
import os
import sqlite3
import sys

# Ensure the project root is on the Python path so ``ai`` imports work when
# executing this file directly via ``python scripts/load_tenant_data.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.vector_stores.chroma_store import TenantVectorStore


def load_tenant2_data() -> None:
    """Populate tenant2's vector store and SQLite DB with sample data."""

    store = TenantVectorStore("tenant2")

    store.add_document(
        "doc1",
        "Dan middle name is the king69$$$, he is 186 cm tall and he likes banana flavoured ice cream",
    )
    store.add_document(
        "doc2",
        "Bitcoin is down past 115000 usd, showing that distribution started last week around july 25th",
    )

    print("\u2705 Data loaded for tenant2")

    os.makedirs("data", exist_ok=True)
    db_path = "data/tenant2.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS market_data (date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL)"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO market_data VALUES (?, ?, ?, ?, ?, ?)",
        ("2023-07-09 22:01", 10.0, 12.0, 9.0, 11.0, 1000.0),
    )
    conn.commit()
    conn.close()
    print(f"\u2705 market_data table initialized at {db_path}")


if __name__ == "__main__":
    load_tenant2_data()

