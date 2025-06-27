# app/services/shopify_service.py
import httpx
import json
from typing import Optional, Dict, Any, List
from app.config.shopify_config import shopify_settings


class ShopifyGraphQLClient:
    """Shopify GraphQL API client for product verification and management"""

    def __init__(self, shop_domain: str, access_token: Optional[str] = None):
        self.shop_domain = shop_domain
        self.access_token = access_token or shopify_settings.shopify_access_token
        self.api_version = shopify_settings.shopify_api_version
        self.base_url = (
            f"https://{shop_domain}/admin/api/{self.api_version}/graphql.json"
        )

    async def execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute GraphQL query against Shopify API"""
        print(f"DEBUG: Attempting to connect to: {self.base_url}")
        print(f"DEBUG: Shop domain: {self.shop_domain}")
        print(f"DEBUG: Access token: {self.access_token[:10]}..." if self.access_token else "DEBUG: No access token")
        
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
                        status
                        variants(first: 10) {
                            edges {
                                node {
                                    id
                                    sku
                                    barcode
                                    title
                                    price
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
                        status
                        variants(first: 10) {
                            edges {
                                node {
                                    id
                                    sku
                                    barcode
                                    title
                                    price
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
            print(f"DEBUG: Client access_token: {self.client.access_token[:10] if self.client.access_token else 'None'}...")

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
                    "variants": [
                        {
                            "id": variant["node"]["id"],
                            "sku": variant["node"]["sku"],
                            "barcode": variant["node"]["barcode"],
                            "title": variant["node"]["title"],
                            "price": variant["node"]["price"],
                        }
                        for variant in product.get("variants", {}).get("edges", [])
                    ],
                },
                "verification_method": verification_method,
            }

        except Exception as e:
            return {"is_verified": False, "error": f"Verification failed: {str(e)}"}
