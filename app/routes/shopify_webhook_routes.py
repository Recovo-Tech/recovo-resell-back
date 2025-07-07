# app/routes/shopify_webhook_routes.py
import hashlib
import hmac
import json
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.config.db_config import get_db
from app.config.shopify_config import shopify_settings
from app.models.product import SecondHandProduct


router = APIRouter(prefix="/webhooks/shopify", tags=["Shopify Webhooks"])


def verify_webhook_signature(data: bytes, signature: str) -> bool:
    """Verify Shopify webhook signature"""
    if not signature:
        return False

    # Remove 'sha256=' prefix if present
    if signature.startswith("sha256="):
        signature = signature[7:]

    # Calculate expected signature
    expected_signature = hmac.new(
        shopify_settings.shopify_webhook_secret.encode("utf-8"), data, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


@router.post("/products/update")
async def handle_product_update(request: Request, db: Session = Depends(get_db)):
    """Handle Shopify product update webhook"""
    # Get raw body and signature
    body = await request.body()
    signature = request.headers.get("X-Shopify-Hmac-Sha256", "")

    # Verify webhook signature
    if not verify_webhook_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="error.Invalid webhook signature"
        )

    try:
        # Parse webhook payload
        payload = json.loads(body.decode("utf-8"))

        # Extract product information
        product_id = f"gid://shopify/Product/{payload.get('id')}"
        product_status = payload.get("status", "")
        variants = payload.get("variants", [])

        # Update related second-hand products if product becomes inactive
        if product_status == "draft" or product_status == "archived":
            # Find second-hand products that reference this Shopify product
            second_hand_products = (
                db.query(SecondHandProduct)
                .filter(SecondHandProduct.shopify_product_id == product_id)
                .all()
            )

            # Mark them as not verified and not approved
            for sh_product in second_hand_products:
                sh_product.is_verified = False
                sh_product.is_approved = False

            db.commit()

            return {
                "message": f"Updated {len(second_hand_products)} second-hand products"
            }

        # Check for SKU/barcode changes
        for variant in variants:
            variant_sku = variant.get("sku", "")
            variant_barcode = variant.get("barcode", "")

            # Find second-hand products with matching SKU or barcode
            sku_products = (
                db.query(SecondHandProduct)
                .filter(SecondHandProduct.original_sku == variant_sku)
                .all()
                if variant_sku
                else []
            )

            barcode_products = (
                db.query(SecondHandProduct)
                .filter(SecondHandProduct.barcode == variant_barcode)
                .all()
                if variant_barcode
                else []
            )

            # Update verification status
            all_products = sku_products + barcode_products
            for sh_product in all_products:
                sh_product.shopify_product_id = product_id
                if product_status == "active":
                    sh_product.is_verified = True
                else:
                    sh_product.is_verified = False
                    sh_product.is_approved = False

            db.commit()

        return {"message": "Product update processed successfully"}

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="error.invalid_json_payload"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"error.Error processing webhook: {str(e)}",
        )


@router.post("/products/delete")
async def handle_product_delete(request: Request, db: Session = Depends(get_db)):
    """Handle Shopify product deletion webhook"""
    # Get raw body and signature
    body = await request.body()
    signature = request.headers.get("X-Shopify-Hmac-Sha256", "")

    # Verify webhook signature
    if not verify_webhook_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="error.Invalid webhook signature"
        )

    try:
        # Parse webhook payload
        payload = json.loads(body.decode("utf-8"))

        # Extract product information
        product_id = f"gid://shopify/Product/{payload.get('id')}"

        # Find and update related second-hand products
        second_hand_products = (
            db.query(SecondHandProduct)
            .filter(SecondHandProduct.shopify_product_id == product_id)
            .all()
        )

        # Mark them as not verified and not approved
        for sh_product in second_hand_products:
            sh_product.is_verified = False
            sh_product.is_approved = False
            sh_product.shopify_product_id = None

        db.commit()

        return {
            "message": f"Updated {len(second_hand_products)} second-hand products after product deletion"
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="error.invalid_json_payload"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"error.Error processing webhook: {str(e)}",
        )
