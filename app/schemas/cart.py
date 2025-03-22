from typing import List, Optional

from pydantic import BaseModel


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int

    class Config:
        orm_mode = True


class CartResponse(BaseModel):
    id: int
    user_id: int
    status: str
    items: List[CartItemResponse] = []

    class Config:
        orm_mode = True


class AddCartItem(BaseModel):
    product_id: int
    quantity: int


class RemoveCartItem(BaseModel):
    product_id: int
    quantity: int


class CartTotalsResponse(BaseModel):
    cart: CartResponse
    totals: dict


class ApplyDiscount(BaseModel):
    discount_id: int
