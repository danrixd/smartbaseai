"""Classify user intent based on simple keyword heuristics."""

from __future__ import annotations

from typing import Dict, List


class IntentRecognizer:
    """Determine the intent of a user message."""

    DEFAULT_PATTERNS: Dict[str, List[str]] = {
        "greeting": ["hello", "hi", "hey"],
        "goodbye": ["bye", "goodbye", "see you"],
        "thanks": ["thank", "thanks"],
    }

    def __init__(self, patterns: Dict[str, List[str]] | None = None) -> None:
        self.patterns = patterns or self.DEFAULT_PATTERNS

    def recognize(self, text: str) -> str:
        """Return an intent label for the provided text."""
        lowered = text.lower()
        for intent, keywords in self.patterns.items():
            for kw in keywords:
                if kw in lowered:
                    return intent
        if lowered.strip().endswith("?"):
            return "question"
        return "statement"
