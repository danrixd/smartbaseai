import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict

DB_PATH = Path("data/system.db")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            username TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add_message(session_id: str, username: str, tenant_id: str, sender: str, message: str) -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (session_id, username, tenant_id, sender, message, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, username, tenant_id, sender, message, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_history(session_id: str, username: str) -> List[Dict]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sender, message, created_at FROM conversations WHERE session_id = ? AND username = ? ORDER BY id",
        (session_id, username),
    )
    rows = cursor.fetchall()
    conn.close()
    history: List[Dict] = []
    for sender, message, created_at in rows:
        history.append({"sender": sender, "message": message, "created_at": created_at})
    return history


def list_sessions(username: str) -> List[Dict]:
    """Return a list of chat sessions for a user with the first message as the title."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT session_id, MIN(id) AS first_id
        FROM conversations
        WHERE username = ?
        GROUP BY session_id
        ORDER BY MAX(id) DESC
        """,
        (username,),
    )
    rows = cursor.fetchall()
    sessions: List[Dict] = []
    for session_id, first_id in rows:
        cursor.execute(
            "SELECT message FROM conversations WHERE id = ?", (first_id,)
        )
        title_row = cursor.fetchone()
        title = title_row[0] if title_row else "New Chat"
        sessions.append({"id": session_id, "title": title[:30]})
    conn.close()
    return sessions


def delete_session(session_id: str, username: str) -> None:
    """Delete all conversation history for a session."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM conversations WHERE session_id = ? AND username = ?",
        (session_id, username),
    )
    conn.commit()
    conn.close()
