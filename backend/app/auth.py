"""
VehicleIQ JWT Authentication Module
Provides Argon2id password hashing, JWT token issuance, and FastAPI security dependencies.
"""

import os
from datetime import datetime, timedelta
import logging
from typing import Optional

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger("VehicleIQ.Auth")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "vehicleiq_super_secret_jwt_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security = HTTPBearer()
password_hasher = PasswordHash.recommended()

def hash_password(password: str) -> str:
    """Hash using Argon2id; the library generates an individual random salt."""
    return password_hasher.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify against the encoded hash's parameters and salt."""
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False
    try:
        return password_hasher.verify(plain_password, hashed_password)
    except UnknownHashError:
        # Legacy SHA-256 values and corrupt/unsupported hashes are rejected safely.
        return False


# In-memory demo user; store a real hash rather than a password-shaped placeholder.
# Demo credentials: admin / VehicleIQ-demo-2026.
USER_DB = {
    "admin": {
        "username": "admin",
        "email": "admin@vehicleiq.ai",
        "hashed_password": hash_password("VehicleIQ-demo-2026"),
    }
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """FastAPI dependency enforcing JWT authentication on protected endpoints."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate JWT credentials")
