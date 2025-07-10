# app/services/shopify_data_transformer.py
"""Centralized data transformation utilities for Shopify API responses"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import re


class ShopifyDataTransformer:
    """Centralized transformer for Shopify API data structures"""

    @staticmethod
    def clean_shopify_id(shopify_id: str) -> str:
        """Extract numeric ID from Shopify GID"""
        if not shopify_id:
            return ""
        
        # Remove gid://shopify/{ResourceType}/ prefix
        if shopify_id.startswith("gid://shopify/"):
            return shopify_id.split("/")[-1]
        return shopify_id

    @staticmethod
    def format_shopify_gid(resource_type: str, resource_id: str) -> str:
        """Format numeric ID as Shopify GID"""
        if not resource_id:
            return ""
        
        # If already a GID, return as-is
        if resource_id.startswith("gid://shopify/"):
            return resource_id
        
        return f"gid://shopify/{resource_type}/{resource_id}"

    @staticmethod
    def transform_money(amount: Union[str, float, None]) -> Optional[float]:
        """Transform Shopify money field to float"""
        if amount is None:
            return None
        
        if isinstance(amount, str):
            try:
                return float(amount)
            except (ValueError, TypeError):
                return None
        
        return float(amount)

    @staticmethod
    def transform_datetime(datetime_str: Optional[str]) -> Optional[str]:
        """Transform Shopify datetime to standardized format"""
        if not datetime_str:
            return None
        
        try:
            # Parse ISO format datetime and return in standard format
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return dt.isoformat()
        except (ValueError, TypeError):
            return datetime_str

    @staticmethod
    def transform_tags(tags_string: Optional[str]) -> List[str]:
        """Transform Shopify tags string to list"""
        if not tags_string:
            return []
        
        # Split by comma and clean up
        tags = [tag.strip() for tag in tags_string.split(",") if tag.strip()]
        return tags

    @staticmethod
    def transform_variant(variant_node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Shopify variant node to standardized format"""
        if not variant_node:
            return {}

        transformed = {
            "id": ShopifyDataTransformer.clean_shopify_id(variant_node.get("id", "")),
            "shopify_id": variant_node.get("id", ""),
            "sku": variant_node.get("sku", ""),
            "barcode": variant_node.get("barcode", ""),
            "title": variant_node.get("title", ""),
            "price": ShopifyDataTransformer.transform_money(variant_node.get("price")),
            "compare_at_price": ShopifyDataTransformer.transform_money(
                variant_node.get("compareAtPrice")
            ),
            "weight": variant_node.get("weight"),
            "weight_unit": variant_node.get("weightUnit", "kg"),
            "inventory_quantity": variant_node.get("inventoryQuantity", 0),
            "available_for_sale": variant_node.get("availableForSale", False),
            "selected_options": []
        }

        # Transform selected options
        selected_options = variant_node.get("selectedOptions", [])
        if selected_options:
            transformed["selected_options"] = [
                {
                    "name": option.get("name", ""),
                    "value": option.get("value", "")
                }
                for option in selected_options
            ]

        # Add inventory tracking
        if "inventoryItem" in variant_node:
            inventory_item = variant_node["inventoryItem"]
            transformed.update({
                "inventory_item_id": ShopifyDataTransformer.clean_shopify_id(
                    inventory_item.get("id", "")
                ),
                "tracked": inventory_item.get("tracked", False),
                "inventory_policy": inventory_item.get("inventoryPolicy", "deny")
            })

        return transformed

    @staticmethod
    def transform_image(image_node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Shopify image node to standardized format"""
        if not image_node:
            return {}

        return {
            "id": ShopifyDataTransformer.clean_shopify_id(image_node.get("id", "")),
            "shopify_id": image_node.get("id", ""),
            "url": image_node.get("url", ""),
            "alt_text": image_node.get("altText", ""),
            "width": image_node.get("width"),
            "height": image_node.get("height")
        }

    @staticmethod
    def transform_option(option_node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Shopify option node to standardized format"""
        if not option_node:
            return {}

        return {
            "id": ShopifyDataTransformer.clean_shopify_id(option_node.get("id", "")),
            "shopify_id": option_node.get("id", ""),
            "name": option_node.get("name", ""),
            "values": option_node.get("values", [])
        }

    @staticmethod
    def transform_collection_reference(collection_node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Shopify collection reference to standardized format"""
        if not collection_node:
            return {}

        return {
            "id": ShopifyDataTransformer.clean_shopify_id(collection_node.get("id", "")),
            "shopify_id": collection_node.get("id", ""),
            "title": collection_node.get("title", ""),
            "handle": collection_node.get("handle", "")
        }

    @staticmethod
    def transform_product(product_node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Shopify product node to standardized format"""
        if not product_node:
            return {}

        # Basic product fields
        transformed = {
            "id": ShopifyDataTransformer.clean_shopify_id(product_node.get("id", "")),
            "shopify_id": product_node.get("id", ""),
            "title": product_node.get("title", ""),
            "handle": product_node.get("handle", ""),
            "description": product_node.get("description", ""),
            "description_html": product_node.get("descriptionHtml", ""),
            "status": product_node.get("status", "").upper(),
            "product_type": product_node.get("productType", ""),
            "vendor": product_node.get("vendor", ""),
            "tags": ShopifyDataTransformer.transform_tags(product_node.get("tags", "")),
            "created_at": ShopifyDataTransformer.transform_datetime(
                product_node.get("createdAt")
            ),
            "updated_at": ShopifyDataTransformer.transform_datetime(
                product_node.get("updatedAt")
            ),
            "published_at": ShopifyDataTransformer.transform_datetime(
                product_node.get("publishedAt")
            )
        }

        # Transform variants
        variants_data = product_node.get("variants", {})
        if variants_data and "edges" in variants_data:
            transformed["variants"] = [
                ShopifyDataTransformer.transform_variant(edge["node"])
                for edge in variants_data["edges"]
            ]
        else:
            transformed["variants"] = []

        # Transform images
        images_data = product_node.get("images", {})
        if images_data and "edges" in images_data:
            transformed["images"] = [
                ShopifyDataTransformer.transform_image(edge["node"])
                for edge in images_data["edges"]
            ]
        else:
            transformed["images"] = []

        # Transform options
        options_data = product_node.get("options", [])
        if options_data:
            transformed["options"] = [
                ShopifyDataTransformer.transform_option(option)
                for option in options_data
            ]
        else:
            transformed["options"] = []

        # Transform collections
        collections_data = product_node.get("collections", {})
        if collections_data and "edges" in collections_data:
            transformed["collections"] = [
                ShopifyDataTransformer.transform_collection_reference(edge["node"])
                for edge in collections_data["edges"]
            ]
        else:
            transformed["collections"] = []

        # Calculate derived fields
        transformed.update(ShopifyDataTransformer._calculate_product_metrics(transformed))

        return transformed

    @staticmethod
    def transform_collection(collection_node: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Shopify collection node to standardized format"""
        if not collection_node:
            return {}

        transformed = {
            "id": ShopifyDataTransformer.clean_shopify_id(collection_node.get("id", "")),
            "shopify_id": collection_node.get("id", ""),
            "title": collection_node.get("title", ""),
            "handle": collection_node.get("handle", ""),
            "description": collection_node.get("description", ""),
            "description_html": collection_node.get("descriptionHtml", ""),
            "sort_order": collection_node.get("sortOrder", ""),
            "updated_at": ShopifyDataTransformer.transform_datetime(
                collection_node.get("updatedAt")
            )
        }

        # Transform collection image
        image_data = collection_node.get("image")
        if image_data:
            transformed["image"] = ShopifyDataTransformer.transform_image(image_data)
        else:
            transformed["image"] = None

        # Transform products if included
        products_data = collection_node.get("products", {})
        if products_data and "edges" in products_data:
            transformed["products"] = [
                ShopifyDataTransformer.transform_product(edge["node"])
                for edge in products_data["edges"]
            ]
            transformed["product_count"] = len(transformed["products"])
        else:
            transformed["products"] = []
            transformed["product_count"] = 0

        return transformed

    @staticmethod
    def transform_pagination_info(page_info: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Shopify page info to standardized format"""
        if not page_info:
            return {
                "has_next_page": False,
                "has_previous_page": False,
                "start_cursor": None,
                "end_cursor": None
            }

        return {
            "has_next_page": page_info.get("hasNextPage", False),
            "has_previous_page": page_info.get("hasPreviousPage", False),
            "start_cursor": page_info.get("startCursor"),
            "end_cursor": page_info.get("endCursor")
        }

    @staticmethod
    def transform_products_response(
        response_data: Dict[str, Any],
        page: int = 1,
        limit: int = 50,
        total_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """Transform complete products response with pagination"""
        
        products_data = response_data.get("data", {}).get("products", {})
        edges = products_data.get("edges", [])
        page_info = products_data.get("pageInfo", {})

        # Transform products
        products = [
            ShopifyDataTransformer.transform_product(edge["node"])
            for edge in edges
        ]

        # Build pagination info
        pagination = {
            "page": page,
            "limit": limit,
            "count": len(products),
            **ShopifyDataTransformer.transform_pagination_info(page_info)
        }

        # Add total count and pages if available
        if total_count is not None:
            pagination["total_count"] = total_count
            pagination["total_pages"] = max(1, (total_count + limit - 1) // limit)

        # Add next cursor for convenience
        if pagination["has_next_page"] and pagination["end_cursor"]:
            pagination["next_cursor"] = pagination["end_cursor"]

        return {
            "products": products,
            "pagination": pagination
        }

    @staticmethod
    def transform_collections_response(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform collections response to standardized format"""
        
        collections_data = response_data.get("data", {}).get("collections", {})
        edges = collections_data.get("edges", [])

        return [
            ShopifyDataTransformer.transform_collection(edge["node"])
            for edge in edges
        ]

    @staticmethod
    def _calculate_product_metrics(product: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived metrics for a product"""
        variants = product.get("variants", [])
        
        metrics = {
            "variant_count": len(variants),
            "image_count": len(product.get("images", [])),
            "collection_count": len(product.get("collections", [])),
            "has_variants": len(variants) > 1,
            "available_for_sale": False,
            "min_price": None,
            "max_price": None,
            "total_inventory": 0
        }

        if variants:
            prices = [v.get("price") for v in variants if v.get("price") is not None]
            if prices:
                metrics["min_price"] = min(prices)
                metrics["max_price"] = max(prices)

            # Check availability and sum inventory
            for variant in variants:
                if variant.get("available_for_sale"):
                    metrics["available_for_sale"] = True
                
                inventory = variant.get("inventory_quantity", 0)
                if isinstance(inventory, (int, float)):
                    metrics["total_inventory"] += inventory

        return metrics

    @staticmethod
    def extract_search_filters(products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract available filter options from products list"""
        
        product_types = set()
        vendors = set()
        tags = set()
        collections = set()

        for product in products:
            # Collect product types
            if product.get("product_type"):
                product_types.add(product["product_type"])

            # Collect vendors
            if product.get("vendor"):
                vendors.add(product["vendor"])

            # Collect tags
            for tag in product.get("tags", []):
                tags.add(tag)

            # Collect collections
            for collection in product.get("collections", []):
                if collection.get("title"):
                    collections.add(collection["title"])

        return {
            "product_types": sorted(list(product_types)),
            "vendors": sorted(list(vendors)),
            "tags": sorted(list(tags)),
            "collections": sorted(list(collections))
        }
