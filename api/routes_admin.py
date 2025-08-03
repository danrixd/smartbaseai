from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from tenants.tenant_manager import TenantManager
from .auth_middleware import require_admin


router = APIRouter(prefix="/admin", tags=["admin"])
manager = TenantManager()


class TenantData(BaseModel):
    config: dict


@router.get("/tenants")
def list_tenants(user=Depends(require_admin)):
    """Return all tenant identifiers."""
    return manager.list()


@router.get("/tenants/{tenant_id}")
def get_tenant(tenant_id: str, user=Depends(require_admin)):
    """Return configuration for a tenant."""
    config = manager.get(tenant_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return config


@router.post("/tenants/{tenant_id}")
def create_tenant(tenant_id: str, data: TenantData, user=Depends(require_admin)):
    """Create a new tenant."""
    manager.create(tenant_id, data.config)
    return {"status": "created"}


@router.delete("/tenants/{tenant_id}")
def delete_tenant(tenant_id: str, user=Depends(require_admin)):
    """Delete a tenant."""
    manager.delete(tenant_id)
    return {"status": "deleted"}
