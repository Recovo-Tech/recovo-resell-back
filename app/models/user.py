from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship

from app.config.db_config import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    username = Column(
        String(50), nullable=False
    )  # Removed unique=True since usernames are unique per tenant
    email = Column(
        String(100), nullable=False
    )  # Removed unique=True since emails are unique per tenant
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default="client")  # 'admin' or 'client'

    # Relationships
    tenant = relationship("Tenant")
    carts = relationship("Cart", back_populates="user")
    second_hand_products = relationship("SecondHandProduct", back_populates="seller")
