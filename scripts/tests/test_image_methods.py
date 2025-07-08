#!/usr/bin/env python3
"""
Script to test different approaches to image handling in Shopify GraphQL API
Compares:
1. productSet with files included
2. productCreate + productCreateMedia (fallback)
"""

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid

from sqlalchemy.orm import sessionmaker

from app.config.db_config import engine
from app.models.tenant import Tenant
from app.services.shopify_service import ShopifyGraphQLClient


async def test_image_upload_approaches():
    """Test different approaches to uploading images to Shopify"""

    # Test image URLs (use publicly available images)
    test_images = [
        "https://cdn.shopify.com/s/files/1/0533/2089/files/placeholder-images-image_large.png",
        "https://via.placeholder.com/600x400/FF5733/FFFFFF?text=Test+Image+1",
        "https://via.placeholder.com/600x400/33C3FF/FFFFFF?text=Test+Image+2",
    ]

    # Get database session and tenant
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Get the first tenant for testing
        tenant = db.query(Tenant).first()
        if not tenant:
            print("❌ No tenant found for testing")
            return

        print(
            f"🧪 Testing image upload approaches for tenant: {tenant.shopify_app_url}"
        )

        # Get Shopify client using tenant credentials
        if not tenant.shopify_app_url or not tenant.shopify_access_token:
            print("❌ Tenant missing Shopify credentials")
            return

        client = ShopifyGraphQLClient(
            tenant.shopify_app_url, tenant.shopify_access_token
        )

        print(f"✅ Connected to Shopify: {tenant.shopify_app_url}")

        # Method 1: productSet with files included directly
        print("\n🔄 Method 1: productSet with files included directly")
        success1 = await test_productset_with_files(client, test_images)

        # Method 2: productCreate + productCreateMedia (current fallback)
        print("\n🔄 Method 2: productCreate + productCreateMedia (fallback)")
        success2 = await test_productcreate_with_media(client, test_images)

        # Summary
        print("\n📊 SUMMARY:")
        print(
            f"   Method 1 (productSet with files): {'✅ Success' if success1 else '❌ Failed'}"
        )
        print(
            f"   Method 2 (productCreate + media): {'✅ Success' if success2 else '❌ Failed'}"
        )

        print("\n💡 RECOMMENDATIONS:")
        if success1 and success2:
            print(
                "   Both methods work. productSet is more modern and should be preferred."
            )
        elif success1:
            print("   Use productSet with files - it's the modern approach.")
        elif success2:
            print("   Use productCreate + productCreateMedia as fallback.")
        else:
            print(
                "   Both methods failed - investigate API credentials and image URLs."
            )

    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


async def test_productset_with_files(client, image_urls):
    """Test productSet mutation with files included directly"""
    try:
        files_input = []
        for i, url in enumerate(image_urls):
            files_input.append(
                {
                    "originalSource": url,
                    "alt": f"Test Image {i + 1}",
                    "contentType": "IMAGE",
                    "duplicateResolutionMode": "REPLACE",
                }
            )

        mutation = """
        mutation productSet($input: ProductSetInput!) {
            productSet(input: $input) {
                product {
                    id
                    title
                    handle
                    images(first: 10) {
                        edges {
                            node {
                                id
                                src
                                altText
                            }
                        }
                    }
                }
                userErrors {
                    field
                    message
                    code
                }
            }
        }
        """

        variables = {
            "input": {
                "title": "Test Product - productSet Method",
                "descriptionHtml": "<p>Test product created using productSet with files included directly.</p>",
                "vendor": "Test Vendor",
                "productType": "Test",
                "status": "DRAFT",  # Create as draft for testing
                "files": files_input,
                "variants": [
                    {
                        "price": "29.99",
                        "inventoryManagement": "SHOPIFY",
                        "inventoryPolicy": "DENY",
                    }
                ],
            }
        }

        print(f"   📤 Creating product with {len(files_input)} images...")
        result = await client.execute_query(mutation, variables)

        if result and "data" in result:
            product_data = result["data"].get("productSet", {})
            user_errors = product_data.get("userErrors", [])

            if user_errors:
                print(f"   ❌ Errors: {user_errors}")
                return False

            product = product_data.get("product")
            if product:
                product_id = product["id"]
                images = product.get("images", {}).get("edges", [])
                print(f"   ✅ Product created: {product_id}")
                print(f"   📸 Images attached: {len(images)}")

                for i, img_edge in enumerate(images):
                    img = img_edge["node"]
                    print(f"      {i+1}. {img['src']} (Alt: {img['altText']})")

                # Clean up - delete the test product
                await cleanup_product(client, product_id)
                return len(images) > 0

        print(f"   ❌ Unexpected response: {result}")
        return False

    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        return False


