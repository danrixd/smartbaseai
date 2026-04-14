#!/usr/bin/env python3
"""Standalone Phase 6 runner for the financebench loader.

The full loader (scripts/load_financebench.py) reliably reaches the end of
Phase 5 (SEC EDGAR) and then segfaults at the Phase 6 transition — almost
certainly native-level state left over from pyrate-limiter / requests inside
sec-edgar-downloader. Running the ingest in a fresh Python process avoids it.

Usage:
    python scripts/ingest_financebench.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Force CPU before any torch / chromadb import
os.environ["CUDA_VISIBLE_DEVICES"] = ""

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Import only the chunker + ingest from the big loader — and nothing else
# (specifically NOT yfinance / sec_edgar_downloader / pypdf which brought in
# the state that was crashing).
from scripts.load_financebench import DATA, MAX_CHUNK_CHARS, TENANT_ID, chunk_text  # noqa: E402


def ensure_tenant_and_user() -> None:
    from db import user_repository
    from tenants.tenant_manager import TenantManager

    tm = TenantManager()
    models = [
        {"provider": "ollama", "name": "llama3", "label": "Local Llama 3"},
        {"provider": "openai", "name": "gpt-4o-mini", "label": "GPT-4o mini"},
        {"provider": "anthropic", "name": "claude-opus-4-6", "label": "Claude Opus 4.6"},
    ]
    cfg = {
        "name": "S&P 500 Fundamentals",
        "description": "SEC 10-K filings + daily bars + company profiles.",
        "db_type": "sqlite",
        "db_config": {"path": "data/financebench.db"},
        "models": models,
        "model_type": models[0]["provider"],
        "model_name": models[0]["name"],
    }
    if tm.get(TENANT_ID) is None:
        tm.create(TENANT_ID, cfg)
        print(f"[tenant] created '{TENANT_ID}'")
    else:
        tm.update(TENANT_ID, cfg)
        print(f"[tenant] updated '{TENANT_ID}'")

    if user_repository.get_user("fbuser") is None:
        user_repository.create_user("fbuser", "FbUser123!", "user", TENANT_ID)
        print("[user] created fbuser / FbUser123!")


def main() -> int:
    try:
        from tqdm import tqdm
    except Exception:
        def tqdm(it, **_):
            return it

    ensure_tenant_and_user()

    # Import TenantVectorStore last so CUDA_VISIBLE_DEVICES is already set
    from ai.vector_stores.chroma_store import TenantVectorStore

    store = TenantVectorStore(TENANT_ID)
    try:
        existing = store.collection.get(include=["metadatas"])
        if existing and existing.get("ids"):
            store.collection.delete(ids=existing["ids"])
            print(f"[ingest] wiped {len(existing['ids'])} stale vectors")
    except Exception as e:
        print(f"[ingest] wipe skipped: {type(e).__name__}: {e}")

    md_files = sorted(DATA.rglob("*.md"))
    print(f"[ingest] {len(md_files)} markdown files to process")

    n_files = 0
    n_chunks = 0
    n_skipped = 0
    batch_ids: list[str] = []
    batch_docs: list[str] = []
    batch_metas: list[dict] = []
    BATCH = 32

    def flush() -> int:
        if not batch_ids:
            return 0
        try:
            store.collection.add(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
            n = len(batch_ids)
        except Exception as e:
            print(f"  [batch-error] {len(batch_ids)} docs: {type(e).__name__}: {str(e)[:120]}")
            # Fall back to one-by-one
            n = 0
            for i, did in enumerate(batch_ids):
                try:
                    store.collection.add(
                        ids=[did], documents=[batch_docs[i]], metadatas=[batch_metas[i]]
                    )
                    n += 1
                except Exception as ee:
                    print(f"    [single-error] {did}: {ee}")
        batch_ids.clear()
        batch_docs.clear()
        batch_metas.clear()
        return n

    for path in tqdm(md_files, desc="[ingest]"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"  [read-error] {path.name}: {e}")
            n_skipped += 1
            continue
        if not text.strip():
            n_skipped += 1
            continue

        ticker = path.parent.name
        filename = path.name
        base_id = f"{TENANT_ID}:{ticker}/{filename}"
        try:
            chunks = chunk_text(text, target_tokens=500)
        except Exception as e:
            print(f"  [chunk-error] {ticker}/{filename}: {e}")
            n_skipped += 1
            continue

        file_added = False
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            chunk = chunk[:MAX_CHUNK_CHARS]
            batch_ids.append(f"{base_id}#{i}")
            batch_docs.append(chunk)
            batch_metas.append(
                {
                    "tenant": TENANT_ID,
                    "ticker": ticker,
                    "filename": filename,
                    "path": f"{ticker}/{filename}",
                    "chunk_idx": i,
                    "source": "financebench-loader",
                }
            )
            file_added = True
            if len(batch_ids) >= BATCH:
                n_chunks += flush()
        if file_added:
            n_files += 1
        else:
            n_skipped += 1

    n_chunks += flush()

    print("\n" + "=" * 60)
    print(f"INGEST DONE — files: {n_files}, chunks: {n_chunks}, skipped: {n_skipped}")
    print(f"Collection size: {store.collection.count()}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
