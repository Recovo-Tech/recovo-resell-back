from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.config.db_config import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)

    carts = relationship("Cart", back_populates="user")
