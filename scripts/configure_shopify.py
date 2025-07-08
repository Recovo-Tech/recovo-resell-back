"""
Script to configure Shopify settings for the default tenant
"""

import os
import sys

import psycopg2
from psycopg2 import sql

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

# Database connection parameters
db_user = os.getenv("DATABASE_USERNAME", "postgres")
db_password = os.getenv("DATABASE_PASSWORD")
db_host = os.getenv("DATABASE_HOSTNAME", "localhost")
db_port = os.getenv("DATABASE_PORT", "5432")
db_name = os.getenv("DATABASE_NAME", "recovo")


def configure_default_tenant_shopify():
    """Configure Shopify settings for the default tenant"""
    try:
        # Get Shopify config from environment
        shopify_app_url = os.getenv("SHOPIFY_APP_URL", "recovodev.myshopify.com")
        shopify_api_key = os.getenv("SHOPIFY_API_KEY")
        shopify_api_secret = os.getenv("SHOPIFY_API_SECRET")
        shopify_access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
        shopify_webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")
        shopify_scopes = os.getenv("SHOPIFY_SCOPES", "read_products,read_inventory")
        shopify_api_version = os.getenv("SHOPIFY_API_VERSION", "2023-10")

        # Connect to the database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
        )

        cursor = conn.cursor()

        # Update the default tenant with Shopify configuration
        cursor.execute(
            """
            UPDATE tenants 
            SET shopify_app_url = %s,
                shopify_api_key = %s,
                shopify_api_secret = %s,
                shopify_access_token = %s,
                shopify_webhook_secret = %s,
                shopify_scopes = %s,
                shopify_api_version = %s,
                updated_at = now()
            WHERE subdomain = 'default'
        """,
            (
                shopify_app_url,
                shopify_api_key,
                shopify_api_secret,
                shopify_access_token,
                shopify_webhook_secret,
                shopify_scopes,
                shopify_api_version,
            ),
        )

        if cursor.rowcount > 0:
            conn.commit()
            print(f"✅ Successfully updated default tenant with Shopify configuration:")
            print(f"   - App URL: {shopify_app_url}")
            print(f"   - API Version: {shopify_api_version}")
            print(f"   - Scopes: {shopify_scopes}")
            print(
                f"   - Access Token: {'***' + shopify_access_token[-4:] if shopify_access_token else 'Not set'}"
            )
        else:
            print("❌ No default tenant found to update")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error configuring Shopify settings: {e}")


if __name__ == "__main__":
    configure_default_tenant_shopify()
