# app/services/shopify_service.py
from typing import Any, Dict, List, Optional

import httpx

from app.config.shopify_config import shopify_settings


class ShopifyGraphQLClient:
    """Shopify GraphQL API client for product verification and management"""

    def __init__(self, shop_domain: str, access_token: Optional[str] = None):
        # Clean the domain by removing any existing protocol
        clean_domain = shop_domain.replace("https://", "").replace("http://", "")

        self.shop_domain = clean_domain  # Store clean domain
        self.access_token = access_token or shopify_settings.shopify_access_token
        self.api_version = shopify_settings.shopify_api_version

        self.base_url = (
            f"https://{clean_domain}/admin/api/{self.api_version}/graphql.json"
        )

    async def execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute GraphQL query against Shopify API"""
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url, headers=headers, json=payload, timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def verify_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """Verify if a product exists in Shopify by SKU"""
        query = """
        query getProductBySku($query: String!) {
            products(first: 1, query: $query) {
                edges {
                    node {
                        id
                        title
                        handle
                        description
                        descriptionHtml
                        status
                        productType
                        vendor
                        options {
                            id
                            name
                            values
                            }
                        images(first: 1) {
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
                                    sku
                                    barcode
                                    title
                                    price
                                    weight
                                    weightUnit
                                    selectedOptions {
                                        name
                                        value
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        variables = {"query": f"sku:{sku}"}
        result = await self.execute_query(query, variables)

        products = result.get("data", {}).get("products", {}).get("edges", [])
        if products:
            return products[0]["node"]
        return None

    async def verify_product_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Verify if a product exists in Shopify by barcode"""
        query = """
        query getProductByBarcode($query: String!) {
            products(first: 1, query: $query) {
                edges {
                    node {
                        id
                        title
                        handle
                        description
                        descriptionHtml
                        status
                        productType
                        vendor
                        options {
                            id
                            name
                            values
                        }
                        images(first: 1) {
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
                                    sku
                                    barcode
                                    title
                                    price
                                    weight
                                    weightUnit
                                    selectedOptions {
                                        name
                                        value
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        variables = {"query": f"barcode:{barcode}"}
        result = await self.execute_query(query, variables)

        products = result.get("data", {}).get("products", {}).get("edges", [])
        if products:
            return products[0]["node"]
        return None

    async def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product details by Shopify product ID"""
        query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                handle
                description
                status
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
                            sku
                            barcode
                            title
                            price
                            inventoryQuantity
                        }
                    }
                }
            }
        }
        """

        variables = {"id": product_id}
        result = await self.execute_query(query, variables)

        return result.get("data", {}).get("product")

    async def get_products_paginated(
        self,
        first: int = 50,
        after: str = None,
        collection_id: str = None,
        product_type: str = None,
        vendor: str = None,
        status: str = "ACTIVE",
        query: str = None,
    ) -> Dict[str, Any]:
        """
        Fetch products from Shopify with pagination and filtering

        Args:
            first: Number of products to fetch (max 250)
            after: Cursor for pagination
            collection_id: Filter by collection/category ID
            product_type: Filter by product type
            vendor: Filter by vendor
            status: Filter by product status (ACTIVE, ARCHIVED, DRAFT)
            query: Search query string
        """
        # Build the GraphQL query
        graphql_query = """
        query getProducts($first: Int!, $after: String, $query: String) {
            products(first: $first, after: $after, query: $query) {
                edges {
                    node {
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
                        images(first: 5) {
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
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """

        # Build query string for filtering
        query_parts = []

        if status:
            query_parts.append(f"status:{status}")

        if collection_id:
            # Clean collection ID if it has the GID prefix
            clean_collection_id = collection_id.replace("gid://shopify/Collection/", "")
            query_parts.append(f"collection_id:{clean_collection_id}")

        if product_type:
            query_parts.append(f"product_type:{product_type}")

        if vendor:
            query_parts.append(f"vendor:{vendor}")

        if query:
            query_parts.append(query)

        query_string = " AND ".join(query_parts) if query_parts else None

        variables = {"first": min(first, 250)}  # Shopify limits to 250
        if after:
            variables["after"] = after
        if query_string:
            variables["query"] = query_string

        try:
            response = await self.execute_query(graphql_query, variables)

            if "errors" in response:
                print(f"GraphQL errors: {response['errors']}")
                return {"products": [], "page_info": {}, "errors": response["errors"]}

            products_data = response.get("data", {}).get("products", {})
            edges = products_data.get("edges", [])
            page_info = products_data.get("pageInfo", {})

            # Transform products to a more friendly format
            products = []
            for edge in edges:
                product = edge["node"]

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

                # Extract variants
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
                            "price": (
                                float(variant["price"]) if variant["price"] else 0.0
                            ),
                            "compare_at_price": (
                                float(variant["compareAtPrice"])
                                if variant.get("compareAtPrice")
                                else None
                            ),
                            "weight": variant.get("weight"),
                            "weight_unit": variant.get("weightUnit"),
                            "inventory_quantity": variant.get("inventoryQuantity", 0),
                            "available_for_sale": variant.get(
                                "availableForSale", False
                            ),
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

                products.append(
                    {
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
                        "created_at": product.get("createdAt"),
                        "updated_at": product.get("updatedAt"),
                        "images": images,
                        "variants": variants,
                        "collections": collections,
                        "options": product_options,
                    }
                )

            return {
                "products": products,
                "page_info": {
                    "has_next_page": page_info.get("hasNextPage", False),
                    "has_previous_page": page_info.get("hasPreviousPage", False),
                    "start_cursor": page_info.get("startCursor"),
                    "end_cursor": page_info.get("endCursor"),
                },
                "total_count": len(products),
            }

        except Exception as e:
            print(f"Error fetching products: {e}")
            raise

    async def get_product_filters(self) -> Dict[str, List[str]]:
        """Get available filter options from the store by sampling products"""
        # First, get a sample of products to extract unique values
        query = """
        query getProductsForFilters($first: Int!) {
            products(first: $first) {
                edges {
                    node {
                        productType
                        vendor
                        tags
                    }
                }
            }
        }
        """

        try:
            # Get a larger sample to ensure we get comprehensive filter options
            response = await self.execute_query(query, {"first": 250})

            if "errors" in response:
                print(f"GraphQL errors: {response['errors']}")
                return {}

            products_data = (
                response.get("data", {}).get("products", {}).get("edges", [])
            )

            # Extract unique values
            product_types = set()
            vendors = set()
            tags = set()

            for edge in products_data:
                product = edge["node"]

                # Add product type
                if product.get("productType"):
                    product_types.add(product["productType"])

                # Add vendor
                if product.get("vendor"):
                    vendors.add(product["vendor"])

                # Add tags
                for tag in product.get("tags", []):
                    if tag:
                        tags.add(tag)

            return {
                "product_types": sorted(list(product_types)),
                "vendors": sorted(list(vendors)),
                "tags": sorted(list(tags)),
            }

        except Exception as e:
            print(f"Error fetching product filters: {e}")
            return {}

    async def get_all_collections(self) -> List[Dict[str, Any]]:
        """Get all collections from Shopify"""
        query = """
        query getCollections($first: Int!, $after: String) {
            collections(first: $first, after: $after) {
                edges {
                    node {
                        id
                        title
                        handle
                        description
                        descriptionHtml
                        image {
                            url
                            altText
                        }
                        productsCount {
                            count
                        }
                        updatedAt
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        all_collections = []
        has_next_page = True
        after_cursor = None

        while has_next_page:
            variables = {"first": 50, "after": after_cursor}

            result = await self.execute_query(query, variables)

            if result.get("data", {}).get("collections"):
                collections_data = result["data"]["collections"]
                edges = collections_data.get("edges", [])

                for edge in edges:
                    collection = edge["node"]
                    all_collections.append(
                        {
                            "id": collection["id"],
                            "title": collection["title"],
                            "handle": collection["handle"],
                            "description": collection.get("description", ""),
                            "description_html": collection.get("descriptionHtml", ""),
                            "image": collection.get("image"),
                            "products_count": collection.get("productsCount", {}).get(
                                "count", 0
                            ),
                            "updated_at": collection.get("updatedAt"),
                        }
                    )

                page_info = collections_data.get("pageInfo", {})
                has_next_page = page_info.get("hasNextPage", False)
                after_cursor = page_info.get("endCursor")
            else:
                break

        return all_collections

    async def get_collection_by_id(
        self, collection_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific collection by ID with sample products"""
        query = """
        query getCollection($id: ID!) {
            collection(id: $id) {
                id
                title
                handle
                description
                descriptionHtml
                image {
                    url
                    altText
                }
                productsCount {
                    count
                }
                products(first: 10) {
                    edges {
                        node {
                            id
                            title
                            handle
                            priceRange {
                                minVariantPrice {
                                    amount
                                    currencyCode
                                }
                            }
                            images(first: 1) {
                                edges {
                                    node {
                                        url
                                        altText
                                    }
                                }
                            }
                        }
                    }
                }
                updatedAt
            }
        }
        """

        variables = {"id": collection_id}
        result = await self.execute_query(query, variables)

        if result.get("data", {}).get("collection"):
            collection = result["data"]["collection"]

            # Process products
            products = []
            for edge in collection.get("products", {}).get("edges", []):
                product = edge["node"]
                product_data = {
                    "id": product["id"],
                    "title": product["title"],
                    "handle": product["handle"],
                    "price": None,
                    "currency": None,
                    "image": None,
                }

                # Get price
                if product.get("priceRange", {}).get("minVariantPrice"):
                    price_data = product["priceRange"]["minVariantPrice"]
                    product_data["price"] = float(price_data.get("amount", 0))
                    product_data["currency"] = price_data.get("currencyCode", "USD")

                # Get first image
                if product.get("images", {}).get("edges"):
                    first_image = product["images"]["edges"][0]["node"]
                    product_data["image"] = {
                        "url": first_image.get("url"),
                        "alt_text": first_image.get("altText"),
                    }

                products.append(product_data)

            return {
                "id": collection["id"],
                "title": collection["title"],
                "handle": collection["handle"],
                "description": collection.get("description", ""),
                "description_html": collection.get("descriptionHtml", ""),
                "image": collection.get("image"),
                "products_count": collection.get("productsCount", {}).get("count", 0),
                "products": products,
                "updated_at": collection.get("updatedAt"),
            }

        return None

    async def get_taxonomy(self) -> Dict[str, Any]:
        """Get Shopify's official product taxonomy/categories"""
        query = """
                    query GetAllCategories {
            taxonomy {
                categories(first: 250) {
                nodes {
                    id
                    name
                }
                }
            }
            }
        """

        try:
            response = await self.execute_query(query, {"first": 250})

            if "errors" in response:
                print(f"GraphQL errors: {response['errors']}")
                # Fallback to product sampling if taxonomy is not available
                return await self.get_product_filters()

            taxonomy_data = response.get("data", {}).get("taxonomy", {})
            categories_connection = taxonomy_data.get("categories", {})
            categories_edges = categories_connection.get("edges", [])

            # Process taxonomy categories
            categories = []
            for edge in categories_edges:
                category = edge["node"]

                categories.append(
                    {
                        "id": category.get("id"),
                        "name": category.get("name"),
                        "full_name": category.get("fullName"),
                        "parent_id": category.get("parentId"),
                        "level": category.get("level"),
                        "is_leaf": category.get("isLeaf"),
                        "is_root": category.get("isRoot"),
                        "children_ids": category.get("childrenIds", []),
                        "attributes": [],  # Remove attributes to avoid union type issues
                    }
                )

            return {"categories": categories, "total": len(categories)}

        except Exception as e:
            print(f"Error fetching taxonomy: {e}")
            # Fallback to product sampling
            print("Falling back to product sampling for categories...")
            return await self.get_product_filters()


class ShopifyProductVerificationService:
    """Service for verifying products against Shopify store inventory"""

    def __init__(self, shop_domain: str, access_token: str):
        self.client = ShopifyGraphQLClient(shop_domain, access_token)

    async def verify_product_eligibility(
        self, sku: str = None, barcode: str = None
    ) -> Dict[str, Any]:
        """
        Verify if a product with given SKU or barcode is eligible for second-hand sale

        Returns:
            Dict with verification status, product info, and any errors
        """
        if not sku and not barcode:
            return {
                "is_verified": False,
                "error": "Either SKU or barcode must be provided",
            }

        try:
            product = None
            verification_method = None

            # Try to verify by SKU first
            if sku:
                product = await self.client.verify_product_by_sku(sku)
                verification_method = "sku"

            # If no product found by SKU, try barcode
            if not product and barcode:
                product = await self.client.verify_product_by_barcode(barcode)
                verification_method = "barcode"

            if not product:
                return {
                    "is_verified": False,
                    "error": "Product not found in store inventory",
                }

            # Check if product is active
            if product.get("status") != "ACTIVE":
                return {
                    "is_verified": False,
                    "error": "Product is not active in the store",
                }

            # Extract color information from options and variants
            colors = []
            color_options = []

            # Get color options from product options
            product_options = product.get("options", [])
            for option in product_options:
                option_name = option.get("name", "").lower()
                if "color" in option_name or "colour" in option_name:
                    color_options.extend(option.get("values", []))

            # Get colors from variant selectedOptions
            variants = product.get("variants", {}).get("edges", [])
            for variant in variants:
                selected_options = variant.get("node", {}).get("selectedOptions", [])
                for selected_option in selected_options:
                    option_name = selected_option.get("name", "").lower()
                    if "color" in option_name or "colour" in option_name:
                        color_value = selected_option.get("value", "")
                        if color_value and color_value not in colors:
                            colors.append(color_value)

            # Combine and deduplicate colors
            all_colors = list(set(colors + color_options))

            return {
                "is_verified": True,
                "product_info": {
                    "shopify_id": product["id"],
                    "title": product["title"],
                    "handle": product["handle"],
                    "description": product.get("description", ""),
                    "descriptionHtml": product.get("descriptionHtml", ""),
                    "productType": product.get("productType", ""),
                    "vendor": product.get("vendor", ""),
                    "colors": all_colors,  # Add colors array
                    "available_colors": color_options,  # All possible colors for this product
                    "first_image": (
                        product.get("images", {})
                        .get("edges", [{}])[0]
                        .get("node", {})
                        .get("url")
                        if product.get("images", {}).get("edges")
                        else None
                    ),
                    "weight": (
                        product.get("variants", {})
                        .get("edges", [{}])[0]
                        .get("node", {})
                        .get("weight")
                        if product.get("variants", {}).get("edges")
                        else None
                    ),
                    "weightUnit": (
                        product.get("variants", {})
                        .get("edges", [{}])[0]
                        .get("node", {})
                        .get("weightUnit")
                        if product.get("variants", {}).get("edges")
                        else None
                    ),
                    "variants": [
                        {
                            "id": variant["node"]["id"],
                            "sku": variant["node"]["sku"],
                            "barcode": variant["node"]["barcode"],
                            "title": variant["node"]["title"],
                            "price": variant["node"]["price"],
                            "weight": variant["node"].get("weight"),
                            "weightUnit": variant["node"].get("weightUnit"),
                            "selectedOptions": variant["node"].get(
                                "selectedOptions", []
                            ),
                        }
                        for variant in product.get("variants", {}).get("edges", [])
                    ],
                },
                "verification_method": verification_method,
            }

        except Exception as e:
            return {"is_verified": False, "error": f"Verification failed: {str(e)}"}
