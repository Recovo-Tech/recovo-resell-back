"""
Script to test the improvements to product approval and Shopify publishing:
1. Weight is properly saved in published product
2. Category (productType) is correctly set from original product info
3. Description format is improved (second-hand + original description)
4. Error handling provides proper user feedback
"""
import os
import sys
import asyncio
import psycopg2
import uuid
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.second_hand_product_service import SecondHandProductService
from app.services.shopify_service import ShopifyGraphQLClient
from app.config.db_config import SessionLocal

async def test_improvements():
    """Test all the improvements made to the product approval process"""
    try:
        # Get database session
        db = SessionLocal()
        
        # Create service
        service = SecondHandProductService(db)
        
        print("🧪 Testing Product Approval Improvements")
        print("=" * 50)
        
        # Get database connection for direct queries
        conn = psycopg2.connect(
            host=os.getenv("DATABASE_HOSTNAME", "localhost"),
            port=os.getenv("DATABASE_PORT", "5432"),
            database=os.getenv("DATABASE_NAME", "recovo"),
            user=os.getenv("DATABASE_USERNAME", "postgres"),
            password=os.getenv("DATABASE_PASSWORD")
        )
        
        cursor = conn.cursor()
        
        # Test 1: Check products with original product info and weight data
        print("\n📋 Test 1: Finding products with weight and original info...")
        cursor.execute("""
            SELECT shp.id, shp.tenant_id, shp.name, shp.description, 
                   shp.weight, shp.weight_unit, shp.original_title, 
                   shp.original_description, shp.original_product_type, 
                   shp.original_vendor, shp.is_approved, shp.shopify_product_id
            FROM second_hand_products shp
            WHERE shp.weight IS NOT NULL AND shp.weight > 0
            AND shp.original_product_type IS NOT NULL
            LIMIT 3;
        """)
        
        products_with_data = cursor.fetchall()
        
        if products_with_data:
            print(f"Found {len(products_with_data)} products with weight and original info:")
            for product in products_with_data:
                pid, tenant_id, name, desc, weight, weight_unit, orig_title, orig_desc, orig_type, orig_vendor, is_approved, shopify_id = product
                print(f"  📦 Product ID: {pid}")
                print(f"     Name: {name}")
                print(f"     Weight: {weight} {weight_unit}")
                print(f"     Original Type: {orig_type}")
                print(f"     Original Vendor: {orig_vendor}")
                print(f"     Approved: {is_approved}")
                print(f"     Shopify ID: {shopify_id}")
                print()
        else:
            print("❌ No products found with weight and original info. Creating test data...")
            await create_test_product_with_data(cursor, db)
            return
        
        # Test 2: Test approval process with detailed output
        print("\n🔄 Test 2: Testing approval process...")
        
        # Find an unapproved product or re-test an approved one
        test_product = None
        for product in products_with_data:
            if not product[10]:  # not approved
                test_product = product
                break
        
        if not test_product:
            # Use first approved product for re-testing
            test_product = products_with_data[0]
            print("ℹ️ No unapproved products, testing with approved product (should show re-approval handling)")
        
        pid, tenant_id, name, desc, weight, weight_unit, orig_title, orig_desc, orig_type, orig_vendor, is_approved, shopify_id = test_product
        
        print(f"Testing approval for Product ID: {pid}")
        print(f"  Name: {name}")
        print(f"  Description: {desc[:100]}{'...' if len(desc) > 100 else ''}")
        print(f"  Weight: {weight} {weight_unit}")
        print(f"  Original Type: {orig_type}")
        print(f"  Original Vendor: {orig_vendor}")
        
        # Test the approval
        print("\n🚀 Starting approval process...")
        approval_result = await service.approve_product(pid, tenant_id)
        
        print("\n📊 Approval Results:")
        if approval_result["success"]:
            print("✅ Approval succeeded!")
            
            approved_product = approval_result["product"]
            print(f"  📋 Message: {approval_result.get('message', 'N/A')}")
            
            if "warning" in approval_result:
                print(f"  ⚠️ Warning: {approval_result['warning']}")
                print(f"  🏷️ Error Code: {approval_result.get('error_code', 'N/A')}")
            
            if "shopify_product_id" in approval_result:
                shopify_product_id = approval_result['shopify_product_id']
                print(f"  🛍️ Shopify Product ID: {shopify_product_id}")
                
                # Test 3: Verify Shopify product details
                print(f"\n🔍 Test 3: Verifying Shopify product details...")
                await verify_shopify_product(tenant_id, shopify_product_id, weight, weight_unit, orig_type, orig_vendor)
            
        else:
            print("❌ Approval failed!")
            print(f"  Error: {approval_result['error']}")
            print(f"  Error Code: {approval_result.get('error_code', 'N/A')}")
        
        # Test 4: Test error handling
        print(f"\n🧪 Test 4: Testing error handling...")
        
        # Test with non-existent product
        print("Testing with non-existent product ID...")
        fake_result = await service.approve_product(99999, tenant_id)
        print(f"Result: Success={fake_result['success']}, Error='{fake_result.get('error', 'N/A')}', Code={fake_result.get('error_code', 'N/A')}")
        
        # Test with invalid tenant
        print("Testing with invalid tenant ID...")
        fake_tenant_id = uuid.uuid4()
        invalid_result = await service.approve_product(pid, fake_tenant_id)
        print(f"Result: Success={invalid_result['success']}, Error='{invalid_result.get('error', 'N/A')}', Code={invalid_result.get('error_code', 'N/A')}")
        
        cursor.close()
        conn.close()
        db.close()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

