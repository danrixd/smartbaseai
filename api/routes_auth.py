from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import jwt

from db import user_repository
from api.auth_middleware import require_role, get_current_user

SECRET_KEY = "super_secret"
ALGORITHM = "HS256"

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str
    tenant_id: str | None = None


@router.post("/login")
def login(req: LoginRequest):
    user = user_repository.get_user(req.username)
    if not user or not user_repository.verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.encode(
        {
            "sub": user["username"],
            "role": user["role"],
            "tenant_id": user["tenant_id"],
            "exp": datetime.utcnow() + timedelta(hours=12),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    user_repository.update_last_login(user["id"])
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register")
def register(req: RegisterRequest, user=Depends(require_role(["super_admin", "tenant_admin"]))):
    if user_repository.get_user(req.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    # Tenant admins can only create users within their own tenant
    if user["role"] == "tenant_admin":
        if req.tenant_id is not None and req.tenant_id != user["tenant_id"]:
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        req.tenant_id = user["tenant_id"]

    user_repository.create_user(req.username, req.password, req.role, req.tenant_id)
    return {"status": "created"}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user
