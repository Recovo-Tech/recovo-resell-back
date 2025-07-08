# app/repositories/second_hand_product.py
import uuid
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.product import SecondHandProduct
from app.repositories.base import BaseRepository


class SecondHandProductRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, SecondHandProduct)

    def get_by_id_and_tenant(
        self, product_id: int, tenant_id: uuid.UUID
    ) -> Optional[SecondHandProduct]:
        """Get a product by its ID, ensuring it belongs to the correct tenant."""
        return (
            self.db.query(self.model)
            .filter(
                and_(
                    self.model.id == product_id,
                    self.model.tenant_id == tenant_id,
                )
            )
            .first()
        )

    def get_by_id_and_user_and_tenant(
        self, product_id: int, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[SecondHandProduct]:
        """Get a product by ID, ensuring it belongs to the correct user and tenant."""
        return (
            self.db.query(self.model)
            .filter(
                and_(
                    self.model.id == product_id,
                    self.model.seller_id == user_id,
                    self.model.tenant_id == tenant_id,
                )
            )
            .first()
        )

    def get_user_products(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[SecondHandProduct]:
        """Get all second-hand products for a specific user within their tenant."""
        return (
            self.db.query(self.model)
            .filter(
                and_(
                    self.model.seller_id == user_id,
                    self.model.tenant_id == tenant_id,
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_approved_products(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[SecondHandProduct]:
        """Get all approved and verified products for public listing within a tenant."""
        return (
            self.db.query(self.model)
            .filter(
                and_(
                    self.model.is_approved == True,
                    self.model.is_verified == True,
                    self.model.tenant_id == tenant_id,
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_not_approved_products(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[SecondHandProduct]:
        """Get all not approved  for public listing within a tenant."""
        return (
            self.db.query(self.model)
            .filter(
                and_(
                    self.model.is_approved == False,
                    self.model.tenant_id == tenant_id,
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search(
        self,
        tenant_id: uuid.UUID,
        query: str = None,
        condition: str = None,
        size: str = None,
        color: str = None,
        min_price: float = None,
        max_price: float = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SecondHandProduct]:
        """Search approved second-hand products with filters within a tenant."""
        db_query = self.db.query(self.model).filter(
            and_(
                self.model.is_approved == True,
                self.model.is_verified == True,
                self.model.tenant_id == tenant_id,
            )
        )

        if query:
            db_query = db_query.filter(self.model.name.ilike(f"%{query}%"))
        if condition:
            db_query = db_query.filter(self.model.condition == condition)
        if size:
            db_query = db_query.filter(self.model.size == size)
        if color:
            db_query = db_query.filter(self.model.color == color)
        if min_price is not None:
            db_query = db_query.filter(self.model.price >= min_price)
        if max_price is not None:
            db_query = db_query.filter(self.model.price <= max_price)

        return db_query.offset(skip).limit(limit).all()
