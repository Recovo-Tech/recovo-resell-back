#!/usr/bin/env python3
"""
Test script for the new productSet API implementation
Tests the modern Shopify GraphQL API with files directly included
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import sessionmaker
from app.models.second_hand_product import SecondHandProduct
from app.models.user import User
from app.models.tenant import Tenant
from app.config.db_config import engine, get_db
from app.services.second_hand_product_service import SecondHandProductService
import uuid


async def test_productset_api():
    """Test the new productSet API with files included directly"""

    # Get a database session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Get a test second-hand product that hasn't been published yet
        test_product = (
            db.query(SecondHandProduct)
            .filter(
                SecondHandProduct.is_approved == True,
                SecondHandProduct.is_verified == True,
                SecondHandProduct.shopify_product_id.is_(None),
            )
            .first()
        )

        if not test_product:
            print(
                "❌ No suitable test product found. Need an approved and verified product without Shopify ID."
            )
            return

        print(f"🧪 Testing with product: {test_product.name}")
        print(f"   - ID: {test_product.id}")
        print(f"   - Condition: {test_product.condition}")
        print(f"   - Price: ${test_product.price}")
        print(f"   - Images: {len(test_product.images)} images")

        for i, img in enumerate(test_product.images):
            print(f"     {i+1}. {img.image_url}")

        # Initialize the service
        service = SecondHandProductService(db)

        # Test the publish to Shopify method
        print("\n🚀 Publishing to Shopify using new productSet API...")
        shopify_id = await service.publish_to_shopify(test_product)

        if shopify_id:
            print(f"✅ SUCCESS! Product published to Shopify with ID: {shopify_id}")

            # Update the product in database
            test_product.shopify_product_id = shopify_id
            db.commit()
            print("✅ Database updated with Shopify product ID")

            # Verification: Check if product exists in Shopify
            print("\n🔍 Verifying product in Shopify...")

            from app.config.shopify_config import get_shopify_client_for_tenant

            client = await get_shopify_client_for_tenant(test_product.tenant_id)

            if client:
                verification_query = """
                query getProduct($id: ID!) {
                    product(id: $id) {
                        id
                        title
                        handle
                        status
                        vendor
                        tags
                        images(first: 10) {
                            edges {
                                node {
                                    id
                                    src
                                    altText
                                }
                            }
                        }
                        variants(first: 1) {
                            edges {
                                node {
                                    id
                                    sku
                                    price
                                    inventoryQuantity
                                }
                            }
                        }
                    }
                }
                """

                result = await client.execute_query(
                    verification_query, {"id": shopify_id}
                )

                if result and "data" in result and result["data"]["product"]:
                    product_data = result["data"]["product"]
                    print(f"✅ Product verified in Shopify:")
                    print(f"   - Title: {product_data['title']}")
                    print(f"   - Handle: {product_data['handle']}")
                    print(f"   - Status: {product_data['status']}")
                    print(f"   - Vendor: {product_data['vendor']}")
                    print(f"   - Tags: {product_data['tags']}")

                    images = product_data.get("images", {}).get("edges", [])
                    print(f"   - Images: {len(images)} images found")
                    for i, img_edge in enumerate(images):
                        img = img_edge["node"]
                        print(f"     {i+1}. {img['src']} (Alt: {img['altText']})")

                    variants = product_data.get("variants", {}).get("edges", [])
                    if variants:
                        variant = variants[0]["node"]
                        print(f"   - Variant SKU: {variant['sku']}")
                        print(f"   - Price: ${variant['price']}")
                        print(f"   - Inventory: {variant['inventoryQuantity']}")
                else:
                    print("❌ Could not verify product in Shopify")
            else:
                print("❌ Could not get Shopify client for verification")

        else:
            print("❌ FAILED! Product could not be published to Shopify")

    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_productset_api())
