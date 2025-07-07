from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user, get_product_service
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=list[ProductResponse])
def get_products(product_service=Depends(get_product_service)):
    return product_service.get_all_products()


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, product_service=Depends(get_product_service)):
    product = product_service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="error.product_not_found")
    return product


@router.post("/", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    product_service=Depends(get_product_service),
    current_user=Depends(get_current_user),
):
    return product_service.create_product(product.model_dump())


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product: ProductUpdate,
    product_service=Depends(get_product_service),
    current_user=Depends(get_current_user),
):
    updated = product_service.update_product(
        product_id, product.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="error.product_not_found")
    return updated


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    product_service=Depends(get_product_service),
    current_user=Depends(get_current_user),
):
    success = product_service.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="error.product_not_found")
    return {"detail": "Product deleted"}
