"""Seed three demo knowledge vaults that illustrate multi-level tenancy.

Tenants created (idempotent — re-running only updates what's missing):

* ``personal``     — a single-user knowledge vault (habits, goals, contacts).
* ``company``      — Acme Analytics corporate docs + market-data CSV.
* ``organization`` — fictional Project Lunar Harbor (Moon program) with a
                     work plan and non-public contingency procedures.

Each tenant owns its own isolated Chroma collection under ``vector_store/``,
its own SQLite structured DB under ``data/{tenant}.db``, and its own
default user. A single super_admin (``admin``) can see all three via the
admin UI.

    python scripts/seed_demo.py
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.vector_stores.chroma_store import TenantVectorStore
from db import user_repository
from tenants.tenant_manager import TenantManager

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MODELS = [
    {"provider": "ollama", "name": "llama3", "label": "Local Llama 3"},
    {"provider": "openai", "name": "gpt-4o-mini", "label": "GPT-4o mini"},
    {"provider": "anthropic", "name": "claude-opus-4-6", "label": "Claude Opus 4.6"},
]

VAULTS = [
    {
        "id": "personal",
        "name": "Personal Knowledge Vault",
        "source_dir": ROOT / "data" / "personal",
        "user": ("alice", "Alice123!"),
        "description": "A single user's private notes, routines, and contacts.",
    },
    {
        "id": "company",
        "name": "Acme Analytics — Company Vault",
        "source_dir": ROOT / "data" / "demo",
        "user": ("demo", "Demo123!"),
        "description": "Acme Analytics product docs, policies, FAQ, and market data.",
    },
    {
        "id": "organization",
        "name": "Project Lunar Harbor — Organization Vault",
        "source_dir": ROOT / "data" / "organization",
        "user": ("orion", "Orion123!"),
        "description": "Fictional multi-agency Moon program: mission overview, work plan, non-public contingencies.",
    },
    {
        "id": "relativity",
        "name": "General Relativity Research Vault",
        "source_dir": ROOT / "data" / "relativity",
        "user": ("einat", "Einat123!"),
        "description": "Lab notebook, Hubble-tension notes, ringdown method, reading list.",
    },
    {
        "id": "saas-ai",
        "name": "SaaS in the Age of AI",
        "source_dir": ROOT / "data" / "saas-ai",
        "user": ("nadav", "Nadav123!"),
        "description": "Unit economics, competitive moats, and a pricing playbook for AI-native SaaS.",
    },
    {
        "id": "smartbase-docs",
        "name": "SmartBaseAI — Product Documentation",
        "source_dir": ROOT / "data" / "smartbase-docs",
        "user": ("docs", "Docs1234!"),
        "description": "How to use SmartBaseAI, what the RAG Visualizer shows, and the company value pitch.",
    },
]

INGESTIBLE_SUFFIXES = {".md", ".txt", ".csv", ".log", ".markdown"}


def ensure_tenant(vault: dict) -> None:
    tm = TenantManager()
    existing = tm.get(vault["id"])
    config = {
        "name": vault["name"],
        "description": vault["description"],
        "db_type": "sqlite",
        "db_config": {"path": f"data/{vault['id']}.db"},
        "models": DEFAULT_MODELS,
        "model_type": DEFAULT_MODELS[0]["provider"],
        "model_name": DEFAULT_MODELS[0]["name"],
    }
    if existing is None:
        tm.create(vault["id"], config)
        print(f"[tenant] created '{vault['id']}'")
    else:
        # Re-save so existing tenants pick up the new models[] array.
        existing.update(
            {
                "name": vault["name"],
                "description": vault["description"],
                "models": DEFAULT_MODELS,
            }
        )
        existing.setdefault("model_type", DEFAULT_MODELS[0]["provider"])
        existing.setdefault("model_name", DEFAULT_MODELS[0]["name"])
        from tenants.tenant_storage import TenantStorage

        all_tenants = TenantStorage.load()
        all_tenants[vault["id"]] = existing
        TenantStorage.save(all_tenants)
        print(f"[tenant] '{vault['id']}' updated with models[] array")


def ensure_user(vault: dict) -> None:
    username, password = vault["user"]
    if user_repository.get_user(username) is not None:
        print(f"[user] '{username}' already exists")
        return
    user_repository.create_user(username, password, "user", vault["id"])
    print(f"[user] created '{username}' / '{password}' (tenant={vault['id']})")


def ingest_documents(vault: dict) -> int:
    source_dir: Path = vault["source_dir"]
    if not source_dir.exists():
        print(f"[ingest] source dir missing: {source_dir}")
        return 0
    store = TenantVectorStore(vault["id"])
    count = 0
    for path in sorted(source_dir.glob("*")):
        if path.suffix.lower() not in INGESTIBLE_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            continue
        # Use stable doc_id so re-ingest replaces rather than duplicating
        doc_id = f"{vault['id']}:{path.name}"
        try:
            store.collection.delete(ids=[doc_id])
        except Exception:
            pass
        store.add_document(
            doc_id,
            text,
            {"filename": path.name, "source": "seed", "tenant": vault["id"]},
        )
        count += 1
        print(f"[ingest] {vault['id']}/{path.name}")
    return count


def seed_structured_db(vault: dict) -> None:
    csv_path: Path | None = None
    for name in ("market-data.csv", "06-market-data.csv", "05-telemetry.csv"):
        candidate = vault["source_dir"] / name
        if candidate.exists():
            csv_path = candidate
            break
    if csv_path is None:
        return

    db_path = Path(f"data/{vault['id']}.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        # Accept either the market-data shape or the telemetry shape
        if {"date", "open", "high", "low", "close", "volume"} <= set(fields):
            conn.execute(
                "CREATE TABLE IF NOT EXISTS market_data ("
                "date TEXT PRIMARY KEY, open REAL, high REAL, low REAL, close REAL, volume REAL)"
            )
            conn.execute("DELETE FROM market_data")
            rows = [
                (r["date"], float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]), float(r["volume"]))
                for r in reader
            ]
            conn.executemany("INSERT INTO market_data VALUES (?, ?, ?, ?, ?, ?)", rows)
        elif "date" in fields and "anomaly_code" in fields:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS market_data ("
                "date TEXT PRIMARY KEY, open REAL, high REAL, low REAL, close REAL, volume REAL)"
            )
            conn.execute("DELETE FROM market_data")
            # Map telemetry into the market_data shape so the existing exact_lookup path still works.
            rows = [
                (
                    r["date"],
                    float(r.get("battery_volts") or 0),
                    float(r.get("battery_volts") or 0),
                    float(r.get("battery_volts") or 0),
                    float(r.get("battery_volts") or 0),
                    float(r.get("solar_watts") or 0),
                )
                for r in reader
            ]
            conn.executemany("INSERT INTO market_data VALUES (?, ?, ?, ?, ?, ?)", rows)
        else:
            conn.close()
            return
    conn.commit()
    conn.close()
    print(f"[structured] loaded {csv_path.name} into {db_path}")


def main() -> None:
    for vault in VAULTS:
        ensure_tenant(vault)
        ensure_user(vault)
        n = ingest_documents(vault)
        seed_structured_db(vault)
        print(f"  -> {n} docs in '{vault['id']}'\n")

    print("Seed complete. Logins:")
    for v in VAULTS:
        u, p = v["user"]
        print(f"  {v['id']:13s}  {u} / {p}")
    print("  super_admin  admin / ChangeThis123! (cross-tenant)")


if __name__ == "__main__":
    main()
