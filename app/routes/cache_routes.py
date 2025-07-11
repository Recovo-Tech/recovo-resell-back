# app/routes/cache_routes.py

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dependencies import admin_required
from app.middleware.tenant_middleware import get_current_tenant
from app.models.tenant import Tenant
from app.models.user import User
from app.services.shopify_product_service import ShopifyProductService
from app.services.shopify_collection_service import ShopifyCollectionService

router = APIRouter(prefix="/admin/cache", tags=["Cache Management"])


@router.get("/stats")
async def get_cache_stats(
    current_user: User = Depends(admin_required),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get cache statistics for current tenant"""
    try:
        product_service = ShopifyProductService(current_tenant)
        stats = await product_service.get_cache_stats()
        return {
            "success": True,
            "cache_stats": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting cache stats: {str(e)}"
        )


@router.delete("/products")
async def clear_products_cache(
    current_user: User = Depends(admin_required),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Clear all products cache for current tenant"""
    try:
        product_service = ShopifyProductService(current_tenant)
        success = await product_service.clear_cache()
        return {
            "success": success,
            "message": "Products cache cleared" if success else "Failed to clear cache"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing cache: {str(e)}"
        )


@router.delete("/products/{product_id}")
async def invalidate_product_cache(
    product_id: str,
    current_user: User = Depends(admin_required),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Invalidate cache for a specific product"""
    try:
        product_service = ShopifyProductService(current_tenant)
        success = await product_service.invalidate_cache(product_id)
        return {
            "success": success,
            "message": f"Cache invalidated for product {product_id}" if success else "Failed to invalidate cache"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error invalidating cache: {str(e)}"
        )


@router.delete("/collections")
async def clear_collections_cache(
    current_user: User = Depends(admin_required),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Clear all collections cache for current tenant"""
    try:
        collection_service = ShopifyCollectionService(current_tenant)
        # Clear collections cache
        await collection_service.cache.backend.clear(f"shopify:collections:{current_tenant.id}")
        return {
            "success": True,
            "message": "Collections cache cleared"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing collections cache: {str(e)}"
        )


@router.delete("/all")
async def clear_all_cache(
    current_user: User = Depends(admin_required),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Clear all cache for current tenant"""
    try:
        product_service = ShopifyProductService(current_tenant)
        collection_service = ShopifyCollectionService(current_tenant)
        
        # Clear all caches
        products_success = await product_service.clear_cache()
        await collection_service.cache.backend.clear(f"shopify:collections:{current_tenant.id}")
        
        return {
            "success": products_success,
            "message": "All cache cleared" if products_success else "Partial cache clear"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing all cache: {str(e)}"
        )
