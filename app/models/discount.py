# app/models/discount.py

from sqlalchemy import Boolean, Column, Float, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.config.db_config import Base


class Discount(Base):
    __tablename__ = "discounts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    discount_type = Column(String(20), nullable=False)
    value = Column(Float, nullable=False)
    min_purchase = Column(Float, nullable=True)
    active = Column(Boolean, default=True)

    # Relationships
    tenant = relationship("Tenant")
