# SmartBaseAI — getting started

SmartBaseAI is a multi-tenant LLM platform that grounds chat answers in two sources: (1) **structured data** from each tenant's database, and (2) **unstructured documents** stored in each tenant's vault. Every tenant gets an isolated knowledge vault, an isolated vector store, and its own choice of LLM backend.

This vault is the user-facing documentation. Ask it questions like:
- "How do I add a file to a vault?"
- "What does the RAG Visualizer actually show me?"
- "Which LLM providers does SmartBaseAI support?"
- "What's the most valuable thing SmartBaseAI delivers to a company?"

## First login

1. Navigate to the login page at `http://localhost:5173/`.
2. Sign in with a default account:
   - **super_admin** — `admin / ChangeThis123!` (sees every vault).
   - **tenant user** — varies per vault. See the "Seeded users" list in the full docs.
3. You land on the chat page. The sidebar shows your available vaults and the live API-connection status.

## Picking a vault

- **Super-admin** must explicitly pick a vault from the top-right "Active vault" dropdown before chatting — they have access to all tenants but no auto-selection.
- **Tenant admins** and **regular users** see their own vault auto-selected.
- The active vault determines which documents the chat retrieves from and which structured database the exact-lookup path queries.

## The three main screens

- **Chat** — the grounded chat interface. Every reply is produced by the orchestrator that merges conversation history, structured DB lookups, and hybrid RAG retrieval.
- **RAG Visualizer** — opens a live diagram of how a single query flows through the pipeline. See `02-rag-visualizer.md`.
- **Vault** — the editor for the active tenant's files. Upload new ones or edit existing ones; the system auto-re-embeds on save so changes are immediately visible to chat.

## Settings (super_admin only)

The Settings page is where you:
- Enter API keys for Anthropic, OpenAI, Ollama.
- Test provider connectivity live.
- Configure each tenant's list of available LLM models (every tenant can have multiple providers + models; users pick at chat time).
