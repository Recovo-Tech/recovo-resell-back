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
    "/top-level",
    summary="Get top-level categories",
    description="Get only top-level categories (categories with no parent)",
)
async def get_top_level_categories(service=Depends(get_shopify_category_service)):
    """Get only top-level categories"""
    try:
        categories = await service.get_top_level_categories()
        return {
            "categories": categories,
            "total": len(categories),
            "message": f"Successfully fetched {len(categories)} top-level categories",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_fetch_top_level_categories: {str(e)}"
        )


@router.get(
    "/debug/taxonomy",
    summary="Debug taxonomy data",
    description="Get raw taxonomy data for debugging",
)
async def debug_taxonomy(service=Depends(get_shopify_category_service)):
    """Debug endpoint to see raw taxonomy data"""
    try:
        # Get raw taxonomy data from the client
        taxonomy_data = await service.client.get_taxonomy()
        return {
            "raw_taxonomy": taxonomy_data,
            "message": "Raw taxonomy data retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_fetch_debug_taxonomy: {str(e)}"
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


@router.get(
    "get/{category_id}/subcategories",
    summary="Get subcategories",
    description="Get subcategories for a specific parent category",
)
async def get_subcategories(
    category_id: str, service=Depends(get_shopify_category_service)
):
    """Get subcategories for a specific parent category"""
    print(f"=== SUBCATEGORIES ENDPOINT CALLED ===")
    print(f"Raw category_id parameter: {repr(category_id)}")
    print(f"Category ID type: {type(category_id)}")
    print(f"Category ID length: {len(category_id)}")
    
    try:
        print(f"Subcategories endpoint called with category_id: {category_id}")
        subcategories = await service.get_subcategories(category_id)
        print(f"Service returned {len(subcategories)} subcategories")
        return {
            "subcategories": subcategories,
            "total": len(subcategories),
            "parent_id": category_id,
            "message": f"Found {len(subcategories)} subcategories for category {category_id}",
        }
    except Exception as e:
        print(f"Error in subcategories endpoint: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_fetch_subcategories: {str(e)}"
        )


@router.get(
    "/{category_id}/tree",
    summary="Get category tree",
    description="Get full category tree starting from a specific category",
)
async def get_category_tree(
    category_id: str,
    max_depth: int = Query(
        3, ge=1, le=10, description="Maximum depth to fetch (1-10)"
    ),
    service=Depends(get_shopify_category_service),
):
    """Get full category tree starting from a specific category"""
    try:
        tree = await service.get_category_tree(category_id, max_depth)
        return {
            "tree": tree,
            "category_id": category_id,
            "max_depth": max_depth,
            "message": (
                f"Successfully fetched category tree for {category_id} with max depth {max_depth}"
                if tree.get("category")
                else f"Category {category_id} not found"
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_fetch_category_tree: {str(e)}"
        )


