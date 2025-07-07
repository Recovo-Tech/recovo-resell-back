#!/usr/bin/env python3

import os
import sys
import requests
import json
from uuid import uuid4

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_shopify_products():
    """Test the new Shopify products endpoints"""

    base_url = "http://localhost:8000"

    print("🛍️ Testing Shopify Products Endpoints")
    print("=" * 50)

    # Step 1: Register a test user
    test_username = f"testuser_{uuid4().hex[:8]}"
    test_email = f"{test_username}@example.com"
    test_password = "testpass123"

    register_data = {
        "username": test_username,
        "email": test_email,
        "password": test_password,
        "password_confirmation": test_password,
        "tenant_name": "Default Tenant",
        "name": "Test",
        "surname": "User",
    }

    try:
        print(f"🔧 Registering test user: {test_username}")
        response = requests.post(f"{base_url}/auth/register", json=register_data)
        if response.status_code == 200:
            register_result = response.json()
            token = register_result["token"]["access_token"]
            print(f"✅ Registration successful!")
            print(f"🔑 Token: {token[:30]}...")
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during registration: {e}")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # Test 1: Get available filters
    print(f"\n📋 Test 1: Get available filters")
    try:
        response = requests.get(f"{base_url}/shopify/products/filters/available", headers=headers)
        if response.status_code == 200:
            filters = response.json()
            print(f"✅ Successfully fetched filters")
            print(f"   Collections: {len(filters.get('collections', []))}")
            print(f"   Product types: {len(filters.get('product_types', []))}")
            print(f"   Vendors: {len(filters.get('vendors', []))}")
            print(f"   Tags: {len(filters.get('tags', []))}")
        else:
            print(f"❌ Failed to fetch filters: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error fetching filters: {e}")

    # Test 2: List all products (first page)
    print(f"\n📋 Test 2: List all products (first page)")
    try:
        response = requests.get(f"{base_url}/shopify/products/", headers=headers, params={"limit": 10})
        if response.status_code == 200:
            products_data = response.json()
            products = products_data.get('products', [])
            pagination = products_data.get('pagination', {})
            print(f"✅ Successfully fetched {len(products)} products")
            
            for i, product in enumerate(products[:3], 1):  # Show first 3 products
                print(f"   {i}. {product['title']} (ID: {product['id']})")
                print(f"      Type: {product.get('product_type', 'N/A')}")
                print(f"      Vendor: {product.get('vendor', 'N/A')}")
                print(f"      Variants: {len(product.get('variants', []))}")
                print(f"      Images: {len(product.get('images', []))}")
                print(f"      Collections: {len(product.get('collections', []))}")
            
            print(f"   Pagination: Page {pagination.get('page', 1)}, Has next: {pagination.get('has_next_page', False)}")
            
            # Save a product ID for further testing
            test_product_id = products[0]['id'] if products else None
            
        else:
            print(f"❌ Failed to fetch products: {response.status_code}")
            print(f"Response: {response.text}")
            test_product_id = None
    except Exception as e:
        print(f"❌ Error fetching products: {e}")
        test_product_id = None

    # Test 3: Get specific product details
    if test_product_id:
        print(f"\n🔍 Test 3: Get product details")
        try:
            response = requests.get(f"{base_url}/shopify/products/{test_product_id}", headers=headers)
            if response.status_code == 200:
                product = response.json()
                print(f"✅ Successfully fetched product: {product['title']}")
                print(f"   Description: {product.get('description', 'N/A')[:100]}...")
                print(f"   Status: {product.get('status', 'N/A')}")
                print(f"   Handle: {product.get('handle', 'N/A')}")
                
                variants = product.get('variants', [])
                if variants:
                    print(f"   Variants:")
                    for variant in variants[:3]:  # Show first 3 variants
                        print(f"     - {variant.get('title', 'N/A')}: ${variant.get('price', 0)} (SKU: {variant.get('sku', 'N/A')})")
                        if variant.get('options'):
                            print(f"       Options: {variant['options']}")
                
            else:
                print(f"❌ Failed to fetch product details: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"❌ Error fetching product details: {e}")

    # Test 4: Search products
    print(f"\n🔎 Test 4: Search products")
    try:
        search_data = {
            "query": "shirt",
            "page": 1,
            "limit": 5
        }
        response = requests.post(f"{base_url}/shopify/products/search", headers=headers, json=search_data)
        if response.status_code == 200:
            search_results = response.json()
            products = search_results.get('products', [])
            print(f"✅ Found {len(products)} products matching 'shirt'")
            
            for i, product in enumerate(products, 1):
                print(f"   {i}. {product['title']}")
                
        else:
            print(f"❌ Failed to search products: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error searching products: {e}")

    # Test 5: Filter by collection (if collections exist)
    print(f"\n🏷️ Test 5: Filter by collection")
    try:
        # First get collections
        response = requests.get(f"{base_url}/shopify/categories/", headers=headers)
        if response.status_code == 200:
            collections = response.json()
            if collections:
                collection_id = collections[0]['id']
                print(f"   Testing with collection: {collections[0]['name']} (ID: {collection_id})")
                
                # Now filter products by this collection
                response = requests.get(
                    f"{base_url}/shopify/products/", 
                    headers=headers, 
                    params={"collection_id": collection_id, "limit": 5}
                )
                if response.status_code == 200:
                    filtered_products = response.json()
                    products = filtered_products.get('products', [])
                    print(f"✅ Found {len(products)} products in collection")
                else:
                    print(f"❌ Failed to filter by collection: {response.status_code}")
            else:
                print("   No collections found to test filtering")
        else:
            print(f"❌ Failed to fetch collections: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing collection filtering: {e}")

    # Test 6: Advanced search with filters
    print(f"\n🔍 Test 6: Advanced search with filters")
    try:
        advanced_search_data = {
            "query": "",
            "filters": {
                "status": "ACTIVE",
                "product_type": "T-Shirt"
            },
            "page": 1,
            "limit": 3
        }
        response = requests.post(f"{base_url}/shopify/products/search", headers=headers, json=advanced_search_data)
        if response.status_code == 200:
            search_results = response.json()
            products = search_results.get('products', [])
            print(f"✅ Found {len(products)} products with advanced filters")
            
            for i, product in enumerate(products, 1):
                print(f"   {i}. {product['title']} (Type: {product.get('product_type', 'N/A')})")
                
        else:
            print(f"❌ Advanced search failed: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error in advanced search: {e}")

    print(f"\n🎉 Shopify products testing completed!")
    return True


if __name__ == "__main__":
    success = test_shopify_products()
    sys.exit(0 if success else 1)
