"""
Script to create a fresh test product with unique images
"""

import asyncio
import os
import sys
import uuid

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.config.db_config import SessionLocal
from app.models.product import SecondHandProduct, SecondHandProductImage
from app.services.second_hand_product_service import SecondHandProductService


async def test_clean_product_with_images():
    """Create a fresh product and test single image upload"""
    try:
        # Get database session
        db = SessionLocal()
        service = SecondHandProductService(db)

        # Get the default tenant and user
        from app.models.tenant import Tenant
        from app.models.user import User

        tenant = db.query(Tenant).first()
        test_user = db.query(User).first()

        if not tenant or not test_user:
            print("No tenant or user found")
            return

        print(f"Using tenant: {tenant.name}")
        print(f"Using user: {test_user.username}")

        # Create a fresh second-hand product using existing SKU
        print("\\nCreating fresh test product...")
        product_data = await service.create_second_hand_product(
            user_id=test_user.id,
            tenant_id=tenant.id,
            name="Clean Test Product - No Duplicates",
            description="This is a clean test to verify single image upload",
            price=25.99,
            condition="good",
            original_sku="1234",  # Use existing SKU
            barcode=None,
            shop_domain=tenant.shopify_app_url,
            shopify_access_token=tenant.shopify_access_token,
        )

        if not product_data["success"]:
            print(f"Failed to create product: {product_data.get('error')}")
            return

        product = product_data["product"]
        print(f"✅ Created product: {product.name} (ID: {product.id})")

        # Add 3 unique test images (using different working URLs)
        unique_image_urls = [
            "https://cdn.shopify.com/s/files/1/0922/7750/6390/files/Sintitulo32.jpg?v=1749647251",  # Shopify CDN
            "https://recovo-resell.s3.eu-north-1.amazonaws.com/second_hand_products/recovodev/1153f7c3-1e82-4728-9d11-d44937482fdf7/d1a0ba0e-9241-44cb-9d02-71f4b699e833.png",  # S3 PNG
            "https://recovo-resell.s3.eu-north-1.amazonaws.com/second_hand_products/recovodev/1153f7c3-1e82-4728-9d11-d44937482fdf7/24f3f0db-01f8-44a3-859d-15cce37df2b1.jpg",  # S3 JPG
        ]

        print(f"\\nAdding {len(unique_image_urls)} unique images...")
        for i, img_url in enumerate(unique_image_urls):
            image = SecondHandProductImage(
                product_id=product.id, image_url=img_url, is_primary=(i == 0)
            )
            db.add(image)
            print(f"  Added image {i+1}: {img_url}")

        db.commit()
        print("✅ Unique images added to product")

        # Approve the product
        print("\\nApproving product to trigger Shopify upload...")
        approved_product = await service.approve_product(product.id, tenant.id)

        if approved_product and approved_product.shopify_product_id:
            print(f"✅ Product approved and published to Shopify!")
            print(f"   Shopify ID: {approved_product.shopify_product_id}")
            print(
                "\\n🚀 Check your Shopify dashboard - this product should have exactly 3 unique images!"
            )
        else:
            print("❌ Failed to approve or publish product")

        db.close()

    except Exception as e:
        print(f"Error in clean test: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_clean_product_with_images())
