#!/usr/bin/env python3

import os
import sys
import requests
import json
from uuid import uuid4

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_shopify_categories():
    """Test the new Shopify categories endpoints"""
    
    base_url = "http://localhost:8000"
    
    print("🛍️  Testing Shopify Categories Endpoints")
    print("=" * 50)
    
    # First, get a valid token by registering/logging in a user
    test_username = f"testuser_{uuid4().hex[:8]}"
    test_email = f"{test_username}@example.com"
    test_password = "testpass123"
    
    # Register user
    register_data = {
        "username": test_username,
        "email": test_email,
        "password": test_password,
        "password_confirmation": test_password,
        "tenant_name": "Default Tenant",
        "name": "Test",
        "surname": "User"
    }
    
    try:
        print(f"🔧 Registering test user: {test_username}")
        response = requests.post(f"{base_url}/auth/register", json=register_data)
        if response.status_code == 200:
            register_result = response.json()
            token = register_result['token']['access_token']
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
    
    # Test 1: Get all categories
    print(f"\n📋 Test 1: Get all categories")
    try:
        response = requests.get(f"{base_url}/shopify/categories", headers=headers)
        if response.status_code == 200:
            result = response.json()
            categories = result.get('categories', [])
            print(f"✅ Successfully fetched {len(categories)} categories")
            
            # Show first few categories
            for i, category in enumerate(categories[:3]):
                print(f"   {i+1}. {category['name']} (ID: {category['id']}) - {category['products_count']} products")
            
            if len(categories) > 3:
                print(f"   ... and {len(categories) - 3} more categories")
            
            # Save first category ID for next tests
            first_category_id = categories[0]['id'] if categories else None
            
        else:
            print(f"❌ Failed to fetch categories: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error fetching categories: {e}")
        return False
    
    # Test 2: Get specific category by ID (if we have one)
    if first_category_id:
        print(f"\n🔍 Test 2: Get category by ID")
        try:
            response = requests.get(f"{base_url}/shopify/categories/{first_category_id}", headers=headers)
            if response.status_code == 200:
                result = response.json()
                category = result.get('category', {})
                print(f"✅ Successfully fetched category: {category['name']}")
                print(f"   Description: {category['description'][:100]}..." if category['description'] else "   No description")
                print(f"   Products: {category['products_count']}")
                print(f"   Sample products: {len(category.get('sample_products', []))}")
            else:
                print(f"❌ Failed to fetch category: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"❌ Error fetching category by ID: {e}")
    
    # Test 3: Search categories
    print(f"\n🔎 Test 3: Search categories")
    search_term = "collection"  # Common search term
    try:
        response = requests.get(f"{base_url}/shopify/categories/search/{search_term}", headers=headers)
        if response.status_code == 200:
            result = response.json()
            categories = result.get('categories', [])
            print(f"✅ Found {len(categories)} categories matching '{search_term}'")
            
            for category in categories[:2]:
                print(f"   - {category['name']}")
        else:
            print(f"❌ Failed to search categories: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error searching categories: {e}")
    
    print(f"\n🎉 Shopify categories testing completed!")
    return True

if __name__ == "__main__":
    success = test_shopify_categories()
    sys.exit(0 if success else 1)
