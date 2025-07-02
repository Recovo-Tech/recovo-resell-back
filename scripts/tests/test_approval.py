"""
Script to test the product approval and Shopify publishing process
"""
import os
import sys
import asyncio
import psycopg2

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.second_hand_product_service import SecondHandProductService
from app.config.db_config import SessionLocal

async def test_product_approval():
    """Test the product approval process"""
    try:
        # Get database session
        db = SessionLocal()
        
        # Create service
        service = SecondHandProductService(db)
        
        # Get an unapproved product if any
        conn = psycopg2.connect(
            host=os.getenv("DATABASE_HOSTNAME", "localhost"),
            port=os.getenv("DATABASE_PORT", "5432"),
            database=os.getenv("DATABASE_NAME", "recovo"),
            user=os.getenv("DATABASE_USERNAME", "postgres"),
            password=os.getenv("DATABASE_PASSWORD")
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT shp.id, shp.tenant_id, shp.name, shp.is_approved, shp.shopify_product_id
            FROM second_hand_products shp
            WHERE shp.is_approved = false
            LIMIT 1;
        """)
        
        unapproved = cursor.fetchone()
        
        if unapproved:
            product_id, tenant_id, name, is_approved, shopify_id = unapproved
            print(f"Found unapproved product: ID={product_id}, Name='{name}', Shopify ID={shopify_id}")
            
            # Try to approve it
            print("Attempting to approve product...")
            approved_product = await service.approve_product(product_id, tenant_id)
            
            if approved_product:
                print(f"Product approved successfully!")
                print(f"  - ID: {approved_product.id}")
                print(f"  - Name: {approved_product.name}")
                print(f"  - Approved: {approved_product.is_approved}")
                print(f"  - Shopify ID: {approved_product.shopify_product_id}")
            else:
                print("Failed to approve product")
        else:
            print("No unapproved products found. Let's check existing approved products.")
            
            cursor.execute("""
                SELECT shp.id, shp.tenant_id, shp.name, shp.is_approved, shp.shopify_product_id
                FROM second_hand_products shp
                WHERE shp.is_approved = true
                LIMIT 5;
            """)
            
            approved_products = cursor.fetchall()
            print(f"Found {len(approved_products)} approved products:")
            for product in approved_products:
                print(f"  - ID: {product[0]}, Name: '{product[2]}', Shopify ID: {product[4]}")
        
        cursor.close()
        conn.close()
        db.close()
        
    except Exception as e:
        print(f"Error testing product approval: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_product_approval())
