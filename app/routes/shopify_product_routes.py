# app/routes/shopify_product_routes.py

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.middleware.tenant_middleware import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.shopify_product import (AvailableFilters,
                                         ProductFiltersRequest,
                                         ProductListResponse,
                                         ProductSearchRequest, ShopifyProduct)
from app.services.shopify_product_service import ShopifyProductService

router = APIRouter(prefix="/shopify/products", tags=["Shopify Products"])


@router.get("/", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=250, description="Number of products per page"),
    collection_id: Optional[str] = Query(
        None, description="Filter by collection/category ID"
    ),
    product_type: Optional[str] = Query(None, description="Filter by product type"),
    vendor: Optional[str] = Query(None, description="Filter by vendor"),
    status: Optional[str] = Query("ACTIVE", description="Filter by product status"),
    search: Optional[str] = Query(None, description="Search query"),
    after_cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    include_count: bool = Query(True, description="Include total count (may be slower for large stores)"),
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

    **Pagination Information:**
    - Uses cursor-based pagination for optimal performance
    - Returns total_count and total_pages when include_count=true
    - For large stores, set include_count=false for faster responses

    **Frontend Pagination Example:**
    ```javascript
    // Traditional pagination with page numbers
    const response = await fetch('/shopify/products?page=1&limit=20&include_count=true');
    const data = await response.json();
    console.log(`Page ${data.pagination.page} of ${data.pagination.total_pages}`);
    console.log(`${data.products.length} of ${data.pagination.total_count} products`);

    // Cursor-based pagination for performance
    const nextPage = await fetch(`/shopify/products?after_cursor=${data.pagination.next_cursor}&include_count=false`);
    ```
    """

    # Check if tenant has Shopify configuration
    if not current_tenant.shopify_app_url or not current_tenant.shopify_access_token:
        raise HTTPException(
            status_code=400,
            detail="error.shopify_integration_not_configured_for_this_tenant._please_contact_your_administrator.",
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
            after_cursor=after_cursor,
            include_count=include_count,
        )

        # If collection_id is provided, ensure we only return products that belong to that specific collection
        # This is a backup filter in case Shopify's GraphQL collection_id filter doesn't work properly
        if collection_id:
            original_count = len(result.get('products', []))
            
            # Clean the collection ID for comparison
            clean_collection_id = collection_id.replace("gid://shopify/Collection/", "")
            
            filtered_products = []
            for product in result.get('products', []):
                product_collections = product.get('collections', [])
                # Check if the product belongs to the requested collection
                for collection in product_collections:
                    if (collection.get('id') == clean_collection_id or 
                        collection.get('id') == collection_id or
                        collection.get('shopify_id') == collection_id):
                        filtered_products.append(product)
                        break  # Found the collection, no need to check others
            
            result['products'] = filtered_products
            
            # Log the filtering for debugging
            print(f"Collection filter for '{collection_id}': {original_count} products -> {len(filtered_products)} products in collection")

        return ProductListResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.fetching_products: {str(e)}"
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
            detail="error.shopify_integration_not_configured_for_this_tenant._please_contact_your_administrator.",
        )

    try:
        service = ShopifyProductService(current_tenant)

        product = await service.get_product_by_id(product_id)

        if not product:
            raise HTTPException(status_code=404, detail="error.Product not found")

        return ShopifyProduct(**product)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"error.fetching_product: {str(e)}")


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
            detail="error.shopify_integration_not_configured_for_this_tenant._please_contact_your_administrator.",
        )

    try:
        service = ShopifyProductService(current_tenant)

        filters = await service.get_available_filters()

        return AvailableFilters(**filters)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.Error fetching filters: {str(e)}"
        )


@router.post("/search", response_model=ProductListResponse)
async def search_products(
    search_request: ProductSearchRequest,
    include_count: bool = Query(True, description="Include total count (may be slower for large stores)"),
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
            detail="error.shopify_integration_not_configured_for_this_tenant._please_contact_your_administrator.",
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
                "status": search_request.filters.status or "ACTIVE",
            }

        result = await service.search_products(
            query=search_request.query,
            filters=filters,
            page=search_request.page,
            limit=search_request.limit,
            include_count=include_count,
        )

        return ProductListResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.Error searching products: {str(e)}"
        )
