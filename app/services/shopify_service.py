# app/services/shopify_service.py
import httpx
import json
from typing import Optional, Dict, Any, List
from app.config.shopify_config import shopify_settings


class ShopifyGraphQLClient:
    """Shopify GraphQL API client for product verification and management"""

    def __init__(self, shop_domain: str, access_token: Optional[str] = None):
        print(f"DEBUG: Raw shop_domain input = '{shop_domain}'")
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
        print(f"DEBUG: Attempting to connect to: {self.base_url}")
        print(f"DEBUG: Shop domain: {self.shop_domain}")
        print(
            f"DEBUG: Access token: {self.access_token[:10]}..."
            if self.access_token
            else "DEBUG: No access token"
        )

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

    async def get_all_collections(self) -> List[Dict[str, Any]]:
        """Fetch all collections/categories from Shopify"""
        query = """
        query getAllCollections($first: Int!) {
            collections(first: $first) {
                edges {
                    node {
                        id
                        title
                        handle
                        description
                        descriptionHtml
                        image {
                            id
                            url
                            altText
                        }
                        productsCount {
                            count
                        }
                        updatedAt
                    }
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
        cursor = None

        try:
            while has_next_page:
                variables = {"first": 50}  # Fetch 50 collections at a time
                if cursor:
                    variables["after"] = cursor
                    # Modify query for pagination
                    paginated_query = query.replace("($first: Int!)", "($first: Int!, $after: String!)")
                    paginated_query = paginated_query.replace("collections(first: $first)", "collections(first: $first, after: $after)")
                    query_to_use = paginated_query
                else:
                    query_to_use = query

                response = await self.execute_query(query_to_use, variables)

                if "errors" in response:
                    print(f"GraphQL errors: {response['errors']}")
                    break

                collections_data = response.get("data", {}).get("collections", {})
                edges = collections_data.get("edges", [])
                page_info = collections_data.get("pageInfo", {})

                # Extract collection data
                for edge in edges:
                    collection = edge["node"]
                    all_collections.append({
                        "id": collection["id"],
                        "title": collection["title"],
                        "handle": collection["handle"],
                        "description": collection.get("description", ""),
                        "description_html": collection.get("descriptionHtml", ""),
                        "image": collection.get("image"),
                        "products_count": collection.get("productsCount", {}).get("count", 0),
                        "updated_at": collection.get("updatedAt"),
                    })

                has_next_page = page_info.get("hasNextPage", False)
                cursor = page_info.get("endCursor")

        except Exception as e:
            print(f"Error fetching collections: {e}")
            raise

        return all_collections


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

            print(f"DEBUG: Starting verification with SKU: {sku}, Barcode: {barcode}")
            print(f"DEBUG: Client shop_domain: {self.client.shop_domain}")
            print(
                f"DEBUG: Client access_token: {self.client.access_token[:10] if self.client.access_token else 'None'}..."
            )

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
                        }
                        for variant in product.get("variants", {}).get("edges", [])
                    ],
                },
                "verification_method": verification_method,
            }

        except Exception as e:
            return {"is_verified": False, "error": f"Verification failed: {str(e)}"}
