#!/usr/bin/env python3
"""
Script to verify images in an existing Shopify product after some processing time
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.shopify_service import ShopifyGraphQLClient
from sqlalchemy.orm import sessionmaker
from app.config.db_config import engine
from app.models.tenant import Tenant

async def check_shopify_images():
    """Check if images are now visible in the last created product"""
    
    # The product ID from our last test
    product_id = "gid://shopify/Product/9687241556310"
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        tenant = db.query(Tenant).first()
        if not tenant:
            print("❌ No tenant found")
            return
        
        client = ShopifyGraphQLClient(tenant.shopify_app_url, tenant.shopify_access_token)
        
        verification_query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                images(first: 10) {
                    edges {
                        node {
                            id
                            src
                            altText
                            width
                            height
                        }
                    }
                }
                media(first: 10) {
                    edges {
                        node {
                            ... on MediaImage {
                                id
                                image {
                                    src
                                    altText
                                    width
                                    height
                                }
                                status
                            }
                        }
                    }
                }
            }
        }
        """
        
        print(f"🔍 Checking product {product_id} for images...")
        result = await client.execute_query(verification_query, {"id": product_id})
        
        if result and "data" in result and result["data"]["product"]:
            product_data = result["data"]["product"]
            
            # Check images
            images = product_data.get("images", {}).get("edges", [])
            print(f"📸 Images field: {len(images)} images found")
            for i, img_edge in enumerate(images):
                img = img_edge["node"]
                print(f"   {i+1}. {img.get('src', 'No src')} - {img.get('altText', 'No alt')}")
            
            # Check media (more detailed)
            media = product_data.get("media", {}).get("edges", [])
            print(f"🎬 Media field: {len(media)} media items found")
            for i, media_edge in enumerate(media):
                media_item = media_edge["node"]
                if "image" in media_item:
                    img_data = media_item.get("image")
                    status = media_item.get("status", "unknown")
                    print(f"   {i+1}. Status: {status}")
                    if img_data:
                        print(f"      Image: {img_data.get('src', 'No src')} - {img_data.get('altText', 'No alt')}")
                    else:
                        print(f"      Image: Still processing (null)")
                        
            # Summary
            if len(images) > 0:
                print("✅ SUCCESS! Images are now visible")
            elif len(media) > 0:
                print("⏳ Images uploaded but still processing")
            else:
                print("❌ No images or media found")
                
        else:
            print("❌ Product not found or API error")
            print(f"Response: {result}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(check_shopify_images())
