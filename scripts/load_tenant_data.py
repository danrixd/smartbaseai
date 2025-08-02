"""Utility script to seed tenant2's vector store with example data."""

from pathlib import Path
import sys

# Ensure the project root is on the Python path so ``ai`` imports work when
# executing this file directly via ``python scripts/load_tenant_data.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.vector_stores.chroma_store import TenantVectorStore

def load_tenant2_data():
    store = TenantVectorStore("tenant2")

    store.add_document("doc1", "Dan middle name is the king69$$$, he is 186 cm tall and he likes banana flavoured ice cream")
    store.add_document("doc2", "Bitcoin is down past 115000 usd, showing that distribution started last week around july 25th")

    print("\u2705 Data loaded for tenant2")

if __name__ == "__main__":
    load_tenant2_data()
