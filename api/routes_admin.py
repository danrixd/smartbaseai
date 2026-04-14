from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from tenants.tenant_manager import TenantManager
from db import (
    audit_log_repository,
    settings_repository,
    usage_repository,
    user_repository,
)
from ai.vector_stores.chroma_store import TenantVectorStore
from .auth_middleware import require_role
from ai.models.anthropic_model import AnthropicModel
from ai.models.openai_model import OpenAIModel
from ai.models.ollama_model import OllamaModel

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


class SettingsUpdate(BaseModel):
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    ollama_base_url: str | None = None


class ModelTestRequest(BaseModel):
    provider: str
    api_key: str | None = None
    base_url: str | None = None


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
    try:
        manager.create(data.tenant_id, data.config)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    audit_log_repository.log_action(user["username"], "create_tenant", data.tenant_id)
    return {"status": "created"}


@router.patch("/tenants/{tenant_id}")
def update_tenant(tenant_id: str, data: TenantData, user=Depends(require_role(["super_admin"]))):
    """Update an existing tenant configuration."""
    if manager.get(tenant_id) is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    try:
        manager.update(tenant_id, data.config)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
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
    if user_repository.get_user(data.username) is not None:
        raise HTTPException(status_code=409, detail="User already exists")
    try:
        user_repository.create_user(data.username, data.password, data.role, data.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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


@router.get("/settings")
def get_settings(user=Depends(require_role(["super_admin"]))):
    """Return masked runtime settings for the admin UI."""
    return settings_repository.all_masked()


@router.put("/settings")
def put_settings(data: SettingsUpdate, user=Depends(require_role(["super_admin"]))):
    """Upsert runtime settings. Empty string clears a value (fall back to env)."""
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    settings_repository.set_many(payload)
    audit_log_repository.log_action(
        user["username"], "update_settings", ",".join(payload.keys())
    )
    return settings_repository.all_masked()


@router.get("/models/status")
def models_status(user=Depends(require_role(["user", "admin", "super_admin"]))):
    """Live connectivity check for every supported model backend.

    Callable by any authenticated role so the sidebar indicator can show real
    status for regular users too. Does not leak API keys.
    """
    ollama_ok, ollama_detail = OllamaModel.ping()
    openai_ok, openai_detail = OpenAIModel.ping()
    anthropic_ok, anthropic_detail = AnthropicModel.ping()
    return {
        "ollama": {"ok": ollama_ok, "detail": ollama_detail},
        "openai": {"ok": openai_ok, "detail": openai_detail},
        "anthropic": {"ok": anthropic_ok, "detail": anthropic_detail},
    }


@router.post("/models/test")
def models_test(
    data: ModelTestRequest,
    user=Depends(require_role(["super_admin"])),
):
    """Test a specific provider, optionally with an override key before saving."""
    provider = data.provider.lower()
    if provider == "anthropic":
        ok, detail = AnthropicModel.ping(api_key=data.api_key)
    elif provider == "openai":
        ok, detail = OpenAIModel.ping(api_key=data.api_key)
    elif provider == "ollama":
        ok, detail = OllamaModel.ping(base_url=data.base_url)
    else:
        raise HTTPException(status_code=400, detail=f"unknown provider: {provider}")
    return {"provider": provider, "ok": ok, "detail": detail}


@router.get("/audit-log")
def get_audit_log(
    limit: int = 200,
    offset: int = 0,
    username: str | None = None,
    action: str | None = None,
    user=Depends(require_role(["super_admin"])),
):
    """Return recent audit events, newest first. Super_admin only."""
    return {
        "total": audit_log_repository.count_logs(username=username, action=action),
        "logs": audit_log_repository.list_logs(
            limit=min(max(limit, 1), 1000),
            offset=max(offset, 0),
            username=username,
            action=action,
        ),
    }


@router.get("/usage")
def get_usage_rollup(
    limit: int = 60,
    user=Depends(require_role(["super_admin"])),
):
    """Per-day, per-tenant LLM usage + estimated cost."""
    return {"rollup": usage_repository.rollup(limit=min(max(limit, 1), 365))}


@router.get("/search")
def cross_tenant_search(
    q: str,
    tenants: str | None = None,
    top_k: int = 5,
    user=Depends(require_role(["super_admin"])),
):
    """Super-admin cross-tenant retrieval.

    Runs the same query against the hybrid retriever for every tenant in
    ``tenants`` (comma-separated) or every tenant if omitted, and returns a
    flat list of hits with tenant tags.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="q is required")
    target_tenants: list[str]
    if tenants:
        target_tenants = [t.strip() for t in tenants.split(",") if t.strip()]
    else:
        target_tenants = manager.list()

    results = []
    for tid in target_tenants:
        try:
            store = TenantVectorStore(tid)
            trace = store.hybrid_query_trace(q, n_results=top_k)
        except Exception as exc:
            logger.warning("cross-tenant search failed for %s: %s", tid, exc)
            continue
        for entry in trace.get("combined", []):
            results.append(
                {
                    "tenant_id": tid,
                    "source": entry.get("source"),
                    "score": entry.get("score"),
                    "filename": (entry.get("metadata") or {}).get("filename"),
                    "path": (entry.get("metadata") or {}).get("path"),
                    "preview": (entry.get("document") or "")[:400],
                }
            )
    # Rank across tenants: keyword hits first, then semantic by distance
    results.sort(
        key=lambda r: (
            0 if r["source"] == "keyword" else 1,
            r["score"] if r["score"] is not None else 9.99,
        )
    )
    return {"query": q, "tenants": target_tenants, "hits": results[: top_k * max(len(target_tenants), 1)]}


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
