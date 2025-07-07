#!/usr/bin/env python3
"""
Test script to verify collection assignment fix
"""
import os
import sys
import asyncio
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.shopify_service import ShopifyGraphQLClient
from app.config.db_config import get_db
from app.models.tenant import Tenant
from sqlalchemy.orm import Session

async def test_collection_assignment():
    """Test adding an existing product to the Second Hand collection"""
    
    print("🧪 Testing Collection Assignment Fix")
    print("=" * 50)
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        # Get the first tenant
        tenant = db.query(Tenant).first()
        if not tenant:
            print("❌ No tenant found in database")
            return
        
        print(f"📋 Using tenant: {tenant.shopify_app_url}")
        
        # Create Shopify client
        client = ShopifyGraphQLClient(
            shop_domain=tenant.shopify_app_url,
            access_token=tenant.shopify_access_token
        )
        
        # Test with an existing product ID
        product_id = "gid://shopify/Product/9695364153686"
        
        print(f"🔄 Testing collection assignment for product: {product_id}")
        
        # Import the service method we need
        from app.services.second_hand_product_service import SecondHandProductService
        service = SecondHandProductService(db)
        
        # Test adding product to collection
        success = await service._add_to_second_hand_collection(client, product_id)
        
        if success:
            print("✅ Collection assignment test passed!")
        else:
            print("❌ Collection assignment test failed!")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_collection_assignment())
