import sqlite3
from passlib.hash import bcrypt
from pathlib import Path

DB_PATH = Path("data/system.db")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "ChangeThis123!"
ADMIN_ROLE = "admin"
TENANT_ID = "tenant1"


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

    cursor.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USERNAME,))
    if cursor.fetchone():
        print(f"⚠️ המשתמש '{ADMIN_USERNAME}' כבר קיים, לא נוצר מחדש.")
    else:
        password_hash = bcrypt.hash(ADMIN_PASSWORD)
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, role, tenant_id)
            VALUES (?, ?, ?, ?)
            """,
            (ADMIN_USERNAME, password_hash, ADMIN_ROLE, TENANT_ID),
        )
        print(f"✅ נוצר משתמש אדמין: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")

    conn.commit()
    conn.close()
    print(f"📦 קובץ DB נוצר ב: {DB_PATH}")


if __name__ == "__main__":
    init_db()
