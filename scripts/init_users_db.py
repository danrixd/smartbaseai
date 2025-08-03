"""Initialize the users database and seed a default super admin user.

This script ensures the users table exists (including migrating legacy
schemas) and creates an initial super admin account if one does not yet
exist.  It relies on the helpers in :mod:`db.user_repository` so it stays
in sync with application logic.
"""

from pathlib import Path

from db import user_repository

DB_PATH: Path = Path("data/system.db")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "ChangeThis123!"
ADMIN_ROLE = "super_admin"


def init_db() -> None:
    """Create the database and seed the default admin user."""
    # ensure repository uses the same DB path as this script
    user_repository.DB_PATH = DB_PATH
    user_repository.init_db()

    if user_repository.get_user(ADMIN_USERNAME):
        print(f"⚠️ המשתמש '{ADMIN_USERNAME}' כבר קיים, לא נוצר מחדש.")
    else:
        user_repository.create_user(ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_ROLE)
        print(f"✅ נוצר משתמש אדמין: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")

    print(f"📦 קובץ DB נוצר ב: {DB_PATH}")


if __name__ == "__main__":
    init_db()

