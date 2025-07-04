from datetime import datetime, timedelta
from os import environ as env
from typing import Any, Dict, Optional
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.services.user import UserService

SECRET_KEY = env.get("SECRET_KEY")
ALGORITHM = env.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(env.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


class AuthService:
    def __init__(self, db):
        self.user_service = UserService(db)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )

    def authenticate_user(
        self, username: str, password: str, tenant_id: UUID
    ) -> Optional[Dict[str, Any]]:
        # Look for user within the specific tenant
        user = self.user_service.get_user_by_username_and_tenant(username, tenant_id)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None

        return {
            "id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }

    def authenticate_user_global(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticate user globally across all tenants"""
        # Look for user by username (without tenant restriction)
        user = self.user_service.get_user_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None

        return {
            "id": str(user.id),  # Convert UUID to string for JSON serialization
            "tenant_id": str(user.tenant_id),  # Include tenant_id in user data
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def decode_access_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
