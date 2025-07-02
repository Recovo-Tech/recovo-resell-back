# app/middleware/tenant_middleware.py

import os
import jwt
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
            detail="No tenant context found. This might be an unauthenticated request."
        )
    return tenant_context.tenant


async def tenant_middleware(request: Request, call_next):
    """Middleware to detect and set tenant context from JWT token"""
    # Reset tenant context for each request
    tenant_context.tenant = None
    
    # Get tenant from database
    db: Session = next(get_db())
    try:
        tenant_service = TenantService(db)
        
        # Try to get tenant from JWT token first
        authorization = request.headers.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            try:
                # Decode JWT to get tenant_id (without verification for middleware)
                secret_key = os.getenv("SECRET_KEY", "your-secret-key")
                algorithm = os.getenv("ALGORITHM", "HS256")
                payload = jwt.decode(token, secret_key, algorithms=[algorithm])
                tenant_id = payload.get("tenant_id")
                
                if tenant_id:
                    tenant = tenant_service.get_tenant_by_id(tenant_id)
                    if tenant and tenant.is_active:
                        tenant_context.tenant = tenant
            except jwt.InvalidTokenError:
                # Token is invalid, continue without tenant (will be handled by auth)
                pass
        
        # If no tenant from token, check for public endpoints that might need default tenant
        if not tenant_context.tenant:
            # For registration and other public endpoints, use default tenant
            # This allows unauthenticated requests to proceed
            tenant = tenant_service.get_tenant_by_subdomain("default")
            if tenant and tenant.is_active:
                tenant_context.tenant = tenant
    
    finally:
        db.close()
    
    response = await call_next(request)
    return response
