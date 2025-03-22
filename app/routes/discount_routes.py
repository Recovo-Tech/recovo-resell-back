# app/routes/discount_routes.py
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user, get_discount_service
from app.schemas.discount import (DiscountCreate, DiscountResponse,
                                  DiscountUpdate)

router = APIRouter(prefix="/discounts", tags=["Discounts"])


@router.post("/", response_model=DiscountResponse)
def create_discount(
    discount: DiscountCreate,
    current_user=Depends(get_current_user),
    discount_service=Depends(get_discount_service),
):
    return discount_service.create_discount(discount.model_dump())


@router.get("/", response_model=list[DiscountResponse])
def get_discounts(discount_service=Depends(get_discount_service)):
    return discount_service.get_all_discounts()


@router.put("/{discount_id}", response_model=DiscountResponse)
def update_discount(
    discount_id: int,
    discount: DiscountUpdate,
    current_user=Depends(get_current_user),
    discount_service=Depends(get_discount_service),
):
    updated = discount_service.update_discount(
        discount_id, discount.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Discount not found")
    return updated


@router.delete("/{discount_id}")
def deactivate_discount(
    discount_id: int,
    current_user=Depends(get_current_user),
    discount_service=Depends(get_discount_service),
):

    success = discount_service.deactivate_discount(discount_id)
    if not success:
        raise HTTPException(status_code=404, detail="Discount not found")
    return {"detail": "Discount deactivated"}
