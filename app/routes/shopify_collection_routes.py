# app/routes/shopify_collection_routes.py

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_shopify_collection_service

router = APIRouter(prefix="/shopify/collections", tags=["Shopify Collections"])


@router.get(
    "",
    summary="Get all collections",
    description="Fetch all collections from the tenant's Shopify store",
)
async def get_collections(service=Depends(get_shopify_collection_service)):
    """Get all collections from Shopify"""
    try:
        collections = await service.get_collections()
        return {
            "collections": collections,
            "total": len(collections),
            "message": f"Successfully fetched {len(collections)} collections",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_fetch_collections: {str(e)}"
        )


@router.get(
    "/{collection_id}",
    summary="Get collection by ID",
    description="Fetch a specific collection by its ID with sample products",
)
async def get_collection_by_id(
    collection_id: str, service=Depends(get_shopify_collection_service)
):
    """Get a specific collection by its ID"""
    try:
        collection = await service.get_collection_by_id(collection_id)
        if not collection:
            raise HTTPException(
                status_code=404,
                detail=f"error.collection_with_ID_{collection_id}_not_found",
            )

        return {"collection": collection, "message": "Collection fetched successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_fetch_collection: {str(e)}"
        )


@router.get(
    "/search/{query}",
    summary="Search collections",
    description="Search collections by name or description",
)
async def search_collections(
    query: str, service=Depends(get_shopify_collection_service)
):
    """Search collections by name or description"""
    try:
        collections = await service.search_collections(query)
        return {
            "collections": collections,
            "total": len(collections),
            "query": query,
            "message": f"Found {len(collections)} collections matching '{query}'",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.failed_to_search_collections: {str(e)}"
        )
