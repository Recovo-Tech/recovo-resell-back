# app/services/shopify_collection_service.py

from typing import Any, Dict, List, Optional

from app.models.tenant import Tenant
from app.services.shopify_service import ShopifyGraphQLClient


class ShopifyCollectionService:
    """Service for managing Shopify collections"""

    def __init__(self, tenant: Tenant):
        if not tenant.shopify_app_url or not tenant.shopify_access_token:
            raise ValueError("Tenant must have Shopify credentials configured")

        self.client = ShopifyGraphQLClient(
            tenant.shopify_app_url, tenant.shopify_access_token
        )
        self.tenant = tenant

    async def get_collections(self) -> List[Dict[str, Any]]:
        """Get all collections from the tenant's Shopify store"""
        try:
            collections = await self.client.get_all_collections()

            # Transform the data to a more frontend-friendly format
            transformed_collections = []
            for collection in collections:
                transformed_collection = {
                    "id": collection["id"].replace("gid://shopify/Collection/", ""),
                    "shopify_id": collection["id"],
                    "name": collection["title"],
                    "slug": collection["handle"],
                    "description": collection["description"],
                    "description_html": collection["description_html"],
                    "products_count": collection["products_count"],
                    "image_url": (
                        collection["image"]["url"] if collection["image"] else None
                    ),
                    "image_alt": (
                        collection["image"]["altText"] if collection["image"] else None
                    ),
                    "updated_at": collection["updated_at"],
                    "tenant_id": str(self.tenant.id),
                }
                transformed_collections.append(transformed_collection)

            return transformed_collections

        except Exception as e:
            print(f"Error fetching collections for tenant {self.tenant.name}: {e}")
            raise

    async def get_collection_by_id(
        self, collection_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific collection by its Shopify ID"""
        try:
            # Add the Shopify GID prefix if not present
            shopify_id = collection_id
            if not collection_id.startswith("gid://shopify/Collection/"):
                shopify_id = f"gid://shopify/Collection/{collection_id}"

            query = """
            query getCollection($id: ID!) {
                collection(id: $id) {
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
                    products(first: 10) {
                        edges {
                            node {
                                id
                                title
                                handle
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
                }
            }
            """

            response = await self.client.execute_query(query, {"id": shopify_id})

            if "errors" in response:
                print(f"GraphQL errors: {response['errors']}")
                return None

            collection = response.get("data", {}).get("collection")
            if not collection:
                return None

            # Transform to frontend-friendly format
            transformed_collection = {
                "id": collection["id"].replace("gid://shopify/Collection/", ""),
                "shopify_id": collection["id"],
                "name": collection["title"],
                "slug": collection["handle"],
                "description": collection["description"],
                "description_html": collection["descriptionHtml"],
                "products_count": collection.get("productsCount", {}).get("count", 0),
                "image_url": (
                    collection["image"]["url"] if collection["image"] else None
                ),
                "image_alt": (
                    collection["image"]["altText"] if collection["image"] else None
                ),
                "updated_at": collection["updatedAt"],
                "tenant_id": str(self.tenant.id),
                "sample_products": [],
            }

            # Add sample products
            products_edges = collection.get("products", {}).get("edges", [])
            for edge in products_edges:
                product = edge["node"]
                image_url = None
                if product.get("images", {}).get("edges"):
                    image_url = product["images"]["edges"][0]["node"]["url"]

                transformed_collection["sample_products"].append(
                    {
                        "id": product["id"].replace("gid://shopify/Product/", ""),
                        "title": product["title"],
                        "handle": product["handle"],
                        "image_url": image_url,
                    }
                )

            return transformed_collection

        except Exception as e:
            print(f"Error fetching collection {collection_id}: {e}")
            raise

    async def search_collections(self, query: str) -> List[Dict[str, Any]]:
        """Search collections by name or description"""
        try:
            all_collections = await self.get_collections()
            query_lower = query.lower()

            filtered_collections = []
            for collection in all_collections:
                if (
                    query_lower in collection["name"].lower()
                    or query_lower in collection["description"].lower()
                ):
                    filtered_collections.append(collection)

            return filtered_collections

        except Exception as e:
            print(f"Error searching collections: {e}")
            raise
