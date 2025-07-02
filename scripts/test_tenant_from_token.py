#!/usr/bin/env python3

import os
import sys
import requests
import json
from uuid import uuid4

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_tenant_from_token():
    """Test the new tenant-from-token authentication flow"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Tenant-from-Token Authentication Flow")
    print("=" * 50)
    
    # Step 1: Use default tenant name (much simpler!)
    tenant_name = "default"
    print(f"✅ Using tenant name: {tenant_name}")
    
    # Step 2: Register a test user with tenant_name
    test_username = f"testuser_{uuid4().hex[:8]}"
    test_email = f"{test_username}@example.com"
    test_password = "testpass123"
    
    register_data = {
        "username": test_username,
        "email": test_email,
        "password": test_password,
        "password_confirmation": test_password,
        "tenant_name": tenant_name,
        "name": "Test",
        "surname": "User"
    }
    
    try:
        print(f"🔧 Registering user: {test_username}")
        response = requests.post(f"{base_url}/auth/register", json=register_data)
        if response.status_code == 200:
            register_result = response.json()
            token = register_result['token']['access_token']
            user_id = register_result['user']['id']
            print(f"✅ Registration successful! User ID: {user_id}")
            print(f"🔑 Token obtained: {token[:20]}...")
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during registration: {e}")
        return False
    
    # Step 3: Test login with the new user
    login_data = {
        "username": test_username,
        "password": test_password
    }
    
    try:
        print(f"🔐 Testing login for: {test_username}")
        response = requests.post(f"{base_url}/auth/login", json=login_data)
        if response.status_code == 200:
            login_result = response.json()
            login_token = login_result['token']['access_token']
            print(f"✅ Login successful!")
            print(f"🔑 New token obtained: {login_token[:20]}...")
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return False
    
    # Step 4: Test accessing a protected endpoint with the token
    headers = {"Authorization": f"Bearer {login_token}"}
    
    try:
        print("🔒 Testing protected endpoint access...")
        response = requests.get(f"{base_url}/users/me", headers=headers)
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Protected endpoint access successful!")
            print(f"👤 User info: {user_info['username']} (tenant: {user_info.get('tenant_id', 'N/A')})")
        else:
            print(f"❌ Protected endpoint access failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error accessing protected endpoint: {e}")
        return False
    
    print("\n🎉 All tests passed! Tenant-from-token authentication is working correctly.")
    return True

if __name__ == "__main__":
    success = test_tenant_from_token()
    sys.exit(0 if success else 1)
