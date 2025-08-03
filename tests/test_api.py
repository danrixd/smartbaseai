
from fastapi.testclient import TestClient

from tenants import tenant_storage, tenant_manager
from config import tenant_config

import api.routes_admin as routes_admin
import api.routes_chat as routes_chat
from chatbot.conversation_manager import ConversationManager
from api.app import app
from db import user_repository
from scripts import init_users_db
import sqlite3
from datetime import datetime
from passlib.hash import bcrypt


def setup_client(tmp_path, monkeypatch):
    monkeypatch.setattr(tenant_storage, "TENANT_FILE", tmp_path / "tenants.json")
    # new tenant manager using patched storage
    tm = tenant_manager.TenantManager()
    monkeypatch.setattr(routes_admin, "manager", tm)
    monkeypatch.setattr(routes_chat, "conversation_manager", ConversationManager())
    monkeypatch.setattr(routes_chat, "tenant_manager", tm)

    db_path = tmp_path / "system.db"
    monkeypatch.setattr(user_repository, "DB_PATH", db_path)
    monkeypatch.setattr(init_users_db, "DB_PATH", db_path)
    init_users_db.init_db()

    return TestClient(app)


def get_token(client: TestClient) -> str:
    resp = client.post("/auth/login", json={"username": "admin", "password": "ChangeThis123!"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_login_and_whoami(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)
    token = get_token(client)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "admin"


def test_admin_and_chat_endpoints(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # prepare tenant config for chat
    monkeypatch.setitem(tenant_config.TENANT_CONFIGS, "t1", {"model": "ollama"})

    # create tenant via admin API
    resp = client.post(
        "/admin/tenants/t1",
        json={"config": {"plan": "basic", "model_type": "ollama"}},
        headers=headers,
    )
    assert resp.status_code == 200

    # list tenants
    resp = client.get("/admin/tenants", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == ["t1"]

    # get tenant
    resp = client.get("/admin/tenants/t1", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"plan": "basic", "model_type": "ollama"}

    # send chat message
    resp = client.post(
        "/chat/message",
        json={"session_id": "s1", "tenant_id": "t1", "message": "hello"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"].startswith("[Ollama")
    assert len(data["history"]) == 2


def test_chat_with_ollama(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    monkeypatch.setitem(
        tenant_config.TENANT_CONFIGS,
        "ol",
        {"model": "ollama"},
    )

    resp = client.post(
        "/admin/tenants/ol",
        json={"config": {"model_type": "ollama", "model_name": "llama3"}},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.post(
        "/chat/message",
        json={"session_id": "s1", "tenant_id": "ol", "message": "hi"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "[Ollama" in resp.json()["reply"]


def test_login_migrates_legacy_password_column(tmp_path, monkeypatch):
    """Existing DBs with a 'password' column should be migrated automatically."""

    monkeypatch.setattr(tenant_storage, "TENANT_FILE", tmp_path / "tenants.json")
    tm = tenant_manager.TenantManager()
    monkeypatch.setattr(routes_admin, "manager", tm)
    monkeypatch.setattr(routes_chat, "conversation_manager", ConversationManager())
    monkeypatch.setattr(routes_chat, "tenant_manager", tm)

    db_path = tmp_path / "system.db"

    # create legacy schema with 'password' column
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            tenant_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO users (username, password, role, tenant_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "admin",
            bcrypt.hash("ChangeThis123!"),
            "super_admin",
            None,
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(user_repository, "DB_PATH", db_path)
    monkeypatch.setattr(init_users_db, "DB_PATH", db_path)

    client = TestClient(app)
    resp = client.post(
        "/auth/login",
        json={"username": "admin", "password": "ChangeThis123!"},
    )
    assert resp.status_code == 200

    # verify column migration
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cursor.fetchall()]
    conn.close()
    assert "hashed_password" in cols
    assert "password" not in cols


def test_login_migrates_missing_columns(tmp_path, monkeypatch):
    """Databases missing multiple new columns are upgraded on demand."""

    monkeypatch.setattr(tenant_storage, "TENANT_FILE", tmp_path / "tenants.json")
    tm = tenant_manager.TenantManager()
    monkeypatch.setattr(routes_admin, "manager", tm)
    monkeypatch.setattr(routes_chat, "conversation_manager", ConversationManager())
    monkeypatch.setattr(routes_chat, "tenant_manager", tm)

    db_path = tmp_path / "system.db"

    # very old schema with only username/password
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        ("admin", bcrypt.hash("ChangeThis123!")),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(user_repository, "DB_PATH", db_path)
    monkeypatch.setattr(init_users_db, "DB_PATH", db_path)

    client = TestClient(app)
    resp = client.post(
        "/auth/login",
        json={"username": "admin", "password": "ChangeThis123!"},
    )
    assert resp.status_code == 200

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cursor.fetchall()]
    conn.close()

    for expected in [
        "hashed_password",
        "role",
        "tenant_id",
        "created_at",
        "updated_at",
        "last_login",
    ]:
        assert expected in cols


def test_login_upgrades_plaintext_password(tmp_path, monkeypatch):
    """Plaintext passwords are converted to bcrypt hashes automatically."""

    monkeypatch.setattr(tenant_storage, "TENANT_FILE", tmp_path / "tenants.json")
    tm = tenant_manager.TenantManager()
    monkeypatch.setattr(routes_admin, "manager", tm)
    monkeypatch.setattr(routes_chat, "conversation_manager", ConversationManager())
    monkeypatch.setattr(routes_chat, "tenant_manager", tm)

    db_path = tmp_path / "system.db"

    # schema already uses hashed_password but stores plain text value
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL,
            tenant_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login TEXT
        )
        """
    )
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO users (username, hashed_password, role, tenant_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("admin", "ChangeThis123!", "super_admin", None, now, now),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(user_repository, "DB_PATH", db_path)
    monkeypatch.setattr(init_users_db, "DB_PATH", db_path)

    client = TestClient(app)
    resp = client.post(
        "/auth/login",
        json={"username": "admin", "password": "ChangeThis123!"},
    )
    assert resp.status_code == 200

    # password should now be stored as bcrypt hash
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT hashed_password FROM users WHERE username = ?",
        ("admin",),
    )
    stored = cursor.fetchone()[0]
    conn.close()
    assert stored.startswith("$2b$")


def test_login_plaintext_without_migration(tmp_path, monkeypatch):
    """Login succeeds even if migration didn't run before verifying."""

    monkeypatch.setattr(tenant_storage, "TENANT_FILE", tmp_path / "tenants.json")
    tm = tenant_manager.TenantManager()
    monkeypatch.setattr(routes_admin, "manager", tm)
    monkeypatch.setattr(routes_chat, "conversation_manager", ConversationManager())
    monkeypatch.setattr(routes_chat, "tenant_manager", tm)

    db_path = tmp_path / "system.db"

    # schema uses hashed_password but stores plain text value
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL,
            tenant_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login TEXT
        )
        """
    )
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO users (username, hashed_password, role, tenant_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("admin", "ChangeThis123!", "super_admin", None, now, now),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(user_repository, "DB_PATH", db_path)
    monkeypatch.setattr(init_users_db, "DB_PATH", db_path)

    # simulate missing migration
    monkeypatch.setattr(user_repository, "init_db", lambda: None)

    client = TestClient(app)
    resp = client.post(
        "/auth/login",
        json={"username": "admin", "password": "ChangeThis123!"},
    )
    assert resp.status_code == 200

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT hashed_password FROM users WHERE username = ?",
        ("admin",),
    )
    stored = cursor.fetchone()[0]
    conn.close()
    assert stored.startswith("$2b$")

