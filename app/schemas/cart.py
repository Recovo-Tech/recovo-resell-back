from pydantic import BaseModel
from typing import List, Optional

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
    user_id: int
    product_id: int
    quantity: int

class RemoveCartItem(BaseModel):
    user_id: int
    product_id: int
    quantity: int

class CartTotalsResponse(BaseModel):
    cart: CartResponse
    totals: dict
