# app/config/shopify_config.py
import os
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class ShopifySettings(BaseSettings):
    """Shopify API configuration settings"""

    shopify_app_url: str = os.getenv("SHOPIFY_APP_URL", "")
    shopify_api_key: str = os.getenv("SHOPIFY_API_KEY", "")
    shopify_api_secret: str = os.getenv("SHOPIFY_API_SECRET", "")
    shopify_webhook_secret: str = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")
    shopify_scopes: str = os.getenv(
        "SHOPIFY_SCOPES", "read_products,write_products,read_inventory,write_inventory"
    )
    shopify_api_version: str = os.getenv("SHOPIFY_API_VERSION", "2024-01")

    model_config = ConfigDict(
        env_file=".env", extra="ignore"  # Allow extra fields but ignore them
    )


shopify_settings = ShopifySettings()
