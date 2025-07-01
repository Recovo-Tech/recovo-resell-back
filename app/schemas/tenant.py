# app/schemas/tenant.py

from typing import Optional
from datetime import datetime
import uuid
from pydantic import BaseModel


class TenantBase(BaseModel):
    name: str
    subdomain: str
    domain: Optional[str] = None
    shopify_app_url: Optional[str] = None
    shopify_api_key: Optional[str] = None
    shopify_api_secret: Optional[str] = None
    shopify_access_token: Optional[str] = None
    shopify_webhook_secret: Optional[str] = None
    shopify_scopes: Optional[str] = None
    shopify_api_version: Optional[str] = None
    is_active: bool = True
    settings: Optional[str] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    shopify_app_url: Optional[str] = None
    shopify_api_key: Optional[str] = None
    shopify_api_secret: Optional[str] = None
    shopify_access_token: Optional[str] = None
    shopify_webhook_secret: Optional[str] = None
    shopify_scopes: Optional[str] = None
    shopify_api_version: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[str] = None


class Tenant(TenantBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
