from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from tenants.tenant_manager import TenantManager
from db import user_repository, audit_log_repository
from .auth_middleware import require_role

router = APIRouter(prefix="/admin", tags=["admin"])
manager = TenantManager()
logger = logging.getLogger(__name__)


class TenantData(BaseModel):
    tenant_id: str | None = None
    config: dict


class UserData(BaseModel):
    username: str
    password: str
    role: str
    tenant_id: str | None = None


class UserUpdate(BaseModel):
    role: str | None = None


@router.get("/tenants")
def list_tenants(user=Depends(require_role(["super_admin"]))):
    """Return all tenant identifiers (super admins only)."""
    return manager.list()


@router.get("/tenants/{tenant_id}")
def get_tenant(tenant_id: str, user=Depends(require_role(["super_admin"]))):
    """Return configuration for a tenant."""
    config = manager.get(tenant_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return config


@router.post("/tenants")
def create_tenant(data: TenantData, user=Depends(require_role(["super_admin"]))):
    """Create a new tenant."""
    if not data.tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id required")
    manager.create(data.tenant_id, data.config)
    audit_log_repository.log_action(user["username"], "create_tenant", data.tenant_id)
    return {"status": "created"}


@router.patch("/tenants/{tenant_id}")
def update_tenant(tenant_id: str, data: TenantData, user=Depends(require_role(["super_admin"]))):
    """Update an existing tenant configuration."""
    if manager.get(tenant_id) is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    manager.create(tenant_id, data.config)
    audit_log_repository.log_action(user["username"], "update_tenant", tenant_id)
    return {"status": "updated"}


@router.delete("/tenants/{tenant_id}")
def delete_tenant(tenant_id: str, user=Depends(require_role(["super_admin"]))):
    """Delete a tenant."""
    manager.delete(tenant_id)
    audit_log_repository.log_action(user["username"], "delete_tenant", tenant_id)
    return {"status": "deleted"}


@router.get("/users")
def list_users(user=Depends(require_role(["super_admin", "admin"]))):
    """List users scoped by role."""
    if user["role"] == "super_admin":
        return user_repository.list_users()
    return user_repository.list_users(user["tenant_id"])


@router.post("/users")
def create_user(data: UserData, user=Depends(require_role(["super_admin", "admin"]))):
    """Create a new user."""
    if user["role"] == "admin":
        if data.tenant_id and data.tenant_id != user["tenant_id"]:
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        data.tenant_id = user["tenant_id"]
        if data.role == "super_admin":
            raise HTTPException(status_code=403, detail="Cannot create super_admin")
    user_repository.create_user(data.username, data.password, data.role, data.tenant_id)
    audit_log_repository.log_action(user["username"], "create_user", data.username)
    return {"status": "created"}


@router.patch("/users/{username}")
def update_user(username: str, data: UserUpdate, user=Depends(require_role(["super_admin", "admin"]))):
    """Update user details."""
    target = user_repository.get_user(username)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user["role"] == "admin" and target.get("tenant_id") != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    if data.role:
        if user["role"] == "admin" and data.role == "super_admin":
            raise HTTPException(status_code=403, detail="Cannot assign super_admin")
        user_repository.update_user_role(username, data.role)
        audit_log_repository.log_action(user["username"], "update_user_role", f"{username}:{data.role}")
    return {"status": "updated"}


@router.delete("/users/{username}")
def delete_user(username: str, user=Depends(require_role(["super_admin", "admin"]))):
    """Delete a user."""
    target = user_repository.get_user(username)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user["role"] == "admin" and target.get("tenant_id") != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    user_repository.delete_user(username)
    audit_log_repository.log_action(user["username"], "delete_user", username)
    return {"status": "deleted"}
