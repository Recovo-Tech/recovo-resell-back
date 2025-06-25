# app/models/product.py

from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.db_config import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)


class SecondHandProduct(Base):
    __tablename__ = "second_hand_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    condition = Column(String(20), nullable=False)  # new, like_new, good, fair, poor
    original_sku = Column(
        String(100), nullable=False, index=True
    )  # Original product SKU from store
    barcode = Column(String(100), nullable=True, index=True)  # Product barcode
    shopify_product_id = Column(
        String(50), nullable=True
    )  # Shopify product ID for verification
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_verified = Column(
        Boolean, default=False
    )  # Whether the product SKU/barcode is verified
    is_approved = Column(
        Boolean, default=False
    )  # Whether the product is approved for sale
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    seller = relationship("User", back_populates="second_hand_products")
    images = relationship(
        "SecondHandProductImage", back_populates="product", cascade="all, delete-orphan"
    )


class SecondHandProductImage(Base):
    __tablename__ = "second_hand_product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("second_hand_products.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("SecondHandProduct", back_populates="images")
