#!/usr/bin/env python3
"""
Test script to verify automatic publishing when creating verified second-hand products via HTTP API
"""
import json
import os
import sys
from pathlib import Path

import requests

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import create_access_token


def test_auto_publish_http():
    """Test creating a verified product that should auto-publish via HTTP API"""

    print("🧪 Testing Automatic Publishing via HTTP API")
    print("=" * 60)

    # Get database session to fetch real user and tenant
    db: Session = next(get_db())

    try:
        # Get the first tenant and user from database
        tenant = db.query(Tenant).first()
        user = db.query(User).first()

        if not tenant:
            print("❌ No tenant found in database")
            return

        if not user:
            print("❌ No user found in database")
            return

        print(f"📋 Using tenant: {tenant.shopify_app_url}")
        print(f"👤 Using user: {user.email}")

        # Create access token for the user
        access_token = create_access_token(
            data={"sub": str(user.id), "tenant_id": str(tenant.id), "role": user.role}
        )

        print("✅ Access token created")

        # API base URL (assuming server is running on localhost:8000)
        base_url = "http://localhost:8000"

        # Set up headers with authorization and tenant
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tenant-ID": str(tenant.id),
        }

        # Test product data - using a SKU that we know exists and is verified
        product_data = {
            "name": "Test Auto-Publish Product via HTTP",
            "description": "This product should be automatically published",
            "price": 29.99,
            "condition": "like_new",
            "original_sku": "1234",  # Use the SKU we know exists
            "size": "L",
        }

        print(f"📝 Creating product with SKU: {product_data['original_sku']}")
        print(f"   Expected: Product should be verified and auto-published")

        # Create the product
        create_response = requests.post(
            f"{base_url}/second-hand/products", data=product_data, headers=headers
        )

        print(f"📊 Response Status: {create_response.status_code}")

        if create_response.status_code == 200:
            product_result = create_response.json()
            print("✅ Product created successfully!")
            print(f"   📋 Product ID: {product_result.get('id')}")
            print(f"   🔍 Is Verified: {product_result.get('is_verified')}")
            print(f"   ✅ Is Approved: {product_result.get('is_approved')}")
            print(
                f"   🛍️ Shopify Product ID: {product_result.get('shopify_product_id')}"
            )

            # Check if auto-publishing worked
            if product_result.get("is_verified") and product_result.get("is_approved"):
                if product_result.get("shopify_product_id"):
                    print(
                        "🎉 SUCCESS: Product was automatically verified, approved, AND published to Shopify!"
                    )
                else:
                    print(
                        "⚠️ PARTIAL: Product was verified and approved but no Shopify ID found"
                    )
            elif product_result.get("is_verified"):
                print("⚠️ ISSUE: Product was verified but not automatically approved")
            else:
                print(
                    "ℹ️ INFO: Product was not verified (expected for non-existent SKUs)"
                )

        else:
            print(f"❌ Product creation failed: {create_response.status_code}")
            try:
                error_detail = create_response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Response text: {create_response.text}")

    except requests.exceptions.ConnectionError:
        print(
            "❌ Could not connect to server. Make sure it's running on localhost:8000"
        )
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_auto_publish_http()
