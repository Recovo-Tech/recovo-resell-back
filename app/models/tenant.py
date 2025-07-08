# app/models/tenant.py

import uuid

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.config.db_config import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True,
    )
    name = Column(String(100), nullable=False)  # Tenant/Client name
    subdomain = Column(
        String(50), unique=True, nullable=False, index=True
    )  # e.g., "client1" for client1.recovo.com
    domain = Column(String(100), nullable=True, index=True)  # Custom domain (optional)

    # Shopify configuration per tenant
    shopify_app_url = Column(
        String(200), nullable=True
    )  # e.g., "client1.myshopify.com"
    shopify_api_key = Column(String(100), nullable=True)
    shopify_api_secret = Column(String(100), nullable=True)
    shopify_access_token = Column(String(200), nullable=True)
    shopify_webhook_secret = Column(String(100), nullable=True)
    shopify_scopes = Column(String(500), nullable=True)
    shopify_api_version = Column(String(20), nullable=True)

    # Tenant settings
    is_active = Column(Boolean, default=True)
    settings = Column(
        Text, nullable=True
    )  # JSON field for additional tenant-specific settings

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
