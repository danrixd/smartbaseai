from __future__ import annotations

import shutil
from pathlib import Path
import logging

from fastapi import APIRouter, Depends, File, UploadFile

from db import file_repository, audit_log_repository
from .auth_middleware import get_current_user

router = APIRouter(prefix="/files", tags=["files"])
UPLOAD_DIR = Path("data/uploads")
logger = logging.getLogger(__name__)


@router.post("/upload")
def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    tenant_id = user.get("tenant_id") or "global"
    dest_dir = UPLOAD_DIR / tenant_id / user["username"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file.filename
    with dest_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    file_repository.add_file(user["username"], tenant_id, file.filename, str(dest_path))
    audit_log_repository.log_action(user["username"], "upload_file", file.filename)
    return {"filename": file.filename}


@router.get("/list")
def list_files(user=Depends(get_current_user)):
    return file_repository.list_files(user["username"])
