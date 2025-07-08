# app/services/tenant_service.py

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate


class TenantService:
    def __init__(self, db: Session):
        self.db = db

    def get_tenant_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        """Get a tenant by ID"""
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_tenant_by_subdomain(self, subdomain: str) -> Optional[Tenant]:
        """Get a tenant by subdomain"""
        return self.db.query(Tenant).filter(Tenant.subdomain == subdomain).first()

    def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        """Get a tenant by custom domain"""
        return self.db.query(Tenant).filter(Tenant.domain == domain).first()

    def get_tenant_by_host(self, host: str) -> Optional[Tenant]:
        """Get tenant by host (subdomain or custom domain)"""
        # First try custom domain
        tenant = self.get_tenant_by_domain(host)
        if tenant:
            return tenant

        # Then try subdomain (extract subdomain from host)
        if "." in host:
            subdomain = host.split(".")[0]
            return self.get_tenant_by_subdomain(subdomain)

        return None

    def get_tenant_by_name(self, name: str) -> Optional[Tenant]:
        """Get a tenant by name"""
        return self.db.query(Tenant).filter(Tenant.name == name).first()

    def create_tenant(self, tenant_data: TenantCreate) -> Tenant:
        """Create a new tenant"""
        tenant = Tenant(**tenant_data.dict())
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def update_tenant(
        self, tenant_id: uuid.UUID, update_data: TenantUpdate
    ) -> Optional[Tenant]:
        """Update a tenant"""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None

        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        for key, value in update_dict.items():
            setattr(tenant, key, value)

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def get_all_tenants(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """Get all tenants"""
        return self.db.query(Tenant).offset(skip).limit(limit).all()

    def delete_tenant(self, tenant_id: uuid.UUID) -> bool:
        """Delete a tenant"""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False

        self.db.delete(tenant)
        self.db.commit()
        return True
