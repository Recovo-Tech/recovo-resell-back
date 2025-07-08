#!/usr/bin/env python3
"""
Test script to check publications and publication status
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import sessionmaker

from app.config.db_config import engine
from app.models.tenant import Tenant
from app.services.shopify_service import ShopifyGraphQLClient


async def test_publications_and_product():
    """Test publications and product status"""

    # Get tenant with Shopify credentials
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
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
        print(f"🔗 Shop URL: {tenant.shopify_app_url}")
        print(f"🔑 Access token: {tenant.shopify_access_token[:10]}...")

        client = ShopifyGraphQLClient(
            tenant.shopify_app_url, tenant.shopify_access_token
        )

        # Test 1: Get publications
        print("\n🔍 Testing publications query...")
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

        result = await client.execute_query(publications_query)

        if result.get("data"):
            publications = result["data"].get("publications", {}).get("edges", [])
            print(f"✅ Found {len(publications)} publications:")
            online_store_id = None
            for pub in publications:
                print(f"  - {pub['node']['name']}: {pub['node']['id']}")
                if pub["node"]["name"] == "Online Store":
                    online_store_id = pub["node"]["id"]

            if online_store_id:
                print(f"✅ Online Store publication ID: {online_store_id}")
            else:
                print("❌ Online Store publication not found")

        else:
            print(f"❌ Publications query failed: {result}")

        # Test 2: Check a specific product
        print("\n🔍 Testing product query...")
        product_query = """
        query {
            products(first: 1, query: "tag:second-hand") {
                edges {
                    node {
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
            }
        }
        """

        result = await client.execute_query(product_query)

        if result.get("data"):
            products = result["data"].get("products", {}).get("edges", [])
            if products:
                product = products[0]["node"]
                print(f"✅ Found product: {product['title']}")
                print(f"📊 Status: {product['status']}")
                print(f"📅 Published at: {product['publishedAt']}")

                publications = product.get("resourcePublications", {}).get("edges", [])
                print(f"📢 Publications ({len(publications)}):")

                for pub in publications:
                    pub_info = pub["node"]
                    publication_name = pub_info["publication"]["name"]
                    is_published = pub_info["isPublished"]
                    publish_date = pub_info["publishDate"]

                    print(
                        f"  - {publication_name}: {'✅ Published' if is_published else '❌ Not published'}"
                    )
                    if publish_date:
                        print(f"    Published on: {publish_date}")
            else:
                print("❌ No second-hand products found")
        else:
            print(f"❌ Product query failed: {result}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_publications_and_product())
