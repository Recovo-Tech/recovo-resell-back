# app/schemas/shopify_product.py

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ProductOption(BaseModel):
    """Shopify product option (Color, Size, etc.)"""

    id: str
    name: str
    values: List[str]


class ProductVariantOption(BaseModel):
    """Product variant specific option values"""

    name: str
    value: str


class ProductVariant(BaseModel):
    """Shopify product variant"""

    id: str
    shopify_id: str
    title: str
    sku: str = ""
    barcode: str = ""
    price: float
    compare_at_price: Optional[float] = None
    weight: Optional[float] = None
    weight_unit: Optional[str] = None
    inventory_quantity: int = 0
    available_for_sale: bool = False
    options: Dict[str, str] = {}  # e.g., {"color": "red", "size": "M"}


class ProductImage(BaseModel):
    """Shopify product image"""

    id: str
    url: str
    alt_text: str


class ProductCollection(BaseModel):
    """Shopify product collection/category"""

    id: str
    shopify_id: str
    title: str
    handle: str


class ShopifyProduct(BaseModel):
    """Complete Shopify product"""

    id: str
    shopify_id: str
    title: str
    handle: str
    description: str = ""
    description_html: str = ""
    status: str
    product_type: str = ""
    vendor: str = ""
    tags: List[str] = []
    created_at: str = ""
    updated_at: str = ""
    images: List[ProductImage] = []
    variants: List[ProductVariant] = []
    collections: List[ProductCollection] = []
    options: List[ProductOption] = []


class ProductPagination(BaseModel):
    """Pagination information"""

    page: int
    limit: int
    has_next_page: bool
    has_previous_page: bool
    next_cursor: Optional[str] = None
    previous_cursor: Optional[str] = None


class ProductListResponse(BaseModel):
    """Response for paginated product listing"""

    products: List[ShopifyProduct]
    pagination: ProductPagination
    tenant_id: str


class ProductFiltersRequest(BaseModel):
    """Request filters for product listing"""

    collection_id: Optional[str] = None
    product_type: Optional[str] = None
    vendor: Optional[str] = None
    status: Optional[str] = "ACTIVE"
    search: Optional[str] = None
    tags: Optional[List[str]] = None


class ProductSearchRequest(BaseModel):
    """Advanced product search request"""

    query: str
    filters: Optional[ProductFiltersRequest] = None
    page: int = 1
    limit: int = 50


class FilterOption(BaseModel):
    """Available filter option"""

    id: str
    title: str
    handle: str


class AvailableFilters(BaseModel):
    """Available filters for products"""

    collections: List[FilterOption]
    product_types: List[str]
    vendors: List[str]
    tags: List[str]
