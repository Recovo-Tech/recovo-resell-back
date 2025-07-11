# app/services/shopify_product_service.py

from typing import Any, Dict, List, Optional

from app.models.tenant import Tenant
from app.services.shopify_service import ShopifyGraphQLClient
from app.services.cache_service import ShopifyCacheService, get_global_cache_service, CacheConfig
from app.services.shopify_data_transformer import ShopifyDataTransformer


class ShopifyProductService:
    """Service for managing Shopify products listing and filtering"""

    def __init__(self, tenant: Tenant, cache_service: Optional[ShopifyCacheService] = None):
        if not tenant.shopify_app_url or not tenant.shopify_access_token:
            raise ValueError("Tenant must have Shopify credentials configured")

        # Use tenant's API version or default to 2024-01
        api_version = tenant.shopify_api_version or "2024-01"

        self.client = ShopifyGraphQLClient(
            shop_domain=tenant.shopify_app_url,
            access_token=tenant.shopify_access_token,
            api_version=api_version
        )
        self.tenant = tenant
        
        # Initialize cache service - use global cache service for shared state
        self.cache = cache_service or get_global_cache_service()
        
        # Initialize data transformer
        self.transformer = ShopifyDataTransformer()

    async def get_products(
        self,
        page: int = 1,
        limit: int = 50,
        collection_id: str = None,
        product_type: str = None,
        vendor: str = None,
        status: str = "ACTIVE",
        search: str = None,
        after_cursor: str = None,
        include_count: bool = True,
    ) -> Dict[str, Any]:
        """
        Get paginated products with filtering

        Args:
            page: Page number (1-based, used if after_cursor not provided)
            limit: Number of products per page (max 250)
            collection_id: Filter by collection/category ID
            product_type: Filter by product type
            vendor: Filter by vendor
            status: Filter by product status
            search: Search query
            after_cursor: Cursor for pagination (overrides page)
            include_count: Whether to include total count (slower for large stores)
        """
        try:
            # Create cache key based on parameters
            cache_filters = {
                "collection_id": collection_id,
                "product_type": product_type,
                "vendor": vendor,
                "status": status,
                "search": search,
                "include_count": include_count
            }
            
            # Try to get from cache first
            if not after_cursor:  # Only cache page-based requests
                cached_result = await self.cache.get_products_page(
                    tenant_id=str(self.tenant.id),
                    page=page,
                    limit=limit,
                    **cache_filters
                )
                if cached_result:
                    print(f"✅ Cache HIT for products page {page}")
                    return cached_result
                else:
                    print(f"❌ Cache MISS for products page {page} - fetching from Shopify API")

            # If no cursor provided, we use page-based approach
            # Note: Shopify GraphQL doesn't support offset-based pagination,
            # so this is an approximation for the first few pages
            cursor = after_cursor

            # Get total count first if needed for page validation
            total_count = None
            total_pages = None
            
            if include_count:
                try:
                    total_count = await self.client.get_products_count(
                        collection_id=collection_id,
                        product_type=product_type,
                        vendor=vendor,
                        status=status,
                        query=search,
                    )
                    
                    if total_count > 0 and limit > 0:
                        total_pages = (total_count + limit - 1) // limit  # Ceiling division
                        
                        # If requesting a page beyond available pages, return empty result
                        if page > total_pages:
                            empty_result = {
                                "products": [],
                                "pagination": {
                                    "page": page,
                                    "limit": limit,
                                    "total_count": total_count,
                                    "total_pages": total_pages,
                                    "has_next_page": False,
                                    "has_previous_page": page > 1,
                                    "next_cursor": None,
                                    "previous_cursor": None,
                                },
                                "tenant_id": str(self.tenant.id),
                            }
                            # Cache empty result for a short time
                            if not after_cursor:
                                await self.cache.set_products_page(
                                    tenant_id=str(self.tenant.id),
                                    page=page,
                                    limit=limit,
                                    products_data=empty_result,
                                    **cache_filters
                                )
                            return empty_result
                        
                except Exception as count_error:
                    print(f"Error getting product count: {count_error}")
                    # Continue without count information

            # Get products
            # For page-based requests without cursor, we need to handle pagination properly
            if page > 1 and not cursor:
                # Try to get cursor from cache first
                cached_cursor = await self.cache.get_cursor_for_page(
                    tenant_id=str(self.tenant.id),
                    page=page,
                    **cache_filters
                )
                
                if cached_cursor:
                    print(f"Using cached cursor for page {page}")
                    cursor = cached_cursor
                else:
                    # For pages beyond 1 without a cursor, we need to make sequential requests
                    # This is not ideal for performance but necessary for page-based pagination
                    current_cursor = None
                    current_page = 1
                    
                    # Navigate to the requested page
                    while current_page < page:
                        page_result = await self.client.get_products_paginated(
                            first=min(limit, 250),
                            after=current_cursor,
                            collection_id=collection_id,
                            product_type=product_type,
                            vendor=vendor,
                            status=status,
                            query=search,
                        )
                        
                        # If there's no next page, we've reached the end
                        if not page_result["page_info"]["has_next_page"]:
                            empty_result = {
                                "products": [],
                                "pagination": {
                                    "page": page,
                                    "limit": limit,
                                    "total_count": total_count,
                                    "total_pages": total_pages,
                                    "has_next_page": False,
                                    "has_previous_page": page > 1,
                                    "next_cursor": None,
                                    "previous_cursor": None,
                                },
                                "tenant_id": str(self.tenant.id),
                            }
                            # Cache empty result
                            await self.cache.set_products_page(
                                tenant_id=str(self.tenant.id),
                                page=page,
                                limit=limit,
                                products_data=empty_result,
                                **cache_filters
                            )
                            return empty_result
                        
                        current_cursor = page_result["page_info"]["end_cursor"]
                        current_page += 1
                    
                    # Cache the cursor for future use
                    await self.cache.set_cursor_for_page(
                        tenant_id=str(self.tenant.id),
                        page=page,
                        cursor=current_cursor,
                        **cache_filters
                    )
                    cursor = current_cursor
                
                # Now fetch the actual page we want
                result = await self.client.get_products_paginated(
                    first=min(limit, 250),
                    after=cursor,
                    collection_id=collection_id,
                    product_type=product_type,
                    vendor=vendor,
                    status=status,
                    query=search,
                )
            else:
                # Page 1 or cursor-based request
                result = await self.client.get_products_paginated(
                    first=min(limit, 250),
                    after=cursor,
                    collection_id=collection_id,
                    product_type=product_type,
                    vendor=vendor,
                    status=status,
                    query=search,
                )

            final_result = {
                "products": result["products"],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next_page": result["page_info"]["has_next_page"],
                    "has_previous_page": page > 1,  # More accurate than Shopify's cursor-based flag
                    "next_cursor": result["page_info"]["end_cursor"],
                    "previous_cursor": result["page_info"]["start_cursor"],
                },
                "tenant_id": str(self.tenant.id),
            }
            
            # Cache the result (only for page-based requests)
            if not after_cursor:
                cache_success = await self.cache.set_products_page(
                    tenant_id=str(self.tenant.id),
                    page=page,
                    limit=limit,
                    products_data=final_result,
                    **cache_filters
                )
                if cache_success:
                    print(f"💾 Cached products page {page}")
                else:
                    print(f"❌ Failed to cache products page {page}")

            return final_result

        except Exception as e:
            print(f"Error fetching products for tenant {self.tenant.name}: {e}")
            raise

    async def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific product by its Shopify ID with full details"""
        try:
            # Try to get from cache first
            cached_product = await self.cache.get_product(
                tenant_id=str(self.tenant.id),
                product_id=product_id
            )
            if cached_product:
                print(f"Cache hit for product {product_id}")
                return cached_product

            # Add the Shopify GID prefix if not present
            shopify_id = product_id
            if not product_id.startswith("gid://shopify/Product/"):
                shopify_id = f"gid://shopify/Product/{product_id}"

            # Use a more comprehensive query for individual product
            query = """
            query getProduct($id: ID!) {
                product(id: $id) {
                    id
                    title
                    handle
                    description
                    descriptionHtml
                    status
                    productType
                    vendor
                    tags
                    createdAt
                    updatedAt
                    images(first: 10) {
                        edges {
                            node {
                                id
                                url
                                altText
                            }
                        }
                    }
                    variants(first: 10) {
                        edges {
                            node {
                                id
                                title
                                sku
                                barcode
                                price
                                compareAtPrice
                                weight
                                weightUnit
                                inventoryQuantity
                                availableForSale
                                selectedOptions {
                                    name
                                    value
                                }
                            }
                        }
                    }
                    collections(first: 10) {
                        edges {
                            node {
                                id
                                title
                                handle
                            }
                        }
                    }
                    options {
                        id
                        name
                        values
                    }
                }
            }
            """

            response = await self.client.execute_query(query, {"id": shopify_id})

            if "errors" in response:
                print(f"GraphQL errors: {response['errors']}")
                return None

            product = response.get("data", {}).get("product")
            if not product:
                return None

            # Transform to a more detailed format
            # Extract images
            images = []
            for img_edge in product.get("images", {}).get("edges", []):
                img = img_edge["node"]
                images.append(
                    {
                        "id": img["id"],
                        "url": img["url"],
                        "alt_text": img.get("altText", ""),
                    }
                )

            # Extract variants with full details
            variants = []
            for var_edge in product.get("variants", {}).get("edges", []):
                variant = var_edge["node"]

                # Extract variant options (color, size, etc.)
                options = {}
                for option in variant.get("selectedOptions", []):
                    options[option["name"].lower()] = option["value"]

                variants.append(
                    {
                        "id": variant["id"].replace(
                            "gid://shopify/ProductVariant/", ""
                        ),
                        "shopify_id": variant["id"],
                        "title": variant["title"],
                        "sku": variant.get("sku") or "",
                        "barcode": variant.get("barcode") or "",
                        "price": float(variant["price"]) if variant["price"] else 0.0,
                        "compare_at_price": (
                            float(variant["compareAtPrice"])
                            if variant.get("compareAtPrice")
                            else None
                        ),
                        "weight": variant.get("weight"),
                        "weight_unit": variant.get("weightUnit"),
                        "inventory_quantity": variant.get("inventoryQuantity", 0),
                        "available_for_sale": variant.get("availableForSale", False),
                        "options": options,
                    }
                )

            # Extract collections
            collections = []
            for col_edge in product.get("collections", {}).get("edges", []):
                col = col_edge["node"]
                collections.append(
                    {
                        "id": col["id"].replace("gid://shopify/Collection/", ""),
                        "shopify_id": col["id"],
                        "title": col["title"],
                        "handle": col["handle"],
                    }
                )

            # Extract product options (Color, Size, etc.)
            product_options = []
            for option in product.get("options", []):
                product_options.append(
                    {
                        "id": option["id"],
                        "name": option["name"],
                        "values": option["values"],
                    }
                )

            product_result = {
                "id": product["id"].replace("gid://shopify/Product/", ""),
                "shopify_id": product["id"],
                "title": product["title"],
                "handle": product["handle"],
                "description": product.get("description", ""),
                "description_html": product.get("descriptionHtml", ""),
                "status": product["status"],
                "product_type": product.get("productType", ""),
                "vendor": product.get("vendor", ""),
                "tags": product.get("tags", []),
                "created_at": product.get("createdAt", ""),
                "updated_at": product.get("updatedAt", ""),
                "images": images,
                "variants": variants,
                "collections": collections,
                "options": product_options,
                "tenant_id": str(self.tenant.id),
            }

            # Cache the result
            await self.cache.set_product(
                tenant_id=str(self.tenant.id),
                product_id=product_id,
                product_data=product_result
            )
            print(f"Cached product {product_id} for tenant {self.tenant.id}")

            return product_result

        except Exception as e:
            print(f"Error fetching product {product_id}: {e}")
            raise

    async def get_available_filters(self) -> Dict[str, List[str]]:
        """Get available filter options from the tenant's Shopify store"""
        try:
            # Try to get from cache first
            cached_filters = await self.cache.get_available_filters(
                tenant_id=str(self.tenant.id)
            )
            if cached_filters:
                print(f"Cache hit for available filters")
                return cached_filters

            filters = await self.client.get_product_filters()

            # Also get collections for category filtering using the correct method
            collections_result = await self.client.get_products_paginated(
                first=250, query="status:ACTIVE"
            )

            # Extract unique collections from products
            unique_collections = {}
            for product in collections_result.get("products", []):
                for collection in product.get("collections", []):
                    unique_collections[collection["id"]] = {
                        "id": collection["id"],
                        "title": collection["title"],
                        "handle": collection["handle"],
                    }

            filters_result = {
                "collections": list(unique_collections.values()),
                "product_types": filters.get("product_types", []),
                "vendors": filters.get("vendors", []),
                "tags": filters.get("tags", []),
            }

            # Cache the result
            await self.cache.set_available_filters(
                tenant_id=str(self.tenant.id),
                filters_data=filters_result
            )
            print(f"Cached available filters for tenant {self.tenant.id}")

            return filters_result

        except Exception as e:
            print(f"Error fetching filters: {e}")
            raise

    async def search_products(
        self, query: str, filters: Dict[str, Any] = None, page: int = 1, limit: int = 50, include_count: bool = True
    ) -> Dict[str, Any]:
        """
        Search products with advanced filtering

        Args:
            query: Search query
            filters: Additional filters (collection_id, product_type, vendor, etc.)
            page: Page number
            limit: Results per page
            include_count: Whether to include total count
        """
        filters = filters or {}

        return await self.get_products(
            page=page,
            limit=limit,
            collection_id=filters.get("collection_id"),
            product_type=filters.get("product_type"),
            vendor=filters.get("vendor"),
            status=filters.get("status", "ACTIVE"),
            search=query,
            include_count=include_count,
        )

    async def invalidate_cache(self, product_id: str = None) -> bool:
        """
        Invalidate cache for this tenant
        
        Args:
            product_id: Optional specific product ID to invalidate
        """
        try:
            if product_id:
                # Invalidate specific product
                await self.cache.invalidate_product(
                    tenant_id=str(self.tenant.id),
                    product_id=product_id
                )
                print(f"Invalidated cache for product {product_id}")
            else:
                # Invalidate all product-related cache
                await self.cache.invalidate_products_cache(
                    tenant_id=str(self.tenant.id)
                )
                print(f"Invalidated all product cache for tenant {self.tenant.id}")
            
            return True
        except Exception as e:
            print(f"Error invalidating cache: {e}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for this tenant"""
        try:
            return await self.cache.get_cache_stats(
                tenant_id=str(self.tenant.id)
            )
        except Exception as e:
            print(f"Error getting cache stats: {e}")
            return {
                "error": str(e),
                "tenant_id": str(self.tenant.id)
            }

    async def clear_cache(self) -> bool:
        """Clear all cache for this tenant"""
        try:
            await self.cache.invalidate_products_cache(
                tenant_id=str(self.tenant.id)
            )
            # Also clear filters cache
            await self.cache.backend.clear(f"shopify:filters:{self.tenant.id}")
            print(f"Cleared all cache for tenant {self.tenant.id}")
            return True
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return False
