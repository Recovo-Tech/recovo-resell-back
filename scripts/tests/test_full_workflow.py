"""
Script to create a test second-hand product and approve it
"""

import asyncio
import os
import sys
import uuid

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.config.db_config import SessionLocal
from app.services.second_hand_product_service import SecondHandProductService


async def test_full_workflow():
    """Test creating and approving a second-hand product"""
    try:
        # Get database session
        db = SessionLocal()
        service = SecondHandProductService(db)

        # Get the default tenant
        from app.models.tenant import Tenant

        tenant = db.query(Tenant).first()

        if not tenant:
            print("No tenant found")
            return

        print(f"Using tenant: {tenant.name}")

        # Create a test user (for testing only)
        from app.models.user import User

        test_user = db.query(User).first()

        if not test_user:
            print("No user found")
            return

        print(f"Using user: {test_user.username}")

        # Create a test second-hand product using existing SKU
        print("\\nCreating test second-hand product...")
        product_data = await service.create_second_hand_product(
            user_id=test_user.id,
            tenant_id=tenant.id,
            name="Another Test Camiseta (Different Condition)",
            description="This is another test listing of the same product in different condition",
            price=15.99,
            condition="fair",
            original_sku="1234",  # Use existing SKU that we know works
            barcode=None,
            shop_domain=tenant.shopify_app_url,
            shopify_access_token=tenant.shopify_access_token,
        )

        if not product_data["success"]:
            print(f"Failed to create product: {product_data.get('error')}")
            return

        product = product_data["product"]
        print(f"✅ Created product: {product.name} (ID: {product.id})")
        print(f"   Verified: {product.is_verified}")
        print(f"   Approved: {product.is_approved}")

        # Approve the product
        print("\\nApproving product...")
        approved_product = await service.approve_product(product.id, tenant.id)

        if approved_product:
            print(f"✅ Product approved!")
            print(f"   Shopify ID: {approved_product.shopify_product_id}")

            if approved_product.shopify_product_id:
                print(
                    "\\n🚀 Check your Shopify dashboard - the new second-hand product should be visible!"
                )
            else:
                print("❌ Product approved but not published to Shopify")
        else:
            print("❌ Failed to approve product")

        db.close()

    except Exception as e:
        print(f"Error in test workflow: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_full_workflow())
