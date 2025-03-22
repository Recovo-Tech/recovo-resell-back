# app/models/discount.py

from sqlalchemy import Column, Integer, String, Float, Boolean
from app.config.db_config import Base


class Discount(Base):
    __tablename__ = "discounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    discount_type = Column(String(20), nullable=False)
    value = Column(Float, nullable=False)
    min_purchase = Column(Float, nullable=True)
    active = Column(Boolean, default=True)
