from fastapi.testclient import TestClient

from tenants import tenant_storage, tenant_manager
from config import tenant_config

import api.routes_admin as routes_admin
import api.routes_chat as routes_chat
import api.routes_files as routes_files
from chatbot.conversation_manager import ConversationManager
from api.app import app
from db import user_repository, conversation_repository, file_repository, audit_log_repository
from scripts import init_users_db
import sqlite3
from datetime import datetime
from passlib.hash import bcrypt


def setup_client(tmp_path, monkeypatch):
    monkeypatch.setattr(tenant_storage, "TENANT_FILE", tmp_path / "tenants.json")
    tm = tenant_manager.TenantManager()
    monkeypatch.setattr(routes_admin, "manager", tm)
    monkeypatch.setattr(routes_chat, "conversation_manager", ConversationManager())
    monkeypatch.setattr(routes_chat, "tenant_manager", tm)

    db_path = tmp_path / "system.db"
    monkeypatch.setattr(user_repository, "DB_PATH", db_path)
    monkeypatch.setattr(conversation_repository, "DB_PATH", db_path)
    monkeypatch.setattr(file_repository, "DB_PATH", db_path)
    monkeypatch.setattr(audit_log_repository, "DB_PATH", db_path)
    monkeypatch.setattr(init_users_db, "DB_PATH", db_path)
    init_users_db.init_db()

    monkeypatch.setattr(routes_files, "UPLOAD_DIR", tmp_path / "uploads")

    return TestClient(app)


def get_token(client: TestClient, username="admin", password="ChangeThis123!") -> str:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_login_and_whoami(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)
    token = get_token(client)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "admin"
    assert data["role"] == "super_admin"
    assert data["tenant_id"] is None


def test_admin_chat_and_history(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    monkeypatch.setitem(tenant_config.TENANT_CONFIGS, "t1", {"model": "ollama"})

    resp = client.post(
        "/admin/tenants",
        json={"tenant_id": "t1", "config": {"plan": "basic", "model_type": "ollama"}},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.get("/admin/tenants", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == ["t1"]

    resp = client.get("/admin/tenants/t1", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"plan": "basic", "model_type": "ollama"}

    resp = client.post(
        "/chat/message",
        json={"session_id": "s1", "tenant_id": "t1", "message": "hello"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"].startswith("[Ollama")
    assert len(data["history"]) == 2
    assert data["source"] in {"None", "DB", "RAG", "DB + RAG"}

    resp = client.get("/chat/history", params={"session_id": "s1"}, headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["history"]) == 2

    resp = client.get("/chat/sessions", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["sessions"][0]["id"] == "s1"

    resp = client.delete("/chat/session/s1", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/chat/sessions", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["sessions"] == []


def test_user_and_file_endpoints(tmp_path, monkeypatch):
    client = setup_client(tmp_path, monkeypatch)
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/admin/tenants", json={"tenant_id": "t1", "config": {}}, headers=headers)
    assert resp.status_code == 200

    resp = client.post(
        "/admin/users",
        json={"username": "manager", "password": "Pass123!", "role": "admin", "tenant_id": "t1"},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.post(
        "/auth/login", json={"username": "manager", "password": "Pass123!"}
    )
    token_admin = resp.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    resp = client.post(
        "/admin/users",
        json={"username": "viewer", "password": "Pass123!", "role": "user"},
        headers=headers_admin,
    )
    assert resp.status_code == 200

    resp = client.get("/admin/users", headers=headers_admin)
    assert resp.status_code == 200
    usernames = {u["username"] for u in resp.json()}
    assert usernames == {"manager", "viewer"}

    resp = client.post(
        "/auth/login", json={"username": "viewer", "password": "Pass123!"}
    )
    token_user = resp.json()["access_token"]
    headers_user = {"Authorization": f"Bearer {token_user}"}

    files = {"file": ("hello.txt", b"hello")}
    resp = client.post("/files/upload", files=files, headers=headers_user)
    assert resp.status_code == 200

    resp = client.get("/files/list", headers=headers_user)
    assert resp.status_code == 200
    assert resp.json()[0]["filename"] == "hello.txt"
