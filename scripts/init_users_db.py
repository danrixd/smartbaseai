import sqlite3
from passlib.hash import bcrypt
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/system.db")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "ChangeThis123!"
ADMIN_ROLE = "super_admin"


def init_db() -> None:
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

    cursor.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USERNAME,))
    if cursor.fetchone():
        print(f"⚠️ המשתמש '{ADMIN_USERNAME}' כבר קיים, לא נוצר מחדש.")
    else:
        now = datetime.utcnow().isoformat()
        password_hash = bcrypt.hash(ADMIN_PASSWORD)
        cursor.execute(
            """
            INSERT INTO users (username, hashed_password, role, tenant_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ADMIN_USERNAME, password_hash, ADMIN_ROLE, None, now, now),
        )
        print(f"✅ נוצר משתמש אדמין: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")

    conn.commit()
    conn.close()
    print(f"📦 קובץ DB נוצר ב: {DB_PATH}")


if __name__ == "__main__":
    init_db()
