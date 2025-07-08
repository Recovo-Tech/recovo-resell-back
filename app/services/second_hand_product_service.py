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
            print(
                f"DEBUG: Found {len(images)} images for product {product.id}: {images}"
            )

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
                    print(f"DEBUG: Added image {i+1} to media input: {img_url}")
                else:
                    print(f"WARNING: Skipping invalid image URL: {img_url}")

            print(f"DEBUG: Final media input array: {media_input}")

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
                    {f'<li><strong>Original Brand:</strong> {product.original_vendor}</li>' if product.original_vendor else ''}
                    {f'<li><strong>Weight:</strong> {product.weight} {product.weight_unit}</li>' if product.weight else ''}
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
                    "productOptions": [
                        {
                            "name": "Size",
                            "values": [
                                {"name": product.size if product.size else None},
                            ],
                        }
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

            print(
                f"DEBUG: Publishing product to Shopify with variables: {product_variables}"
            )
            result = await client.execute_query(mutation, product_variables)
            print(f"DEBUG: Shopify API response: {result}")

            # Check for GraphQL errors
            if result.get("errors"):
                error_messages = [
                    error.get("message", "Unknown error") for error in result["errors"]
                ]
                error_msg = f"GraphQL errors: {', '.join(error_messages)}"
                print(f"Shopify GraphQL errors: {error_msg}")
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
                print(f"Shopify product creation errors: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": "PRODUCT_CREATE_ERROR",
                }

            shopify_product = (
                result.get("data", {}).get("productCreate", {}).get("product")
            )
            if shopify_product:
                print(f"DEBUG: Successfully created product: {shopify_product}")
                shopify_product_id = shopify_product["id"]

                # Validate that product details were properly set
                print(f"✅ Product created with:")
                print(f"   - Title: {shopify_product.get('title')}")
                print(f"   - Product Type: {shopify_product.get('productType')}")
                print(f"   - Vendor: {shopify_product.get('vendor')}")

                # Validate that weight was properly set
                if shopify_product.get("variants", {}).get("edges"):
                    variant = shopify_product["variants"]["edges"][0]["node"]
                    variant_weight = variant.get("weight")
                    variant_weight_unit = variant.get("weightUnit")
                    print(f"   - Weight: {variant_weight} {variant_weight_unit}")

                    if weight_value > 0 and (
                        not variant_weight or variant_weight != weight_value
                    ):
                        print(
                            f"⚠️ WARNING: Expected weight {weight_value} but got {variant_weight}"
                        )

                # Always add images using productCreateMedia (most reliable method)
                if len(media_input) > 0:
                    print(
                        f"DEBUG: Uploading {len(media_input)} images using productCreateMedia..."
                    )
                    image_success = await self._add_images_to_product(
                        client, shopify_product_id, media_input
                    )
                    if image_success:
                        print("✅ Image upload completed successfully")
                    else:
                        print("⚠️ Image upload failed - product created without images")
                        # Don't fail the entire operation for image upload issues
                else:
                    print("ℹ️ No images to upload")

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
                                "Warning: Failed to set inventory quantity, but product was created successfully"
                            )
                    else:
                        print(
                            "DEBUG: Inventory not tracked for this product or no inventory item ID found"
                        )

                # Add product to "Second Hand" collection
                collection_success = await self._add_to_second_hand_collection(
                    client, shopify_product_id
                )
                if collection_success:
                    print("✅ Product added to Second Hand collection")
                else:
                    print("⚠️ Failed to add product to Second Hand collection")

                return {
                    "success": True,
                    "shopify_product_id": shopify_product_id,
                    "message": "Product successfully published to Shopify",
                }
            else:
                print("ERROR: No product returned in response despite no errors")
                return {
                    "success": False,
                    "error": "Product creation succeeded but no product data was returned",
                    "error_code": "NO_PRODUCT_DATA",
                }

        except Exception as e:
            error_msg = f"Unexpected error publishing to Shopify: {str(e)}"
            print(error_msg)
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
            print(f"DEBUG: Using location: {location_name} ({location_id})")

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

            print(f"DEBUG: Setting inventory with variables: {inventory_variables}")
            inventory_result = await client.execute_query(
                inventory_mutation, inventory_variables
            )
            print(f"DEBUG: Inventory set response: {inventory_result}")

            # Check for errors
            if (
                inventory_result.get("data", {})
                .get("inventorySetOnHandQuantities", {})
                .get("userErrors")
            ):
                errors = inventory_result["data"]["inventorySetOnHandQuantities"][
                    "userErrors"
                ]
                print(f"Inventory set errors: {errors}")
                return False

            # Check if adjustment was successful
            adjustment_group = (
                inventory_result.get("data", {})
                .get("inventorySetOnHandQuantities", {})
                .get("inventoryAdjustmentGroup")
            )
            if adjustment_group:
                print(
                    f"✅ Successfully set inventory quantity - adjustment created at {adjustment_group.get('createdAt')}"
                )
                changes = adjustment_group.get("changes", [])
                for change in changes:
                    print(f"   - {change.get('name')}: delta {change.get('delta')}")
                return True
            else:
                print("✅ Inventory set successfully (no adjustment group needed)")
                return True

        except Exception as e:
            print(f"Error setting inventory: {str(e)}")
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
            print("No images to upload")
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
                    print(
                        f"DEBUG: Uploading image {i+1}/{total_images}: {media_item['originalSource']}"
                    )

                    media_variables = {
                        "productId": product_id,
                        "media": [media_item],  # Upload one at a time
                    }

                    result = await client.execute_query(media_mutation, media_variables)

                    if result and "data" in result:
                        media_data = result["data"].get("productCreateMedia", {})
                        media_errors = media_data.get("mediaUserErrors", [])

                        if media_errors:
                            print(f"   ❌ Error uploading image {i+1}: {media_errors}")
                            continue

                        created_media = media_data.get("media", [])
                        if created_media:
                            media_info = created_media[0]
                            media_id = media_info.get("id")
                            status = media_info.get("status", "unknown")

                            print(
                                f"   ✅ Image {i+1} uploaded: {media_id} (status: {status})"
                            )

                            # Check if image details are available
                            image_data = media_info.get("image")
                            if image_data and image_data.get("src"):
                                print(f"      URL: {image_data['src']}")
                            else:
                                print(f"      Image processing in background...")

                            successful_uploads += 1
                        else:
                            print(f"   ❌ No media returned for image {i+1}")
                    else:
                        print(f"   ❌ API error for image {i+1}: {result}")

                    # Small delay between uploads to avoid rate limiting
                    if i < total_images - 1:  # Don't delay after the last upload
                        await asyncio.sleep(0.5)

                except Exception as e:
                    print(f"   ❌ Exception uploading image {i+1}: {str(e)}")
                    continue

            print(
                f"✅ Successfully uploaded {successful_uploads}/{total_images} images"
            )

            # Wait a moment for processing, then verify uploads
            if successful_uploads > 0:
                print("⏳ Waiting for image processing...")
                await asyncio.sleep(2)  # Give Shopify time to process

                # Verify the uploads
                verified_count = await self._verify_product_images(
                    client, product_id, successful_uploads
                )
                print(
                    f"🔍 Verified {verified_count}/{successful_uploads} images are accessible"
                )

                return verified_count > 0

            return successful_uploads > 0

        except Exception as e:
            print(f"Error adding images to product: {str(e)}")
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
            print(f"Error verifying images: {str(e)}")
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

            print(f"DEBUG: Adding product {product_id} to collection {collection_id}")
            result = await client.execute_query(add_product_mutation, variables)
            print(f"DEBUG: Collection add result: {result}")

            # Check for errors
            if (
                result.get("data", {})
                .get("collectionAddProducts", {})
                .get("userErrors")
            ):
                errors = result["data"]["collectionAddProducts"]["userErrors"]
                print(f"Error adding product to collection: {errors}")
                return False

            # Check if the operation was successful
            collection_data = (
                result.get("data", {})
                .get("collectionAddProducts", {})
                .get("collection")
            )
            if collection_data:
                products_count = collection_data.get("productsCount", {}).get(
                    "count", "unknown"
                )
                print(
                    f"✅ Product added to collection '{collection_data.get('title')}' (Products count: {products_count})"
                )
                return True

            return False

        except Exception as e:
            print(f"Error adding product to Second Hand collection: {str(e)}")
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

            print(f"DEBUG: Searching for collection with title '{collection_title}'")
            result = await client.execute_query(find_collection_query, search_variables)

            # Check if collection already exists
            collections = result.get("data", {}).get("collections", {}).get("edges", [])
            if collections:
                collection_id = collections[0]["node"]["id"]
                print(f"✅ Found existing collection: {collection_id}")
                return collection_id

            # Collection doesn't exist, create it
            print(f"Collection '{collection_title}' not found, creating new one...")

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

            print(f"DEBUG: Creating collection with variables: {create_variables}")
            create_result = await client.execute_query(
                create_collection_mutation, create_variables
            )
            print(f"DEBUG: Collection creation result: {create_result}")

            # Check for creation errors
            if (
                create_result.get("data", {})
                .get("collectionCreate", {})
                .get("userErrors")
            ):
                errors = create_result["data"]["collectionCreate"]["userErrors"]
                print(f"Error creating collection: {errors}")
                return None

            # Get the created collection ID
            created_collection = (
                create_result.get("data", {})
                .get("collectionCreate", {})
                .get("collection")
            )
            if created_collection:
                collection_id = created_collection["id"]
                print(
                    f"✅ Created new collection: {collection_id} - '{created_collection.get('title')}'"
                )
                return collection_id

            return None

        except Exception as e:
            print(f"Error finding or creating collection: {str(e)}")
            import traceback

            traceback.print_exc()
            return None
