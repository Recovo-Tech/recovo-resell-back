# app/schemas/second_hand_product.py
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SecondHandProductImageBase(BaseModel):
    image_url: str
    is_primary: bool = False


class SecondHandProductImageCreate(SecondHandProductImageBase):
    pass


class SecondHandProductImage(SecondHandProductImageBase):
    id: int
    product_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SecondHandProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    condition: str = Field(..., pattern="^(new|like_new|good|fair|poor)$")
    original_sku: str = Field(..., min_length=1, max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    size: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=50)
    return_address: Optional[str] = Field(None, max_length=255)
    category_id: Optional[str] = Field(None, max_length=100, description="Shopify taxonomy category ID")
    category_name: Optional[str] = Field(None, max_length=200, description="Human-readable category name")


class SecondHandProductCreate(SecondHandProductBase):
    image_urls: Optional[List[str]] = []


class SecondHandProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    condition: Optional[str] = Field(None, pattern="^(new|like_new|good|fair|poor)$")
    size: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=50)
    return_address: Optional[str] = Field(None, max_length=255)
    category_id: Optional[str] = Field(None, max_length=100, description="Shopify taxonomy category ID")
    category_name: Optional[str] = Field(None, max_length=200, description="Human-readable category name")


class SecondHandProduct(SecondHandProductBase):
    id: int
    seller_id: uuid.UUID
    is_verified: bool
    is_approved: bool
    shopify_product_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    images: List[SecondHandProductImage] = []
    # Include category fields from base class
    category_id: Optional[str] = None
    category_name: Optional[str] = None

    class Config:
        from_attributes = True


class SecondHandProductList(BaseModel):
    products: List[SecondHandProduct]
    total: int
    skip: int
    limit: int


class ProductVerificationRequest(BaseModel):
    sku: Optional[str] = None
    barcode: Optional[str] = None


class ProductVerificationResponse(BaseModel):
    is_verified: bool
    error: Optional[str] = None
    product_info: Optional[dict] = None
    verification_method: Optional[str] = None


class ProductSearchFilters(BaseModel):
    query: Optional[str] = None
    condition: Optional[str] = Field(None, pattern="^(new|like_new|good|fair|poor)$")
    size: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=50)
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)


class ProductCategory(BaseModel):
    """Schema for product category information"""
    id: str = Field(..., description="Shopify taxonomy category ID")
    name: str = Field(..., description="Human-readable category name")
    full_name: Optional[str] = Field(None, description="Full category path name")
    level: Optional[int] = Field(None, description="Category hierarchy level")
    is_leaf: Optional[bool] = Field(None, description="Whether this is a leaf category")
    parent_id: Optional[str] = Field(None, description="Parent category ID")


class CategoryUpdateRequest(BaseModel):
    """Schema for updating product category"""
    category_id: str = Field(..., description="Shopify taxonomy category ID")
    category_name: Optional[str] = Field(None, description="Human-readable category name")