async def verify_shopify_product(tenant_id, shopify_product_id, expected_weight, expected_weight_unit, expected_type, expected_vendor):
    """Verify that the Shopify product has correct weight, category, and description"""
    try:
        # Get tenant Shopify credentials
        from app.models.tenant import Tenant
        db = SessionLocal()
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        
        if not tenant or not tenant.shopify_app_url or not tenant.shopify_access_token:
            print("⚠️ Cannot verify Shopify product - no tenant credentials")
            return
        
        # Create Shopify client
        client = ShopifyGraphQLClient(tenant.shopify_app_url, tenant.shopify_access_token)
        
        # Query product details
        query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                descriptionHtml
                productType
                vendor
                variants(first: 1) {
                    edges {
                        node {
                            id
                            weight
                            weightUnit
                        }
                    }
                }
            }
        }
        """
        
        result = await client.execute_query(query, {"id": shopify_product_id})
        
        if result and "data" in result and result["data"]["product"]:
            product = result["data"]["product"]
            
            print(f"  📋 Shopify Product Details:")
            print(f"     Title: {product.get('title')}")
            print(f"     Product Type: {product.get('productType')}")
            print(f"     Vendor: {product.get('vendor')}")
            
            # Check weight
            if product.get("variants", {}).get("edges"):
                variant = product["variants"]["edges"][0]["node"]
                actual_weight = variant.get("weight")
                actual_weight_unit = variant.get("weightUnit")
                
                print(f"     Weight: {actual_weight} {actual_weight_unit}")
                
                # Validate weight
                if expected_weight and actual_weight:
                    if abs(float(actual_weight) - float(expected_weight)) < 0.01:
                        print("     ✅ Weight matches expected value")
                    else:
                        print(f"     ❌ Weight mismatch: expected {expected_weight}, got {actual_weight}")
                
                # Validate weight unit
                if expected_weight_unit and actual_weight_unit:
                    if actual_weight_unit.upper() == expected_weight_unit.upper():
                        print("     ✅ Weight unit matches expected value")
                    else:
                        print(f"     ❌ Weight unit mismatch: expected {expected_weight_unit}, got {actual_weight_unit}")
            
            # Validate product type
            actual_type = product.get("productType")
            if expected_type and actual_type:
                if actual_type == expected_type:
                    print("     ✅ Product type matches original value")
                else:
                    print(f"     ❌ Product type mismatch: expected '{expected_type}', got '{actual_type}'")
            
            # Validate vendor
            actual_vendor = product.get("vendor")
            if expected_vendor and actual_vendor:
                if actual_vendor == expected_vendor:
                    print("     ✅ Vendor matches original value")
                else:
                    print(f"     ❌ Vendor mismatch: expected '{expected_vendor}', got '{actual_vendor}'")
            
            # Check description format
            description = product.get("descriptionHtml", "")
            if "Original Description:" in description:
                print("     ✅ Description includes original description section")
            else:
                print("     ⚠️ Description may not include original description section")
                
        else:
            print("  ❌ Failed to retrieve Shopify product details")
            
        db.close()
        
    except Exception as e:
        print(f"  ❌ Error verifying Shopify product: {e}")

async def create_test_product_with_data(cursor, db):
    """Create a test product with weight and original product info"""
    print("Creating test product with complete data...")
    
    # This would need to be implemented based on your specific requirements
    print("❌ Test product creation not implemented in this script")
    print("Please ensure you have products with weight and original_product_type data")

if __name__ == "__main__":
    asyncio.run(test_improvements())
