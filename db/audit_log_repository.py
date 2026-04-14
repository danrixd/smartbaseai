import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("data/system.db")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC)"
    )
    conn.commit()
    conn.close()


def log_action(username: str, action: str, details: str | None = None) -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_logs (username, action, details, created_at) VALUES (?, ?, ?, ?)",
        (username, action, details, _now()),
    )
    conn.commit()
    conn.close()


def list_logs(limit: int = 200, offset: int = 0, username: str | None = None, action: str | None = None) -> list[dict]:
    """Return recent audit events, newest first. Used by the admin viewer."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        q = "SELECT id, username, action, details, created_at FROM audit_logs WHERE 1=1"
        params: list = []
        if username:
            q += " AND username = ?"
            params.append(username)
        if action:
            q += " AND action LIKE ?"
            params.append(f"%{action}%")
        q += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(q, params).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r[0],
            "username": r[1],
            "action": r[2],
            "details": r[3],
            "created_at": r[4],
        }
        for r in rows
    ]


def count_logs(username: str | None = None, action: str | None = None) -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        q = "SELECT COUNT(*) FROM audit_logs WHERE 1=1"
        params: list = []
        if username:
            q += " AND username = ?"
            params.append(username)
        if action:
            q += " AND action LIKE ?"
            params.append(f"%{action}%")
        return int(conn.execute(q, params).fetchone()[0])
    finally:
        conn.close()
