# app/schemas/tenant.py

import uuid
from datetime import datetime
from typing import Optional

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


class TenantResponse(BaseModel):
    """Response schema for tenant data with sensitive fields masked"""
    id: uuid.UUID
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
    created_at: datetime
    updated_at: Optional[datetime] = None

    @classmethod
    def from_tenant(cls, tenant: "Tenant") -> "TenantResponse":
        """Create TenantResponse from Tenant model with sensitive data masked"""
        def mask_sensitive(value: Optional[str]) -> Optional[str]:
            if value and len(value) > 0:
                return "*" * min(12, len(value))
            return value

        return cls(
            id=tenant.id,
            name=tenant.name,
            subdomain=tenant.subdomain,
            domain=tenant.domain,
            shopify_app_url=tenant.shopify_app_url,
            shopify_api_key=mask_sensitive(tenant.shopify_api_key),
            shopify_api_secret=mask_sensitive(tenant.shopify_api_secret),
            shopify_access_token=mask_sensitive(tenant.shopify_access_token),
            shopify_webhook_secret=mask_sensitive(tenant.shopify_webhook_secret),
            shopify_scopes=tenant.shopify_scopes,
            shopify_api_version=tenant.shopify_api_version,
            is_active=tenant.is_active,
            settings=tenant.settings,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )

    class Config:
        from_attributes = True
