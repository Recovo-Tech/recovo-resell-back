from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    username: str
    email: EmailStr
    name: Optional[str] = None
    surname: Optional[str] = None
    role: Optional[str] = None


class UserCreate(UserBase):
    password: str
    password_confirmation: str
    tenant_name: str  # Use tenant name/subdomain instead of UUID
    


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    tenant_id: UUID
    role: str
    name: Optional[str] = None
    surname: Optional[str] = None

    class Config:
        from_attributes = True
