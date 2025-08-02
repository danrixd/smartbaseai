"""Generate chat responses by combining structured and unstructured data.

The :class:`ResponseGenerator` orchestrates three sources of information:

* Conversation history provided by the :class:`chatbot.conversation_manager.ConversationManager`.
* Structured records retrieved from a tenant specific database.
* Free form context retrieved from a vector store (RAG).

Each source is handled by a dedicated helper method which keeps the logic
modular and makes it easy to plug additional data providers in the future.

The final prompt sent to the language model contains conversation history and a
single consolidated context block derived from the DB and RAG sources. If both
lookups fail, ``"אין מידע"`` is returned.
"""

from __future__ import annotations

import re
from typing import Iterable, Mapping

from ai.models.ollama_model import OllamaModel
from ai.models.openai_model import OpenAIModel
from ai.rag_pipeline import RAGPipeline
from db.query_engine import exact_lookup

# Simple pattern for ISO like ``YYYY-MM-DD HH:MM`` timestamps.
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")


class ResponseGenerator:
    """Generate responses combining DB lookup, RAG and conversation history."""

    MODELS = {
        "ollama": OllamaModel,
        "openai": OpenAIModel,
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
        """Return a formatted row from the tenant's DB if the message contains a date."""
        match = DATE_PATTERN.search(message)
        if not match:
            return ""

        date_str = match.group(0)
        row = exact_lookup(date_str, self.tenant_id)
        if not row:
            return ""
        return (
            f"Close value for {date_str} is {row['close']} "
            f"(Open: {row['open']}, High: {row['high']}, "
            f"Low: {row['low']}, Volume: {row['volume']})"
        )

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
        Hebrew "no information" string is returned.
        """

        db_text = self._lookup_db(user_message)
        rag_text = self._search_rag(user_message)
        context = self._merge_sources(db_text, rag_text)

        if not context:
            return "אין מידע"

        prompt = self._build_prompt(user_message, history, context)
        return self.model.generate(prompt)


# ---------------------------------------------------------------------------
# Extension notes

# To integrate additional data sources create a new helper similar to
# ``_lookup_db`` or ``_search_rag`` that returns a string representation of the
# retrieved information. Include the result when constructing the prompt in
# ``_build_prompt``. This keeps each provider decoupled and the main logic
# focused on prompt assembly.