async def test_productcreate_with_media(client, image_urls):
    """Test productCreate + productCreateMedia approach"""
    try:
        # First, create product without images
        create_mutation = """
        mutation productCreate($input: ProductInput!) {
            productCreate(input: $input) {
                product {
                    id
                    title
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
                "title": "Test Product - productCreate Method",
                "descriptionHtml": "<p>Test product created using productCreate + productCreateMedia.</p>",
                "vendor": "Test Vendor",
                "productType": "Test",
                "status": "DRAFT",
                "variants": [
                    {
                        "price": "39.99",
                        "inventoryManagement": "SHOPIFY",
                        "inventoryPolicy": "DENY",
                    }
                ],
            }
        }

        print(f"   📤 Creating product...")
        result = await client.execute_query(create_mutation, create_variables)

        if not result or "data" not in result:
            print(f"   ❌ Failed to create product: {result}")
            return False

        product_data = result["data"].get("productCreate", {})
        user_errors = product_data.get("userErrors", [])

        if user_errors:
            print(f"   ❌ Product creation errors: {user_errors}")
            return False

        product = product_data.get("product")
        if not product:
            print("   ❌ No product returned")
            return False

        product_id = product["id"]
        print(f"   ✅ Product created: {product_id}")

        # Now add images using productCreateMedia
        media_input = []
        for i, url in enumerate(image_urls):
            media_input.append(
                {
                    "mediaContentType": "IMAGE",
                    "originalSource": url,
                    "alt": f"Test Image {i + 1}",
                }
            )

        media_mutation = """
        mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
            productCreateMedia(productId: $productId, media: $media) {
                media {
                    ... on MediaImage {
                        id
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

        media_variables = {"productId": product_id, "media": media_input}

        print(f"   📤 Adding {len(media_input)} images...")
        media_result = await client.execute_query(media_mutation, media_variables)

        if media_result and "data" in media_result:
            media_data = media_result["data"].get("productCreateMedia", {})
            media_errors = media_data.get("mediaUserErrors", [])

            if media_errors:
                print(f"   ❌ Media errors: {media_errors}")

            created_media = media_data.get("media", [])
            print(f"   📸 Images attached: {len(created_media)}")

            for i, media in enumerate(created_media):
                if "image" in media and media["image"]:
                    img = media["image"]
                    print(f"      {i+1}. {img['src']} (Alt: {img['altText']})")

            # Clean up - delete the test product
            await cleanup_product(client, product_id)
            return len(created_media) > 0

        print(f"   ❌ Media upload failed: {media_result}")
        await cleanup_product(client, product_id)
        return False

    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        return False


async def cleanup_product(client, product_id):
    """Delete a test product"""
    try:
        delete_mutation = """
        mutation productDelete($input: ProductDeleteInput!) {
            productDelete(input: $input) {
                deletedProductId
                userErrors {
                    field
                    message
                }
            }
        }
        """

        delete_variables = {"input": {"id": product_id}}

        result = await client.execute_query(delete_mutation, delete_variables)
        if result and "data" in result:
            deleted_id = result["data"].get("productDelete", {}).get("deletedProductId")
            if deleted_id:
                print(f"   🗑️ Cleaned up test product: {deleted_id}")
            else:
                print(f"   ⚠️ Could not delete test product: {result}")
    except Exception as e:
        print(f"   ⚠️ Cleanup failed: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_image_upload_approaches())
