from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import jwt

from db import user_repository

SECRET_KEY = "super_secret"
ALGORITHM = "HS256"

security = HTTPBearer()


def get_current_user(token=Depends(security)):
    """Decode the JWT token and return the associated user."""
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user = user_repository.get_user(username)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(roles: list[str]):
    """Dependency to ensure the current user has one of the required roles."""
    def role_checker(user=Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return role_checker
