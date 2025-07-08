# app/routes/shopify_category_routes.py

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_shopify_category_service

router = APIRouter(prefix="/shopify/categories", tags=["Shopify Categories"])


@router.get(
    "",
    summary="Get all categories",
    description="Fetch all product categories (product types, vendors, tags) from the tenant's Shopify store",
)
async def get_categories(service=Depends(get_shopify_category_service)):
    """Get all product categories from Shopify"""
    try:
        categories = await service.get_categories()
        return {
            "categories": categories,
            "total": len(categories),
            "message": f"Successfully fetched {len(categories)} categories",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_fetch_categories: {str(e)}"
        )


@router.get(
    "/product-types",
    summary="Get product types",
    description="Fetch only product types from the tenant's Shopify store",
)
async def get_product_types(service=Depends(get_shopify_category_service)):
    """Get only product types from Shopify"""
    try:
        product_types = await service.get_product_types()
        return {
            "product_types": product_types,
            "total": len(product_types),
            "message": f"Successfully fetched {len(product_types)} product types",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_fetch_product_types: {str(e)}"
        )


@router.get(
    "/vendors",
    summary="Get vendors",
    description="Fetch only vendors from the tenant's Shopify store",
)
async def get_vendors(service=Depends(get_shopify_category_service)):
    """Get only vendors from Shopify"""
    try:
        vendors = await service.get_vendors()
        return {
            "vendors": vendors,
            "total": len(vendors),
            "message": f"Successfully fetched {len(vendors)} vendors",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_fetch_vendors: {str(e)}"
        )


@router.get(
    "/tags",
    summary="Get tags",
    description="Fetch product tags from the tenant's Shopify store",
)
async def get_tags(
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of tags to return"
    ),
    service=Depends(get_shopify_category_service),
):
    """Get product tags from Shopify"""
    try:
        tags = await service.get_tags(limit=limit)
        return {
            "tags": tags,
            "total": len(tags),
            "limit": limit,
            "message": f"Successfully fetched {len(tags)} tags",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_fetch_tags: {str(e)}"
        )


@router.get(
    "/search/{query}",
    summary="Search categories",
    description="Search categories by name",
)
async def search_categories(query: str, service=Depends(get_shopify_category_service)):
    """Search categories by name"""
    try:
        categories = await service.search_categories(query)
        return {
            "categories": categories,
            "total": len(categories),
            "query": query,
            "message": f"Found {len(categories)} categories matching '{query}'",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_search_categories: {str(e)}"
        )
