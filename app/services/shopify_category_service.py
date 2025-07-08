# app/services/shopify_category_service.py

from typing import Any, Dict, List, Optional

from app.models.tenant import Tenant
from app.services.shopify_service import ShopifyGraphQLClient


class ShopifyCategoryService:
    """Service for managing Shopify product categories/types"""

    def __init__(self, tenant: Tenant):
        if not tenant.shopify_app_url or not tenant.shopify_access_token:
            raise ValueError("Tenant must have Shopify credentials configured")

        self.client = ShopifyGraphQLClient(
            tenant.shopify_app_url, tenant.shopify_access_token
        )
        self.tenant = tenant

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all product categories from Shopify taxonomy"""
        try:
            # Try to get official Shopify taxonomy first
            taxonomy_data = await self.client.get_taxonomy()

            # If we got official taxonomy categories
            if "categories" in taxonomy_data:
                categories = []
                for category in taxonomy_data["categories"]:
                    categories.append(
                        {
                            "id": category["id"],
                            "name": category["name"],
                            "full_name": category["full_name"],
                            "type": "taxonomy_category",
                            "level": category["level"],
                            "is_leaf": category["is_leaf"],
                            "is_root": category["is_root"],
                            "parent_id": category["parent_id"],
                            "children_ids": category["children_ids"],
                            "attributes": category["attributes"],
                            "tenant_id": str(self.tenant.id),
                        }
                    )
                return categories

            # Fallback to product filters if taxonomy is not available
            filters = await self.client.get_product_filters()
            categories = []

            # Add product types as categories
            for product_type in filters.get("product_types", []):
                if product_type and product_type.strip():
                    categories.append(
                        {
                            "id": f"product_type_{product_type.lower().replace(' ', '_')}",
                            "name": product_type,
                            "type": "product_type",
                            "slug": product_type.lower().replace(" ", "-"),
                            "tenant_id": str(self.tenant.id),
                        }
                    )

            # Add vendors as categories
            for vendor in filters.get("vendors", []):
                if vendor and vendor.strip():
                    categories.append(
                        {
                            "id": f"vendor_{vendor.lower().replace(' ', '_')}",
                            "name": vendor,
                            "type": "vendor",
                            "slug": vendor.lower().replace(" ", "-"),
                            "tenant_id": str(self.tenant.id),
                        }
                    )

            return categories

        except Exception as e:
            print(f"Error fetching categories: {e}")
            return []

            # Add popular tags as categories
            for tag in filters.get("tags", [])[:20]:  # Limit to first 20 tags
                if tag and tag.strip():
                    categories.append(
                        {
                            "id": f"tag_{tag.lower().replace(' ', '_')}",
                            "name": tag,
                            "type": "tag",
                            "slug": tag.lower().replace(" ", "-"),
                            "tenant_id": str(self.tenant.id),
                        }
                    )

            return categories

        except Exception as e:
            print(f"Error fetching categories for tenant {self.tenant.name}: {e}")
            raise

    async def get_product_types(self) -> List[Dict[str, Any]]:
        """Get only product types from Shopify"""
        try:
            filters = await self.client.get_product_filters()

            product_types = []
            for product_type in filters.get("product_types", []):
                if product_type and product_type.strip():
                    product_types.append(
                        {
                            "id": f"product_type_{product_type.lower().replace(' ', '_')}",
                            "name": product_type,
                            "type": "product_type",
                            "slug": product_type.lower().replace(" ", "-"),
                            "tenant_id": str(self.tenant.id),
                        }
                    )

            return product_types

        except Exception as e:
            print(f"Error fetching product types for tenant {self.tenant.name}: {e}")
            raise

    async def get_vendors(self) -> List[Dict[str, Any]]:
        """Get only vendors from Shopify"""
        try:
            filters = await self.client.get_product_filters()

            vendors = []
            for vendor in filters.get("vendors", []):
                if vendor and vendor.strip():
                    vendors.append(
                        {
                            "id": f"vendor_{vendor.lower().replace(' ', '_')}",
                            "name": vendor,
                            "type": "vendor",
                            "slug": vendor.lower().replace(" ", "-"),
                            "tenant_id": str(self.tenant.id),
                        }
                    )

            return vendors

        except Exception as e:
            print(f"Error fetching vendors for tenant {self.tenant.name}: {e}")
            raise

    async def get_tags(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get product tags from Shopify"""
        try:
            filters = await self.client.get_product_filters()

            tags = []
            for tag in filters.get("tags", [])[:limit]:
                if tag and tag.strip():
                    tags.append(
                        {
                            "id": f"tag_{tag.lower().replace(' ', '_')}",
                            "name": tag,
                            "type": "tag",
                            "slug": tag.lower().replace(" ", "-"),
                            "tenant_id": str(self.tenant.id),
                        }
                    )

            return tags

        except Exception as e:
            print(f"Error fetching tags for tenant {self.tenant.name}: {e}")
            raise

    async def search_categories(self, query: str) -> List[Dict[str, Any]]:
        """Search categories by name"""
        try:
            all_categories = await self.get_categories()
            query_lower = query.lower()

            filtered_categories = []
            for category in all_categories:
                if query_lower in category["name"].lower():
                    filtered_categories.append(category)

            return filtered_categories

        except Exception as e:
            print(f"Error searching categories: {e}")
            raise
