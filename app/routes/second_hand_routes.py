# app/routes/second_hand_routes.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.middleware.tenant_middleware import get_current_tenant
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
from app.dependencies import get_current_user, admin_required


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
            detail="error.shopify_integration_not_configured_for_this_tenant._please_contact_your_administrator.",
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"error.error_verifying_product: {str(e)}"
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
    files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Create a new second-hand product listing with image uploads in one request"""
    service = SecondHandProductService(db)
    upload_service = FileUploadService()

    # Validate condition
    valid_conditions = ["new", "like_new", "good", "fair", "poor"]
    if condition not in valid_conditions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"error.invalid_condition._must_be_one_of: {', '.join(valid_conditions)}",
        )

    # Step 1: Verify the product exists in Shopify first using tenant config
    verification_service = ShopifyProductVerificationService(
        current_tenant.shopify_app_url, current_tenant.shopify_access_token
    )

    verification_result = await verification_service.verify_product_eligibility(
        sku=original_sku, barcode=barcode
    )

    if not verification_result["is_verified"]:
        is_verified = False
    else:
        is_verified = True
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=f"error.product_verification_failed: {verification_result.get('error', 'product_not_found in Shopify')}",
    #     )

    # Step 2: Create the product in the database
    result = await service.create_second_hand_product(
        user_id=current_user.id,
        tenant_id=current_tenant.id,  # Add tenant_id
        name=name,
        description=description,
        price=price,
        condition=condition,
        original_sku=original_sku,
        barcode=barcode,
        size=size,
        shop_domain=current_tenant.shopify_app_url,  # Use tenant config
        shopify_access_token=current_tenant.shopify_access_token,  # Use tenant config
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"]
        )

    created_product = result["product"]

    # Step 3: Upload user-submitted images
    user_image_urls = []
    if files and files[0].filename:  # Check if files were actually uploaded
        try:
            user_image_urls = await upload_service.upload_multiple_images(
                files,
                user_id=str(current_user.id),
                shopify_url=current_tenant.shopify_app_url,  # Use tenant config
            )
        except HTTPException:
            # If image upload fails, we should clean up the created product
            service.delete_product(
                created_product.id, current_user.id, current_tenant.id
            )
            raise
        except Exception as e:
            # If image upload fails, we should clean up the created product
            service.delete_product(
                created_product.id, current_user.id, current_tenant.id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"error.error_uploading_images: {str(e)}",
            )

    # Step 4: Update the product with all image URLs (Shopify + user uploaded)
    all_image_urls = []

    # Add Shopify image first (if available from verification)
    shopify_image_url = None
    product_info = verification_result.get("product_info")
    if product_info:
        # Try common keys for image URL
        shopify_image_url = product_info.get("image_url") or product_info.get(
            "first_image"
        )
    if shopify_image_url:
        all_image_urls.append(shopify_image_url)

    # Add user uploaded images
    all_image_urls.extend(user_image_urls)

    # Add all images to the product
    if all_image_urls:
        service.add_product_images(
            created_product.id, current_tenant.id, all_image_urls
        )
        db.refresh(created_product)
    
    # DEBUG: Check verification status before automatic approval
    print(f"DEBUG ROUTE: Product {created_product.id} verification status:")
    print(f"  - is_verified: {created_product.is_verified}")
    print(f"  - is_approved: {created_product.is_approved}")
    print(f"  - verification_result: {verification_result.get('is_verified')}")
    
    # If product is verified, automatically approve and publish it
    if created_product.is_verified:
        print(f"DEBUG ROUTE: Product {created_product.id} is verified, attempting automatic approval...")
        try:
            approval_result = await service.approve_product(
                created_product.id, current_tenant.id
            )
            
            print(f"DEBUG ROUTE: Approval result: {approval_result}")
            
            if approval_result["success"]:
                print(f"DEBUG ROUTE: Product {created_product.id} automatically approved and published to Shopify")
                # Refresh the product to get updated fields (like shopify_product_id)
                db.refresh(created_product)
                print(f"DEBUG ROUTE: After refresh - is_approved: {created_product.is_approved}, shopify_id: {created_product.shopify_product_id}")
            else:
                print(f"WARNING ROUTE: Automatic approval failed for product {created_product.id}: {approval_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"ERROR ROUTE: Exception during automatic approval: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print(f"DEBUG ROUTE: Product {created_product.id} is NOT verified, skipping automatic approval")
   

    return created_product


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
            status_code=status.HTTP_404_NOT_FOUND, detail="error.product_not_found"
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
            detail="error.product_not_found_or_you_don't_have_permission_to_update_it",
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
            detail="error.product_not_found_or_you_don't_have_permission_to_delete_it",
        )

    return {"message": "Product deleted successfully"}


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
    service = SecondHandProductService(db)

    result = await service.approve_product(product_id, current_tenant.id)

    if not result["success"]:
        if result["error_code"] == "PRODUCT_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="error.product_not_found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"]
            )

    # Return response with appropriate warnings
    response = {
        "success": True,
        "product": result["product"],
        "message": result.get("message", "Product approved successfully"),
    }

    # Include warnings if any
    if "warning" in result:
        response["warning"] = result["warning"]
        response["error_code"] = result.get("error_code")

    if "shopify_product_id" in result:
        response["shopify_product_id"] = result["shopify_product_id"]

    return response
