# Demo script — SmartBaseAI walkthrough

A 90-second walkthrough anyone can record with ScreenToGif / Peek / OBS
to produce a GIF or MP4 for the README. Each step is narrated with the
vault / query / expected output so the recorder can line them up.

**Recording window:** 1440 × 900. Open a Chrome window at that size to keep
the capture tight. Use incognito so the sidebar doesn't cache state.

## Step 0 — log in
- Visit <http://localhost:5173/>
- Username: `admin`  Password: `ChangeThis123!`
- Should land on the Chat page with the "Pick a vault" gate visible

## Step 1 — pick a vault (shows the multi-tenant story)
- Click the "Active vault" dropdown in the top right
- Select `financebench`
- The gate disappears, chat UI renders

## Step 2 — the killer query (DB + RAG fusion)
- Click the RAG Visualizer sidebar link
- Paste: *"What was AAPL closing price on 2024-06-14?"*
- Click **Run trace**
- DB exact lookup card goes green with the AAPL row (close=212.49, volume=70.1M)
- Hybrid retrieval card shows top-3 semantic matches with distance bars
- Fusion block shows the DB row + "Additional context:" with retrieved chunks
- LLM card shows the Anthropic reply grounded in both

## Step 3 — fundamentals query (pure RAG)
- Paste: *"What was Microsoft's net income in FY2023?"*
- Scroll to the "Vector store search" panel
- Call out: 197,201 vectors scanned, MiniLM-L6-v2 on CUDA, score bars

## Step 4 — save the trace (zero-token replay)
- Click **💾 Save trace**, name it "MSFT net income FY2023 (Opus)"
- Expand "Saved traces" — the row appears
- Click **⬇ .md** — downloads a formatted markdown report

## Step 5 — vault editor with search
- Click Vault in sidebar
- Search `AAPL` — tree collapses to just the Apple folder
- Click `profile.md`, show the edit / split / preview toggle

## Step 6 — cross-tenant search (super_admin only)
- Click Cross-tenant Search
- Query: `quokka` — hits in the `organization` vault

## Step 7 — usage dashboard
- Click Usage — per-day × per-tenant rollup with estimated cost

## Short version (30 seconds)
Steps 0 → 2 only. The headline story: multi-tenant knowledge vault with
live LLM providers, orchestrator hits SQLite for the exact row and RAG
for context, pipeline visualized live.

## Suggested output
- `demo.gif` at repo root, referenced from README
- 15–20 seconds, 8–10 fps, ≤5 MB
