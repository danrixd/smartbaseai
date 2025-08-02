import csv
import os
"""Utility script to seed tenant2's vector store with example data."""

from pathlib import Path
import sys
import argparse
# Ensure the project root is on the Python path so ``ai`` imports work when
# executing this file directly via ``python scripts/load_tenant_data.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import shutil
from ai.vector_stores.chroma_store import TenantVectorStore

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

def reset_vector_store(tenant_id):
    """Delete tenant's vector store folder before reload."""
    base_dir = os.path.join("vector_store", tenant_id)
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
        print(f"🗑️ Deleted existing vector store for tenant '{tenant_id}'.")

def load_csv_to_tenant(tenant_id, csv_file, show_progress=False):
    """Load CSV data into tenant vector store."""
    store = TenantVectorStore(tenant_id)

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        iterator = tqdm(reader, desc="📥 Loading documents", unit="doc") if show_progress and tqdm else reader

        for idx, row in enumerate(iterator, start=1):
            # Use row number as unique ID
            doc_id = f"row{idx}"
            text_parts = [f"{k}: {v}" for k, v in row.items()]
            text = ", ".join(text_parts)

            store.add_document(
                doc_id,
                text,
                {"source": csv_file}
            )

    print(f"✅ Loaded {len(reader)} documents into tenant '{tenant_id}' vector store.")

    return store

def verify_entry(store, search_term):
    """Verify if a specific entry exists in the vector store."""
    results = store.query(search_term)
    print(f"\n🔍 Search for '{search_term}' returned:")
    for r in results:
        print(" -", r)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tenant_id", help="Tenant ID")
    parser.add_argument("csv_file", help="Path to CSV file")
    parser.add_argument("--progress", action="store_true", help="Show progress bar")
    args = parser.parse_args()

    # Step 1: Delete old vector store
    reset_vector_store(args.tenant_id)

    # Step 2: Load CSV into vector store
    store = load_csv_to_tenant(args.tenant_id, args.csv_file, show_progress=args.progress)

    # Step 3: Verify a known date exists (adjust date format if needed)
    verify_entry(store, "2023-07-09 22:01")