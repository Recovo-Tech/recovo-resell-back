from pydantic import BaseModel

from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    username: str
    password: str
    tenant_name: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: int


class RegisterResponse(BaseModel):
    user: UserResponse
    token: Token


class LoginResponse(BaseModel):
    user: UserResponse
    token: Token
