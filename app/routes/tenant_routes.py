# app/routes/tenant_routes.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.middleware.tenant_middleware import get_current_tenant
from app.services.tenant_service import TenantService
from app.schemas.tenant import Tenant as TenantSchema, TenantCreate, TenantUpdate
from app.dependencies import admin_required

router = APIRouter(prefix="/admin/tenants", tags=["Tenant Management"])


@router.get("/", response_model=List[TenantSchema])
async def get_all_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Get all tenants (super admin only)"""
    # TODO: Add super admin check
    service = TenantService(db)
    return service.get_all_tenants(skip, limit)


@router.post("/", response_model=TenantSchema)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Create a new tenant (super admin only)"""
    # TODO: Add super admin check
    service = TenantService(db)
    return service.create_tenant(tenant_data)


@router.get("/current", response_model=TenantSchema)
async def get_current_tenant_info(
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """Get current tenant information"""
    return current_tenant


@router.put("/current", response_model=TenantSchema)
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return updated_tenant


@router.get("/{tenant_id}", response_model=TenantSchema)
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return tenant


@router.put("/{tenant_id}", response_model=TenantSchema)
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
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return updated_tenant


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
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    return {"message": "Tenant deleted successfully"}
