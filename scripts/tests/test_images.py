"""
Script to add images to a second-hand product and test Shopify image upload
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


async def test_images_upload():
    """Test adding images to a product and uploading to Shopify"""
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

        # Find a product without images (one of our test products)
        product = (
            db.query(SecondHandProduct)
            .filter(
                SecondHandProduct.id
                >= 3  # Products 3+ are our test products without images
            )
            .first()
        )

        if not product:
            print("No test product found")
            return

        print(f"Testing with product: {product.name} (ID: {product.id})")

        # Check current images
        current_images = (
            db.query(SecondHandProductImage)
            .filter(SecondHandProductImage.product_id == product.id)
            .all()
        )
        print(f"Current images: {len(current_images)}")

        # Add some test images (using the same working URLs from camiseta de pana)
        test_image_urls = [
            "https://cdn.shopify.com/s/files/1/0922/7750/6390/files/Sintitulo32.jpg?v=1749647251",
            "https://recovo-resell.s3.eu-north-1.amazonaws.com/second_hand_products/recovodev/1153f7c3-1e82-4728-9d11-d44937482fdf7/d1a0ba0e-9241-44cb-9d02-71f4b699e833.png",
            "https://recovo-resell.s3.eu-north-1.amazonaws.com/second_hand_products/recovodev/1153f7c3-1e82-4728-9d11-d44937482fdf7/24f3f0db-01f8-44a3-859d-15cce37df2b1.jpg",
        ]

        # Add images to the product
        print(f"\\nAdding {len(test_image_urls)} test images...")
        for i, img_url in enumerate(test_image_urls):
            image = SecondHandProductImage(
                product_id=product.id, image_url=img_url, is_primary=(i == 0)
            )
            db.add(image)

        db.commit()
        print("✅ Images added to product")

        # Verify images were added
        updated_images = (
            db.query(SecondHandProductImage)
            .filter(SecondHandProductImage.product_id == product.id)
            .all()
        )
        print(f"Updated images count: {len(updated_images)}")
        for img in updated_images:
            print(f"  - {img.image_url}")

        # Now re-approve the product to trigger Shopify upload
        print("\\nRe-approving product to trigger Shopify upload...")

        # First mark as not approved
        product.is_approved = False
        product.shopify_product_id = None  # Clear previous Shopify ID
        db.commit()

        # Now approve it again
        approved_product = await service.approve_product(product.id, tenant.id)

        if approved_product and approved_product.shopify_product_id:
            print(f"✅ Product re-approved and published to Shopify!")
            print(f"   Shopify ID: {approved_product.shopify_product_id}")
            print(
                "\\n🚀 Check your Shopify dashboard - the product should now have images!"
            )
        else:
            print("❌ Failed to re-approve or publish product")

        db.close()

    except Exception as e:
        print(f"Error testing images: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_images_upload())
