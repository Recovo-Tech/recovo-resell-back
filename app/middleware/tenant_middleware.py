# app/middleware/tenant_middleware.py

from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from app.config.db_config import get_db
from app.services.tenant_service import TenantService
from app.models.tenant import Tenant


class TenantContext:
    """Store tenant context for the current request"""
    def __init__(self):
        self.tenant: Tenant = None


# Global tenant context for each request
tenant_context = TenantContext()


def get_current_tenant() -> Tenant:
    """Dependency to get current tenant from context"""
    if not tenant_context.tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tenant context found. Please ensure request includes proper domain/subdomain."
        )
    return tenant_context.tenant


async def tenant_middleware(request: Request, call_next):
    """Middleware to detect and set tenant context"""
    # Reset tenant context for each request
    tenant_context.tenant = None
    
    # Get host from request
    host = request.headers.get("host", "")
    
    # Remove port if present
    if ":" in host:
        host = host.split(":")[0]
    
    # Get tenant from database
    db: Session = next(get_db())
    try:
        tenant_service = TenantService(db)
        tenant = tenant_service.get_tenant_by_host(host)
        
        if tenant and tenant.is_active:
            tenant_context.tenant = tenant
        elif not host.startswith("localhost") and not host.startswith("127.0.0.1"):
            # For non-localhost requests, require tenant
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant not found for domain: {host}"
            )
        else:
            # For localhost/development, use default tenant
            tenant = tenant_service.get_tenant_by_subdomain("default")
            if tenant:
                tenant_context.tenant = tenant
    
    finally:
        db.close()
    
    response = await call_next(request)
    return response
