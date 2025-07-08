#!/usr/bin/env python3
"""
Test script to create a new product and verify it's published to the online store
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uuid

from sqlalchemy.orm import sessionmaker

from app.config.db_config import engine
from app.models.tenant import Tenant
from app.models.user import User
from app.services.second_hand_product_service import SecondHandProductService
from app.services.shopify_service import ShopifyGraphQLClient


async def test_new_product_creation_and_publishing():
    """Create a new product and verify it's published to the online store"""

    # Create database session
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Create service
        service = SecondHandProductService(db)

        # Find a tenant with Shopify credentials
        tenant = (
            db.query(Tenant)
            .filter(
                Tenant.shopify_app_url.isnot(None),
                Tenant.shopify_access_token.isnot(None),
            )
            .first()
        )

        if not tenant:
            print("❌ No tenant with Shopify credentials found")
            return

        print(f"✅ Found tenant: {tenant.name}")

        # Find a user in this tenant
        user = db.query(User).filter(User.tenant_id == tenant.id).first()

        if not user:
            print("❌ No user found in tenant")
            return

        print(f"✅ Found user: {user.email}")

        # Create a new product
        print("🔄 Creating new product...")
        result = await service.create_second_hand_product(
            user_id=user.id,
            tenant_id=tenant.id,
            name="Test Product for Online Store",
            description="This is a test product to verify online store publishing",
            price=29.99,
            condition="good",
            original_sku="TEST-ONLINE-001",
            size="M",
            shop_domain=tenant.shopify_app_url,
            shopify_access_token=tenant.shopify_access_token,
        )

        if result["success"]:
            product = result["product"]
            print(f"✅ Product created successfully: {product.name} (ID: {product.id})")

            # Approve the product
            print("🔄 Approving product...")
            approval_result = await service.approve_product(product.id, tenant.id)

            if approval_result["success"]:
                print("✅ Product approved successfully!")

                if "shopify_product_id" in approval_result:
                    shopify_id = approval_result["shopify_product_id"]
                    print(f"✅ Shopify product ID: {shopify_id}")

                    # Check if product is published to online store
                    print("🔍 Checking if product is published to online store...")

                    client = ShopifyGraphQLClient(
                        tenant.shopify_app_url, tenant.shopify_access_token
                    )

                    # Query to check publication status
                    query = """
                    query getProduct($id: ID!) {
                        product(id: $id) {
                            id
                            title
                            status
                            publishedAt
                            resourcePublications(first: 10) {
                                edges {
                                    node {
                                        publication {
                                            id
                                            name
                                        }
                                        publishDate
                                        isPublished
                                    }
                                }
                            }
                        }
                    }
                    """

                    result = await client.execute_query(query, {"id": shopify_id})

                    if result.get("data") and result["data"].get("product"):
                        product_data = result["data"]["product"]
                        print(f"📊 Product status: {product_data['status']}")
                        print(f"📅 Published at: {product_data['publishedAt']}")

                        publications = product_data.get("resourcePublications", {}).get(
                            "edges", []
                        )
                        online_store_published = False

                        for pub in publications:
                            pub_info = pub["node"]
                            publication_name = pub_info["publication"]["name"]
                            is_published = pub_info["isPublished"]

                            if publication_name == "Online Store" and is_published:
                                online_store_published = True
                                break

                        if online_store_published:
                            print(
                                "✅ Product is successfully published to the Online Store!"
                            )
                        else:
                            print("❌ Product is NOT published to the Online Store")

                    else:
                        print(f"❌ Failed to query product: {result}")

                else:
                    print("⚠️ Product approved but no Shopify product ID returned")
                    if "warning" in approval_result:
                        print(f"⚠️ Warning: {approval_result['warning']}")
            else:
                print(
                    f"❌ Product approval failed: {approval_result.get('error', 'Unknown error')}"
                )

        else:
            print(f"❌ Product creation failed: {result}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_new_product_creation_and_publishing())
