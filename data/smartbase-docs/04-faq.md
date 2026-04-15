# SmartBaseAI — FAQ

## How many LLM providers does it support?

Three, pluggable via the same `ResponseGenerator.MODELS` registry:
- **Ollama** (local) — any Ollama model.
- **OpenAI** — any chat model via the official Python SDK (default `gpt-4o-mini`).
- **Anthropic** — any Claude model via the official Python SDK (default `claude-opus-4-6` with adaptive thinking and prompt caching on the stable system prompt).

Any tenant can have **multiple** providers and models configured at once; users pick the model at chat time from a dropdown in the chat page.

## Which data sources can be ingested?

The bulk ETL path (`ingestion/etl_manager.py`) supports Postgres, MySQL, MongoDB, and generic HTTP APIs. For per-user upload via the Vault page, any UTF-8 text file is supported (`.md`, `.txt`, `.csv`, `.log`).

## How is data isolated between tenants?

Each tenant has:
- Its own directory under `vector_store/{tenant_id}/` containing a persistent Chroma collection.
- Its own SQLite database under `data/{tenant_id}.db` for structured lookups.
- Its own vault directory under `data/{tenant_id}/` (or `data/vaults/{tenant_id}/` for non-seeded tenants).
- Its own set of users, scoped by `tenant_id` in the users table and enforced in every route.

Cross-tenant access is only possible for the `super_admin` role, and the super-admin must explicitly pick a vault from the top-right dropdown — there is no automatic "show everything" view.

## Is the chat grounded or does it hallucinate?

Grounded. The orchestrator calls the LLM with a Context block that includes the exact DB row (if a date matches) and the hybrid-retrieved documents. If both the DB and the RAG retrieval are empty, the orchestrator returns an explicit `"No information"` and does not call the LLM at all.

## What does "re-ingest" mean?

When a file in the vault is edited or a new file is uploaded, the backend drops the old vector from the tenant's Chroma collection and embeds the new content under the same stable `doc_id` (`{tenant}:{filename}`). No duplicate vectors accumulate, and subsequent queries use the updated content immediately.

## How do I run it locally?

    pip install -r requirements.txt
    python scripts/run_server.py --reload    # backend on :8000
    cd frontend && npm install && npm run dev  # frontend on :5173
    python scripts/seed_demo.py              # optional: seed six demo vaults

## Where can I find the source?

`https://github.com/danrixd/smartbaseai`
