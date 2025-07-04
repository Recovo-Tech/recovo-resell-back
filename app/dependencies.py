# app/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from uuid import UUID

from app.config.db_config import get_db
from app.models.tenant import Tenant
from app.middleware.tenant_middleware import get_current_tenant
from app.services import (
    AuthService,
    CartService,
    DiscountService,
    ProductService,
    UserService,
)
from app.services.tenant_service import TenantService
from app.services.shopify_category_service import ShopifyCategoryService

# Use HTTPBearer instead of OAuth2PasswordBearer for cleaner Swagger UI
# This allows simple Bearer token authorization without OAuth2 complexity
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    auth_service = AuthService(db)
    payload = auth_service.decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("id")
    tenant_id = payload.get("tenant_id")

    if user_id is None or tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user id or tenant id",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user and verify they belong to the token's tenant
    user_service = UserService(db)
    user = user_service.get_user_by_id_and_tenant(UUID(user_id), UUID(tenant_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or tenant mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def admin_required(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def client_required(current_user=Depends(get_current_user)):
    if current_user.role != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client privileges required",
        )
    return current_user


def get_cart_service(db: Session = Depends(get_db)) -> CartService:
    return CartService(db)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(db)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_discount_service(db: Session = Depends(get_db)) -> DiscountService:
    return DiscountService(db)


def get_tenant_service(db: Session = Depends(get_db)) -> TenantService:
    return TenantService(db)


def get_current_tenant_from_token(
    credentials = Depends(security),
    db: Session = Depends(get_db),
) -> Tenant:
    """Get current tenant directly from JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    auth_service = AuthService(db)
    payload = auth_service.decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tenant_id = payload.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing tenant id",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tenant_service = TenantService(db)
    tenant = tenant_service.get_tenant_by_id(UUID(tenant_id))
    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return tenant


def get_shopify_category_service(
    tenant: Tenant = Depends(get_current_tenant_from_token)
) -> ShopifyCategoryService:
    """Dependency to get ShopifyCategoryService for the current tenant"""
    try:
        return ShopifyCategoryService(tenant)
    except ValueError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Shopify not configured for tenant: {str(e)}"
        )