# TODO

Ideas surfaced during the upgrade / polish pass. None of these are scoped for the current branch — they're a backlog, not a plan.

## Polish still to do
- Capture a demo GIF of the running app (login → upload doc → chat → DB-lookup answer) and embed in the README.
- Add 3–5 PNG screenshots to `docs/screenshots/` (login, chat, files, admin).
- Run `gh repo edit` to set topics and description (commands drafted in `docs/gh-repo-edit.sh`).
- Consider a public demo instance on Fly.io / Railway and link from README.

## Bugs worth fixing
- `datetime.utcnow()` is deprecated and spams 70+ warnings during test runs. Migrate to `datetime.now(UTC)` in `db/*_repository.py`, `api/routes_auth.py`, and `ingestion/metadata_generator.py`.
- `requirements.txt` has no version pins — reproducibility will drift. Pin or move to `pyproject.toml` + `uv lock`.
- `ui/web` and `ui/admin_panel` are stale Next.js skeletons that are no longer referenced — delete or clearly mark as deprecated.
- `config/tenant_config.py` is imported by `db/query_engine.py` but the **actual** orchestrator uses `exact_lookup` which reads `data/<tenant>.db` directly and ignores tenant config. These two code paths should converge.
- CORS `origins` in `api/app.py` only includes `http://localhost:5173` — add `http://127.0.0.1:5173` and make configurable via env.
- `SECRET_KEY` still has a `"super_secret"` fallback for test ergonomics. Production mode should refuse to start without one.

## Feature ideas
- Binary file ingestion: PDF → text (pdfminer / pypdf), DOCX → text (python-docx), then push through the same ingest path as `.txt`.
- Chunking strategy: current upload ingestion stores the **whole file** as one document. Should chunk on ~500 token windows with overlap for better retrieval.
- Streaming responses from the LLM back to the frontend (SSE).
- Model routing: allow a tenant to use different models for cheap/retrieval vs. final generation.
- Intent recognition is a stub — wire `chatbot/intent_recognition.py` into the orchestrator so non-RAG intents (e.g. "show me my files") route to structured handlers instead of the LLM.
- Audit log viewer in the admin UI.
- Rate limiting per tenant.
- Switch SQLite system DB to a proper Postgres for production deploys.

## Tests worth adding
- End-to-end test that exercises the full three-source fusion (DB + RAG + history) — currently `tests/test_api.py` covers each in isolation but not the merge.
- Test for the tenant-visibility fix: create tenant via admin route, immediately chat under it, assert 200 not 404.
- Test for upload → chat retrieval roundtrip (the new auto-ingest path).
