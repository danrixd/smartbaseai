import requests
import sqlite3
from pathlib import Path

DB_PATH = Path("data/system.db")
API_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "ChangeThis123!"


def check_admin_in_db() -> bool:
    if not DB_PATH.exists():
        print(f"❌ קובץ DB {DB_PATH} לא קיים")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username, role, tenant_id FROM users WHERE username = ?", (USERNAME,))
    row = cursor.fetchone()
    conn.close()

    if row:
        print(f"✅ נמצא משתמש ב-DB: {row}")
        return True
    else:
        print("❌ לא נמצא משתמש Admin ב-DB")
        return False


def try_login() -> str | None:
    print(f"🔑 מנסה להתחבר ל-API: {USERNAME}")
    try:
        response = requests.post(f"{API_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD})
        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                print(f"✅ התחברות הצליחה, Token:\n{token}")
                return token
            print("❌ ההתחברות הצליחה אבל לא חזר Token")
        else:
            print(f"❌ שגיאת התחברות: {response.status_code} {response.text}")
    except Exception as e:
        print(f"❌ שגיאה בהתחברות ל-API: {e}")
    return None


def check_admin_tenants(token: str) -> None:
    print("📡 בודק גישה ל-/admin/tenants")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_URL}/admin/tenants", headers=headers)
        if response.status_code == 200:
            tenants = response.json()
            print(f"✅ יש גישה ל-/admin/tenants, רשימת ה-Tenants:\n{tenants}")
        else:
            print(f"❌ אין גישה ל-/admin/tenants: {response.status_code} {response.text}")
    except Exception as e:
        print(f"❌ שגיאה בבדיקת tenants: {e}")


if __name__ == "__main__":
    if check_admin_in_db():
        token = try_login()
        if token:
            check_admin_tenants(token)
