# What the RAG Visualizer shows you

The RAG Visualizer page (`/rag`) is a live view of the orchestrator pipeline for a single query. Open it, paste a question, hit **Run trace**, and every stage of the pipeline lights up with the actual data that passed through it.

## The pipeline, stage by stage

### 1. User query
The raw question you typed, along with the active tenant ID. This is the input the orchestrator receives.

### 2. Orchestrator — three parallel sources

The orchestrator fans out to three sources at once:

- **History** — recent messages from your session, via `ConversationManager`. Shown as a compact list.
- **DB exact lookup** — if the query contains an ISO date (`YYYY-MM-DD HH:MM`), the orchestrator runs `exact_lookup` against the tenant's structured database. If a row matches, the card lights green and shows the row as JSON plus a human-readable summary.
- **Hybrid retrieval** — runs keyword match AND semantic top-k against the tenant's Chroma store, merged with keyword hits first. Each retrieved doc is shown as a chip with its filename, source (keyword or semantic), and distance score.

### 3. Fusion
DB text is preferred and RAG is treated as supplemental context. If both are empty, the orchestrator returns `"No information"` without calling the model — this is the explicit guardrail against hallucination.

### 4. Prompt assembly
The full prompt is assembled: conversation history + merged context + the user question. This is the exact string sent to the LLM. The visualizer shows you the whole thing in a monospace panel.

### 5. LLM
The model type and the generated reply. With a real Anthropic or OpenAI key, this is a real answer; without, you get a clearly-marked unavailability stub so you can still see the pipeline flow.

## What to look for

- **Which document contributed** — look at the distance scores. Scores below ~1.0 are very strong semantic matches. Scores above ~1.8 are weak and may be noise.
- **Keyword vs semantic** — a keyword hit is an exact substring match. A semantic hit is an embedding-nearest neighbor. When keyword and semantic both return the same file, that's the clearest signal that retrieval is working.
- **DB lookup overriding RAG** — for dated queries, you should see the DB card green and the exact row in the fusion block above the supplemental RAG text.
- **Empty retrieval** — if both keyword and semantic return nothing, the fusion block will say "both sources empty → 'No information'". This is not a bug; it's the guardrail.

## Use cases

- Debugging why a chat answer was wrong.
- Showing a stakeholder how retrieval actually works (not just "AI magic").
- Comparing the same query across two different vaults to see how tenant-scoping affects the result.
