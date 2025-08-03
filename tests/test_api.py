
from fastapi.testclient import TestClient

from tenants import tenant_storage, tenant_manager
from config import tenant_config

import api.routes_admin as routes_admin
import api.routes_chat as routes_chat
from chatbot.conversation_manager import ConversationManager
from api.app import app
from db import user_repository
from scripts import init_users_db


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
    assert r.json()["sub"] == "admin"


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

