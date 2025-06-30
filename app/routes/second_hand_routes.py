# app/routes/second_hand_routes.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.models.user import User
from app.services.second_hand_product_service import SecondHandProductService
from app.services.shopify_service import ShopifyProductVerificationService
from app.services.file_upload_service import FileUploadService
from app.schemas.second_hand_product import (
    SecondHandProduct,
    SecondHandProductCreate,
    SecondHandProductUpdate,
    SecondHandProductList,
    ProductVerificationRequest,
    ProductVerificationResponse,
    ProductSearchFilters,
)
from app.dependencies import get_current_user  
from app.config.shopify_config import shopify_settings


router = APIRouter(prefix="/second-hand", tags=["Second Hand Products"])


@router.post("/verify-product", response_model=ProductVerificationResponse)
async def verify_product(
    verification_request: ProductVerificationRequest, db: Session = Depends(get_db)
):
    """Verify if a product with given SKU/barcode exists in the Shopify store (single store only)"""
    # Get Shopify config from environment
    shopify_config = shopify_settings
    verification_service = ShopifyProductVerificationService(
        shopify_config.shopify_app_url, shopify_config.shopify_access_token
    )

    result = await verification_service.verify_product_eligibility(
        sku=verification_request.sku, barcode=verification_request.barcode
    )

    return ProductVerificationResponse(**result)


@router.post("/upload-images")
async def upload_product_images(
    files: List[UploadFile] = File(...), current_user: User = Depends(get_current_user)
):
    """Upload product images"""
    upload_service = FileUploadService()

    try:
        image_paths = await upload_service.upload_multiple_images(files)
        return {"success": True, "image_urls": image_paths, "count": len(image_paths)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading images: {str(e)}",
        )


@router.post("/products", response_model=SecondHandProduct)
async def create_second_hand_product(
    product_data: SecondHandProductCreate,
    shop_domain: str,
    shopify_access_token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new second-hand product listing"""
    service = SecondHandProductService(db)

    result = await service.create_second_hand_product(
        user_id=current_user.id,
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        condition=product_data.condition,
        original_sku=product_data.original_sku,
        barcode=product_data.barcode,
        shop_domain=shop_domain,
        shopify_access_token=shopify_access_token,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"]
        )

    # Add images if provided
    if product_data.image_urls:
        service.add_product_images(result["product"].id, product_data.image_urls)
        db.refresh(result["product"])

    return result["product"]


@router.get("/products/my", response_model=List[SecondHandProduct])
async def get_my_products(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's second-hand products"""
    service = SecondHandProductService(db)
    return service.get_user_products(current_user.id, skip, limit)


@router.get("/products", response_model=List[SecondHandProduct])
async def get_approved_products(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """Get all approved second-hand products"""
    service = SecondHandProductService(db)
    return service.get_approved_products(skip, limit)


@router.get("/products/{product_id}", response_model=SecondHandProduct)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a specific second-hand product by ID"""
    service = SecondHandProductService(db)
    product = service.get_product_by_id(product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    return product


@router.put("/products/{product_id}", response_model=SecondHandProduct)
async def update_product(
    product_id: int,
    update_data: SecondHandProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a second-hand product (only by owner)"""
    service = SecondHandProductService(db)

    # Convert update_data to dict, excluding None values
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

    product = service.update_product(product_id, current_user.id, update_dict)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or you don't have permission to update it",
        )

    return product


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a second-hand product (only by owner)"""
    service = SecondHandProductService(db)

    success = service.delete_product(product_id, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or you don't have permission to delete it",
        )

    return {"message": "Product deleted successfully"}


@router.post("/products/search", response_model=List[SecondHandProduct])
async def search_products(filters: ProductSearchFilters, db: Session = Depends(get_db)):
    """Search approved second-hand products with filters"""
    service = SecondHandProductService(db)

    return service.search_products(
        query=filters.query,
        condition=filters.condition,
        min_price=filters.min_price,
        max_price=filters.max_price,
        skip=filters.skip,
        limit=filters.limit,
    )


# Admin routes (require admin authentication)
@router.post("/admin/products/{product_id}/approve", response_model=SecondHandProduct)
async def approve_product(
    product_id: int,
    current_user: User = Depends(get_current_user),  # Add admin check here
    db: Session = Depends(get_db),
):
    """Approve a second-hand product for sale and publish to Shopify (admin only)"""
    # TODO: Add admin role check
    service = SecondHandProductService(db)

    product = await service.approve_product(product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    return product
