from app.models.tenant import Tenant
from app.repositories import TenantRepository


class TenantService:
    def __init__(self, db):
        self.repo = TenantRepository(db)

    def get_all_tenants(self):
        return self.repo.get_all()

    def get_tenant_by_id(self, tenant_id: int):
        return self.repo.get_by_id(tenant_id)

    def get_tenant_by_name(self, tenant_name: str):
        """Get tenant by name, ensuring uniqueness"""
        return self.repo.get_all_by(Tenant.name == tenant_name).first()

    def create_tenant(self, tenant_data: dict):
        new_tenant = Tenant(**tenant_data)
        return self.repo.create(new_tenant)

    def update_tenant(self, tenant_id: int, update_data: dict):
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        return self.repo.update(tenant, update_data)

    def delete_tenant(self, tenant_id: int):
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False
        self.repo.delete(tenant)
        return True
