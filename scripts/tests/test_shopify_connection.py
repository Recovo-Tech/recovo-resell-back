"""
Script to test Shopify connection and check if products exist
"""

import os
import sys
import asyncio
import psycopg2

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.shopify_service import ShopifyGraphQLClient

# Database connection parameters
db_user = os.getenv("DATABASE_USERNAME", "postgres")
db_password = os.getenv("DATABASE_PASSWORD")
db_host = os.getenv("DATABASE_HOSTNAME", "localhost")
db_port = os.getenv("DATABASE_PORT", "5432")
db_name = os.getenv("DATABASE_NAME", "recovo")


async def test_shopify_connection():
    """Test Shopify connection and check products"""
    try:
        # Connect to the database to get tenant info
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
        )

        cursor = conn.cursor()

        # Get tenant with Shopify credentials
        cursor.execute(
            """
            SELECT shopify_app_url, shopify_access_token
            FROM tenants
            WHERE shopify_app_url IS NOT NULL AND shopify_access_token IS NOT NULL
            LIMIT 1;
        """
        )

        tenant_info = cursor.fetchone()

        if not tenant_info:
            print("No tenant with Shopify credentials found")
            return

        shopify_url, access_token = tenant_info
        print(f"Testing connection to: {shopify_url}")

        # Test Shopify connection
        client = ShopifyGraphQLClient(shopify_url, access_token)

        # Query for products (broader search)
        query = """
        query {
            products(first: 20) {
                edges {
                    node {
                        id
                        title
                        status
                        vendor
                        productType
                        tags
                        createdAt
                        variants(first: 1) {
                            edges {
                                node {
                                    id
                                    sku
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        result = await client.execute_query(query)

        if "errors" in result:
            print(f"GraphQL errors: {result['errors']}")
            return

        products = result.get("data", {}).get("products", {}).get("edges", [])

        print(f"\nFound {len(products)} products in Shopify:")
        print("-" * 100)

        for edge in products:
            product = edge["node"]
            variant_sku = ""
            if product["variants"]["edges"]:
                variant_sku = product["variants"]["edges"][0]["node"]["sku"]

            print(f"ID: {product['id']}")
            print(f"Title: {product['title']}")
            print(f"Status: {product['status']}")
            print(f"Vendor: {product['vendor']}")
            print(f"Type: {product['productType']}")
            print(f"Tags: {', '.join(product['tags'])}")
            print(f"SKU: {variant_sku}")
            print(f"Created: {product['createdAt']}")
            print("-" * 100)

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error testing Shopify connection: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_shopify_connection())
