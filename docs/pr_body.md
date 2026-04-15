Long-running `upgrade` branch — 19 commits that take SmartBaseAI from a half-documented starter kit with mocked model wrappers into a working multi-tenant knowledge platform with real LLM providers, interactive retrieval visualization, a 506-company fundamental-analysis demo, and a full operational surface (audit log, usage tracking, cross-tenant search, session timeout handling, rate limiting, structured logging).

## Headline highlights

- **6 seeded knowledge vaults** (`personal`, `company` / Acme Analytics, `organization` / Project Lunar Harbor, `relativity`, `saas-ai`, `smartbase-docs`) plus one large-scale vault `financebench` with **506 S&P 500 companies**, **1,241 markdown files**, **197,201 Chroma vectors**, **1.23 M daily bar rows**, and **150 ground-truth Q&A** pulled from the FinanceBench open-source benchmark.

- **Real LLM providers** — `AnthropicModel` / `OpenAIModel` / `OllamaModel` now call the live SDKs (was mocked). Anthropic defaults to `claude-opus-4-6` with `cache_control: ephemeral` on the system prompt per the `claude-api` skill guidance, logs `cache_read_input_tokens` per response for verification. Tenants can declare multiple providers; users pick at chat time via a dropdown, with per-request override threaded through `/chat/message` and `/chat/trace`.

- **RAG Visualizer** (new page) — live view of a single query flowing through the three-source orchestrator. Shows the vector-store info strip (tenant, collection, **vector count**, embedding model, device), full semantic candidate ranking with **L2 distance bars**, keyword hits, fusion block, assembled prompt, and LLM reply. Persist traces with 💾 Save trace, reload later without re-running the LLM (**zero-token replay** for demos). Export to JSON / Markdown.

- **Interactive Vault editor** — 1,744-file tree browser with live search (`components/FileTree.jsx`), collapsible per-ticker folders, inline match highlighting, markdown edit/split/preview toggle, bulk upload, automatic section-aware re-chunk + re-embed on save.

- **Generalised `exact_lookup`** — the DB-preferred fusion fast path now dispatches by tenant and table. Financebench queries with a ticker hint (sniffed from the message) hit `daily_bars(ticker, date, open, high, low, close, volume)` and return the exact row. Verified live: *"AAPL closing price on 2024-06-14"* → `close=212.49, volume=70.1M` directly from SQLite, RAG retrieval runs as supplemental context only.

- **FinanceBench eval harness** (`scripts/eval_financebench.py`) — runs the 150 ground-truth questions through `/chat/message`, scores with three strategies (numeric 2% tolerance, substring, optional Claude-as-judge), writes `docs/financebench_eval.md` with headline accuracy, per-question-type breakdown, latency stats, and sample failures.

- **Production surface** — structured logging with request-id middleware, per-tenant daily token cap with 429 on overage, usage rollup (`/admin/usage`), audit log viewer (`/admin/audit-log`), cross-tenant search (`/admin/search`), session-timeout redirect, error boundary, strict `.env` loader that refuses to leak shell env vars.

## Commits (newest first)

```
911f140  fix(eval): ASCII-only progress output to avoid Windows cp1252 crash
e91e3c7  feat: T2/T3/T4 sweep — 16 of the 17 outstanding gap-analysis items
d5c312d  fix(privacy): don't leak absolute filesystem paths into vault content
94738da  feat: persist RAG traces so they can be replayed without spending tokens
b7f04bc  feat(ui): interactive file tree with search + collapsible folders for Vault
c026ab0  fix(files): recursive vault listing + nested-path routes + financebench mapping
b0730c1  fix(loader): standalone ingest script to sidestep native-state segfault
fd04398  fix(loader): resilient SP500 fetch + bounded chunker + CPU ingest fallback
83835a1  feat(demo): load_financebench.py — SEC 10-Ks + S&P 500 bars/profiles loader
8007c34  docs+test: recruiter README, CHANGELOG, architecture doc, smoke scripts, test adapts
5a8a702  feat(frontend): RAG visualizer, Vault editor, Settings page, live API status, vault-selection gate
6a5db9e  feat(demo): six seeded knowledge vaults
1b0e600  feat(backend): real LLM SDKs, multi-model per tenant, settings store, vault CRUD
7b5eddd  chore(repo): gitignore runtime state, untrack vector_store + sqlite dbs
```

## Test state

- **pytest: 24 / 24** green. Deprecation warning count dropped from 83 to 12 after the `datetime.utcnow()` cleanup.
- **ui_smoke.py**: 35 / 39 PASS + 4 NEEDS_KEY (providers without keys), 0 FAIL.
- **Frontend vite build**: 270 modules, clean.

## CI (pending — needs a token with `workflow` scope)

A `.github/workflows/test.yml` is ready locally (backend pytest + frontend vite build, both on Python 3.12 / Node 20 with pip/npm caching). GitHub rejected the push because the current PAT lacks `workflow` scope. Run `gh auth refresh -s workflow`, then the file can be committed to complete CI setup.

## Verified live before opening this PR

- AAPL 2024-06-14 exact_lookup → `close=212.49, volume=70,122,700` straight from `daily_bars`
- Audit log endpoint: 58 historic events, filterable
- Cross-tenant search "quokka" → 29 hits across 7 tenants
- Vault listing on `financebench`: 1,744 files visible recursively
- Privacy scrub: 0 absolute paths in 1,241 markdown files and 0 in the top-5 semantic hits against "Program_Research smartbaseai full-submission.txt"
- Saved-trace round-trip: run → save → list → fetch → delete, all 200
- Three-source orchestrator verified across all 7 tenants

## What is still outstanding

- Demo GIF + screenshots (`docs/screenshots/` empty)
- CI file push (PAT scope)
- Live deploy target (Fly.io / Railway)
- FinanceBench eval run to completion — harness running now with Ollama for 50 questions, `docs/financebench_eval.md` will be generated separately

## How to run locally

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env
# Optional: paste ANTHROPIC_API_KEY / OPENAI_API_KEY into .env
python scripts/run_server.py --reload             # -> http://localhost:8000

# Frontend
cd frontend && npm install && npm run dev         # -> http://localhost:5173

# Seed the 6 hand-curated vaults
python scripts/seed_demo.py

# (optional) load the 506-company FinanceBench vault (~2h first run)
CUDA_VISIBLE_DEVICES= python scripts/load_financebench.py --scale large \
  --sec-user-agent "Your Name <you@example.com>"
CUDA_VISIBLE_DEVICES= python scripts/ingest_financebench.py
```

## Default logins

- **super_admin**: `admin / ChangeThis123!` (cross-tenant)
- **personal**: `alice / Alice123!`
- **company** (Acme): `demo / Demo123!`
- **organization** (Lunar Harbor): `orion / Orion123!`
- **relativity**: `einat / Einat123!`
- **saas-ai**: `nadav / Nadav123!`
- **smartbase-docs**: `docs / Docs1234!`
- **financebench**: `fbuser / FbUser123!`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
