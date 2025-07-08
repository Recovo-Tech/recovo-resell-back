#!/usr/bin/env python3
"""
Test script to verify that color information is returned in product verification
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.models.tenant import Tenant
from app.services.shopify_service import ShopifyProductVerificationService


async def test_color_verification():
    """Test that color information is returned in product verification"""

    print("🎨 Testing Color Information in Product Verification")
    print("=" * 60)

    # Get database session
    db: Session = next(get_db())

    try:
        # Get the first tenant
        tenant = db.query(Tenant).first()

        if not tenant:
            print("❌ No tenant found in database")
            return

        print(f"📋 Using tenant: {tenant.shopify_app_url}")

        # Create verification service
        verification_service = ShopifyProductVerificationService(
            tenant.shopify_app_url, tenant.shopify_access_token
        )

        # Test with SKU we know exists
        test_sku = "1234"

        print(f"🔍 Testing verification for SKU: {test_sku}")

        # Verify the product
        result = await verification_service.verify_product_eligibility(sku=test_sku)

        if result["is_verified"]:
            product_info = result["product_info"]
            print("✅ Product verification successful!")
            print(f"   📋 Product: {product_info.get('title')}")
            print(f"   🏷️ Product Type: {product_info.get('productType')}")
            print(f"   🏢 Vendor: {product_info.get('vendor')}")

            # Check for color information
            colors = product_info.get("colors", [])
            available_colors = product_info.get("available_colors", [])

            print(f"   🎨 Colors found: {colors}")
            print(f"   🎨 Available colors: {available_colors}")

            if colors or available_colors:
                print("✅ Color information successfully retrieved!")
            else:
                print("ℹ️ No color information found for this product")

            # Show variant information with colors
            variants = product_info.get("variants", [])
            if variants:
                print(f"   📦 Variants ({len(variants)}):")
                for i, variant in enumerate(variants):
                    selected_options = variant.get("selectedOptions", [])
                    color_options = [
                        opt
                        for opt in selected_options
                        if "color" in opt.get("name", "").lower()
                    ]

                    print(f"     - Variant {i+1}: SKU {variant.get('sku')}")
                    if color_options:
                        for color_opt in color_options:
                            print(
                                f"       🎨 {color_opt.get('name')}: {color_opt.get('value')}"
                            )
                    else:
                        print(f"       ℹ️ No color options for this variant")

        else:
            print(f"❌ Product verification failed: {result.get('error')}")

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_color_verification())
