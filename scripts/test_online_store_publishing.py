#!/usr/bin/env python3
"""
Test script to verify online store publishing functionality
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.shopify_service import ShopifyGraphQLClient


async def test_publications():
    """Test getting publications from Shopify"""
    # Test credentials - replace with actual values
    shop_domain = "your-shop.myshopify.com"  # Replace with actual shop domain
    access_token = "your-access-token"  # Replace with actual access token

    if shop_domain == "your-shop.myshopify.com":
        print("❌ Please update the shop_domain and access_token in the script")
        return

    try:
        client = ShopifyGraphQLClient(shop_domain, access_token)

        # Test getting publications
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

        print("🔍 Testing publications query...")
        result = await client.execute_query(publications_query)

        if result.get("data"):
            publications = result["data"].get("publications", {}).get("edges", [])
            print(f"✅ Found {len(publications)} publications:")
            for pub in publications:
                print(f"  - {pub['node']['name']}: {pub['node']['id']}")

            # Look for Online Store
            online_store = next(
                (p for p in publications if p["node"]["name"] == "Online Store"), None
            )
            if online_store:
                print(
                    f"✅ Online Store publication found: {online_store['node']['id']}"
                )
            else:
                print("❌ Online Store publication not found")
        else:
            print(f"❌ Error: {result}")

    except Exception as e:
        print(f"❌ Error testing publications: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_publications())
