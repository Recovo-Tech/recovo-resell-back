"""
Script to check second-hand products and their Shopify publishing status
"""

import os
import sys

import psycopg2

# Database connection parameters
db_user = os.getenv("DATABASE_USERNAME", "postgres")
db_password = os.getenv("DATABASE_PASSWORD")
db_host = os.getenv("DATABASE_HOSTNAME", "localhost")
db_port = os.getenv("DATABASE_PORT", "5432")
db_name = os.getenv("DATABASE_NAME", "recovo")


def check_product_status():
    """Check second-hand products and their Shopify status"""
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
        )

        cursor = conn.cursor()

        # Get recent second-hand products
        cursor.execute(
            """
            SELECT 
                shp.id,
                shp.name,
                shp.is_verified,
                shp.is_approved,
                shp.shopify_product_id,
                shp.created_at,
                t.name as tenant_name,
                t.shopify_app_url,
                CASE WHEN t.shopify_access_token IS NOT NULL THEN 'Has Token' ELSE 'No Token' END as token_status
            FROM second_hand_products shp
            LEFT JOIN tenants t ON shp.tenant_id = t.id
            ORDER BY shp.created_at DESC
            LIMIT 10;
        """
        )

        products = cursor.fetchall()
        print("Recent second-hand products:")
        print("-" * 120)
        print(
            f"{'ID':<5} {'Name':<20} {'Verified':<10} {'Approved':<10} {'Shopify ID':<15} {'Tenant':<15} {'Shop URL':<25} {'Token':<10}"
        )
        print("-" * 120)

        for product in products:
            print(
                f"{product[0]:<5} {product[1][:19]:<20} {product[2]:<10} {product[3]:<10} {product[4] or 'None':<15} {product[6][:14]:<15} {product[7] or 'None':<25} {product[8]:<10}"
            )

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error checking product status: {e}")


if __name__ == "__main__":
    check_product_status()
