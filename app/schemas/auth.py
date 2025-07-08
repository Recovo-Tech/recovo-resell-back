from pydantic import BaseModel, Field

from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username for login", example="nachoooo")
    password: str = Field(..., description="Password for login", example="Recovo!")
    tenant_name: str = Field(..., description="Tenant name", example="Default Tenant")

    class Config:
        schema_extra = {
            "example": {
                "username": "nachoooo",
                "password": "Recovo!",
                "tenant_name": "Default Tenant",
            }
        }


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
