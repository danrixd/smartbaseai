import sqlite3

# חיבור ל-DB של ה-tenant
db_path = r"data/tenant2.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# בדיקה אם השורה קיימת
date_to_check = "2023-07-09 22:39"
cursor.execute("SELECT * FROM market_data WHERE date = ?", (date_to_check,))
rows = cursor.fetchall()

if rows:
    print(f"✅ Found {len(rows)} row(s):")
    for row in rows:
        print(row)
else:
    print("❌ No rows found for", date_to_check)

conn.close()
