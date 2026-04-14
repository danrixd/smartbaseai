# Changelog

All notable changes to SmartBaseAI are documented here. Dates are approximate and derived from git history.

## [Unreleased] — upgrade branch

### Fixed
- **`SECRET_KEY` now read from the environment.** Both `api/routes_auth.py` and `api/auth_middleware.py` previously hardcoded `"super_secret"`, silently ignoring the `.env` value. A new `api/config.py` centralizes the setting and loads `.env` via `python-dotenv` when available.
- **File uploads are now ingested into the tenant vector store.** `POST /files/upload` previously only wrote the file to disk. Text formats (`.txt`, `.md`, `.csv`, `.log`) are now pushed through `TenantVectorStore.add_document` so uploaded content is immediately searchable by chat. Unsupported binary formats still save cleanly and log a skip.
- **Tenants created via the admin API are now immediately visible to the chat route.** `TenantManager` previously cached `tenants.json` in memory at construction time, so the `tenant_manager` instance owned by `routes_chat.py` never saw tenants created via the `manager` instance owned by `routes_admin.py` until the process restarted. Now `TenantManager` re-reads storage on every call.
- **Duplicate tenant / user creation returns `409 Conflict`** instead of surfacing a `ValueError` as a generic `500`.

### Added
- `scripts/smoke_test.py` — end-to-end test that exercises auth, admin, tenant CRUD, user CRUD, file upload with ingestion, chat RAG path, and chat DB-lookup path against a live server.
- `docs/architecture.md` with a Mermaid diagram of the orchestration flow.
- Recruiter-facing `README.md` rewrite — hero, elevator pitch, quickstart, tech stack, contact.
- `TODO.md` for out-of-scope ideas surfaced during polish.

### Changed
- `python-dotenv` added to `requirements.txt`.

---

## Historical milestones (from git log)

### Auth and multi-tenancy
- JWT auth with role-based access (`super_admin` / `admin` / `user`)
- Multi-tenant user model scoped by `tenant_id`
- Legacy plaintext password migration with bcrypt rehash on verify
- Schema migrations for legacy `users` tables (rename `password` → `hashed_password`, backfill timestamps)

### Retrieval + orchestration
- `ResponseGenerator` introduced as the three-source orchestrator (history + DB + RAG)
- Fusion layer — DB-preferred with RAG as supplemental context
- Persistent per-tenant Chroma vector store via `TenantVectorStore`
- Hybrid search (keyword ∪ semantic) returned in Chroma-compatible format
- `exact_lookup` fast path for date-keyed structured queries (`data/<tenant>.db`)
- CUDA auto-detected for `sentence-transformers` with CPU fallback

### Model backends
- Ollama integration with real HTTP calls and streaming-JSON handling
- OpenAI and Anthropic model wrappers under `ai/models/`
- Local Llama support

### Data ingestion
- `ETLManager` with pluggable connectors (Postgres / MySQL / MongoDB / HTTP API)
- Cleaners + metadata generator
- Script to load CSV data into a tenant's structured sample DB

### API
- FastAPI app with routers for auth, chat, admin, and files
- CORS middleware
- Conversation + audit log repositories (SQLite)
- Tenant listing and per-tenant chat session management

### Frontend
- React 19 + Vite + Tailwind frontend under `frontend/`
- Login, chat, files, and admin pages with role-aware views
- Axios client with configurable `VITE_API_BASE_URL`
- Tenant selection for super-admins, persistent chat sessions

### Testing
- `pytest` suites for AI pipeline, API routes, ingestion, hybrid search, and user migration
