from __future__ import annotations

import re
import shutil
from pathlib import Path
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from ai.vector_stores.chroma_store import TenantVectorStore
from db import file_repository, audit_log_repository
from .auth_middleware import get_current_user

router = APIRouter(prefix="/files", tags=["files"])
VAULT_ROOTS = {
    "personal": Path("data/personal"),
    "company": Path("data/demo"),
    "organization": Path("data/organization"),
    "relativity": Path("data/relativity"),
    "saas-ai": Path("data/saas-ai"),
    "smartbase-docs": Path("data/smartbase-docs"),
    "financebench": Path("data/financebench"),
}
VAULT_FALLBACK = Path("data/vaults")
INGESTIBLE_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".log"}
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
logger = logging.getLogger(__name__)


def _vault_root(tenant_id: str) -> Path:
    """Return the directory backing a tenant's editable vault.

    Seeded tenants (personal/company/organization) use hand-curated dirs.
    Everything else falls back to ``data/vaults/{tenant_id}/`` so upload and
    edit flows work uniformly across new tenants.
    """
    if tenant_id in VAULT_ROOTS:
        return VAULT_ROOTS[tenant_id]
    return VAULT_FALLBACK / tenant_id


class VaultFileUpdate(BaseModel):
    content: str


def _ingest_file_into_tenant_store(tenant_id: str, path: Path, filename: str) -> bool:
    """Read a text file and push it into the tenant's vector store.

    Uses a stable per-tenant doc_id (``{tenant}:{filename}``) so that editing
    or re-uploading a file replaces the existing vector rather than growing
    the collection.
    """
    if path.suffix.lower() not in INGESTIBLE_SUFFIXES:
        logger.info("Skipping ingestion for unsupported file type: %s", filename)
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("Skipping non-UTF8 file during ingestion: %s", filename)
        return False
    if not text.strip():
        return False
    store = TenantVectorStore(tenant_id)
    doc_id = f"{tenant_id}:{filename}"
    try:
        store.collection.delete(ids=[doc_id])
    except Exception:
        pass
    store.add_document(
        doc_id, text, {"filename": filename, "source": "upload", "tenant": tenant_id}
    )
    return True


@router.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    tenant_id: str | None = None,
    user=Depends(get_current_user),
):
    """Upload a file directly into a tenant's vault and auto-ingest it.

    Files land in the same directory as seeded vault content so the Vault
    editor lists them uniformly. ``tenant_id`` is optional; if omitted it
    defaults to the caller's tenant (non-super-admins can't cross that).
    """
    tenant = _resolve_tenant(user, tenant_id)
    if not file.filename or not SAFE_NAME_RE.match(file.filename):
        raise HTTPException(status_code=400, detail="invalid filename")
    root = _vault_root(tenant)
    root.mkdir(parents=True, exist_ok=True)
    dest_path = root / file.filename
    with dest_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    file_repository.add_file(user["username"], tenant, file.filename, str(dest_path))

    ingested = False
    try:
        ingested = _ingest_file_into_tenant_store(tenant, dest_path, file.filename)
    except Exception as exc:  # pragma: no cover - defensive, don't fail upload
        logger.exception("Failed to ingest uploaded file: %s", exc)

    audit_log_repository.log_action(
        user["username"], "upload_file", f"{tenant}:{file.filename}"
    )
    return {"tenant_id": tenant, "filename": file.filename, "ingested": ingested}


@router.get("/list")
def list_files(user=Depends(get_current_user)):
    return file_repository.list_files(user["username"])


def _resolve_tenant(user: dict, tenant_id: str | None) -> str:
    """Resolve the target tenant for a vault operation, enforcing scoping."""
    requested = (tenant_id or user.get("tenant_id") or "").strip()
    if not requested:
        raise HTTPException(status_code=400, detail="tenant_id required")
    if user.get("role") != "super_admin" and user.get("tenant_id") != requested:
        raise HTTPException(status_code=403, detail="Tenant access denied")
    return requested


def _safe_vault_path(tenant_id: str, filename: str) -> Path:
    """Resolve ``filename`` under the tenant's vault root, rejecting traversal.

    ``filename`` can be a bare name (``profile.md``) or a nested path
    (``AAPL/10k_2022.md``) using forward slashes. Every path segment must
    match SAFE_NAME_RE, and the resolved path must live inside the vault
    root — otherwise we raise 400 rather than serve a file outside the vault.
    """
    if not filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="invalid filename")
    parts = filename.replace("\\", "/").split("/")
    if any(p in ("", "..", ".") for p in parts):
        raise HTTPException(status_code=400, detail="invalid filename")
    for p in parts:
        if not SAFE_NAME_RE.match(p):
            raise HTTPException(status_code=400, detail="invalid filename")
    root = _vault_root(tenant_id).resolve()
    path = (root / "/".join(parts)).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="path traversal rejected")
    return path


@router.get("/vault")
def list_vault(tenant_id: str | None = None, user=Depends(get_current_user)):
    """List the editable files in the current tenant's vault.

    Walks recursively so tenants like ``financebench`` whose content is
    organized under per-ticker subdirectories show all their files. Each
    entry's ``filename`` is the POSIX path relative to the vault root.
    """
    tenant = _resolve_tenant(user, tenant_id)
    root = _vault_root(tenant)
    files = []
    if root.exists():
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in INGESTIBLE_SUFFIXES:
                continue
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            files.append(
                {
                    "filename": rel,
                    "size": path.stat().st_size,
                    "suffix": path.suffix.lower(),
                }
            )
    return {"tenant_id": tenant, "root": str(root), "count": len(files), "files": files}


@router.get("/vault/{filename:path}")
def read_vault_file(filename: str, tenant_id: str | None = None, user=Depends(get_current_user)):
    tenant = _resolve_tenant(user, tenant_id)
    path = _safe_vault_path(tenant, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return {
        "tenant_id": tenant,
        "filename": filename,
        "content": path.read_text(encoding="utf-8"),
    }


@router.put("/vault/{filename:path}")
def update_vault_file(
    filename: str,
    data: VaultFileUpdate,
    tenant_id: str | None = None,
    user=Depends(get_current_user),
):
    """Overwrite a vault file's content and re-ingest it into the tenant store.

    This is how "change specific file data by user commands" works end-to-end:
    the frontend posts the new body, the file is rewritten on disk, and the
    tenant's Chroma collection drops the old vector and re-embeds the new
    content under the same stable ``doc_id`` so the next chat query retrieves
    the updated material instead of the stale one.
    """
    tenant = _resolve_tenant(user, tenant_id)
    path = _safe_vault_path(tenant, filename)
    if path.suffix.lower() not in INGESTIBLE_SUFFIXES:
        raise HTTPException(status_code=400, detail="unsupported file type")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data.content, encoding="utf-8")

    store = TenantVectorStore(tenant)
    doc_id = f"{tenant}:{filename}"
    try:
        store.collection.delete(ids=[doc_id])
    except Exception:
        pass
    store.add_document(
        doc_id,
        data.content,
        {"filename": filename, "source": "vault-edit", "tenant": tenant},
    )
    audit_log_repository.log_action(user["username"], "edit_vault_file", f"{tenant}:{filename}")
    return {
        "tenant_id": tenant,
        "filename": filename,
        "bytes": len(data.content),
        "reingested": True,
    }
