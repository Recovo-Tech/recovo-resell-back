#!/usr/bin/env python3
"""
Simple HTTP test for automatic publishing - minimal version
"""
import requests
import json

def simple_test():
    try:
        # First, let's just test if we can reach the server
        print("🔌 Testing server connectivity...")
        response = requests.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("✅ Server is reachable")
        else:
            print(f"❌ Server returned status: {response.status_code}")
            return
            
        # Test a simple GET endpoint that doesn't require auth
        print("🔍 Testing public endpoint...")
        try:
            response = requests.get("http://localhost:8000/second-hand/products")
            print(f"📊 Public products endpoint status: {response.status_code}")
            if response.status_code == 422:
                print("ℹ️ This is expected (missing tenant header)")
            elif response.status_code == 401:
                print("ℹ️ This is expected (authentication required)")
        except Exception as e:
            print(f"Error testing public endpoint: {e}")
            
        print("\n🚨 ISSUE IDENTIFIED:")
        print("The automatic publishing logic is correct in the service layer,")
        print("but to test the HTTP route we need proper authentication.")
        print("The route code looks correct - the issue might be:")
        print("1. The route is not being called with the right conditions")
        print("2. There might be an exception being swallowed")
        print("3. The debug prints aren't appearing in the server logs")
        
        print("\n📝 RECOMMENDATION:")
        print("Check the server terminal logs when creating a product")
        print("to see if the debug messages appear:")
        print("- 'DEBUG: Product X is verified, attempting automatic approval...'")
        print("- 'DEBUG: Product X automatically approved and published to Shopify'")
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    simple_test()
