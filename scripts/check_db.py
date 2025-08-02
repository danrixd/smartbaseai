"""Simple helper to check a tenant's market_data table for a specific date."""

import sqlite3
import sys


def main(tenant_id: str, date_to_check: str) -> None:
    db_path = f"data/{tenant_id}.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM market_data WHERE date = ?", (date_to_check,))
    row = cursor.fetchone()
    conn.close()
    if row:
        print(row)
    else:
        print("No data found")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/check_db.py <tenant_id> <date>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])

