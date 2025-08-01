import pytest

from tenants import tenant_storage, tenant_manager


def test_tenant_manager_crud(tmp_path, monkeypatch):
    file = tmp_path / "tenants.json"
    monkeypatch.setattr(tenant_storage, "TENANT_FILE", file)
    manager = tenant_manager.TenantManager()

    assert manager.list() == []

    manager.create("t1", {"plan": "pro"})
    assert manager.list() == ["t1"]
    assert manager.get("t1") == {"plan": "pro"}

    manager.delete("t1")
    assert manager.list() == []


def test_create_existing_tenant(tmp_path, monkeypatch):
    file = tmp_path / "tenants.json"
    monkeypatch.setattr(tenant_storage, "TENANT_FILE", file)
    manager = tenant_manager.TenantManager()

    manager.create("t1", {})
    with pytest.raises(ValueError):
        manager.create("t1", {})
