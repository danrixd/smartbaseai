import sqlite3
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from passlib.hash import bcrypt

DB_PATH = Path("data/system.db")


def init_db() -> None:
    """Create the users table and migrate legacy schemas if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('super_admin', 'tenant_admin', 'user')),
            tenant_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login TEXT
        )
        """
    )

    # inspect existing columns for migration of older schemas
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]

    # rename legacy password column
    if "hashed_password" not in columns and "password" in columns:
        cursor.execute("ALTER TABLE users RENAME COLUMN password TO hashed_password")
        columns[columns.index("password")] = "hashed_password"

    # required columns with their SQL definitions
    required = {
        "hashed_password": "TEXT NOT NULL DEFAULT ''",
        "role": "TEXT NOT NULL DEFAULT 'user'",
        "tenant_id": "TEXT",
        "created_at": "TEXT NOT NULL DEFAULT ''",
        "updated_at": "TEXT NOT NULL DEFAULT ''",
        "last_login": "TEXT",
    }

    for column, ddl in required.items():
        if column not in columns:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {ddl}")

    # ensure timestamps exist for existing rows
    now = _current_time()
    cursor.execute(
        "UPDATE users SET created_at = ? WHERE created_at IS NULL OR created_at = ''",
        (now,),
    )
    cursor.execute(
        "UPDATE users SET updated_at = ? WHERE updated_at IS NULL OR updated_at = ''",
        (now,),
    )

    # upgrade any legacy plaintext passwords to bcrypt hashes
    _rehash_plaintext_passwords(cursor)

    conn.commit()
    conn.close()


def _current_time() -> str:
    return datetime.utcnow().isoformat()


def create_user(username: str, password: str, role: str, tenant_id: Optional[str] = None) -> None:
    """Create a new user with the given credentials."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = _current_time()
    password_hash = bcrypt.hash(password)
    cursor.execute(
        """
        INSERT INTO users (username, hashed_password, role, tenant_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (username, password_hash, role, tenant_id, now, now),
    )
    conn.commit()
    conn.close()


def get_user(username: str) -> Optional[Dict]:
    """Return a user record by username."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, username, hashed_password, role, tenant_id, created_at, updated_at, last_login
            FROM users WHERE username = ?
            """,
            (username,),
        )
    except sqlite3.OperationalError as e:
        conn.close()
        if "no such column" in str(e).lower():
            init_db()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, hashed_password, role, tenant_id, created_at, updated_at, last_login
                FROM users WHERE username = ?
                """,
                (username,),
            )
        else:
            raise

    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "username": row[1],
            "hashed_password": row[2],
            "role": row[3],
            "tenant_id": row[4],
            "created_at": row[5],
            "updated_at": row[6],
            "last_login": row[7],
        }
    return None


def list_users(tenant_id: Optional[str] = None) -> List[Dict]:
    """Return all users or only those belonging to a tenant."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if tenant_id is None:
        cursor.execute("SELECT id, username, role, tenant_id, created_at, updated_at, last_login FROM users")
    else:
        cursor.execute(
            "SELECT id, username, role, tenant_id, created_at, updated_at, last_login FROM users WHERE tenant_id = ?",
            (tenant_id,),
        )
    rows = cursor.fetchall()
    conn.close()
    users: List[Dict] = []
    for row in rows:
        users.append(
            {
                "id": row[0],
                "username": row[1],
                "role": row[2],
                "tenant_id": row[3],
                "created_at": row[4],
                "updated_at": row[5],
                "last_login": row[6],
            }
        )
    return users


def update_user_role(username: str, new_role: str) -> None:
    """Update a user's role."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET role = ?, updated_at = ? WHERE username = ?",
        (new_role, _current_time(), username),
    )
    conn.commit()
    conn.close()


def delete_user(username: str) -> None:
    """Delete a user by username."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()


def _rehash_plaintext_passwords(cursor: sqlite3.Cursor) -> None:
    """Upgrade any plaintext passwords stored in the DB to bcrypt hashes."""
    cursor.execute("SELECT id, username, hashed_password FROM users")
    for user_id, username, pwd in cursor.fetchall():
        if pwd and not bcrypt.identify(pwd):
            cursor.execute(
                "UPDATE users SET hashed_password = ?, updated_at = ? WHERE id = ?",
                (bcrypt.hash(pwd), _current_time(), user_id),
            )


def verify_password(password: str, password_hash: str, username: Optional[str] = None) -> bool:
    """Verify a password against the stored hash.

    If the stored value is plaintext (legacy DBs), verify against the
    plaintext and upgrade the stored value to a bcrypt hash.
    """
    if bcrypt.identify(password_hash):
        return bcrypt.verify(password, password_hash)

    # temporary support for plaintext passwords
    if password == password_hash:
        if username:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET hashed_password = ?, updated_at = ? WHERE username = ?",
                (bcrypt.hash(password), _current_time(), username),
            )
            conn.commit()
            conn.close()
        return True
    return False


def update_last_login(user_id: int) -> None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_login = ?, updated_at = ? WHERE id = ?",
        (_current_time(), _current_time(), user_id),
    )
    conn.commit()
    conn.close()
