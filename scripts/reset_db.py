"""Reset the system users database.

Deletes the existing SQLite database file and reinitializes it using
``scripts.init_users_db`` so a fresh schema is created and the default
super admin account is seeded.
"""

from pathlib import Path

from db import user_repository
import init_users_db


def reset_db() -> None:
    """Remove the current DB file and recreate it with the seed admin user."""
    db_path: Path = user_repository.DB_PATH
    if db_path.exists():
        db_path.unlink()
        print(f"🗑️ Deleted existing DB at {db_path}")
    else:
        print(f"ℹ️ No DB found at {db_path}, creating fresh one")

    # Recreate the DB and seed default admin
    init_users_db.init_db()


if __name__ == "__main__":
    reset_db()
