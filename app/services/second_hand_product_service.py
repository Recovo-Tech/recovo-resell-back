# app/services/second_hand_product_service.py
import asyncio
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.config.shopify_config import shopify_settings
from app.models.product import SecondHandProduct, SecondHandProductImage
from app.models.user import User
from app.services.shopify_service import (ShopifyGraphQLClient,
                                          ShopifyProductVerificationService)


class SecondHandProductService:
    """Service for managing second-hand products"""

    def __init__(self, db: Session):
        self.db = db

    async def create_second_hand_product(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        name: str,
        description: str,
        price: float,
        condition: str,
        original_sku: str,
        size: str = None,
        color: str = None,
        return_address: str = None,
        barcode: Optional[str] = None,
        shop_domain: str = None,
        shopify_access_token: str = None,
    ) -> Dict[str, Any]:
        """Create a new second-hand product listing"""

        # Verify the product against Shopify store
        if shop_domain and shopify_access_token:
            verification_service = ShopifyProductVerificationService(
                shop_domain, shopify_access_token
            )
            verification_result = await verification_service.verify_product_eligibility(
                sku=original_sku, barcode=barcode
            )

            if not verification_result["is_verified"]:
                verification_result = {"is_verified": False, "product_info": {}}
        else:
            verification_result = {"is_verified": False, "product_info": {}}

        # Extract product information from verification_result if available
        product_info = verification_result.get("product_info", {})
        weight = product_info.get("weight")
        weight_unit = product_info.get("weightUnit")
        original_title = product_info.get("title", "")
        original_description = product_info.get("description", "")
        original_product_type = product_info.get("productType", "")
        original_vendor = product_info.get("vendor", "")

        # Create the second-hand product
        second_hand_product = SecondHandProduct(
            name=name,
            description=description,
            price=price,
            size=size,
            color=color,
            return_address=return_address,
            condition=condition,
            original_sku=original_sku,
            barcode=barcode,
            seller_id=user_id,
            tenant_id=tenant_id,  # Add tenant_id
            is_verified=verification_result["is_verified"],
            is_approved=False,  # Requires admin approval
            shopify_product_id=product_info.get("shopify_id"),
            weight=weight,
            weight_unit=weight_unit,
            original_title=original_title,
            original_description=original_description,
            original_product_type=original_product_type,
            original_vendor=original_vendor,
        )

        self.db.add(second_hand_product)
        self.db.commit()
        self.db.refresh(second_hand_product)

        return {
            "success": True,
            "product": second_hand_product,
            "verification_info": verification_result,
        }

    def get_user_products(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[SecondHandProduct]:
        """Get all second-hand products for a user within their tenant"""
        return (
            self.db.query(SecondHandProduct)
            .filter(
                and_(
                    SecondHandProduct.seller_id == user_id,
                    SecondHandProduct.tenant_id == tenant_id,
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_approved_products(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[SecondHandProduct]:
        """Get all approved second-hand products for public listing within tenant"""
        return (
            self.db.query(SecondHandProduct)
            .filter(
                and_(
                    SecondHandProduct.is_approved == True,
                    SecondHandProduct.is_verified == True,
                    SecondHandProduct.tenant_id == tenant_id,
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_product_by_id(
        self, product_id: int, tenant_id: uuid.UUID
    ) -> Optional[SecondHandProduct]:
        """Get a second-hand product by ID within tenant"""
        return (
            self.db.query(SecondHandProduct)
            .filter(
                and_(
                    SecondHandProduct.id == product_id,
                    SecondHandProduct.tenant_id == tenant_id,
                )
            )
            .first()
        )

    def update_product(
        self,
        product_id: int,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        update_data: Dict[str, Any],
    ) -> Optional[SecondHandProduct]:
        """Update a second-hand product (only by owner within tenant)"""
        product = (
            self.db.query(SecondHandProduct)
            .filter(
                and_(
                    SecondHandProduct.id == product_id,
                    SecondHandProduct.seller_id == user_id,
                    SecondHandProduct.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if not product:
            return None

        for field, value in update_data.items():
            if hasattr(product, field) and field not in [
                "id",
                "seller_id",
                "tenant_id",
                "created_at",
            ]:
                setattr(product, field, value)

        self.db.commit()
        self.db.refresh(product)
        return product

    def delete_product(
        self, product_id: int, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> bool:
        """Delete a second-hand product (only by owner within tenant)"""
        product = (
            self.db.query(SecondHandProduct)
            .filter(
                and_(
                    SecondHandProduct.id == product_id,
                    SecondHandProduct.seller_id == user_id,
                    SecondHandProduct.tenant_id == tenant_id,
                )
            )
            .first()
        )

        if not product:
            return False

        self.db.delete(product)
        self.db.commit()
        return True

    async def approve_product(
        self, product_id: int, tenant_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Approve a second-hand product for sale and publish to Shopify (admin only)"""
        product = self.get_product_by_id(product_id, tenant_id)
        if not product:
            return {
                "success": False,
                "error": "Product not found",
                "error_code": "PRODUCT_NOT_FOUND",
            }

        # Mark as approved
        product.is_approved = True
        self.db.commit()
        self.db.refresh(product)

        # Try to publish to Shopify using the tenant's credentials
        try:
            # Load the tenant relationship
            tenant = product.tenant
            if tenant and tenant.shopify_app_url and tenant.shopify_access_token:
                shopify_client = ShopifyGraphQLClient(
                    tenant.shopify_app_url, tenant.shopify_access_token
                )
                publish_result = await self._publish_to_shopify(shopify_client, product)

                if publish_result["success"]:
                    product.shopify_product_id = publish_result["shopify_product_id"]
                    self.db.commit()
                    self.db.refresh(product)

                    return {
                        "success": True,
                        "product": product,
                        "shopify_product_id": publish_result["shopify_product_id"],
                        "message": "Product approved and successfully published to Shopify",
                    }
                else:
                    # Product approved but Shopify publish failed
                    return {
                        "success": True,
                        "product": product,
                        "warning": f"Product approved but failed to publish to Shopify: {publish_result['error']}",
                        "error_code": publish_result.get(
                            "error_code", "SHOPIFY_PUBLISH_FAILED"
                        ),
                    }
            else:
                return {
                    "success": True,
                    "product": product,
                    "warning": "Product approved but Shopify credentials not configured",
                    "error_code": "SHOPIFY_NOT_CONFIGURED",
                }
        except Exception as e:
            error_msg = f"Unexpected error during approval: {str(e)}"
            print(error_msg)
            return {
                "success": True,
                "product": product,
                "warning": f"Product approved but failed to publish to Shopify: {error_msg}",
                "error_code": "UNEXPECTED_ERROR",
            }

    async def _publish_to_shopify(
        self, client: ShopifyGraphQLClient, product: SecondHandProduct
    ) -> Dict[str, Any]:
        """Publish a second-hand product to Shopify store with images and inventory"""

        try:
            # Get product images
            images = [img.image_url for img in product.images] if product.images else []

            # Prepare media input for images with proper structure and validation
            media_input = []
            for i, img_url in enumerate(images):
                if img_url and img_url.startswith(("http://", "https://")):
                    media_input.append(
                        {
                            "mediaContentType": "IMAGE",
                            "originalSource": img_url,
                            "alt": f"{product.name} - Image {i + 1}",
                        }
                    )
                else:
                    print(f"WARNING: Skipping invalid image URL: {img_url}")

            # Build enhanced description with proper formatting
            description_parts = []

            # Add second-hand product description first
            if product.description and product.description.strip():
                description_parts.append(f"<p>{product.description}</p>")

            # Add original description if available
            if product.original_description and product.original_description.strip():
                description_parts.append(f"<h3>Original Description:</h3>")
                # Handle both plain text and HTML descriptions
                if product.original_description.startswith("<"):
                    description_parts.append(product.original_description)
                else:
                    description_parts.append(f"<p>{product.original_description}</p>")

            # Add product details section
            details_html = f"""
                <h3>Product Details</h3>
                <ul>
                    <li><strong>Condition:</strong> {product.condition.replace('_', ' ').title()}</li>
                    <li><strong>Original SKU:</strong> {product.original_sku}</li>
                    {f'<li><strong>Barcode:</strong> {product.barcode}</li>' if product.barcode else ''}
                    {f'<li><strong>Size:</strong> {product.size}</li>' if product.size else ''}
                    {f'<li><strong>Color:</strong> {product.color}</li>' if product.color else ''}
                    {f'<li><strong>Original Brand:</strong> {product.original_vendor}</li>' if product.original_vendor else ''}
                    {f'<li><strong>Weight:</strong> {product.weight} {product.weight_unit}</li>' if product.weight else ''}
                    {f'<li><strong>Return Address:</strong> {product.return_address}</li>' if product.return_address else ''}
                </ul>
                <p><em>This is a high-quality second-hand item sold through our marketplace platform.</em></p>
            """
            description_parts.append(details_html)

            # Combine all description parts
            enhanced_description = "".join(description_parts)

            # Determine product type - use original if available, otherwise default
            product_type = (
                product.original_product_type
                if product.original_product_type
                else "Second-Hand"
            )

            # Determine vendor - use original if available, otherwise default
            vendor = (
                product.original_vendor
                if product.original_vendor
                else "Second-Hand Marketplace"
            )

            # Validate and prepare weight data
            weight_value = 0.0
            weight_unit = "GRAMS"
            if product.weight and product.weight > 0:
                weight_value = float(product.weight)
                if product.weight_unit:
                    # Ensure weight unit is valid for Shopify
                    valid_units = ["GRAMS", "KILOGRAMS", "OUNCES", "POUNDS"]
                    weight_unit = product.weight_unit.upper()
                    if weight_unit not in valid_units:
                        print(
                            f"WARNING: Invalid weight unit '{weight_unit}', defaulting to GRAMS"
                        )
                        weight_unit = "GRAMS"
                print(f"DEBUG: Setting product weight: {weight_value} {weight_unit}")
            else:
                print("DEBUG: No weight data available, using default values")

            # Use the proven productCreate mutation (most reliable approach)
            mutation = """
                mutation productCreate($input: ProductInput!) {
                    productCreate(input: $input) {
                        product {
                            id
                            title
                            handle
                            status
                            productType
                            vendor
                            publishedAt
                            variants(first: 1) {
                                edges {
                                    node {
                                        id
                                        weight
                                        weightUnit
                                        inventoryItem {
                                            id
                                            tracked
                                        }
                                    }
                                }
                            }
                        }
                        userErrors {
                            field
                            message
                        }
                    }
                }
                """

            # Prepare product input using the proven ProductInput structure
            product_variables = {
                "input": {
                    "title": f"{product.name} (Second-Hand)",
                    "descriptionHtml": enhanced_description,
                    "vendor": vendor,
                    "productType": product_type,
                    "status": "ACTIVE",
                    "published": True,  # Publish to online store
                    "productOptions": [
                        {
                            "name": "Size",
                            "values": [
                                {"name": product.size if product.size else "One Size"},
                            ],
                        },
                        {
                            "name": "Color",
                            "values": [
                                {"name": product.color if product.color else "Default"},
                            ],
                        },
                    ],
                    "tags": [
                        "second-hand",
                        product.condition,
                        "marketplace",
                        "pre-owned",
                    ],
                    "variants": [
                        {
                            "price": str(product.price),
                            "compareAtPrice": None,
                            "inventoryManagement": "SHOPIFY",
                            "inventoryPolicy": "DENY",
                            "sku": f"SH-{product.id}-{product.original_sku}",
                            "barcode": product.barcode if product.barcode else None,
                            "weight": weight_value,
                            "weightUnit": weight_unit,
                            "requiresShipping": True,
                            "taxable": True,
                        }
                    ],
                }
            }

            result = await client.execute_query(mutation, product_variables)

            # Check for GraphQL errors
            if result.get("errors"):
                error_messages = [
                    error.get("message", "Unknown error") for error in result["errors"]
                ]
                error_msg = f"GraphQL errors: {', '.join(error_messages)}"
                print(f"WARNING: Shopify GraphQL errors: {error_msg}")
                return {
                    "success": False,
                    "error": f"Failed to connect to Shopify API: {error_msg}",
                    "error_code": "GRAPHQL_ERROR",
                }

            # Check for user errors in the response
            if result.get("data", {}).get("productCreate", {}).get("userErrors"):
                errors = result["data"]["productCreate"]["userErrors"]
                error_messages = []
                for error in errors:
                    field = (
                        error.get("field", ["unknown"])[0]
                        if error.get("field")
                        else "unknown"
                    )
                    message = error.get("message", "Unknown error")
                    error_messages.append(f"{field}: {message}")

                error_msg = f"Product creation failed: {'; '.join(error_messages)}"
                print(f"WARNING: Shopify product creation errors: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "PRODUCT_CREATE_ERROR",
                }

            shopify_product = (
                result.get("data", {}).get("productCreate", {}).get("product")
            )
            if shopify_product:
                shopify_product_id = shopify_product["id"]

                # Validate that weight was properly set
                if shopify_product.get("variants", {}).get("edges"):
                    variant = shopify_product["variants"]["edges"][0]["node"]
                    variant_weight = variant.get("weight")
                    variant_weight_unit = variant.get("weightUnit")
                    if weight_value > 0 and (
                        not variant_weight or variant_weight != weight_value
                    ):
                        print(
                            f"⚠️ WARNING: Expected weight {weight_value} but got {variant_weight}"
                        )

                # Always add images using productCreateMedia (most reliable method)
                if len(media_input) > 0:
                    image_success = await self._add_images_to_product(
                        client, shopify_product_id, media_input
                    )
                    if not image_success:
                        print(
                            "⚠️ WARNING: Image upload failed - product created without images"
                        )
                        # Don't fail the entire operation for image upload issues
                # Set inventory for the variant if we have a variant and it's tracked
                if shopify_product.get("variants", {}).get("edges"):
                    variant = shopify_product["variants"]["edges"][0]["node"]
                    inventory_item = variant.get("inventoryItem", {})
                    inventory_item_id = inventory_item.get("id")
                    is_tracked = inventory_item.get("tracked", False)

                    if inventory_item_id and is_tracked:
                        inventory_success = await self._set_inventory_quantity(
                            client, inventory_item_id, 1
                        )
                        if not inventory_success:
                            print(
                                "⚠️ WARNING: Failed to set inventory quantity, but product was created successfully"
                            )

                # Add product to "Second Hand" collection
                collection_success = await self._add_to_second_hand_collection(
                    client, shopify_product_id
                )
                if not collection_success:
                    print("⚠️ WARNING: Failed to add product to Second Hand collection")

                # Explicitly publish to online store
                publish_success = await self._publish_to_online_store(
                    client, shopify_product_id
                )
                if not publish_success:
                    print("⚠️ WARNING: Failed to publish product to online store")

                return {
                    "success": True,
                    "shopify_product_id": shopify_product_id,
                    "message": "Product successfully published to Shopify",
                }
            else:
                print("⚠️ WARNING: No product returned in response despite no errors")
                return {
                    "success": False,
                    "error": "Product creation succeeded but no product data was returned",
                    "error_code": "NO_PRODUCT_DATA",
                }

        except Exception as e:
            error_msg = f"Unexpected error publishing to Shopify: {str(e)}"
            print(f"⚠️ WARNING: {error_msg}")
            import traceback

            traceback.print_exc()
            return {
                "success": False,
                "error": error_msg,
                "error_code": "UNEXPECTED_ERROR",
            }

    async def _set_inventory_quantity(
        self, client: ShopifyGraphQLClient, inventory_item_id: str, quantity: int
    ) -> bool:
        """Set inventory quantity for a product variant using the new API"""
        try:
            # Get the primary location first
            location_query = """
            query {
                locations(first: 1) {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
            """

            location_result = await client.execute_query(location_query)
            locations = (
                location_result.get("data", {}).get("locations", {}).get("edges", [])
            )

            if not locations:
                print("No locations found for inventory management")
                return False

            location_id = locations[0]["node"]["id"]
            location_name = locations[0]["node"]["name"]

            # Use the correct inventorySetOnHandQuantities mutation
            inventory_mutation = """
            mutation inventorySetOnHandQuantities($input: InventorySetOnHandQuantitiesInput!) {
                inventorySetOnHandQuantities(input: $input) {
                    inventoryAdjustmentGroup {
                        createdAt
                        reason
                        changes {
                            name
                            delta
                        }
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """

            inventory_variables = {
                "input": {
                    "reason": "correction",  # Valid reason from API docs
                    "setQuantities": [
                        {
                            "inventoryItemId": inventory_item_id,
                            "locationId": location_id,
                            "quantity": quantity,  # Set absolute quantity
                        }
                    ],
                }
            }

            inventory_result = await client.execute_query(
                inventory_mutation, inventory_variables
            )

            # Check for errors
            if (
                inventory_result.get("data", {})
                .get("inventorySetOnHandQuantities", {})
                .get("userErrors")
            ):
                errors = inventory_result["data"]["inventorySetOnHandQuantities"][
                    "userErrors"
                ]
                print(f"⚠️ WARNING: Inventory set errors: {errors}")
                return False

            # Check if adjustment was successful
            adjustment_group = (
                inventory_result.get("data", {})
                .get("inventorySetOnHandQuantities", {})
                .get("inventoryAdjustmentGroup")
            )
            if adjustment_group:

                return True
            else:

                return True

        except Exception as e:
            print(f"⚠️ WARNING: Error setting inventory: {str(e)}")
            import traceback

            traceback.print_exc()
            return False

    def add_product_images(
        self, product_id: int, tenant_id: uuid.UUID, image_urls: List[str]
    ) -> List[SecondHandProductImage]:
        """Add images to a second-hand product"""
        product = self.get_product_by_id(product_id, tenant_id)
        if not product:
            return []

        images = []
        for i, url in enumerate(image_urls):
            image = SecondHandProductImage(
                product_id=product_id,
                image_url=url,
                is_primary=(i == 0),  # First image is primary
            )
            self.db.add(image)
            images.append(image)

        self.db.commit()
        return images

    def search_products(
        self,
        tenant_id: uuid.UUID,
        query: str = None,
        condition: str = None,
        size: str = None,
        color: str = None,
        min_price: float = None,
        max_price: float = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SecondHandProduct]:
        """Search approved second-hand products with filters within tenant"""
        db_query = self.db.query(SecondHandProduct).filter(
            and_(
                SecondHandProduct.is_approved == True,
                SecondHandProduct.is_verified == True,
                SecondHandProduct.tenant_id == tenant_id,
            )
        )

        if query:
            db_query = db_query.filter(SecondHandProduct.name.ilike(f"%{query}%"))

        if condition:
            db_query = db_query.filter(SecondHandProduct.condition == condition)

        if size:
            db_query = db_query.filter(SecondHandProduct.size == size)

        if color:
            db_query = db_query.filter(SecondHandProduct.color == color)

        if min_price is not None:
            db_query = db_query.filter(SecondHandProduct.price >= min_price)

        if max_price is not None:
            db_query = db_query.filter(SecondHandProduct.price <= max_price)

        return db_query.offset(skip).limit(limit).all()

    async def _add_images_to_product(
        self, client: ShopifyGraphQLClient, product_id: str, media_input: list
    ) -> bool:
        """Add images to an existing Shopify product using productCreateMedia mutation with retry logic"""
        if not media_input:
            return True

        try:
            media_mutation = """
            mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
                productCreateMedia(productId: $productId, media: $media) {
                    media {
                        ... on MediaImage {
                            id
                            status
                            image {
                                src
                                altText
                            }
                        }
                    }
                    mediaUserErrors {
                        field
                        message
                        code
                    }
                }
            }
            """

            # Upload images one by one to avoid rate limiting and improve success rate
            successful_uploads = 0
            total_images = len(media_input)

            for i, media_item in enumerate(media_input):
                try:
                    media_variables = {
                        "productId": product_id,
                        "media": [media_item],  # Upload one at a time
                    }

                    result = await client.execute_query(media_mutation, media_variables)

                    if result and "data" in result:
                        media_data = result["data"].get("productCreateMedia", {})
                        media_errors = media_data.get("mediaUserErrors", [])

                        if media_errors:
                            continue

                        created_media = media_data.get("media", [])
                        if created_media:
                            successful_uploads += 1
                    # Small delay between uploads to avoid rate limiting
                    if i < total_images - 1:  # Don't delay after the last upload
                        await asyncio.sleep(0.5)

                except Exception as e:
                    continue

            # Wait a moment for processing, then verify uploads
            if successful_uploads > 0:
                await asyncio.sleep(2)  # Give Shopify time to process

                # Verify the uploads
                verified_count = await self._verify_product_images(
                    client, product_id, successful_uploads
                )
                return verified_count > 0

            return successful_uploads > 0

        except Exception as e:
            print(f"⚠️ WARNING: Error adding images to product: {str(e)}")
            import traceback

            traceback.print_exc()
            return False

    async def _verify_product_images(
        self, client: ShopifyGraphQLClient, product_id: str, expected_count: int
    ) -> int:
        """Verify that images have been successfully processed and are accessible"""
        try:
            verification_query = """
            query getProductImages($id: ID!) {
                product(id: $id) {
                    images(first: 10) {
                        edges {
                            node {
                                id
                                src
                                altText
                            }
                        }
                    }
                    media(first: 10) {
                        edges {
                            node {
                                ... on MediaImage {
                                    id
                                    status
                                    image {
                                        src
                                        altText
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """

            result = await client.execute_query(verification_query, {"id": product_id})

            if result and "data" in result and result["data"]["product"]:
                product_data = result["data"]["product"]

                # Count accessible images
                images = product_data.get("images", {}).get("edges", [])
                accessible_images = len(
                    [img for img in images if img["node"].get("src")]
                )

                # Also check media status
                media = product_data.get("media", {}).get("edges", [])
                ready_media = len(
                    [
                        m
                        for m in media
                        if m["node"].get("status") == "READY"
                        and m["node"].get("image", {})
                        and m["node"]["image"].get("src")
                    ]
                )

                return max(accessible_images, ready_media)

            return 0

        except Exception as e:
            print(f"⚠️ WARNING: Error verifying images: {str(e)}")
            return 0

    async def _add_to_second_hand_collection(
        self, client: ShopifyGraphQLClient, product_id: str
    ) -> bool:
        """Add a product to the 'Second Hand' collection"""
        try:
            # First, find or create the "Second Hand" collection
            collection_id = await self._find_or_create_collection(client, "Second Hand")

            if not collection_id:
                print("Failed to find or create 'Second Hand' collection")
                return False

            # Add product to collection using collectionAddProducts mutation
            add_product_mutation = """
            mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
                collectionAddProducts(id: $id, productIds: $productIds) {
                    collection {
                        id
                        title
                        productsCount {
                            count
                        }
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """

            variables = {"id": collection_id, "productIds": [product_id]}

            result = await client.execute_query(add_product_mutation, variables)

            # Check for errors
            if (
                result.get("data", {})
                .get("collectionAddProducts", {})
                .get("userErrors")
            ):
                errors = result["data"]["collectionAddProducts"]["userErrors"]
                print(f"⚠️ WARNING: Error adding product to collection: {errors}")
                return False

            # Check if the operation was successful
            collection_data = (
                result.get("data", {})
                .get("collectionAddProducts", {})
                .get("collection")
            )
            if collection_data:
                return True

            return False

        except Exception as e:
            print(
                f"⚠️ WARNING: Error adding product to Second Hand collection: {str(e)}"
            )
            import traceback

            traceback.print_exc()
            return False

    async def _find_or_create_collection(
        self, client: ShopifyGraphQLClient, collection_title: str
    ) -> Optional[str]:
        """Find an existing collection by title or create a new one"""
        try:
            # First, try to find existing collection
            find_collection_query = """
            query findCollection($query: String!) {
                collections(first: 1, query: $query) {
                    edges {
                        node {
                            id
                            title
                            handle
                        }
                    }
                }
            }
            """

            search_variables = {"query": f"title:{collection_title}"}

            result = await client.execute_query(find_collection_query, search_variables)

            # Check if collection already exists
            collections = result.get("data", {}).get("collections", {}).get("edges", [])
            if collections:
                collection_id = collections[0]["node"]["id"]
                return collection_id

            # Collection doesn't exist, create it

            create_collection_mutation = """
            mutation collectionCreate($input: CollectionInput!) {
                collectionCreate(input: $input) {
                    collection {
                        id
                        title
                        handle
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """

            create_variables = {
                "input": {
                    "title": collection_title,
                    "handle": collection_title.lower().replace(" ", "-"),
                    "descriptionHtml": f"<p>Collection for {collection_title.lower()} products sold through our marketplace.</p>",
                    "published": True,
                }
            }

            create_result = await client.execute_query(
                create_collection_mutation, create_variables
            )

            # Check for creation errors
            if (
                create_result.get("data", {})
                .get("collectionCreate", {})
                .get("userErrors")
            ):
                errors = create_result["data"]["collectionCreate"]["userErrors"]
                print(f"⚠️ WARNING: Error creating collection: {errors}")
                return None

            # Get the created collection ID
            created_collection = (
                create_result.get("data", {})
                .get("collectionCreate", {})
                .get("collection")
            )
            if created_collection:
                collection_id = created_collection["id"]
                return collection_id

            return None

        except Exception as e:
            print(f"⚠️ WARNING: Error finding or creating collection: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    async def _publish_to_online_store(
        self, client: ShopifyGraphQLClient, product_id: str
    ) -> bool:
        """Publish a product to the online store"""
        try:
            # First, get the online store publication ID
            publications_query = """
            query {
                publications(first: 10) {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
            """

            publications_result = await client.execute_query(publications_query)
            publications = (
                publications_result.get("data", {})
                .get("publications", {})
                .get("edges", [])
            )

            # Find the online store publication
            online_store_publication_id = None
            for pub in publications:
                if pub["node"]["name"] == "Online Store":
                    online_store_publication_id = pub["node"]["id"]
                    break

            if not online_store_publication_id:
                print("⚠️ WARNING: Online Store publication not found")
                return False

            # Publish the product to the online store
            publish_mutation = """
            mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
                publishablePublish(id: $id, input: $input) {
                    publishable {
                        availablePublicationCount
                        publicationCount
                    }
                    shop {
                        publicationCount
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """

            publish_variables = {
                "id": product_id,
                "input": [
                    {
                        "publicationId": online_store_publication_id,
                        "publishDate": None,  # Publish immediately
                    }
                ],
            }

            publish_result = await client.execute_query(
                publish_mutation, publish_variables
            )

            # Check for errors
            if (
                publish_result.get("data", {})
                .get("publishablePublish", {})
                .get("userErrors")
            ):
                errors = publish_result["data"]["publishablePublish"]["userErrors"]
                print(f"⚠️ WARNING: Error publishing product to online store: {errors}")
                return False

            return True

        except Exception as e:
            print(f"⚠️ WARNING: Error publishing product to online store: {str(e)}")
            import traceback

            traceback.print_exc()
            return False
