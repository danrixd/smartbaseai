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
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def add_file(username: str, tenant_id: str, filename: str, path: str) -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO files (username, tenant_id, filename, path, uploaded_at) VALUES (?, ?, ?, ?, ?)",
        (username, tenant_id, filename, path, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def list_files(username: str) -> List[Dict]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT filename, path, uploaded_at FROM files WHERE username = ? ORDER BY uploaded_at",
        (username,),
    )
    rows = cursor.fetchall()
    conn.close()
    files: List[Dict] = []
    for filename, path, uploaded_at in rows:
        files.append({"filename": filename, "path": path, "uploaded_at": uploaded_at})
    return files
