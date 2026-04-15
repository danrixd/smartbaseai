"""Generate chat responses by combining structured and unstructured data.

The :class:`ResponseGenerator` orchestrates three sources of information:

* Conversation history provided by the :class:`chatbot.conversation_manager.ConversationManager`.
* Structured records retrieved from a tenant specific database.
* Free form context retrieved from a vector store (RAG).

Each source is handled by a dedicated helper method which keeps the logic
modular and makes it easy to plug additional data providers in the future.

The final prompt sent to the language model contains conversation history and a
single consolidated context block derived from the DB and RAG sources. If both
lookups fail, ``"No information"`` is returned.
"""

from __future__ import annotations

import re
from typing import Iterable, Mapping

from ai.models.anthropic_model import AnthropicModel
from ai.models.ollama_model import OllamaModel
from ai.models.openai_model import OpenAIModel
from ai.rag_pipeline import RAGPipeline
from db.query_engine import exact_lookup

# Match either "YYYY-MM-DD HH:MM" (intraday market_data rows) or bare
# "YYYY-MM-DD" (daily_bars rows). DATE_ONLY_PATTERN is used as a fallback
# when the datetime pattern doesn't fire.
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")
DATE_ONLY_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


class ResponseGenerator:
    """Generate responses combining DB lookup, RAG and conversation history."""

    MODELS = {
        "ollama": OllamaModel,
        "openai": OpenAIModel,
        "anthropic": AnthropicModel,
    }

    def __init__(self, tenant_id: str, model_type: str = "ollama", **model_kwargs) -> None:
        self.tenant_id = tenant_id
        self.rag = RAGPipeline(tenant_id=tenant_id)

        model_cls = self.MODELS.get(model_type)
        if model_cls is None:
            raise ValueError(f"Unsupported model type: {model_type}")
        self.model = model_cls(**model_kwargs)

    # ------------------------------------------------------------------
    # Helpers for the different data sources
    def _lookup_db(self, message: str) -> str:
        """Return a formatted row from the tenant's DB if the message contains a date.

        Tries two patterns:
          1. Intraday "YYYY-MM-DD HH:MM" → legacy market_data rows.
          2. Date-only "YYYY-MM-DD" → financebench daily_bars or market_data.

        The second pattern passes ``message=`` so ``exact_lookup`` can sniff a
        ticker hint for the financebench tenant.
        """
        match = DATE_PATTERN.search(message)
        if match:
            date_str = match.group(0)
            row = exact_lookup(date_str, self.tenant_id, message=message)
            if row:
                return self._format_row(date_str, row)

        match = DATE_ONLY_PATTERN.search(message)
        if match:
            date_str = match.group(0)
            row = exact_lookup(date_str, self.tenant_id, message=message)
            if row:
                return self._format_row(date_str, row)

        return ""

    @staticmethod
    def _format_row(date_str: str, row: dict) -> str:
        """Render a structured row into a one-line context string."""
        ticker = row.get("ticker")
        prefix = f"{ticker} on {row.get('date', date_str)}" if ticker else f"Close value for {date_str}"
        try:
            close = row["close"]
            return (
                f"{prefix}: close={close} "
                f"(open={row.get('open')}, high={row.get('high')}, "
                f"low={row.get('low')}, volume={row.get('volume')})"
            )
        except Exception:
            return f"{prefix}: {row}"

    def _search_rag(self, message: str) -> str:
        """Retrieve free-form context using the RAG pipeline."""
        return self.rag.retrieve_context(message)

    # ------------------------------------------------------------------
    @staticmethod
    def _format_history(history: Iterable[Mapping[str, str]] | None) -> str:
        if not history:
            return ""
        return "\n".join(f"{m['role']}: {m['text']}" for m in history)

    @staticmethod
    def _merge_sources(db_text: str, rag_text: str) -> str:
        """Combine structured DB data with RAG context.

        DB information is preferred and RAG is added as supplemental context
        when available.
        """

        if db_text and rag_text:
            return f"{db_text}\n\nAdditional context:\n{rag_text}"
        return db_text or rag_text

    def _build_prompt(
        self,
        user_message: str,
        history: Iterable[Mapping[str, str]] | None,
        context: str,
    ) -> str:
        history_text = self._format_history(history)
        return (
            "Conversation:\n" + history_text + "\n\n" +
            "Context:\n" + context + "\n\n" +
            f"User: {user_message}\nAssistant:"
        )

    # ------------------------------------------------------------------
    def generate_response(
        self, user_message: str, history: Iterable[Mapping[str, str]] | None = None
    ) -> str:
        """Generate a response by combining DB and RAG results.

        Both structured and unstructured searches are attempted. Missing results
        from one source do not prevent using the other. If both return nothing a
        "no information" message is returned.
        """

        db_text = self._lookup_db(user_message)
        rag_text = self._search_rag(user_message)
        context = self._merge_sources(db_text, rag_text)

        if not context:
            return "No information"

        prompt = self._build_prompt(user_message, history, context)
        return self.model.generate(prompt)

    # ------------------------------------------------------------------
    def generate_response_trace(
        self,
        user_message: str,
        history: Iterable[Mapping[str, str]] | None = None,
    ) -> dict:
        """Same as ``generate_response`` but returns a full pipeline trace.

        The returned dict is designed to be rendered in the RAG visualizer:
        every stage exposes the exact data that flowed through it so a viewer
        can see, for a single query, which document triggered the retrieval
        and which structured row (if any) grounded the answer.
        """
        # 1. History (serialized for display only)
        history_list = list(history or [])
        history_text = self._format_history(history_list)

        # 2. Structured DB lookup (intraday first, then date-only)
        db_row: dict = {}
        db_text = ""
        detected = None
        m = DATE_PATTERN.search(user_message)
        if m:
            detected = m.group(0)
            db_row = exact_lookup(detected, self.tenant_id, message=user_message) or {}
        if not db_row:
            m = DATE_ONLY_PATTERN.search(user_message)
            if m:
                detected = m.group(0)
                db_row = exact_lookup(detected, self.tenant_id, message=user_message) or {}
        if db_row:
            db_text = self._format_row(detected or "", db_row)
        db_stage = {
            "detected_date": detected,
            "matched": bool(db_row),
            "row": db_row,
            "text": db_text,
        }

        # 3. Hybrid retrieval with per-source breakdown + store metadata
        rag_stage: dict = {
            "store": None,
            "keyword": [],
            "semantic": [],
            "combined": [],
            "text": "",
            "n_candidates": 0,
            "n_results": 3,
        }
        store = getattr(self.rag, "store", None)
        if store is not None and hasattr(store, "hybrid_query_trace"):
            trace = store.hybrid_query_trace(user_message, n_results=3)
            rag_stage.update(trace)
            rag_stage["text"] = "\n".join(e["document"] for e in trace.get("combined", []))
        else:
            rag_stage["text"] = self._search_rag(user_message)

        # 4. Fusion
        merged_context = self._merge_sources(db_text, rag_stage["text"])

        # 5. Prompt assembly
        prompt = self._build_prompt(user_message, history_list, merged_context) if merged_context else ""

        # 6. LLM generation
        if merged_context:
            reply = self.model.generate(prompt)
        else:
            reply = "No information"

        return {
            "query": user_message,
            "tenant_id": self.tenant_id,
            "stages": {
                "history": {"messages": history_list, "text": history_text},
                "db_lookup": db_stage,
                "rag_retrieval": rag_stage,
                "fusion": {"db_text": db_text, "rag_text": rag_stage["text"], "merged": merged_context},
                "prompt": {"full": prompt},
                "llm": {
                    "model_type": self.model.__class__.__name__,
                    "reply": reply,
                },
            },
            "reply": reply,
        }


# ---------------------------------------------------------------------------
# Extension notes

# To integrate additional data sources create a new helper similar to
# ``_lookup_db`` or ``_search_rag`` that returns a string representation of the
# retrieved information. Include the result when constructing the prompt in
# ``_build_prompt``. This keeps each provider decoupled and the main logic
# focused on prompt assembly.

