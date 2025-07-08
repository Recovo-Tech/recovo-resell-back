#!/usr/bin/env python3
"""
Test script to verify improved error handling in second-hand routes
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


def test_error_responses():
    """Test that routes return proper structured error responses"""

    print("🚨 Testing Improved Error Handling in Second-Hand Routes")
    print("=" * 70)

    base_url = "http://localhost:8000"

    # Get database session to get real tenant
    db: Session = next(get_db())

    try:
        tenant = db.query(Tenant).first()
        if not tenant:
            print("❌ No tenant found - cannot test")
            return

        print(f"📋 Using tenant: {tenant.shopify_app_url}")

        # Test 1: Verify product with invalid tenant (no headers)
        print("\n🧪 Test 1: Product verification without tenant header")
        response = requests.post(
            f"{base_url}/second-hand/verify-product", json={"sku": "1234"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"   Error Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Error Text: {response.text}")

        # Test 2: Verify product with invalid SKU
        print("\n🧪 Test 2: Product verification with non-existent SKU")
        headers = {"X-Tenant-ID": str(tenant.id)}
        response = requests.post(
            f"{base_url}/second-hand/verify-product",
            headers=headers,
            json={"sku": "NONEXISTENT12345"},
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Verification Result: is_verified={result.get('is_verified')}")
            if not result.get("is_verified"):
                print(f"   Error: {result.get('error')}")
        else:
            try:
                error_data = response.json()
                print(f"   Error Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Error Text: {response.text}")

        # Test 3: Get non-existent product
        print("\n🧪 Test 3: Get non-existent product")
        response = requests.get(
            f"{base_url}/second-hand/products/99999", headers=headers
        )
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"   Error Response: {json.dumps(error_data, indent=2)}")

                # Check if it has proper error structure
                if isinstance(error_data.get("detail"), dict):
                    detail = error_data["detail"]
                    if all(
                        key in detail for key in ["message", "error_code", "success"]
                    ):
                        print("   ✅ Proper structured error response!")
                    else:
                        print("   ⚠️ Error response missing some fields")
                else:
                    print("   ⚠️ Error response not properly structured")
            except:
                print(f"   Error Text: {response.text}")

        # Test 4: Create product without authentication
        print("\n🧪 Test 4: Create product without authentication")
        response = requests.post(
            f"{base_url}/second-hand/products",
            headers={"X-Tenant-ID": str(tenant.id)},
            data={
                "name": "Test Product",
                "description": "Test",
                "price": 10.0,
                "condition": "good",
                "original_sku": "TEST123",
            },
        )
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"   Error Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Error Text: {response.text}")

        # Test 5: Create product with invalid condition
        print("\n🧪 Test 5: Create product with invalid condition")
        response = requests.post(
            f"{base_url}/second-hand/products",
            headers={"X-Tenant-ID": str(tenant.id)},
            data={
                "name": "Test Product",
                "description": "Test",
                "price": 10.0,
                "condition": "invalid_condition",  # This should fail
                "original_sku": "TEST123",
            },
        )
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"   Error Response: {json.dumps(error_data, indent=2)}")

                # Check if it has proper error structure
                if isinstance(error_data.get("detail"), dict):
                    detail = error_data["detail"]
                    if all(
                        key in detail for key in ["message", "error_code", "success"]
                    ):
                        print("   ✅ Proper structured error response!")
                    else:
                        print("   ⚠️ Error response missing some fields")
                else:
                    print("   ⚠️ Error response not properly structured")
            except:
                print(f"   Error Text: {response.text}")

        print("\n📊 Error handling tests completed!")
        print("✅ Routes should now return structured error responses with:")
        print("   - message: Human-readable error description")
        print("   - error: Technical error details")
        print("   - error_code: Machine-readable error code")
        print("   - success: Boolean success flag")

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
    test_error_responses()
