import csv
"""Utility script to seed tenant2's vector store with example data."""

from pathlib import Path
import sys

# Ensure the project root is on the Python path so ``ai`` imports work when
# executing this file directly via ``python scripts/load_tenant_data.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.vector_stores.chroma_store import TenantVectorStore


def load_csv_to_tenant(tenant_id, csv_file):
    store = TenantVectorStore(tenant_id)

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            # יצירת מזהה אוטומטי
            doc_id = f"row{idx}"

            # שימוש בטקסט המתאים – נבנה מכול השדות
            text_parts = [f"{k}: {v}" for k, v in row.items()]
            text = ", ".join(text_parts)

            store.add_document(
                doc_id,
                text,
                {"source": csv_file}
            )

    print(f"✅ Loaded CSV data into tenant '{tenant_id}' vector store.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/load_csv_to_tenant.py <tenant_id> <csv_file>")
        sys.exit(1)

    tenant_id = sys.argv[1]
    csv_file = sys.argv[2]
    load_csv_to_tenant(tenant_id, csv_file)