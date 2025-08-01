"""Manage conversation sessions and maintain history."""

from typing import Dict, List


class ConversationManager:
    """Simple in-memory conversation session manager."""

    def __init__(self) -> None:
        self._sessions: Dict[str, List[dict]] = {}

    def start_session(self, session_id: str) -> None:
        """Initialize a new session if it doesn't already exist."""
        self._sessions.setdefault(session_id, [])

    def add_message(self, session_id: str, role: str, message: str) -> None:
        """Append a message to the session history."""
        self._sessions.setdefault(session_id, []).append({"role": role, "text": message})

    def history(self, session_id: str) -> List[dict]:
        """Return the conversation history for a session."""
        return list(self._sessions.get(session_id, []))

    def end_session(self, session_id: str) -> None:
        """Remove a session and all of its history."""
        self._sessions.pop(session_id, None)
