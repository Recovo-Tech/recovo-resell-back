"""
Script to test Shopify product creation directly
"""

import os
import sys
import asyncio
import psycopg2

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.shopify_service import ShopifyGraphQLClient
from app.services.second_hand_product_service import SecondHandProductService
from app.config.db_config import SessionLocal


async def test_shopify_product_creation():
    """Test creating a new product in Shopify"""
    try:
        # Get database session
        db = SessionLocal()

        # Get the first second-hand product
        from app.models.product import SecondHandProduct

        product = db.query(SecondHandProduct).first()

        if not product:
            print("No second-hand products found")
            return

        print(f"Testing with product: {product.name}")
        print(f"Product ID: {product.id}")
        print(f"Original SKU: {product.original_sku}")
        print(f"Current Shopify ID: {product.shopify_product_id}")

        # Get tenant credentials
        tenant = product.tenant
        if not tenant or not tenant.shopify_app_url or not tenant.shopify_access_token:
            print("ERROR: No valid tenant Shopify credentials")
            return

        print(f"Using Shopify URL: {tenant.shopify_app_url}")

        # Create Shopify client
        client = ShopifyGraphQLClient(
            tenant.shopify_app_url, tenant.shopify_access_token
        )

        # Test the publishing method directly
        service = SecondHandProductService(db)

        print("\\nTesting _publish_to_shopify method...")
        shopify_product_id = await service._publish_to_shopify(client, product)

        if shopify_product_id:
            print(f"✅ Successfully created product in Shopify: {shopify_product_id}")

            # Query the new product to verify it exists
            verify_query = f"""
            query {{
                product(id: "{shopify_product_id}") {{
                    id
                    title
                    vendor
                    productType
                    tags
                    status
                    variants(first: 1) {{
                        edges {{
                            node {{
                                id
                                sku
                                price
                                inventoryQuantity
                            }}
                        }}
                    }}
                }}
            }}
            """

            result = await client.execute_query(verify_query)

            if "errors" in result:
                print(f"Error verifying product: {result['errors']}")
            else:
                new_product = result.get("data", {}).get("product")
                if new_product:
                    print("\\n📋 New product details:")
                    print(f"  Title: {new_product['title']}")
                    print(f"  Vendor: {new_product['vendor']}")
                    print(f"  Type: {new_product['productType']}")
                    print(f"  Tags: {', '.join(new_product['tags'])}")
                    print(f"  Status: {new_product['status']}")

                    if new_product["variants"]["edges"]:
                        variant = new_product["variants"]["edges"][0]["node"]
                        print(f"  SKU: {variant['sku']}")
                        print(f"  Price: {variant['price']}")
                        print(f"  Inventory: {variant['inventoryQuantity']}")
        else:
            print("❌ Failed to create product in Shopify")

        db.close()

    except Exception as e:
        print(f"Error testing Shopify product creation: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_shopify_product_creation())
