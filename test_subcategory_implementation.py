#!/usr/bin/env python3
"""
Test script for Shopify subcategory functionality
Tests the new subcategory and category tree features
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.shopify_service import ShopifyGraphQLClient
from app.services.shopify_category_service import ShopifyCategoryService
from app.config.shopify_config import shopify_settings


async def test_subcategory_functionality():
    """Test the new subcategory functionality"""
    
    # Mock tenant for testing
    class MockTenant:
        def __init__(self):
            self.id = "test-tenant"
            self.name = "Test Tenant"
            self.shopify_app_url = shopify_settings.shopify_app_url
            self.shopify_access_token = shopify_settings.shopify_access_token
    
    tenant = MockTenant()
    
    print("🔍 Testing Shopify Subcategory Functionality...")
    print("=" * 60)
    
    try:
        # Test GraphQL client taxonomy methods
        print("\n1. Testing GraphQL Client - Enhanced Taxonomy Query...")
        client = ShopifyGraphQLClient(tenant.shopify_app_url, tenant.shopify_access_token)
        
        # Test enhanced taxonomy query
        taxonomy_data = await client.get_taxonomy()
        print(f"   ✅ Fetched {taxonomy_data.get('total', 0)} categories from taxonomy")
        
        # Show first few categories with hierarchy info
        categories = taxonomy_data.get('categories', [])
        if categories:
            print(f"   📋 Sample categories with hierarchy:")
            for i, cat in enumerate(categories[:3]):
                print(f"      {i+1}. {cat.get('name')} (ID: {cat.get('id')[:20]}...)")
                print(f"         Level: {cat.get('level', 'N/A')}, Parent: {cat.get('parent_id') is not None}")
                print(f"         Children Count: {cat.get('children_count', 0)}, Is Leaf: {cat.get('is_leaf', 'N/A')}")
        
        # Test category service
        print("\n2. Testing Category Service...")
        service = ShopifyCategoryService(tenant)
        
        # Test getting all categories
        all_categories = await service.get_categories()
        print(f"   ✅ Category service fetched {len(all_categories)} categories")
        
        # Test getting top-level categories
        top_level = await service.get_top_level_categories()
        print(f"   ✅ Found {len(top_level)} top-level categories")
        
        # Show top-level categories
        if top_level:
            print(f"   📋 Top-level categories:")
            for i, cat in enumerate(top_level[:5]):
                print(f"      {i+1}. {cat.get('name')} ({cat.get('type')})")
        
        # Test subcategories for a top-level category (if available)
        if top_level:
            test_parent = None
            for cat in top_level:
                if cat.get('type') == 'taxonomy_category' and cat.get('children_count', 0) > 0:
                    test_parent = cat
                    break
            
            if test_parent:
                print(f"\n3. Testing Subcategories for '{test_parent['name']}'...")
                subcategories = await service.get_subcategories(test_parent['id'])
                print(f"   ✅ Found {len(subcategories)} subcategories")
                
                if subcategories:
                    print(f"   📋 Subcategories:")
                    for i, subcat in enumerate(subcategories[:3]):
                        print(f"      {i+1}. {subcat.get('name')} (Level: {subcat.get('level', 'N/A')})")
                
                # Test category tree
                print(f"\n4. Testing Category Tree for '{test_parent['name']}'...")
                tree = await service.get_category_tree(test_parent['id'], max_depth=2)
                if tree.get('category'):
                    print(f"   ✅ Successfully built category tree")
                    print(f"   📋 Root: {tree['category']['name']}")
                    print(f"   📋 Children: {len(tree.get('children', []))}")
                    
                    for i, child in enumerate(tree.get('children', [])[:3]):
                        child_cat = child.get('category', {})
                        print(f"      {i+1}. {child_cat.get('name')} (Level: {child_cat.get('level', 'N/A')})")
                        if child.get('children'):
                            print(f"         Has {len(child['children'])} grandchildren")
                else:
                    print(f"   ❌ Failed to build category tree")
            else:
                print(f"\n3. ⚠️  No taxonomy categories with children found for testing subcategories")
        
        # Test search functionality
        print(f"\n5. Testing Category Search...")
        search_results = await service.search_categories("apparel")
        print(f"   ✅ Search for 'apparel' returned {len(search_results)} results")
        
        if search_results:
            print(f"   📋 Search results:")
            for i, result in enumerate(search_results[:3]):
                print(f"      {i+1}. {result.get('name')} ({result.get('type')})")
        
        print("\n" + "=" * 60)
        print("✅ All subcategory functionality tests completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_subcategory_functionality()
    if success:
        print("🎉 Subcategory implementation test: PASSED")
        return 0
    else:
        print("💥 Subcategory implementation test: FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
