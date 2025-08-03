import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/system.db")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def log_action(username: str, action: str, details: str | None = None) -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_logs (username, action, details, created_at) VALUES (?, ?, ?, ?)",
        (username, action, details, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
