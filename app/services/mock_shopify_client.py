# app/services/mock_shopify_client.py
"""Mock Shopify client for testing purposes"""

import json
import random
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

from app.exceptions import (
    ShopifyAPIException,
    ShopifyConnectionException,
    ShopifyRateLimitException,
    ProductNotFoundException
)


class MockShopifyGraphQLClient:
    """Mock implementation of ShopifyGraphQLClient for testing"""
    
    def __init__(
        self, 
        shop_domain: str, 
        access_token: str,
        mock_data: Optional[Dict[str, Any]] = None,
        simulate_errors: bool = False,
        simulate_delays: bool = False
    ):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.mock_data = mock_data or self._generate_default_mock_data()
        self.simulate_errors = simulate_errors
        self.simulate_delays = simulate_delays
        
        # Error simulation settings
        self.error_rate = 0.1  # 10% error rate when enabled
        self.rate_limit_probability = 0.05  # 5% chance of rate limit
        self.connection_error_probability = 0.03  # 3% chance of connection error
        
        # Delay simulation settings
        self.min_delay = 0.1  # 100ms minimum
        self.max_delay = 2.0  # 2s maximum
        
        # Track API calls for testing
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []

    async def execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mock implementation of execute_query"""
        self.call_count += 1
        
        # Record the call
        call_record = {
            "timestamp": time.time(),
            "query": query[:100] + "..." if len(query) > 100 else query,
            "variables": variables,
            "call_number": self.call_count
        }
        self.call_history.append(call_record)
        
        # Simulate delays if enabled
        if self.simulate_delays:
            delay = random.uniform(self.min_delay, self.max_delay)
            await self._sleep(delay)
        
        # Simulate errors if enabled
        if self.simulate_errors:
            await self._maybe_simulate_error()
        
        # Parse query to determine response type
        if "products" in query and "edges" in query:
            return self._mock_products_response(query, variables)
        elif "product(" in query:
            return self._mock_single_product_response(query, variables)
        elif "collections" in query and "edges" in query:
            return self._mock_collections_response(query, variables)
        elif "collection(" in query:
            return self._mock_single_collection_response(query, variables)
        else:
            # Generic response
            return {"data": {}}

    async def _sleep(self, duration: float):
        """Mock async sleep"""
        import asyncio
        await asyncio.sleep(duration)

    async def _maybe_simulate_error(self):
        """Simulate various types of errors"""
        if random.random() > self.error_rate:
            return  # No error
        
        error_type = random.random()
        
        if error_type < self.rate_limit_probability:
            raise ShopifyRateLimitException(
                "Simulated rate limit error",
                retry_after=random.randint(1, 5)
            )
        elif error_type < self.rate_limit_probability + self.connection_error_probability:
            raise ShopifyConnectionException("Simulated connection error")
        else:
            raise ShopifyAPIException(
                "Simulated API error",
                status_code=500,
                shopify_errors=[{"message": "Internal server error"}]
            )

    def _mock_products_response(self, query: str, variables: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate mock products response"""
        variables = variables or {}
        
        # Extract pagination parameters
        first = variables.get("first", 50)
        after = variables.get("after")
        query_string = variables.get("query", "")
        
        # Generate products based on query
        all_products = self.mock_data["products"]
        
        # Apply search filter
        if query_string and "status:" not in query_string and "sku:" not in query_string:
            search_term = query_string.lower()
            all_products = [
                p for p in all_products 
                if search_term in p["title"].lower() or search_term in p["description"].lower()
            ]
        
        # Apply status filter
        if "status:" in query_string:
            status = query_string.split("status:")[1].split()[0].upper()
            all_products = [p for p in all_products if p["status"] == status]
        
        # Apply SKU filter
        if "sku:" in query_string:
            sku = query_string.split("sku:")[1].split()[0]
            all_products = [
                p for p in all_products 
                if any(v["sku"] == sku for v in p.get("variants", {}).get("edges", []))
            ]
        
        # Implement cursor-based pagination
        start_index = 0
        if after:
            # Simple cursor implementation - base64 encode index
            try:
                import base64
                start_index = int(base64.b64decode(after).decode())
            except:
                start_index = 0
        
        # Get page of products
        products_page = all_products[start_index:start_index + first]
        
        # Generate cursors
        edges = []
        for i, product in enumerate(products_page):
            cursor = self._generate_cursor(start_index + i + 1)
            edges.append({
                "node": product,
                "cursor": cursor
            })
        
        # Page info
        has_next_page = (start_index + first) < len(all_products)
        has_previous_page = start_index > 0
        
        page_info = {
            "hasNextPage": has_next_page,
            "hasPreviousPage": has_previous_page,
            "startCursor": edges[0]["cursor"] if edges else None,
            "endCursor": edges[-1]["cursor"] if edges else None
        }
        
        return {
            "data": {
                "products": {
                    "edges": edges,
                    "pageInfo": page_info
                }
            }
        }

    def _mock_single_product_response(self, query: str, variables: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate mock single product response"""
        variables = variables or {}
        product_id = variables.get("id", "")
        
        # Find product by ID
        product = None
        for p in self.mock_data["products"]:
            if p["id"] == product_id:
                product = p
                break
        
        if not product:
            raise ProductNotFoundException(f"Product not found: {product_id}")
        
        return {
            "data": {
                "product": product
            }
        }

    def _mock_collections_response(self, query: str, variables: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate mock collections response"""
        collections = self.mock_data["collections"]
        
        edges = []
        for i, collection in enumerate(collections):
            cursor = self._generate_cursor(i + 1)
            edges.append({
                "node": collection,
                "cursor": cursor
            })
        
        return {
            "data": {
                "collections": {
                    "edges": edges,
                    "pageInfo": {
                        "hasNextPage": False,
                        "hasPreviousPage": False,
                        "startCursor": edges[0]["cursor"] if edges else None,
                        "endCursor": edges[-1]["cursor"] if edges else None
                    }
                }
            }
        }

    def _mock_single_collection_response(self, query: str, variables: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate mock single collection response"""
        variables = variables or {}
        collection_id = variables.get("id", "")
        
        # Find collection by ID
        collection = None
        for c in self.mock_data["collections"]:
            if c["id"] == collection_id:
                collection = c
                break
        
        if not collection:
            return {"data": {"collection": None}}
        
        return {
            "data": {
                "collection": collection
            }
        }

    def _generate_cursor(self, position: int) -> str:
        """Generate a cursor for pagination"""
        import base64
        return base64.b64encode(str(position).encode()).decode()

    def _generate_default_mock_data(self) -> Dict[str, Any]:
        """Generate default mock data"""
        
        # Generate mock products
        products = []
        for i in range(100):  # 100 mock products
            product_id = f"gid://shopify/Product/{1000 + i}"
            
            # Generate variants
            variant_edges = []
            for j in range(random.randint(1, 3)):  # 1-3 variants per product
                variant_id = f"gid://shopify/ProductVariant/{2000 + i * 10 + j}"
                variant = {
                    "id": variant_id,
                    "sku": f"SKU-{1000 + i}-{j}",
                    "barcode": f"BAR{1000 + i}{j:02d}",
                    "title": f"Variant {j + 1}",
                    "price": f"{random.randint(10, 200)}.{random.randint(0, 99):02d}",
                    "compareAtPrice": None,
                    "weight": random.randint(100, 2000),
                    "weightUnit": "GRAMS",
                    "inventoryQuantity": random.randint(0, 100),
                    "availableForSale": True,
                    "selectedOptions": [
                        {"name": "Color", "value": random.choice(["Red", "Blue", "Green"])},
                        {"name": "Size", "value": random.choice(["S", "M", "L", "XL"])}
                    ]
                }
                variant_edges.append({"node": variant})
            
            # Generate images
            image_edges = []
            for k in range(random.randint(1, 5)):  # 1-5 images per product
                image_id = f"gid://shopify/ProductImage/{3000 + i * 10 + k}"
                image = {
                    "id": image_id,
                    "url": f"https://cdn.shopify.com/mock/image-{i}-{k}.jpg",
                    "altText": f"Product {i} Image {k + 1}",
                    "width": 800,
                    "height": 600
                }
                image_edges.append({"node": image})
            
            product = {
                "id": product_id,
                "title": f"Mock Product {i + 1}",
                "handle": f"mock-product-{i + 1}",
                "description": f"This is a mock product description for product {i + 1}",
                "descriptionHtml": f"<p>This is a <strong>mock product</strong> description for product {i + 1}</p>",
                "status": random.choice(["ACTIVE", "ACTIVE", "ACTIVE", "DRAFT"]),  # Mostly active
                "productType": random.choice(["Electronics", "Clothing", "Books", "Home", "Sports"]),
                "vendor": random.choice(["MockVendor A", "MockVendor B", "MockVendor C"]),
                "tags": ", ".join(random.sample(["tag1", "tag2", "tag3", "featured", "sale"], k=random.randint(1, 3))),
                "createdAt": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
                "updatedAt": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                "publishedAt": (datetime.now() - timedelta(days=random.randint(1, 300))).isoformat(),
                "options": [
                    {
                        "id": f"gid://shopify/ProductOption/{4000 + i * 2}",
                        "name": "Color",
                        "values": ["Red", "Blue", "Green"]
                    },
                    {
                        "id": f"gid://shopify/ProductOption/{4000 + i * 2 + 1}",
                        "name": "Size",
                        "values": ["S", "M", "L", "XL"]
                    }
                ],
                "variants": {"edges": variant_edges},
                "images": {"edges": image_edges},
                "collections": {
                    "edges": [
                        {
                            "node": {
                                "id": f"gid://shopify/Collection/{500 + (i % 5)}",
                                "title": f"Mock Collection {(i % 5) + 1}",
                                "handle": f"mock-collection-{(i % 5) + 1}"
                            }
                        }
                    ]
                }
            }
            products.append(product)
        
        # Generate mock collections
        collections = []
        for i in range(10):  # 10 mock collections
            collection_id = f"gid://shopify/Collection/{500 + i}"
            collection = {
                "id": collection_id,
                "title": f"Mock Collection {i + 1}",
                "handle": f"mock-collection-{i + 1}",
                "description": f"This is mock collection {i + 1}",
                "descriptionHtml": f"<p>This is <strong>mock collection {i + 1}</strong></p>",
                "sortOrder": "BEST_SELLING",
                "updatedAt": (datetime.now() - timedelta(days=random.randint(1, 60))).isoformat(),
                "image": {
                    "id": f"gid://shopify/CollectionImage/{6000 + i}",
                    "url": f"https://cdn.shopify.com/mock/collection-{i}.jpg",
                    "altText": f"Mock Collection {i + 1}"
                }
            }
            collections.append(collection)
        
        return {
            "products": products,
            "collections": collections
        }

    # Context manager support for cleanup
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Mock cleanup method"""
        pass

    # Test utilities
    def reset_call_history(self):
        """Reset call tracking for tests"""
        self.call_count = 0
        self.call_history.clear()

    def get_call_statistics(self) -> Dict[str, Any]:
        """Get statistics about mock API calls"""
        return {
            "total_calls": self.call_count,
            "call_history": self.call_history,
            "error_simulation_enabled": self.simulate_errors,
            "delay_simulation_enabled": self.simulate_delays,
            "mock_data_size": {
                "products": len(self.mock_data["products"]),
                "collections": len(self.mock_data["collections"])
            }
        }

    def set_error_simulation(self, enabled: bool, error_rate: float = 0.1):
        """Configure error simulation"""
        self.simulate_errors = enabled
        self.error_rate = error_rate

    def set_delay_simulation(self, enabled: bool, min_delay: float = 0.1, max_delay: float = 2.0):
        """Configure delay simulation"""
        self.simulate_delays = enabled
        self.min_delay = min_delay
        self.max_delay = max_delay

    def add_mock_product(self, product_data: Dict[str, Any]):
        """Add a custom mock product"""
        self.mock_data["products"].append(product_data)

    def add_mock_collection(self, collection_data: Dict[str, Any]):
        """Add a custom mock collection"""
        self.mock_data["collections"].append(collection_data)


class MockShopifyServiceFactory:
    """Factory for creating mock Shopify services"""
    
    @staticmethod
    def create_product_service(
        tenant_mock_data: Optional[Dict[str, Any]] = None,
        simulate_errors: bool = False,
        simulate_delays: bool = False
    ):
        """Create a mock product service"""
        from app.services.shopify_product_service import ShopifyProductService
        from app.models.tenant import Tenant
        
        # Create mock tenant
        mock_tenant = type('MockTenant', (), {
            'id': 'mock-tenant-123',
            'shopify_app_url': 'https://mock-store.myshopify.com',
            'shopify_access_token': 'mock-token-123'
        })()
        
        # Create service with mock client
        service = ShopifyProductService(mock_tenant)
        service.client = MockShopifyGraphQLClient(
            mock_tenant.shopify_app_url,
            mock_tenant.shopify_access_token,
            tenant_mock_data,
            simulate_errors,
            simulate_delays
        )
        
        return service
    
    @staticmethod
    def create_mock_product_data(count: int = 10) -> List[Dict[str, Any]]:
        """Create custom mock product data"""
        mock_client = MockShopifyGraphQLClient("test", "test")
        return mock_client.mock_data["products"][:count]
