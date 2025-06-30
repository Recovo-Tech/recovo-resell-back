# app/services/second_hand_product_service.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.product import SecondHandProduct, SecondHandProductImage
from app.models.user import User
from app.services.shopify_service import ShopifyProductVerificationService, ShopifyGraphQLClient
from app.config.shopify_config import shopify_settings


class SecondHandProductService:
    """Service for managing second-hand products"""

    def __init__(self, db: Session):
        self.db = db

    async def create_second_hand_product(
        self,
        user_id: int,
        name: str,
        description: str,
        price: float,
        condition: str,
        original_sku: str,
        barcode: Optional[str] = None,
        shop_domain: str = None,
        shopify_access_token: str = None,
    ) -> Dict[str, Any]:
        """Create a new second-hand product listing"""

        # Verify the product against Shopify store
        if shop_domain and shopify_access_token:
            verification_service = ShopifyProductVerificationService(
                shop_domain, shopify_access_token
            )
            verification_result = await verification_service.verify_product_eligibility(
                sku=original_sku, barcode=barcode
            )

            if not verification_result["is_verified"]:
                return {
                    "success": False,
                    "error": verification_result.get(
                        "error", "Product verification failed"
                    ),
                }
        else:
            verification_result = {"is_verified": False}

        # Create the second-hand product
        second_hand_product = SecondHandProduct(
            name=name,
            description=description,
            price=price,
            condition=condition,
            original_sku=original_sku,
            barcode=barcode,
            seller_id=user_id,
            is_verified=verification_result["is_verified"],
            is_approved=False,  # Requires admin approval
            shopify_product_id=verification_result.get("product_info", {}).get(
                "shopify_id"
            ),
        )

        self.db.add(second_hand_product)
        self.db.commit()
        self.db.refresh(second_hand_product)

        return {
            "success": True,
            "product": second_hand_product,
            "verification_info": verification_result,
        }

    def get_user_products(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[SecondHandProduct]:
        """Get all second-hand products for a user"""
        return (
            self.db.query(SecondHandProduct)
            .filter(SecondHandProduct.seller_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_approved_products(
        self, skip: int = 0, limit: int = 100
    ) -> List[SecondHandProduct]:
        """Get all approved second-hand products for public listing"""
        return (
            self.db.query(SecondHandProduct)
            .filter(
                and_(
                    SecondHandProduct.is_approved == True,
                    SecondHandProduct.is_verified == True,
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_product_by_id(self, product_id: int) -> Optional[SecondHandProduct]:
        """Get a second-hand product by ID"""
        return (
            self.db.query(SecondHandProduct)
            .filter(SecondHandProduct.id == product_id)
            .first()
        )

    def update_product(
        self, product_id: int, user_id: int, update_data: Dict[str, Any]
    ) -> Optional[SecondHandProduct]:
        """Update a second-hand product (only by owner)"""
        product = (
            self.db.query(SecondHandProduct)
            .filter(
                and_(
                    SecondHandProduct.id == product_id,
                    SecondHandProduct.seller_id == user_id,
                )
            )
            .first()
        )

        if not product:
            return None

        for field, value in update_data.items():
            if hasattr(product, field) and field not in [
                "id",
                "seller_id",
                "created_at",
            ]:
                setattr(product, field, value)

        self.db.commit()
        self.db.refresh(product)
        return product

    def delete_product(self, product_id: int, user_id: int) -> bool:
        """Delete a second-hand product (only by owner)"""
        product = (
            self.db.query(SecondHandProduct)
            .filter(
                and_(
                    SecondHandProduct.id == product_id,
                    SecondHandProduct.seller_id == user_id,
                )
            )
            .first()
        )

        if not product:
            return False

        self.db.delete(product)
        self.db.commit()
        return True

    async def approve_product(self, product_id: int) -> Optional[SecondHandProduct]:
        """Approve a second-hand product for sale and publish to Shopify (admin only)"""
        product = (
            self.db.query(SecondHandProduct)
            .filter(SecondHandProduct.id == product_id)
            .first()
        )

        if not product:
            return None

        # Mark as approved
        product.is_approved = True
        
        # Try to publish to Shopify
        try:
            shopify_client = ShopifyGraphQLClient(
                shopify_settings.shopify_app_url, 
                shopify_settings.shopify_access_token
            )
            
            # Create product in Shopify
            shopify_product_id = await self._publish_to_shopify(shopify_client, product)
            
            if shopify_product_id:
                product.shopify_product_id = shopify_product_id
                
        except Exception as e:
            print(f"Warning: Failed to publish to Shopify: {str(e)}")
            # Continue with approval even if Shopify publish fails
        
        self.db.commit()
        self.db.refresh(product)
        return product

    async def _publish_to_shopify(self, client: ShopifyGraphQLClient, product: SecondHandProduct) -> Optional[str]:
        """Publish a second-hand product to Shopify store"""
        mutation = """
        mutation productCreate($input: ProductInput!) {
            productCreate(input: $input) {
                product {
                    id
                    title
                    handle
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        # Get product images
        images = [img.image_url for img in product.images] if product.images else []
        
        variables = {
            "input": {
                "title": f"{product.name} (Second-Hand)",
                "descriptionHtml": f"""
                    <p><strong>Condition:</strong> {product.condition.replace('_', ' ').title()}</p>
                    <p><strong>Original SKU:</strong> {product.original_sku}</p>
                    {f'<p><strong>Barcode:</strong> {product.barcode}</p>' if product.barcode else ''}
                    <p>{product.description if product.description else ''}</p>
                    <p><em>This is a second-hand item sold by our marketplace.</em></p>
                """,
                "vendor": "Second-Hand Marketplace",
                "productType": "Second-Hand",
                "tags": ["second-hand", product.condition, "marketplace"],
                "status": "ACTIVE",
                "variants": [
                    {
                        "price": str(product.price),
                        "inventoryManagement": "SHOPIFY",
                        "inventoryQuantity": 1,
                        "sku": f"SH-{product.id}-{product.original_sku}",
                        "barcode": product.barcode if product.barcode else None,
                        "weight": 0,
                        "weightUnit": "GRAMS"
                    }
                ],
                "images": [{"src": url} for url in images] if images else []
            }
        }
        
        try:
            result = await client.execute_query(mutation, variables)
            
            if result.get("data", {}).get("productCreate", {}).get("userErrors"):
                errors = result["data"]["productCreate"]["userErrors"]
                print(f"Shopify product creation errors: {errors}")
                return None
                
            shopify_product = result.get("data", {}).get("productCreate", {}).get("product")
            if shopify_product:
                return shopify_product["id"]
                
        except Exception as e:
            print(f"Error publishing to Shopify: {str(e)}")
            
        return None

    def add_product_images(
        self, product_id: int, image_urls: List[str]
    ) -> List[SecondHandProductImage]:
        """Add images to a second-hand product"""
        product = self.get_product_by_id(product_id)
        if not product:
            return []

        images = []
        for i, url in enumerate(image_urls):
            image = SecondHandProductImage(
                product_id=product_id,
                image_url=url,
                is_primary=(i == 0),  # First image is primary
            )
            self.db.add(image)
            images.append(image)

        self.db.commit()
        return images

    def search_products(
        self,
        query: str = None,
        condition: str = None,
        min_price: float = None,
        max_price: float = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SecondHandProduct]:
        """Search approved second-hand products with filters"""
        db_query = self.db.query(SecondHandProduct).filter(
            and_(
                SecondHandProduct.is_approved == True,
                SecondHandProduct.is_verified == True,
            )
        )

        if query:
            db_query = db_query.filter(SecondHandProduct.name.ilike(f"%{query}%"))

        if condition:
            db_query = db_query.filter(SecondHandProduct.condition == condition)

        if min_price is not None:
            db_query = db_query.filter(SecondHandProduct.price >= min_price)

        if max_price is not None:
            db_query = db_query.filter(SecondHandProduct.price <= max_price)

        return db_query.offset(skip).limit(limit).all()
