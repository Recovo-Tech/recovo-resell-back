# app/routes/second_hand_routes.py
from typing import List

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.dependencies import admin_required, get_current_user
from app.middleware.tenant_middleware import get_current_tenant
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.second_hand_product import (ProductSearchFilters,
                                             ProductVerificationRequest,
                                             ProductVerificationResponse,
                                             SecondHandProduct,
                                             SecondHandProductCreate,
                                             SecondHandProductList,
                                             SecondHandProductUpdate)
from app.services.file_upload_service import FileUploadService
from app.services.second_hand_product_service import SecondHandProductService
from app.services.shopify_service import ShopifyProductVerificationService

router = APIRouter(prefix="/second-hand", tags=["Second Hand Products"])


@router.post("/verify-product", response_model=ProductVerificationResponse)
async def verify_product(
    verification_request: ProductVerificationRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Verify if a product with given SKU/barcode exists in the Shopify store for current tenant"""

    # Check if tenant has Shopify configuration
    if not current_tenant.shopify_app_url or not current_tenant.shopify_access_token:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Shopify integration not configured for this tenant",
                "error": "Missing Shopify configuration",
                "error_code": "SHOPIFY_NOT_CONFIGURED",
                "success": False,
            },
        )

    # Use tenant-specific Shopify config
    try:
        verification_service = ShopifyProductVerificationService(
            current_tenant.shopify_app_url, current_tenant.shopify_access_token
        )

        result = await verification_service.verify_product_eligibility(
            sku=verification_request.sku, barcode=verification_request.barcode
        )

        return ProductVerificationResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid verification request",
                "error": str(e),
                "error_code": "INVALID_REQUEST",
                "success": False,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error verifying product against Shopify",
                "error": str(e),
                "error_code": "VERIFICATION_ERROR",
                "success": False,
            },
        )


@router.post("/products", response_model=SecondHandProduct)
async def create_second_hand_product(
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    condition: str = Form(...),
    original_sku: str = Form(...),
    barcode: str = Form(None),
    size: str = Form(None),
    color: str = Form(None),
    return_address: str = Form(None),
    files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Create a new second-hand product listing with image uploads in one request"""
    # --- Input Validation ---
    valid_conditions = ["new", "like_new", "good", "fair", "poor"]
    if condition not in valid_conditions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"error.invalid_condition._must_be_one_of: {', '.join(valid_conditions)}",
        )

    allowed_extensions = {"jpg", "jpeg", "png", "webp"}
    if not files or len([f for f in files if f.filename]) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 3 images are required.",
        )
    for file in files:
        if (
            file.filename
            and file.filename.rsplit(".", 1)[-1].lower() not in allowed_extensions
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image format: {file.filename}. Allowed formats: {', '.join(allowed_extensions)}",
            )

    # --- Call the Service to Handle All Business Logic ---
    service = SecondHandProductService(db)
    product_data = {
        "name": name,
        "description": description,
        "price": price,
        "condition": condition,
        "original_sku": original_sku,
        "barcode": barcode,
        "size": size,
        "color": color,
        "return_address": return_address,
    }

    result = await service.create_product_with_images_and_auto_publish(
        user_id=current_user.id,
        tenant=current_tenant,
        product_data=product_data,
        files=files,
    )

    # --- Handle Service Response ---
    if not result.get("success"):
        # Check for a specific warning about auto-approval failure
        if result.get("warning"):
            raise HTTPException(
                status_code=status.HTTP_207_MULTI_STATUS,  # Partial success
                detail={
                    "message": "Product created successfully but automatic approval failed",
                    "product": result.get("product"),  # Return the created product data
                    "warning": result.get("warning"),
                    "warning_details": result.get("warning_details"),
                },
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Failed to create product",
                "error": result.get("error", "An unknown error occurred."),
                "error_code": result.get("error_code", "PRODUCT_CREATION_FAILED"),
            },
        )

    return result["product"]


