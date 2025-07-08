#!/usr/bin/env python3

import json

import requests


def test_exact_curl_command():
    """Test the exact same data as the user's curl command"""

    base_url = "http://localhost:8000"

    print("🧪 Testing Exact Curl Command Data")
    print("=" * 40)

    # Similar data to the user's curl command but with unique username/email
    from uuid import uuid4

    unique_id = uuid4().hex[:8]
    register_data = {
        "username": f"nachovaoss_{unique_id}",
        "email": f"nacho_{unique_id}@recovo.co",
        "name": "nacho",
        "surname": "bares",
        "password": "Recovo!",
        "password_confirmation": "Recovo!",
        "tenant_name": "Default Tenant",
    }

    try:
        print(f"🔧 Registering user with tenant: 'Default Tenant'")
        response = requests.post(f"{base_url}/auth/register", json=register_data)

        if response.status_code == 200:
            register_result = response.json()
            print(f"✅ Registration successful!")
            print(f"👤 User ID: {register_result['user']['id']}")
            print(f"🔑 Token: {register_result['token']['access_token'][:30]}...")
            return True
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"📋 Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error during registration: {e}")
        return False


if __name__ == "__main__":
    success = test_exact_curl_command()
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}")
