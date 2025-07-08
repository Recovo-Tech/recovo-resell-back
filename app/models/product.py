# app/models/product.py

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.config.db_config import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    tenant = relationship("Tenant")


class SecondHandProduct(Base):
    __tablename__ = "second_hand_products"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    condition = Column(String(20), nullable=False)  # new, like_new, good, fair, poor
    original_sku = Column(String(100), nullable=False, index=True)
    barcode = Column(String(100), nullable=True, index=True)
    shopify_product_id = Column(String(50), nullable=True)
    weight = Column(Float, nullable=True)
    weight_unit = Column(String(20), nullable=True)
    size = Column(String(50), nullable=True)
    color = Column(String(50), nullable=True)
    return_address = Column(String(255), nullable=True)

    original_title = Column(String(200), nullable=True)
    original_description = Column(Text, nullable=True)
    original_product_type = Column(String(100), nullable=True)
    original_vendor = Column(String(100), nullable=True)

    seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_verified = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tenant = relationship("Tenant")
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

    product = relationship("SecondHandProduct", back_populates="images")
