#!/usr/bin/env python3
"""
Test script to verify automatic publishing via HTTP endpoint
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


def test_http_auto_publish():
    """Test automatic publishing via HTTP endpoint"""

    print("🧪 Testing Automatic Publishing via HTTP Endpoint")
    print("=" * 60)

    # Get database session
    db: Session = next(get_db())

    try:
        # Get the first tenant and user
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

        # Prepare the request
        url = "http://localhost:8000/second-hand/products"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Tenant-ID": str(tenant.id),
        }

        # Test product data
        data = {
            "name": "HTTP Test Auto-Publish Product",
            "description": "This should automatically publish if verified",
            "price": 35.99,
            "condition": "like_new",
            "original_sku": "1234",  # SKU that exists in Shopify
            "size": "L",
        }

        print(f"🔄 Sending HTTP POST request to create product...")
        print(f"   URL: {url}")
        print(f"   Data: {data}")

        # Make the request
        response = requests.post(url, headers=headers, data=data)

        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            product_data = response.json()
            print(f"✅ Product created successfully via HTTP:")
            print(f"   - Product ID: {product_data.get('id')}")
            print(f"   - Name: {product_data.get('name')}")
            print(f"   - Is Verified: {product_data.get('is_verified')}")
            print(f"   - Is Approved: {product_data.get('is_approved')}")
            print(f"   - Shopify Product ID: {product_data.get('shopify_product_id')}")

            if product_data.get("is_verified"):
                if product_data.get("is_approved"):
                    print(f"✅ Product was automatically approved!")
                    if product_data.get("shopify_product_id"):
                        print(f"✅ Product was automatically published to Shopify!")
                    else:
                        print(f"⚠️ Product was approved but no Shopify product ID found")
                else:
                    print(
                        f"❌ Product was NOT automatically approved despite being verified"
                    )
            else:
                print(f"❌ Product was NOT verified")
        else:
            print(f"❌ HTTP request failed:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_http_auto_publish()
