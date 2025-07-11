# app/routes/tenant_routes.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dependencies import admin_required
from app.middleware.tenant_middleware import get_current_tenant
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import Tenant as TenantSchema
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/admin/tenants", tags=["Tenant Management"])


@router.get("/", response_model=List[TenantResponse])
async def get_all_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Get all tenants (super admin only)"""
    # TODO: Add super admin check
    service = TenantService(db)
    tenants = service.get_all_tenants(skip, limit)
    return [TenantResponse.from_tenant(tenant) for tenant in tenants]


@router.post("/", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Create a new tenant (super admin only)"""
    # TODO: Add super admin check
    service = TenantService(db)
    tenant = service.create_tenant(tenant_data)
    return TenantResponse.from_tenant(tenant)


@router.get("/current", response_model=TenantResponse)
async def get_current_tenant_info(
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """Get current tenant information"""
    return TenantResponse.from_tenant(current_tenant)


@router.put("/current", response_model=TenantResponse)
async def update_current_tenant(
    update_data: TenantUpdate,
    current_user: User = Depends(admin_required),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Update current tenant (admin only)"""
    service = TenantService(db)
    updated_tenant = service.update_tenant(current_tenant.id, update_data)

    if not updated_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="error.tenant_not_found"
        )

    return TenantResponse.from_tenant(updated_tenant)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant_by_id(
    tenant_id: str,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Get tenant by ID (super admin only)"""
    # TODO: Add super admin check
    service = TenantService(db)
    tenant = service.get_tenant_by_id(tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="error.tenant_not_found"
        )

    return TenantResponse.from_tenant(tenant)


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    update_data: TenantUpdate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Update tenant by ID (super admin only)"""
    # TODO: Add super admin check
    service = TenantService(db)
    updated_tenant = service.update_tenant(tenant_id, update_data)

    if not updated_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="error.tenant_not_found"
        )

    return TenantResponse.from_tenant(updated_tenant)


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Delete tenant by ID (super admin only)"""
    # TODO: Add super admin check
    service = TenantService(db)
    success = service.delete_tenant(tenant_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="error.tenant_not_found"
        )

    return {"message": "Tenant deleted successfully"}
