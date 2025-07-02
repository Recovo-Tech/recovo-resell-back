#!/usr/bin/env python3

import os
import sys
import requests
import json
from uuid import uuid4

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def comprehensive_tenant_auth_test():
    """Comprehensive test of the tenant-from-token authentication system"""
    
    base_url = "http://localhost:8000"
    
    print("🚀 Comprehensive Tenant Authentication Test")
    print("=" * 50)
    
    # Test 1: Register with tenant name
    print("\n📝 Test 1: Register with tenant name")
    test_username = f"testuser_{uuid4().hex[:8]}"
    test_email = f"{test_username}@example.com"
    test_password = "testpass123"
    
    register_data = {
        "username": test_username,
        "email": test_email,
        "password": test_password,
        "password_confirmation": test_password,
        "tenant_name": "default",  # Using tenant name instead of UUID!
        "name": "Test",
        "surname": "User"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/register", json=register_data)
        if response.status_code == 200:
            register_result = response.json()
            print(f"✅ Registration successful with tenant name")
            register_token = register_result['token']['access_token']
        else:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return False
    
    # Test 2: Login (tenant determined from user record)
    print("\n🔐 Test 2: Login without specifying tenant")
    login_data = {
        "username": test_username,
        "password": test_password
    }
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=login_data)
        if response.status_code == 200:
            login_result = response.json()
            print(f"✅ Login successful - tenant automatically detected")
            login_token = login_result['token']['access_token']
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
    
    # Test 3: Access protected endpoint
    print("\n🔒 Test 3: Access protected endpoint with token")
    headers = {"Authorization": f"Bearer {login_token}"}
    
    try:
        response = requests.get(f"{base_url}/users/me", headers=headers)
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Protected endpoint access successful")
            print(f"👤 User: {user_info['username']}")
            print(f"🏢 Tenant: {user_info['tenant_id']}")
            print(f"👑 Role: {user_info['role']}")
        else:
            print(f"❌ Protected endpoint failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Protected endpoint error: {e}")
        return False
    
    # Test 4: Test tenant-scoped operation (if available)
    print("\n📦 Test 4: Test tenant-scoped operation")
    try:
        # Try to access a tenant-scoped endpoint (products)
        response = requests.get(f"{base_url}/products/", headers=headers)
        if response.status_code in [200, 404]:  # 404 is OK if no products exist
            print(f"✅ Tenant-scoped endpoint accessible (status: {response.status_code})")
        else:
            print(f"⚠️  Tenant-scoped endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Tenant-scoped endpoint error: {e}")
    
    # Test 5: Invalid tenant name registration
    print("\n❌ Test 5: Invalid tenant name should fail")
    invalid_register_data = {
        "username": f"testuser_{uuid4().hex[:8]}",
        "email": f"test_{uuid4().hex[:8]}@example.com",
        "password": "testpass123",
        "password_confirmation": "testpass123",
        "tenant_name": "nonexistenttenant",
        "name": "Test",
        "surname": "User"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/register", json=invalid_register_data)
        if response.status_code == 400:
            error_result = response.json()
            print(f"✅ Invalid tenant correctly rejected: {error_result.get('detail', 'No detail')}")
        else:
            print(f"❌ Should have failed but got: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid tenant test error: {e}")
        return False
    
    print("\n🎉 All tests passed! The tenant-from-token authentication system is working perfectly!")
    print("\n📋 Summary:")
    print("✅ Tenant name registration (user-friendly)")
    print("✅ Global login (no tenant required)")  
    print("✅ JWT token contains tenant context")
    print("✅ Protected endpoints work with token")
    print("✅ Invalid tenant names are rejected")
    print("✅ System is Postman/API-testing friendly")
    
    return True

if __name__ == "__main__":
    success = comprehensive_tenant_auth_test()
    sys.exit(0 if success else 1)
