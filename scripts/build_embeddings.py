#!/usr/bin/env python3
"""Generate embeddings for ingested records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on the path when executed directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.etl_manager import ETLManager
from ai.embeddings import OpenAIEmbeddings, LocalEmbeddings, HuggingFaceEmbeddings


EMBEDDER_MAP = {
    "openai": OpenAIEmbeddings,
    "local": LocalEmbeddings,
    "huggingface": HuggingFaceEmbeddings,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build embeddings for data")
    parser.add_argument("--db-type", default="postgres", help="Data source type")
    parser.add_argument(
        "--db-config",
        default="{}",
        help="JSON string with connector configuration",
    )
    parser.add_argument("--source", required=True, help="Source identifier/query")
    parser.add_argument(
        "--embedder",
        choices=list(EMBEDDER_MAP.keys()),
        default="local",
        help="Embedding backend to use",
    )
    parser.add_argument(
        "--dimension", type=int, default=3, help="Embedding vector dimension"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="File to write embeddings to"
    )
    args = parser.parse_args()

    try:
        db_config = json.loads(args.db_config)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON for --db-config: {exc}")

    etl = ETLManager(args.db_type, db_config)
    records = etl.run(args.source)
    etl.close()

    embedder_cls = EMBEDDER_MAP[args.embedder]
    embedder = embedder_cls(dimension=args.dimension)

    texts = [r["text"] for r in records]
    metadata = [r["metadata"] for r in records]
    vectors = embedder.embed(texts)

    output_data = [
        {"embedding": vec, "metadata": meta} for vec, meta in zip(vectors, metadata)
    ]
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"Wrote {len(output_data)} embeddings to {args.output}")


if __name__ == "__main__":
    main()

    # Example usage of a persistent tenant vector store
    from ai.vector_stores.chroma_store import TenantVectorStore

    store = TenantVectorStore("tenant1")
    store.add_document(
        "doc1",
        "Dan middle name is the king69$$$, he is 186 cm tall and he likes banana flavoured ice cream",
    )
    store.add_document(
        "doc2",
        "Bitcoin is down past 115000 usd, showing that distribution started last week around july 25th",
    )
