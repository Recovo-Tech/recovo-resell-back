from enum import Enum as PyEnum

from sqlalchemy import Column, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.config.db_config import Base


class CartStatus(PyEnum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )  # Changed from Integer to UUID
    status = Column(SQLEnum(CartStatus), nullable=False, default=CartStatus.active)
    discount_id = Column(Integer, ForeignKey("discounts.id"), nullable=True)

    # Relationships
    tenant = relationship("Tenant")
    user = relationship("User", back_populates="carts")
    items = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )
    discount = relationship("Discount")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")
