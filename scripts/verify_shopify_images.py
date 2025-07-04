"""
Script to verify if images were successfully uploaded to Shopify
"""

import os
import sys
import asyncio

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.shopify_service import ShopifyGraphQLClient
from app.config.db_config import SessionLocal


async def verify_shopify_images():
    """Verify images in the latest Shopify products"""
    try:
        # Get database session
        db = SessionLocal()

        # Get the default tenant
        from app.models.tenant import Tenant

        tenant = db.query(Tenant).first()

        if not tenant:
            print("No tenant found")
            return

        print(f"Using tenant: {tenant.name}")

        # Create Shopify client
        client = ShopifyGraphQLClient(
            tenant.shopify_app_url, tenant.shopify_access_token
        )

        # Query for recent products
        query = """
        query {
            products(first: 5, reverse: true) {
                edges {
                    node {
                        id
                        title
                        handle
                        createdAt
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
                }
            }
        }
        """

        print("\\nQuerying recent Shopify products...")
        result = await client.execute_query(query)

        products = result.get("data", {}).get("products", {}).get("edges", [])

        print(f"Found {len(products)} recent products:")
        for product_edge in products:
            product = product_edge["node"]
            images = product.get("images", {}).get("edges", [])

            print(f"\\n📦 Product: {product['title']}")
            print(f"   ID: {product['id']}")
            print(f"   Handle: {product['handle']}")
            print(f"   Created: {product['createdAt']}")
            print(f"   Images: {len(images)}")

            for img_edge in images:
                img = img_edge["node"]
                print(f"     - {img['src']} (Alt: {img['altText']})")

        db.close()

    except Exception as e:
        print(f"Error verifying images: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(verify_shopify_images())
