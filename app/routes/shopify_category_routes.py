# app/routes/shopify_category_routes.py

from fastapi import APIRouter, Depends, HTTPException
from  app.dependencies import get_shopify_category_service

router = APIRouter(prefix="/shopify/categories", tags=["Shopify Categories"])

@router.get(
    "",
    summary="Get all categories",
    description="Fetch all categories/collections from the tenant's Shopify store",
)
async def get_categories(
    service = Depends(get_shopify_category_service)
):
    """Get all categories/collections from Shopify"""
    try:
        categories = await service.get_categories()
        return {
            "categories": categories,
            "total": len(categories),
            "message": f"Successfully fetched {len(categories)} categories"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch categories: {str(e)}"
        )


@router.get(
    "/{category_id}",
    summary="Get category by ID",
    description="Fetch a specific category/collection by its ID with sample products",
)
async def get_category_by_id(
    category_id: str,
    service = Depends(get_shopify_category_service)
):
    """Get a specific category by its ID"""
    try:
        category = await service.get_category_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=404,
                detail=f"Category with ID {category_id} not found"
            )
        
        return {
            "category": category,
            "message": "Category fetched successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch category: {str(e)}"
        )


@router.get(
    "/search/{query}",
    summary="Search categories",
    description="Search categories by name or description",
)
async def search_categories(
    query: str,
    service = Depends(get_shopify_category_service)
):
    """Search categories by name or description"""
    try:
        categories = await service.search_categories(query)
        return {
            "categories": categories,
            "total": len(categories),
            "query": query,
            "message": f"Found {len(categories)} categories matching '{query}'"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search categories: {str(e)}"
        )
