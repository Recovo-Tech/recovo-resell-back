#!/usr/bin/env python3
"""
Final test script to verify the image upload issue is resolved
Tests our current implementation against a fresh product
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import sessionmaker
from app.models.product import SecondHandProduct, SecondHandProductImage
from app.models.user import User
from app.models.tenant import Tenant
from app.config.db_config import engine, get_db
from app.services.second_hand_product_service import SecondHandProductService
from app.services.shopify_service import ShopifyGraphQLClient
import uuid


async def test_final_image_upload():
    """Final test to verify image upload works correctly"""

    # Get a database session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Get tenant and user for testing
        tenant = db.query(Tenant).first()
        user = db.query(User).filter(User.tenant_id == tenant.id).first()

        if not tenant or not user:
            print("❌ No tenant or user found for testing")
            return

        print(f"🧪 Creating test product for tenant: {tenant.shopify_app_url}")

        # Create a new second-hand product for testing
        service = SecondHandProductService(db)

        # Test image URLs (use reliable ones)
        test_images = [
            "https://cdn.shopify.com/s/files/1/0533/2089/files/placeholder-images-image_large.png",
            "https://plus.unsplash.com/premium_photo-1669648878551-0490585cfd74?q=80&w=2030&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
            "https://plus.unsplash.com/premium_photo-1669648878551-0490585cfd74?q=80&w=2030&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
        ]

        # Create product without Shopify verification
        result = await service.create_second_hand_product(
            user_id=user.id,
            tenant_id=tenant.id,
            name="Final Image Upload Test Product",
            description="This product is created to test our fixed image upload implementation.",
            price=49.99,
            condition="good",
            original_sku="TEST-FINAL-001",
            barcode="1234567890123",
            # Skip shop_domain and access_token to avoid verification
        )

        if not result["success"]:
            print(f"❌ Failed to create product: {result.get('error')}")
            return

        product = result["product"]
        print(f"✅ Created product: {product.name} (ID: {product.id})")

        # Add test images
        images = service.add_product_images(product.id, tenant.id, test_images)
        print(f"✅ Added {len(images)} images to product")

        # Refresh product to get images
        db.refresh(product)

        # Approve and publish to Shopify
        print("\n🚀 Approving and publishing to Shopify...")
        approved_product = await service.approve_product(product.id, tenant.id)

        if not approved_product:
            print("❌ Failed to approve product")
            return

        if not approved_product.shopify_product_id:
            print("❌ Product approved but not published to Shopify")
            return

        print(f"✅ Product published to Shopify: {approved_product.shopify_product_id}")

        # Verify images in Shopify
        print("\n🔍 Verifying images in Shopify...")

        client = ShopifyGraphQLClient(
            tenant.shopify_app_url, tenant.shopify_access_token
        )

        verification_query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                handle
                images(first: 10) {
                    edges {
                        node {
                            id
                            src
                            altText
                            width
                            height
                        }
                    }
                }
            }
        }
        """

        result = await client.execute_query(
            verification_query, {"id": approved_product.shopify_product_id}
        )

        if result and "data" in result and result["data"]["product"]:
            product_data = result["data"]["product"]
            images = product_data.get("images", {}).get("edges", [])

            print(f"📸 Found {len(images)} images in Shopify:")
            for i, img_edge in enumerate(images):
                img = img_edge["node"]
                print(f"   {i+1}. {img['src']}")
                print(f"      Alt: {img['altText']}")
                print(
                    f"      Dimensions: {img.get('width', 'unknown')}x{img.get('height', 'unknown')}"
                )

            # Summary
            expected_images = len(test_images)
            actual_images = len(images)

            print(f"\n📊 FINAL RESULTS:")
            print(f"   Expected images: {expected_images}")
            print(f"   Actual images: {actual_images}")

            if actual_images == expected_images:
                print("   ✅ SUCCESS! All images uploaded correctly")
                print("   🎉 Image upload issue appears to be resolved!")
            elif actual_images > 0:
                print(
                    f"   ⚠️ PARTIAL SUCCESS: {actual_images}/{expected_images} images uploaded"
                )
                print("   💡 Some images may still be processing or failed to upload")
            else:
                print("   ❌ FAILURE: No images found in Shopify")
                print("   🔧 Image upload issue persists")

        else:
            print("❌ Could not verify product in Shopify")

        # Cleanup option
        print(f"\n🗑️ To clean up, delete product ID {approved_product.id} from database")
        print(f"   and {approved_product.shopify_product_id} from Shopify")

    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_final_image_upload())
