#!/usr/bin/env python3

import os
import sys
import requests
import json
from uuid import uuid4

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_tenant_name_registration():
    """Test the new tenant-name-based registration"""

    base_url = "http://localhost:8000"

    print("🧪 Testing Tenant Name Registration")
    print("=" * 40)

    # Step 1: Test with tenant name "default"
    test_username = f"testuser_{uuid4().hex[:8]}"
    test_email = f"{test_username}@example.com"
    test_password = "testpass123"
    tenant_name = "Default Tenant"  # Use actual tenant name

    register_data = {
        "username": test_username,
        "email": test_email,
        "password": test_password,
        "password_confirmation": test_password,
        "tenant_name": tenant_name,  # Using tenant name instead of UUID!
        "name": "Test",
        "surname": "User",
    }

    try:
        print(f"🔧 Registering user: {test_username} with tenant: {tenant_name}")
        response = requests.post(f"{base_url}/auth/register", json=register_data)

        if response.status_code == 200:
            register_result = response.json()
            token = register_result["token"]["access_token"]
            user_id = register_result["user"]["id"]
            print(f"✅ Registration successful! User ID: {user_id}")
            print(f"🔑 Token obtained: {token[:20]}...")
            return True
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error during registration: {e}")
        return False


def test_invalid_tenant_name():
    """Test registration with invalid tenant name"""

    base_url = "http://localhost:8000"

    print("\n🧪 Testing Invalid Tenant Name")
    print("=" * 40)

    test_username = f"testuser_{uuid4().hex[:8]}"
    test_email = f"{test_username}@example.com"
    test_password = "testpass123"
    invalid_tenant_name = "nonexistent"

    register_data = {
        "username": test_username,
        "email": test_email,
        "password": test_password,
        "password_confirmation": test_password,
        "tenant_name": invalid_tenant_name,
        "name": "Test",
        "surname": "User",
    }

    try:
        print(f"🔧 Testing invalid tenant: {invalid_tenant_name}")
        response = requests.post(f"{base_url}/auth/register", json=register_data)

        if response.status_code == 400:
            error_result = response.json()
            print(f"✅ Correctly rejected invalid tenant!")
            print(f"📋 Error message: {error_result.get('detail', 'No detail')}")
            return True
        else:
            print(f"❌ Should have failed but got: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Starting Tenant Name Tests\n")

    success1 = test_tenant_name_registration()
    success2 = test_invalid_tenant_name()

    if success1 and success2:
        print("\n🎉 All tests passed! Tenant name registration is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)
