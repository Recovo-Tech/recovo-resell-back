#!/usr/bin/env python3
"""
Simple test to debug automatic publishing issue
"""
import os
import sys
import asyncio
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.second_hand_product_service import SecondHandProductService
from app.config.db_config import get_db
from app.models.tenant import Tenant
from app.models.user import User
from sqlalchemy.orm import Session

async def test_auto_publish_debug():
    """Debug the automatic publishing issue"""
    
    print("🔍 Debugging Automatic Publishing Issue")
    print("=" * 50)
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        # Get the first tenant and user
        tenant = db.query(Tenant).first()
        user = db.query(User).first()
        
        print(f"📋 Tenant: {tenant.shopify_app_url}")
        print(f"👤 User: {user.email}")
        
        # Create service
        service = SecondHandProductService(db)
        
        # Create a verified product
        print("🔄 Step 1: Creating product...")
        result = await service.create_second_hand_product(
            user_id=user.id,
            tenant_id=tenant.id,
            name="Debug Auto-Publish Test",
            description="Testing automatic publishing",
            price=19.99,
            condition="like_new",
            original_sku="1234",
            size="M",
            shop_domain=tenant.shopify_app_url,
            shopify_access_token=tenant.shopify_access_token,
        )
        
        if result["success"]:
            product = result["product"]
            print(f"✅ Product created:")
            print(f"   - ID: {product.id}")
            print(f"   - Verified: {product.is_verified}")
            print(f"   - Approved: {product.is_approved}")
            
            # If verified but not approved, manually test approval
            if product.is_verified and not product.is_approved:
                print("🔄 Step 2: Manually testing approval (simulating what route should do)...")
                approval_result = await service.approve_product(product.id, tenant.id)
                
                print(f"📊 Approval result: {approval_result}")
                
                if approval_result["success"]:
                    # Refresh product
                    db.refresh(product)
                    print(f"✅ After approval:")
                    print(f"   - Approved: {product.is_approved}")
                    print(f"   - Shopify ID: {product.shopify_product_id}")
                else:
                    print(f"❌ Approval failed: {approval_result.get('error')}")
                    
        else:
            print(f"❌ Product creation failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_auto_publish_debug())
