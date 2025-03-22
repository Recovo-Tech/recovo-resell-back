from fastapi import APIRouter, Depends, HTTPException
from app.schemas.cart import CartResponse, CartTotalsResponse, AddCartItem, RemoveCartItem
from app.dependencies import get_cart_service, get_current_user

router = APIRouter(prefix="/cart", tags=["Cart"])

@router.get("/", response_model=CartResponse)
def get_active_cart(current_user = Depends(get_current_user), cart_service = Depends(get_cart_service)):
    cart = cart_service.get_active_cart(current_user.id)
    if not cart:
        raise HTTPException(status_code=404, detail="No active cart found")
    return cart

@router.post("/items", response_model=CartResponse)
def add_item_to_cart(item: AddCartItem, current_user = Depends(get_current_user), cart_service = Depends(get_cart_service)):
    if current_user.id != item.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to add items for this user")
    cart_service.add_item_to_cart(current_user.id, item.product_id, item.quantity)
    return cart_service.get_active_cart(current_user.id)

@router.delete("/items", response_model=CartResponse)
def remove_item_from_cart(item: RemoveCartItem, current_user = Depends(get_current_user), cart_service = Depends(get_cart_service)):
    if current_user.id != item.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to remove items for this user")
    cart_service.remove_item_from_cart(current_user.id, item.product_id, item.quantity)
    return cart_service.get_active_cart(current_user.id)

@router.post("/empty", response_model=CartResponse)
def empty_cart(current_user = Depends(get_current_user), cart_service = Depends(get_cart_service)):
    cart = cart_service.empty_cart(current_user.id)
    if not cart:
        raise HTTPException(status_code=404, detail="Active cart not found")
    return cart

@router.post("/finalize", response_model=CartTotalsResponse)
def finalize_cart(current_user = Depends(get_current_user), cart_service = Depends(get_cart_service)):
    result = cart_service.finalize_cart(current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Active cart not found")
    return result

@router.get("/history", response_model=list[CartResponse])
def get_cart_history(current_user = Depends(get_current_user), cart_service = Depends(get_cart_service)):
    return cart_service.get_cart_history(current_user.id)
