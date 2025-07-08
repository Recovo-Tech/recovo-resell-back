#!/usr/bin/env python3
"""
Test the HTTP verify product endpoint to ensure it returns color information
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


def test_verify_endpoint_with_color():
    """Test the HTTP verify endpoint to check color information"""

    print("🎨 Testing HTTP Verify Endpoint for Color Information")
    print("=" * 60)

    # Get database session
    db: Session = next(get_db())

    try:
        # Get the first tenant
        tenant = db.query(Tenant).first()

        if not tenant:
            print("❌ No tenant found in database")
            return

        print(f"📋 Using tenant: {tenant.shopify_app_url}")

        # Test the verify endpoint
        url = "http://localhost:8000/second-hand/verify-product"
        headers = {"Content-Type": "application/json", "X-Tenant-ID": str(tenant.id)}

        # Test data
        verify_data = {"sku": "1234"}

        print(f"🔍 Testing verification endpoint with SKU: {verify_data['sku']}")

        response = requests.post(url, headers=headers, json=verify_data)

        print(f"📊 Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Verification endpoint successful!")

            if result.get("is_verified"):
                product_info = result.get("product_info", {})
                print(f"   📋 Product: {product_info.get('title')}")
                print(f"   🏷️ Product Type: {product_info.get('productType')}")
                print(f"   🏢 Vendor: {product_info.get('vendor')}")

                # Check for color information
                colors = product_info.get("colors", [])
                available_colors = product_info.get("available_colors", [])

                print(f"   🎨 Colors found: {colors}")
                print(f"   🎨 Available colors: {available_colors}")

                if colors or available_colors:
                    print("✅ Color information successfully retrieved via HTTP!")
                else:
                    print(
                        "ℹ️ No color information found for this product (this is normal)"
                    )

                # Show variant information
                variants = product_info.get("variants", [])
                if variants:
                    print(f"   📦 Variants ({len(variants)}):")
                    for i, variant in enumerate(variants):
                        selected_options = variant.get("selectedOptions", [])
                        print(f"     - Variant {i+1}: SKU {variant.get('sku')}")
                        if selected_options:
                            for option in selected_options:
                                print(
                                    f"       🔹 {option.get('name')}: {option.get('value')}"
                                )
                        else:
                            print(f"       ℹ️ No options for this variant")
            else:
                print(f"❌ Product not verified: {result.get('error')}")

        else:
            print(f"❌ HTTP request failed: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Response text: {response.text}")

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
    test_verify_endpoint_with_color()
