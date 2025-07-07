#!/usr/bin/env python3
"""
Test script to verify automatic publishing when creating verified second-hand products via HTTP API
"""
import requests
import json
import os
from pathlib import Path

def test_auto_publish_http():
    """Test creating a verified product that should auto-publish via HTTP API"""
    
    print("🧪 Testing Automatic Publishing via HTTP API")
    print("=" * 60)
    
    # API base URL (assuming server is running on localhost:8000)
    base_url = "http://localhost:8000"
    
    # First, we need to authenticate
    # Let's try to get a token for testing
    login_data = {
        "username": "test@example.com",  # Replace with actual test user
        "password": "testpassword"       # Replace with actual test password
    }
    
    try:
        # Login to get token
        print("🔐 Attempting to authenticate...")
        auth_response = requests.post(f"{base_url}/auth/login", data=login_data)
        
        if auth_response.status_code != 200:
            print(f"❌ Authentication failed: {auth_response.status_code}")
            print(f"Response: {auth_response.text}")
            return
        
        token_data = auth_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            print("❌ No access token received")
            return
        
        print("✅ Authentication successful")
        
        # Set up headers with authorization
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # Test product data - using a SKU that we know exists and is verified
        product_data = {
            "name": "Test Auto-Publish Product",
            "description": "This product should be automatically published",
            "price": 25.99,
            "condition": "like_new",
            "original_sku": "1234",  # Use the SKU we know exists
            "size": "M"
        }
        
        print(f"📝 Creating product with SKU: {product_data['original_sku']}")
        print(f"   Expected: Product should be verified and auto-published")
        
        # Create the product
        create_response = requests.post(
            f"{base_url}/second-hand/products",
            data=product_data,
            headers=headers
        )
        
        print(f"📊 Response Status: {create_response.status_code}")
        
        if create_response.status_code == 200:
            product_result = create_response.json()
            print("✅ Product created successfully!")
            print(f"   📋 Product ID: {product_result.get('id')}")
            print(f"   🔍 Is Verified: {product_result.get('is_verified')}")
            print(f"   ✅ Is Approved: {product_result.get('is_approved')}")
            print(f"   �️ Shopify Product ID: {product_result.get('shopify_product_id')}")
            
            # Check if auto-publishing worked
            if product_result.get('is_verified') and product_result.get('is_approved'):
                if product_result.get('shopify_product_id'):
                    print("🎉 SUCCESS: Product was automatically verified, approved, AND published to Shopify!")
                else:
                    print("⚠️ PARTIAL: Product was verified and approved but no Shopify ID found")
            elif product_result.get('is_verified'):
                print("⚠️ ISSUE: Product was verified but not automatically approved")
            else:
                print("ℹ️ INFO: Product was not verified (expected for non-existent SKUs)")
                
        else:
            print(f"❌ Product creation failed: {create_response.status_code}")
            print(f"Response: {create_response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on localhost:8000")
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")

if __name__ == "__main__":
    test_auto_publish_http()
            "name": "Test Verified Product Auto-Publish",
            "description": "This product should be automatically published if verified",
            "price": 25.99,
            "condition": "like_new",
            "original_sku": "1234",  # This should exist in your Shopify store
            "size": "M",
            "barcode": None,
            "shop_domain": tenant.shopify_app_url,
            "shopify_access_token": tenant.shopify_access_token,
        }
        
        print(f"🔄 Creating second-hand product with SKU: {test_product_data['original_sku']}")
        
        # Create the product (this should trigger verification and automatic publishing)
        result = await service.create_second_hand_product(**test_product_data)
        
        if result["success"]:
            product = result["product"]
            verification_info = result["verification_info"]
            
            print(f"✅ Product created successfully:")
            print(f"   - Product ID: {product.id}")
            print(f"   - Name: {product.name}")
            print(f"   - Is Verified: {product.is_verified}")
            print(f"   - Is Approved: {product.is_approved}")
            print(f"   - Shopify Product ID: {product.shopify_product_id}")
            print(f"   - Weight: {product.weight} {product.weight_unit}")
            print(f"   - Original Vendor: {product.original_vendor}")
            
            if verification_info["is_verified"]:
                print(f"✅ Product was verified against Shopify")
                
                if product.is_approved:
                    print(f"✅ Product was automatically approved!")
                    if product.shopify_product_id:
                        print(f"✅ Product was automatically published to Shopify: {product.shopify_product_id}")
                    else:
                        print(f"⚠️ Product was approved but no Shopify product ID found")
                else:
                    print(f"❌ Product was NOT automatically approved despite being verified")
            else:
                print(f"❌ Product was NOT verified - automatic publishing should not occur")
                
        else:
            print(f"❌ Product creation failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_automatic_publishing())