@router.get("/products/my", response_model=List[SecondHandProduct])
async def get_my_products(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Get current user's second-hand products"""
    service = SecondHandProductService(db)
    return service.get_user_products(current_user.id, current_tenant.id, skip, limit)


@router.get("/products", response_model=List[SecondHandProduct])
async def get_approved_products(
    skip: int = 0,
    limit: int = 100,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Get all approved second-hand products for current tenant"""
    service = SecondHandProductService(db)
    return service.get_approved_products(current_tenant.id, skip, limit)


@router.get("/products/not_approved", response_model=List[SecondHandProduct])
async def get_not_approved_products(
    skip: int = 0,
    limit: int = 100,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Get all approved second-hand products for current tenant"""
    service = SecondHandProductService(db)
    return service.get_not_approved_products(current_tenant.id, skip, limit)


@router.get("/products/{product_id}", response_model=SecondHandProduct)
async def get_product(
    product_id: int,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Get a specific second-hand product by ID within current tenant"""
    service = SecondHandProductService(db)
    product = service.get_product_by_id(product_id, current_tenant.id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Product not found",
                "error": f"No second-hand product found with ID {product_id}",
                "error_code": "PRODUCT_NOT_FOUND",
                "success": False,
            },
        )

    return product


@router.put("/products/{product_id}", response_model=SecondHandProduct)
async def update_product(
    product_id: int,
    update_data: SecondHandProductUpdate,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Update a second-hand product (only by owner within tenant)"""
    service = SecondHandProductService(db)

    # Convert update_data to dict, excluding None values
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

    product = service.update_product(
        product_id, current_user.id, current_tenant.id, update_dict
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Product not found or permission denied",
                "error": f"No product found with ID {product_id} or you don't have permission to update it",
                "error_code": "PRODUCT_NOT_FOUND_OR_NO_PERMISSION",
                "success": False,
            },
        )

    return product


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Delete a second-hand product (only by owner within tenant)"""
    service = SecondHandProductService(db)

    success = service.delete_product(product_id, current_user.id, current_tenant.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "Product not found or permission denied",
                "error": f"No product found with ID {product_id} or you don't have permission to delete it",
                "error_code": "PRODUCT_NOT_FOUND_OR_NO_PERMISSION",
                "success": False,
            },
        )

    return {
        "message": "Product deleted successfully",
        "product_id": product_id,
        "success": True,
    }


@router.post("/products/search", response_model=List[SecondHandProduct])
async def search_products(
    filters: ProductSearchFilters,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Search approved second-hand products with filters within current tenant"""
    service = SecondHandProductService(db)

    return service.search_products(
        tenant_id=current_tenant.id,
        query=filters.query,
        condition=filters.condition,
        size=filters.size,
        color=filters.color,
        min_price=filters.min_price,
        max_price=filters.max_price,
        skip=filters.skip,
        limit=filters.limit,
    )


# Admin routes (require admin authentication)
@router.post("/admin/products/{product_id}/approve")
async def approve_product(
    product_id: int,
    current_user: User = Depends(admin_required),  # Use admin dependency
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Approve a second-hand product for sale and publish to Shopify (admin only)"""
    try:
        service = SecondHandProductService(db)

        result = await service.approve_product(product_id, current_tenant.id)

        if not result["success"]:
            if result.get("error_code") == "PRODUCT_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "message": "Product not found",
                        "error": f"no_second-hand_product_found_with_ID_{product_id}",
                        "error_code": "PRODUCT_NOT_FOUND",
                        "success": False,
                    },
                )
            else:
                error_code = result.get("error_code", "APPROVAL_FAILED")
                error_message = result.get(
                    "error", "unknown_error_during_product_approval"
                )

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Product approval failed",
                        "error": error_message,
                        "error_code": error_code,
                        "success": False,
                    },
                )

        # Return response with appropriate warnings
        response = {
            "success": True,
            "product_id": product_id,
            "message": result.get("message", "Product approved successfully"),
        }

        # Include warnings if any
        if "warning" in result:
            response["warning"] = result["warning"]
            response["warning_code"] = result.get("error_code")

        if "shopify_product_id" in result:
            response["shopify_product_id"] = result["shopify_product_id"]

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unexpected error during product approval",
                "error": str(e),
                "error_code": "APPROVAL_EXCEPTION",
                "success": False,
            },
        )
