# app/routes/shopify_product_routes.py

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.models.tenant import Tenant
from app.middleware.tenant_middleware import get_current_tenant
from app.services.shopify_product_service import ShopifyProductService
from app.schemas.shopify_product import (
    ProductListResponse,
    ShopifyProduct,
    ProductFiltersRequest,
    ProductSearchRequest,
    AvailableFilters
)

router = APIRouter(prefix="/shopify/products", tags=["Shopify Products"])


@router.get("/", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=250, description="Number of products per page"),
    collection_id: Optional[str] = Query(None, description="Filter by collection/category ID"),
    product_type: Optional[str] = Query(None, description="Filter by product type"),
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    status: Optional[str] = Query("ACTIVE", description="Filter by product status"),
    search: Optional[str] = Query(None, description="Search query"),
    after_cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    List products from the tenant's Shopify store with pagination and filtering
    
    Supports filtering by:
    - Collection/Category ID
    - Product type
    - Vendor
    - Status (ACTIVE, ARCHIVED, DRAFT)
    - Search query
    
    Uses cursor-based pagination for optimal performance.
    """
    
    # Check if tenant has Shopify configuration
    if not current_tenant.shopify_app_url or not current_tenant.shopify_access_token:
        raise HTTPException(
            status_code=400,
            detail="Shopify integration not configured for this tenant. Please contact your administrator.",
        )

    try:
        service = ShopifyProductService(current_tenant)
        
        result = await service.get_products(
            page=page,
            limit=limit,
            collection_id=collection_id,
            product_type=product_type,
            vendor=vendor,
            status=status,
            search=search,
            after_cursor=after_cursor
        )
        
        return ProductListResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching products: {str(e)}"
        )


@router.get("/{product_id}", response_model=ShopifyProduct)
async def get_product(
    product_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Get a specific product by its Shopify ID"""
    
    # Check if tenant has Shopify configuration
    if not current_tenant.shopify_app_url or not current_tenant.shopify_access_token:
        raise HTTPException(
            status_code=400,
            detail="Shopify integration not configured for this tenant. Please contact your administrator.",
        )

    try:
        service = ShopifyProductService(current_tenant)
        
        product = await service.get_product_by_id(product_id)
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )
        
        return ShopifyProduct(**product)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching product: {str(e)}"
        )


@router.get("/filters/available", response_model=AvailableFilters)
async def get_available_filters(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Get available filter options for products in the tenant's Shopify store"""
    
    # Check if tenant has Shopify configuration
    if not current_tenant.shopify_app_url or not current_tenant.shopify_access_token:
        raise HTTPException(
            status_code=400,
            detail="Shopify integration not configured for this tenant. Please contact your administrator.",
        )

    try:
        service = ShopifyProductService(current_tenant)
        
        filters = await service.get_available_filters()
        
        return AvailableFilters(**filters)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching filters: {str(e)}"
        )


@router.post("/search", response_model=ProductListResponse)
async def search_products(
    search_request: ProductSearchRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    Advanced product search with filters
    
    Allows complex filtering combinations:
    - Text search across title, description, and tags
    - Filter by collection, product type, vendor
    - Combine multiple filters
    """
    
    # Check if tenant has Shopify configuration
    if not current_tenant.shopify_app_url or not current_tenant.shopify_access_token:
        raise HTTPException(
            status_code=400,
            detail="Shopify integration not configured for this tenant. Please contact your administrator.",
        )

    try:
        service = ShopifyProductService(current_tenant)
        
        # Extract filters
        filters = {}
        if search_request.filters:
            filters = {
                "collection_id": search_request.filters.collection_id,
                "product_type": search_request.filters.product_type,
                "vendor": search_request.filters.vendor,
                "status": search_request.filters.status or "ACTIVE"
            }
        
        result = await service.search_products(
            query=search_request.query,
            filters=filters,
            page=search_request.page,
            limit=search_request.limit
        )
        
        return ProductListResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching products: {str(e)}"
        )
