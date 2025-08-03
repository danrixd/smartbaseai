import sqlite3
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

from passlib.hash import bcrypt

DB_PATH = Path("data/system.db")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
            tenant_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def create_user(username: str, password: str, role: str, tenant_id: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    password_hash = bcrypt.hash(password)
    cursor.execute(
        """
        INSERT INTO users (username, password_hash, role, tenant_id)
        VALUES (?, ?, ?, ?)
        """,
        (username, password_hash, role, tenant_id),
    )
    conn.commit()
    conn.close()


def get_user(username: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, username, password_hash, role, tenant_id, created_at, last_login
        FROM users WHERE username = ?
        """,
        (username,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "username": row[1],
            "password_hash": row[2],
            "role": row[3],
            "tenant_id": row[4],
            "created_at": row[5],
            "last_login": row[6],
        }
    return None


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.verify(password, password_hash)


def update_last_login(user_id: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (datetime.now(), user_id),
    )
    conn.commit()
    conn.close()
