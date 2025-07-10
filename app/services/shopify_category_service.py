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
            print("Fetching categories from Shopify...")
            # Try to get official Shopify taxonomy first
            taxonomy_data = await self.client.get_taxonomy()
            print(f"Taxonomy data received: {taxonomy_data}")

            # If we got official taxonomy categories
            if "categories" in taxonomy_data:
                print(f"Found {len(taxonomy_data['categories'])} taxonomy categories")
                categories = []
                for category in taxonomy_data["categories"]:
                    category_data = {
                        "id": category["id"],
                        "name": category["name"],
                        "full_name": category["full_name"],
                        "type": "taxonomy_category",
                        "tenant_id": str(self.tenant.id),
                    }
                    categories.append(category_data)
                    print(f"Added taxonomy category: {category_data}")
                return categories

            print("No taxonomy categories found, falling back to product filters...")
            # Fallback to product filters if taxonomy is not available
            filters = await self.client.get_product_filters()
            print(f"Product filters: {filters}")
            categories = []

            # Add product types as categories
            for product_type in filters.get("product_types", []):
                if product_type and product_type.strip():
                    category_data = {
                        "id": f"product_type_{product_type.lower().replace(' ', '_')}",
                        "name": product_type,
                        "type": "product_type",
                        "slug": product_type.lower().replace(" ", "-"),
                        "tenant_id": str(self.tenant.id),
                    }
                    categories.append(category_data)
                    print(f"Added product type category: {category_data}")

            # Add vendors as categories
            for vendor in filters.get("vendors", []):
                if vendor and vendor.strip():
                    category_data = {
                        "id": f"vendor_{vendor.lower().replace(' ', '_')}",
                        "name": vendor,
                        "type": "vendor",
                        "slug": vendor.lower().replace(" ", "-"),
                        "tenant_id": str(self.tenant.id),
                    }
                    categories.append(category_data)
                    print(f"Added vendor category: {category_data}")

            print(f"Returning {len(categories)} categories total")
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

    async def get_subcategories(self, parent_category_id: str) -> List[Dict[str, Any]]:
        """Get subcategories for a specific parent category"""
        try:
            print(f"Getting subcategories for parent: {parent_category_id}")
            
            # First try to get from taxonomy if the parent is a taxonomy category
            if parent_category_id.startswith("gid://shopify/TaxonomyCategory/"):
                print(f"Querying Shopify for subcategories of taxonomy category: {parent_category_id}")
                result = await self.client.get_subcategories(parent_category_id)
                print(f"Shopify subcategories result: {result}")
                
                subcategories = []
                for subcategory in result.get("subcategories", []):
                    subcategory_data = {
                        "id": subcategory["id"],
                        "name": subcategory["name"],
                        "full_name": subcategory["full_name"],
                        "type": "taxonomy_category",
                        "parent_id": subcategory["parent_id"],
                        "level": subcategory["level"],
                        "is_leaf": subcategory["is_leaf"],
                        "children_ids": subcategory.get("children_ids", []),
                        "tenant_id": str(self.tenant.id),
                    }
                    subcategories.append(subcategory_data)

                print(f"Processed {len(subcategories)} subcategories")
                return subcategories
            else:
                print(f"Non-taxonomy category ID: {parent_category_id}, returning empty subcategories")
                # For non-taxonomy categories (product types, vendors, tags), return empty
                # as they typically don't have hierarchical subcategories
                return []

        except Exception as e:
            print(f"Error fetching subcategories for {parent_category_id}: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")
            raise

    async def get_category_tree(self, category_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """Get full category tree starting from a specific category"""
        try:
            if category_id.startswith("gid://shopify/TaxonomyCategory/"):
                result = await self.client.get_category_tree(category_id, max_depth)

                if not result.get("category"):
                    return {"category": None, "children": []}

                # Add tenant_id to the category and all children recursively
                def add_tenant_id(category_tree):
                    if category_tree.get("category"):
                        category_tree["category"]["tenant_id"] = str(self.tenant.id)

                    for child in category_tree.get("children", []):
                        add_tenant_id(child)

                    return category_tree

                return add_tenant_id(result)
            else:
                # For non-taxonomy categories, just return the category without children
                all_categories = await self.get_categories()
                category = next((cat for cat in all_categories if cat["id"] == category_id), None)

                if category:
                    return {"category": category, "children": []}
                else:
                    return {"category": None, "children": []}

        except Exception as e:
            print(f"Error fetching category tree for {category_id}: {e}")
            raise

    async def get_top_level_categories(self) -> List[Dict[str, Any]]:
        """Get only top-level categories (categories with no parent)"""
        try:
            all_categories = await self.get_categories()

            # Filter for top-level categories
            top_level = []
            for category in all_categories:
                # Taxonomy categories with no parent_id or level 0 are top-level
                if category.get("type") == "taxonomy_category":
                    if not category.get("parent_id") or category.get("level", 0) == 0:
                        top_level.append(category)
                else:
                    # For non-taxonomy categories (product types, vendors, tags), they're all top-level
                    top_level.append(category)

            return top_level

        except Exception as e:
            print(f"Error fetching top-level categories: {e}")
            raise
